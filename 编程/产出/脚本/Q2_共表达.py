# -*- coding: utf-8 -*-
"""Q2 共表达图 + 感官维度 Top-3 + 稳定性（M2 · TM2-01 · 编程）

本程序及代码是在人工智能工具辅助下完成的。
AI 工具名称：DeepSeek Harness；版本/型号：deepseek-flash；
开发机构/公司：深度求索（DeepSeek）；版本发布日期：2026-10-24（本次运行所用版本）。

唯一入口：在仓库根目录执行
    python 编程/产出/脚本/Q2_共表达.py

口径来源（G-Q2 门冻结，不得回调）：
    建模/产出/方案-M2.md（门材料，台账 R21）
    审阅/规划/M2草案.md v3 §3（验收标准）
输入只读：数据/A/1.csv、数据/A/2.csv、数据/A/4.csv、数据/A/8.xlsx。
随机源固定：bootstrap 种子 20261024、B=200、重采样单元 250 个 beer 行。

本脚本一次跑完：
    1. 建 226 节点共表达图（τ=0.30，边权 |rho|）并出结构统计；
    2. 算 s_direct（Spearman）、s_graph（邻域 |rho| 加权均值）、score（λ=0.70）；
    3. 选 50 维 Top-3；
    4. λ=0 与 λ=0.70 的逐维 Jaccard 对照；
    5. bootstrap 稳定性（甲，B=200）→ boot_freq1..3；
    6. 50 维品类映射 + 化学品类一致性；
    7. GBM 全局对照、聚合列相关性、稳健性检查（T1/T2/T3）；
    8. 行为测试 + 数值审计；
    9. 4 张图。
任何门内参数被改动、候选池/对齐表/维数不符、行为测试失败，均以非零退出码停机。
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

# ----------------------------------------------------------------------------
# 0. 路径与冻结参数
# ----------------------------------------------------------------------------

SCRIPT_PATH = Path(__file__).resolve()
ROOT = Path(os.environ.get("MMC_ROOT", SCRIPT_PATH.parents[3])).resolve()
DATA_DIR = ROOT / "数据" / "A"
OUT_DIR = ROOT / "编程" / "产出"
FIG_DIR = ROOT / "图集" / "M2"
POOL_PATH = ROOT / "审阅" / "规划" / "T0-Q2候选池.csv"
ALIGN_PATH = ROOT / "建模" / "产出" / "化合物名称对齐-M1.csv"
M2_PLAN_PATH = ROOT / "建模" / "产出" / "方案-M2.md"

TAU = 0.30              # 边阈值（冻结，R21 / B19）
LAMBDA = 0.70           # 图项权重（预注册 2026-10-24，R21 / B21）
B_BOOT = 200            # bootstrap 次数（冻结，R21 / B22）
SEED = 20261024         # 唯一随机种子（冻结，R21 / B22）
N_EXPECT_NODES = 226    # 候选池节点数（冻结，B20）
N_EXPECT_DIMS = 50      # 4.csv 感官维度数
N_EXPECT_BEER = 250     # 重采样单元（beer 行）
N_EXPECT_EDGES = 3758   # τ=0.30 下的边数（门内实测，B20；用于一致性断言）
NONCOMP_LABELS = {"Spices", "Internal standard solution"}
AGG_FIELDS = ["esters_sum", "aroma_hops_sum", "acids_sum", "sulfur_sum", "kcalperc"]
AGG_LABELS = {
    "esters_sum": "Total ester compounds",
    "aroma_hops_sum": "Total hop aroma compounds",
    "acids_sum": "Total acids",
    "sulfur_sum": "Total sulfur compounds",
    "kcalperc": "Caloric value",
}
EXCLUDED_NODES = [
    "Total ester compounds",
    "Total hop aroma compounds",
    "Total acids",
    "Total sulfur compounds",
    "Caloric value",
]
META_COLS = ("beer", "beer_id", "tasting_category_fine")
FLOAT_FMT = "%.10f"


def say(msg: str) -> None:
    print(msg, flush=True)


def stop(msg: str, code: int = 2) -> None:
    """触发条款命中：立即停机上报（不修改任何口径）。"""
    print("【停机上报】" + msg, file=sys.stderr, flush=True)
    sys.exit(code)


# ----------------------------------------------------------------------------
# 1. 读入与门内一致性断言
# ----------------------------------------------------------------------------

def load_inputs() -> dict:
    d1 = pd.read_csv(DATA_DIR / "1.csv", encoding="utf-8-sig")
    d2 = pd.read_csv(DATA_DIR / "2.csv", encoding="utf-8-sig", index_col=0)
    d4 = pd.read_csv(DATA_DIR / "4.csv", encoding="utf-8-sig")
    pool = pd.read_csv(POOL_PATH, encoding="utf-8-sig")
    align = pd.read_csv(ALIGN_PATH, encoding="utf-8-sig")
    xbook = pd.ExcelFile(DATA_DIR / "8.xlsx")
    sens_names = xbook.parse("Sensory names", header=0)
    sens_thr = xbook.parse("Sensory thresholds", header=0)
    mdi_raw = pd.read_excel(DATA_DIR / "8.xlsx", sheet_name="GBM importance MDI", header=None)

    # --- 任务书 §⑥ 触发条款 1：候选池 226 且与 2.csv 对得上 ---
    if len(pool) != N_EXPECT_NODES:
        stop(f"候选池行数 {len(pool)} != {N_EXPECT_NODES}")
    if pool["2csv节点名"].duplicated().any():
        stop("候选池存在重复节点名")
    comp = pool["2csv节点名"].tolist()
    missing = [c for c in comp if c not in d2.index]
    if missing:
        stop(f"候选池节点不在 2.csv：{missing[:5]}")
    not_in_pool = [c for c in d2.index if c not in set(comp)]
    if sorted(not_in_pool) != sorted(EXCLUDED_NODES):
        stop(f"2.csv 剔除项与口径不符：{not_in_pool}")

    # --- 2.csv 结构 ---
    if d2.shape != (231, 231):
        stop(f"2.csv 形状 {d2.shape} != (231, 231)")
    if not np.allclose(d2.values, d2.values.T, atol=0, rtol=0):
        stop("2.csv 不对称")
    if not np.allclose(np.diag(d2.values), 1.0):
        stop("2.csv 对角不为 1")
    if int(d2.isna().sum().sum()) != 0:
        stop("2.csv 含缺失")

    # --- 4.csv 感官维度 = 50 ---
    dims = [c for c in d4.columns if c not in META_COLS]
    if len(dims) != N_EXPECT_DIMS:
        stop(f"4.csv 感官列数 {len(dims)} != {N_EXPECT_DIMS}")
    if d4.shape[0] != N_EXPECT_BEER or d1.shape[0] != N_EXPECT_BEER:
        stop(f"样本行数 {d1.shape[0]}/{d4.shape[0]} != {N_EXPECT_BEER}")
    if d1["beer"].tolist() != d4["beer"].tolist():
        stop("1.csv 与 4.csv 的 beer 行序不一致，无法按行重采样")
    if d4[dims].isna().any().any():
        stop("4.csv 感官维度含缺失")

    # --- M1 对齐表 226/226 ---
    features = [c for c in d1.columns if c not in META_COLS]
    if len(features) != 231:
        stop(f"1.csv 特征列数 {len(features)} != 231")
    if set(align["2csv节点名"]) != set(d2.index):
        stop("M1 对齐表未覆盖 2.csv 全部 231 节点")
    if set(align["1csv字段"]) != set(features):
        stop("M1 对齐表未覆盖 1.csv 全部 231 特征")
    fmap = dict(zip(align["2csv节点名"], align["1csv字段"]))
    fields = [fmap[c] for c in comp]
    if len(set(fields)) != N_EXPECT_NODES:
        stop("候选池节点映射到 1.csv 字段后不唯一")

    # --- 品类映射来源 ---
    if "Category" not in sens_names.columns or "R_name" not in sens_names.columns:
        stop("8.xlsx/Sensory names 缺 R_name 或 Category 列")
    if "field_name_R" not in sens_thr.columns or "origin_paper" not in sens_thr.columns:
        stop("8.xlsx/Sensory thresholds 缺 field_name_R 或 origin_paper 列")
    thr_r = sens_thr["field_name_R"].tolist()
    if len(thr_r) != len(set(thr_r)):
        stop("Sensory thresholds 的 field_name_R 有重复")
    miss_thr = [f for f in fields if f not in set(thr_r)]
    if miss_thr:
        stop(f"Sensory thresholds 未覆盖候选池字段：{miss_thr[:5]}")

    # --- GBM MDI：header=None 232 行，首行占位 ---
    if mdi_raw.shape != (232, 2):
        stop(f"GBM importance MDI 原始形状 {mdi_raw.shape} != (232, 2)")
    mdi = mdi_raw.iloc[1:].copy()
    mdi.columns = ["importance", "field"]
    if len(mdi) != 231 or set(mdi["field"]) != set(features):
        stop("GBM importance MDI 去占位后不是 231 个 1.csv 特征")

    say(f"读入完成：1.csv {d1.shape}，2.csv {d2.shape}，4.csv {d4.shape}，"
        f"候选池 {len(comp)}，维度 {len(dims)}")

    return {
        "d1": d1,
        "d2": d2,
        "d4": d4,
        "pool": pool,
        "align": align,
        "fields": fields,
        "comp": comp,
        "dims": dims,
        "features": features,
        "fmap": fmap,
        "sens_names": sens_names,
        "sens_thr": sens_thr,
        "mdi": mdi,
    }


# ----------------------------------------------------------------------------
# 2. 共表达图（τ 裁剪；边权 |rho|）
# ----------------------------------------------------------------------------

def build_graph(rho: np.ndarray, tau: float) -> tuple[np.ndarray, dict]:
    """无向简单图：i≠j 且 |rho_ij| >= tau 连边，边权 = |rho_ij|。"""
    n = rho.shape[0]
    absr = np.abs(rho)
    w = np.where(absr >= tau, absr, 0.0)
    np.fill_diagonal(w, 0.0)
    iu = np.triu_indices(n, 1)
    edges = int((w[iu] > 0).sum())
    deg = (w > 0).sum(axis=1)
    adj = csr_matrix((w > 0).astype(np.int8))
    n_comp, labels = connected_components(adj, directed=False)
    sizes = np.bincount(labels)
    stats = {
        "nodes": n,
        "edges": edges,
        "pos_edges": int((rho[iu] >= tau).sum()),
        "neg_edges": int((rho[iu] <= -tau).sum()),
        "density": edges / (n * (n - 1) / 2),
        "mean_degree": float(deg.mean()),
        "isolated": int((deg == 0).sum()),
        "components": int(n_comp),
        "largest_component": int(sizes.max()),
        "degree_max": int(deg.max()),
    }
    return w, stats


# ----------------------------------------------------------------------------
# 3. 两层打分
# ----------------------------------------------------------------------------

def direct_scores(d1: pd.DataFrame, d4: pd.DataFrame, fields: list[str], dims: list[str]) -> np.ndarray:
    """s_direct(c,d)=|Spearman(1.csv[c], 4.csv[d])|，按列内可用样本 pairwise。"""
    frame = pd.concat([d1[fields], d4[dims]], axis=1)
    corr = frame.corr(method="spearman")
    n = len(fields)
    s = np.abs(corr.values[:n, n:])
    return np.clip(s, 0.0, 1.0)


def graph_smooth(s_direct: np.ndarray, w: np.ndarray) -> np.ndarray:
    """s_graph：邻域 N(c) 内 s_direct 按边权 |rho| 加权均值。

    - 排除自身（w 对角已置 0）；
    - 邻居 s_direct 为 NA 时从分子分母同时剔除（即重归一化）；
    - 无有效邻居（孤立点或邻居全 NA）时回退为 s_direct。
    """
    valid = np.isfinite(s_direct)
    filled = np.where(valid, s_direct, 0.0)
    num = w @ filled
    den = w @ valid.astype(float)
    out = np.full(s_direct.shape, np.nan)
    ok = den > 0
    out[ok] = num[ok] / den[ok]
    fallback = ~np.isfinite(out)
    out[fallback] = s_direct[fallback]
    return out


def compose_score(s_direct: np.ndarray, s_graph: np.ndarray, lam: float) -> np.ndarray:
    """score = (1-lambda) * s_direct + lambda * s_graph。"""
    return (1.0 - lam) * s_direct + lam * s_graph


# ----------------------------------------------------------------------------
# 4. Top-3 选取（并列按 2csv 节点名 ASCII 升序）
# ----------------------------------------------------------------------------

def ascii_rank(comp: list[str]) -> np.ndarray:
    order = sorted(range(len(comp)), key=lambda i: comp[i].encode("utf-8"))
    rank = np.empty(len(comp), dtype=int)
    for r, i in enumerate(order):
        rank[i] = r
    return rank


def top3_index(score: np.ndarray, name_rank: np.ndarray) -> np.ndarray:
    """每个维度取 score 前三；降序，并列按节点名 ASCII 升序；NaN 视为最小。"""
    out = np.empty((score.shape[1], 3), dtype=int)
    for j in range(score.shape[1]):
        col = score[:, j]
        col = np.where(np.isfinite(col), col, -np.inf)
        out[j] = np.lexsort((name_rank, -col))[:3]
    return out


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    sa, sb = set(a.tolist()), set(b.tolist())
    return len(sa & sb) / len(sa | sb)


# ----------------------------------------------------------------------------
# 5. bootstrap 稳定性（甲：重采样 beer 行，B=200，图固定）
# ----------------------------------------------------------------------------

def bootstrap_freq(d1: pd.DataFrame, d4: pd.DataFrame, fields: list[str], dims: list[str],
                   w: np.ndarray, name_rank: np.ndarray, top_main: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n_beer = d1.shape[0]
    frame = pd.concat([d1[fields], d4[dims]], axis=1)
    rng = np.random.default_rng(SEED)
    boot_rows = rng.integers(0, n_beer, size=(B_BOOT, n_beer))
    freq = np.zeros((len(dims), 3))
    for b in range(B_BOOT):
        sub = frame.iloc[boot_rows[b]]
        corr = sub.corr(method="spearman")
        n = len(fields)
        s_b = np.clip(np.abs(corr.values[:n, n:]), 0.0, 1.0)
        sg_b = graph_smooth(s_b, w)
        tb = top3_index(compose_score(s_b, sg_b, LAMBDA), name_rank)
        for k in range(3):
            freq[:, k] += (tb == top_main[:, k:k + 1]).any(axis=1)
        if (b + 1) % 50 == 0:
            say(f"  bootstrap {b + 1}/{B_BOOT}")
    return freq / B_BOOT, boot_rows


# ----------------------------------------------------------------------------
# 6. 维度品类映射 + 化学品类一致性
# ----------------------------------------------------------------------------

def build_dim_map(sens_names: pd.DataFrame, dims: list[str]) -> pd.DataFrame:
    rows = []
    for d in dims:
        hit = sens_names.index[sens_names["R_name"] == d].tolist()
        if len(hit) != 1:
            stop(f"维度 {d} 在 Sensory names 命中 {len(hit)} 行（要求唯一）")
        i = hit[0]
        cat = sens_names.loc[i, "Category"]
        rows.append({
            "dim": d,
            "R_name": sens_names.loc[i, "R_name"],
            "Category": cat,  # NaN 原样保留，to_csv 写空串
            "判定来源行号": int(i) + 2,  # 表头为 Excel 第 1 行
            "是否可比": "否" if pd.isna(cat) else "是",
        })
    return pd.DataFrame(rows, columns=["dim", "R_name", "Category", "判定来源行号", "是否可比"])


def build_compound_origin(sens_thr: pd.DataFrame, comp: list[str], fmap: dict) -> dict:
    thr_idx = {f: i for i, f in enumerate(sens_thr["field_name_R"])}
    out = {}
    for c in comp:
        f = fmap[c]
        if f not in thr_idx:
            stop(f"化合物 {c} 的字段 {f} 不在 Sensory thresholds")
        i = thr_idx[f]
        out[c] = {
            "field": f,
            "origin_paper": sens_thr.loc[i, "origin_paper"],
            "threshold_row": int(i) + 2,
        }
    return out


def consistency_table(comp: list[str], dims: list[str], top_main: np.ndarray,
                      dim_map: pd.DataFrame, origin: dict) -> pd.DataFrame:
    cat_of = dict(zip(dim_map["dim"], dim_map["Category"]))
    recs = []
    for j, d in enumerate(dims):
        cat = cat_of[d]
        for k in range(3):
            c = comp[top_main[j, k]]
            op = origin[c]["origin_paper"]
            if pd.isna(cat) or pd.isna(op) or (isinstance(op, str) and op in NONCOMP_LABELS):
                verdict = "不可比"
                reason = ("维度 Category 为 NaN" if pd.isna(cat)
                          else f"化合物 origin_paper={op}" if not pd.isna(op)
                          else "化合物 origin_paper 为 NaN")
            elif op == cat:
                verdict, reason = "一致", ""
            else:
                verdict, reason = "不一致", ""
            recs.append({
                "dim": d,
                "rank": k + 1,
                "compound": c,
                "1csv字段": origin[c]["field"],
                "origin_paper": "" if pd.isna(op) else op,
                "dim_Category": cat,
                "判定": verdict,
                "不可比原因": reason,
                "计入分母": "否" if verdict == "不可比" else "是",
                "阈值表行号": origin[c]["threshold_row"],
            })
    return pd.DataFrame(recs)


# ----------------------------------------------------------------------------
# 7. 行为测试（意图级，极小用例）
# ----------------------------------------------------------------------------

def run_behavior_tests(w: np.ndarray, rho: np.ndarray, s_direct: np.ndarray,
                       s_graph: np.ndarray, dims: list[str], dim_map: pd.DataFrame,
                       comp: list[str], top_main: np.ndarray) -> list[dict]:
    tests = []

    def rec(name, expected, actual, ok, note=""):
        tests.append({
            "name": name,
            "expected": str(expected),
            "actual": str(actual),
            "ok": bool(ok),
            "note": note,
        })

    # T1 Jaccard 定义：{a,b,c} vs {b,c,d} -> 2/4
    rec("Jaccard 定义", "0.5", jaccard(np.array([0, 1, 2]), np.array([1, 2, 3])),
        abs(jaccard(np.array([0, 1, 2]), np.array([1, 2, 3])) - 0.5) < 1e-12)

    # T2 邻域加权 + NA 邻居重归一：节点 0 的两个邻居一个值 0.8、一个 NA -> 0.8
    s_toy = np.array([[0.0], [0.8], [np.nan]])
    w_toy = np.zeros((3, 3))
    w_toy[0, 1] = w_toy[1, 0] = 0.5
    w_toy[0, 2] = w_toy[2, 0] = 0.3
    g_toy = graph_smooth(s_toy, w_toy)
    rec("NA 邻居剔除后重归一", "[0.8, 0.0, 0.0]", np.round(g_toy.ravel(), 12).tolist(),
        np.allclose(g_toy.ravel(), [0.8, 0.0, 0.0]))

    # T3 孤立点回退 s_direct
    w_iso = np.zeros((3, 3))
    g_iso = graph_smooth(s_toy, w_iso)
    rec("孤立点回退 s_direct", "[0.0, 0.8, NaN]", np.round(g_iso.ravel(), 12).tolist(),
        np.allclose(g_iso.ravel()[:2], [0.0, 0.8]) and np.isnan(g_iso.ravel()[2]))

    # T4 lambda=0 等价纯 s_direct；lambda=1 等价纯 s_graph
    score0 = compose_score(s_direct, s_graph, 0.0)
    score1 = compose_score(s_direct, s_graph, 1.0)
    rec("λ=0 退化为 s_direct", "全等", bool(np.allclose(score0, s_direct, equal_nan=True)),
        np.allclose(score0, s_direct, equal_nan=True))
    rec("λ=1 退化为 s_graph", "全等", bool(np.allclose(score1, s_graph, equal_nan=True)),
        np.allclose(score1, s_graph, equal_nan=True))

    # T5 tau 增大边数不增；tau=0 全连接
    e = []
    for tau in (0.0, 0.25, 0.30, 0.35, 0.60):
        _, st = build_graph(rho, tau)
        e.append(st["edges"])
    rec("τ 增大边数单调不增", "递减序列", e, all(e[i] >= e[i + 1] for i in range(len(e) - 1)))
    rec("τ=0 为完全图", str(len(comp) * (len(comp) - 1) // 2), e[0], e[0] == len(comp) * (len(comp) - 1) // 2)

    # T6 并列按名字 ASCII 升序（构造并列分）
    names = comp[:6]
    rank6 = np.array([sorted(names, key=lambda x: x.encode("utf-8")).index(x) for x in names])
    score_tie = np.array([[0.5], [0.5], [0.5], [0.1], [0.1], [0.1]])
    t = top3_index(score_tie, rank6).ravel().tolist()
    expect = [names.index(x) for x in sorted(names, key=lambda x: x.encode("utf-8"))[:3]]
    rec("并列按 ASCII 升序", expect, t, t == expect)

    # T7 候选池合规（硬断言，失败即非零退出）
    flat = {comp[i] for i in top_main.ravel()}
    ok_pool = flat <= set(comp) and not (flat & set(EXCLUDED_NODES))
    rec("Top-3 全部在 226 候选池且无聚合列", "是", ok_pool, ok_pool)

    # T8 维度映射 50/50 且 NaN 恰为 3 维指定集合
    nan_dims = set(dim_map.loc[dim_map["是否可比"] == "否", "dim"])
    rec("维度映射 50 行且 NaN 三维", "{aftertaste, body, overall}",
        sorted(nan_dims), nan_dims == {"aftertaste", "body", "overall"} and len(dim_map) == 50)

    # T9 bootstrap 种子可复现
    r1 = np.random.default_rng(SEED).integers(0, 250, size=250)
    r2 = np.random.default_rng(SEED).integers(0, 250, size=250)
    rec("随机源固定可复现", "两序列相同", bool(np.array_equal(r1, r2)), np.array_equal(r1, r2))

    # T10 Top-3 三名互不相同
    uniq = all(len(set(top_main[j].tolist())) == 3 for j in range(len(dims)))
    rec("每维 Top-3 互不相同", "是", uniq, uniq)

    return tests


# ----------------------------------------------------------------------------
# 8. 出图
# ----------------------------------------------------------------------------

def setup_font() -> str:
    available = {f.name for f in fm.fontManager.ttflist}
    for name in ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "WenQuanYi Zen Hei", "DejaVu Sans"]:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    plt.rcParams["axes.unicode_minus"] = False
    return "DejaVu Sans"


def make_figures(w: np.ndarray, comp: list[str], dims: list[str], origin: dict,
                 freq: np.ndarray, jac: np.ndarray, inter: np.ndarray, robust: pd.DataFrame) -> list[str]:
    font = setup_font()
    say(f"作图字体：{font}")
    paths = []

    # ---- 图M2-01 共表达网络 ----
    g = nx.Graph()
    g.add_nodes_from(range(len(comp)))
    iu = np.triu_indices(len(comp), 1)
    for a, b in zip(iu[0], iu[1]):
        if w[a, b] > 0:
            g.add_edge(int(a), int(b), weight=float(w[a, b]))
    deg = np.array([g.degree(i) for i in range(len(comp))])
    main_nodes = [i for i in range(len(comp)) if deg[i] > 0]
    iso_nodes = [i for i in range(len(comp)) if deg[i] == 0]
    pos_main = nx.kamada_kawai_layout(g.subgraph(main_nodes))
    pos = {i: np.asarray(pos_main[i], dtype=float) for i in main_nodes}
    if main_nodes:
        xy = np.array([pos[i] for i in main_nodes])
        center = xy.mean(axis=0)
        radius = 1.12 * float(np.max(np.linalg.norm(xy - center, axis=1)))
        for k, i in enumerate(sorted(iso_nodes)):
            ang = np.deg2rad(200 + 40 * k)
            pos[i] = center + radius * np.array([np.cos(ang), np.sin(ang)])
    cats = [str(origin[c]["origin_paper"]) for c in comp]
    cat_order = [x for x in ["Malt", "Hops", "Yeast", "Others", "Wild flora", "Spices",
                             "Internal standard solution"] if x in set(cats)]
    palette = dict(zip(cat_order, plt.get_cmap("tab10").colors[:len(cat_order)]))
    node_colors = [palette[c] for c in cats]
    node_sizes = 10 + 0.8 * deg

    fig, ax = plt.subplots(figsize=(9.6, 6.6))
    nx.draw_networkx_edges(g, pos, ax=ax, edge_color="#8a939e", alpha=0.10, width=0.3)
    nx.draw_networkx_nodes(g, pos, ax=ax, node_size=node_sizes, node_color=node_colors,
                           linewidths=0.3, edgecolors="white")
    handles = [plt.Line2D([], [], marker="o", linestyle="", markersize=7,
                          markerfacecolor=palette[c], markeredgecolor="white", label=c)
               for c in cat_order]
    ax.legend(handles=handles, loc="lower left", fontsize=7, frameon=False, title="化合物来源品类",
              title_fontsize=7)
    ax.set_axis_off()
    fig.tight_layout()
    p = FIG_DIR / "图M2-01-共表达网络.png"
    fig.savefig(p, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    paths.append(p.relative_to(ROOT).as_posix())

    # ---- 图M2-02 稳定性频率 ----
    fig, ax = plt.subplots(figsize=(12.5, 3.4))
    im = ax.imshow(freq.T, aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_yticks([0, 1, 2], ["Top1", "Top2", "Top3"], fontsize=9)
    ax.set_xticks(range(len(dims)), dims, rotation=90, fontsize=6.5)
    ax.set_xlabel("感官维度", fontsize=9)
    ax.set_ylabel("名次", fontsize=9)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("Bootstrap 入选频率", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    fig.tight_layout()
    p = FIG_DIR / "图M2-02-稳定性频率.png"
    fig.savefig(p, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    paths.append(p.relative_to(ROOT).as_posix())

    # ---- 图M2-03 λ 对照 Jaccard ----
    fig, ax = plt.subplots(figsize=(12.5, 4.0))
    colors = {0: "#d94b4b", 1: "#e8a33d", 2: "#4c9f70", 3: "#3b6ea5"}
    xs = np.arange(len(dims))
    ax.bar(xs, jac, color=[colors[int(v)] for v in inter], width=0.75)
    ax.axhline(float(jac.mean()), color="#333333", linestyle="--", linewidth=1.0,
               label=f"均值 {jac.mean():.3f}")
    ax.set_xticks(xs, dims, rotation=90, fontsize=6.5)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("感官维度", fontsize=9)
    ax.set_ylabel("Jaccard 系数 J_d", fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k]) for k in (0, 1, 2, 3)]
    ax.legend(handles + [plt.Line2D([0], [0], color="#333333", linestyle="--")],
              ["重合 0 个", "重合 1 个", "重合 2 个", "重合 3 个", "均值"],
              fontsize=7, frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    fig.tight_layout()
    p = FIG_DIR / "图M2-03-lambda对照Jaccard.png"
    fig.savefig(p, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    paths.append(p.relative_to(ROOT).as_posix())

    # ---- 图M2-04 稳健性检查 ----
    labels = robust["方案"].tolist()
    vals = robust["平均Jaccard"].astype(float).tolist()
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ys = np.arange(len(labels))
    ax.barh(ys, vals, color="#4c78a8", height=0.62)
    for y, v in zip(ys, vals):
        ax.text(v + 0.015, y, f"{v:.3f}", va="center", fontsize=8)
    ax.set_yticks(ys, labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.08)
    ax.set_xlabel("与主口径 Top-3 的平均 Jaccard", fontsize=9)
    fig.tight_layout()
    p = FIG_DIR / "图M2-04-稳健性检查.png"
    fig.savefig(p, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    paths.append(p.relative_to(ROOT).as_posix())

    return paths


# ----------------------------------------------------------------------------
# 9. 主流程
# ----------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    dat = load_inputs()
    d1, d2, d4 = dat["d1"], dat["d2"], dat["d4"]
    comp, dims, fields = dat["comp"], dat["dims"], dat["fields"]
    fmap = dat["fmap"]
    n = len(comp)

    # --- 图 ---
    rho = d2.loc[comp, comp].values.astype(float)
    w, gstats = build_graph(rho, TAU)
    if gstats["edges"] != N_EXPECT_EDGES:
        stop(f"τ={TAU} 实测边数 {gstats['edges']} != 门内 {N_EXPECT_EDGES}")
    say(f"共表达图：节点 {gstats['nodes']}，边 {gstats['edges']}"
        f"（正 {gstats['pos_edges']} / 负 {gstats['neg_edges']}），"
        f"平均度 {gstats['mean_degree']:.2f}，连通分量 {gstats['components']}")

    # --- 两层打分与 Top-3 ---
    s_direct = direct_scores(d1, d4, fields, dims)
    s_graph = graph_smooth(s_direct, w)
    score_main = compose_score(s_direct, s_graph, LAMBDA)
    name_rank = ascii_rank(comp)
    top_main = top3_index(score_main, name_rank)
    top_l0 = top3_index(compose_score(s_direct, s_graph, 0.0), name_rank)

    # --- λ 双设置 Jaccard ---
    jac = np.array([jaccard(top_l0[j], top_main[j]) for j in range(len(dims))])
    inter = np.array([len(set(top_l0[j].tolist()) & set(top_main[j].tolist())) for j in range(len(dims))])
    lam_rows = []
    for j, d in enumerate(dims):
        rec = {"dim": d, "jaccard": float(jac[j]), "overlap": int(inter[j])}
        for k in range(3):
            rec[f"lambda0_rank{k + 1}"] = comp[top_l0[j, k]]
        for k in range(3):
            rec[f"lambda070_rank{k + 1}"] = comp[top_main[j, k]]
        lam_rows.append(rec)
    lam_df = pd.DataFrame(lam_rows)
    say(f"λ=0 vs 0.70 的 Top-3 平均 Jaccard = {jac.mean():.6f}"
        f"（中位 {np.median(jac):.6f}，min {jac.min():.6f}，max {jac.max():.6f}）")

    # --- bootstrap 稳定性 ---
    freq, boot_rows = bootstrap_freq(d1, d4, fields, dims, w, name_rank, top_main)
    say(f"bootstrap 完成：rank1/2/3 平均入选频率 "
        f"{freq.mean(axis=0)[0]:.4f}/{freq.mean(axis=0)[1]:.4f}/{freq.mean(axis=0)[2]:.4f}")

    # --- 品类映射与一致性 ---
    dim_map = build_dim_map(dat["sens_names"], dims)
    origin = build_compound_origin(dat["sens_thr"], comp, fmap)
    cons = consistency_table(comp, dims, top_main, dim_map, origin)
    n_same = int((cons["判定"] == "一致").sum())
    n_diff = int((cons["判定"] == "不一致").sum())
    n_na = int((cons["判定"] == "不可比").sum())
    rate = n_same / (n_same + n_diff) if (n_same + n_diff) else float("nan")
    say(f"化学品类一致性：一致 {n_same} / 不一致 {n_diff} / 不可比 {n_na}，"
        f"一致率 {rate:.4f}")

    # 独立假设粗基线：Σ_c p_orig(c) * p_dim(c)（仅作解释参考，不作验收指标）
    cats_pool = pd.Series([origin[c]["origin_paper"] for c in comp]).dropna()
    p_orig = cats_pool.value_counts(normalize=True)
    comparable_dims = dim_map.loc[dim_map["是否可比"] == "是", "dim"].tolist()
    dim_cat_series = pd.Series([dim_map.set_index("dim").loc[d, "Category"] for d in comparable_dims])
    p_dim = dim_cat_series.value_counts(normalize=True)
    baseline = float(sum(p_orig.get(k, 0.0) * p_dim.get(k, 0.0) for k in set(p_orig.index) | set(p_dim.index)))

    # --- GBM 全局对照 ---
    mdi = dat["mdi"]
    covered = {comp[i] for i in top_main.ravel()}
    sel_fields = [fmap[c] for c in sorted(covered)]
    mdi_fields = set(mdi["field"])
    overlap = sum(1 for f in sel_fields if f in mdi_fields)
    share_sel = overlap / len(sel_fields)
    share_mdi = overlap / len(mdi)
    pct = mdi["importance"].rank(pct=True)
    pct_map = dict(zip(mdi["field"], pct))
    mean_pct_sel = float(np.mean([pct_map[f] for f in sel_fields]))
    mean_pct_pool = float(np.mean([pct_map[f] for f in fields]))

    # --- 聚合列相关性 ---
    agg_fields = [f for f in AGG_FIELDS if f in dat["features"]]
    if len(agg_fields) != 5:
        stop("4 个 *_sum 与 kcalperc 未全部出现在 1.csv 特征中")
    frame_agg = pd.concat([d1[agg_fields], d4[dims]], axis=1)
    corr_agg = np.abs(frame_agg.corr(method="spearman").values[:5, 5:])
    top1_score = np.array([np.nanmax(score_main[:, j]) for j in range(len(dims))])
    top1_sd = np.array([s_direct[top_main[j, 0], j] for j in range(len(dims))])
    max_agg = corr_agg.max(axis=0)
    exceed_sd = max_agg > top1_sd
    exceed_score = max_agg > top1_score
    agg_rows = []
    for j, d in enumerate(dims):
        rec = {"dim": d, "top1_compound": comp[top_main[j, 0]],
               "top1_s_direct": float(top1_sd[j]), "top1_score": float(top1_score[j]),
               "max_agg_corr": float(max_agg[j]),
               "是否高于Top1_s_direct": "是" if exceed_sd[j] else "否",
               "是否高于Top1_score": "是" if exceed_score[j] else "否"}
        for i, f in enumerate(agg_fields):
            rec[f"corr_{f}"] = float(corr_agg[i, j])
        agg_rows.append(rec)
    agg_df = pd.DataFrame(agg_rows)

    # --- 稳健性检查（不改主结果） ---
    rob_rows = [{
        "方案": "λ=0（对照）",
        "参数": "score=s_direct",
        "平均Jaccard": float(jac.mean()),
        "中位Jaccard": float(np.median(jac)),
        "全同维数": int(sum(1 for j in range(len(dims)) if jaccard(top_l0[j], top_main[j]) == 1.0)),
        "备注": "λ 双设置对照（验收 3）",
    }]
    for tau in (0.25, 0.35):
        w_t, st_t = build_graph(rho, tau)
        s_t = compose_score(s_direct, graph_smooth(s_direct, w_t), LAMBDA)
        t_t = top3_index(s_t, name_rank)
        jt = np.array([jaccard(t_t[j], top_main[j]) for j in range(len(dims))])
        rob_rows.append({
            "方案": f"T1 τ={tau:.2f}",
            "参数": f"边数 {st_t['edges']}",
            "平均Jaccard": float(jt.mean()),
            "中位Jaccard": float(np.median(jt)),
            "全同维数": int(sum(1 for j in range(len(dims)) if jt[j] == 1.0)),
            "备注": "邻域阈值扰动",
        })
    w_pos = np.where(rho > 0, w, 0.0)
    s_pos = compose_score(s_direct, graph_smooth(s_direct, w_pos), LAMBDA)
    t_pos = top3_index(s_pos, name_rank)
    jp = np.array([jaccard(t_pos[j], top_main[j]) for j in range(len(dims))])
    rob_rows.append({
        "方案": "T2 正边-only",
        "参数": f"边数 {int((w_pos > 0).sum() // 2)}",
        "平均Jaccard": float(jp.mean()),
        "中位Jaccard": float(np.median(jp)),
        "全同维数": int(sum(1 for j in range(len(dims)) if jp[j] == 1.0)),
        "备注": "去掉负边后的敏感性",
    })
    for lam in (0.30, 0.50):
        s_l = compose_score(s_direct, s_graph, lam)
        t_l = top3_index(s_l, name_rank)
        jl = np.array([jaccard(t_l[j], top_main[j]) for j in range(len(dims))])
        rob_rows.append({
            "方案": f"T3 λ={lam:.2f}",
            "参数": "同一张图",
            "平均Jaccard": float(jl.mean()),
            "中位Jaccard": float(np.median(jl)),
            "全同维数": int(sum(1 for j in range(len(dims)) if jl[j] == 1.0)),
            "备注": "图项权重扰动",
        })
    rob_df = pd.DataFrame(rob_rows)

    # --- 非退化性 ---
    rank_corr = []
    for j in range(len(dims)):
        x, y = score_main[:, j], s_direct[:, j]
        m = np.isfinite(x) & np.isfinite(y)
        rank_corr.append(pd.Series(x[m]).corr(pd.Series(y[m]), method="spearman"))
    rank_corr = np.array(rank_corr, dtype=float)
    sd_ratio = float(np.nanmean(np.nanstd(s_graph, axis=0) / np.nanstd(s_direct, axis=0)))

    # --- 行为测试 ---
    tests = run_behavior_tests(w, rho, s_direct, s_graph, dims, dim_map, comp, top_main)
    if not all(t["ok"] for t in tests):
        for t in tests:
            if not t["ok"]:
                print(f"行为测试失败：{t['name']} 期望 {t['expected']} 实际 {t['actual']}",
                      file=sys.stderr)
        stop("行为测试未通过，禁止出结果", code=3)

    # --- 结果表 ---
    top_rows = []
    for j, d in enumerate(dims):
        rec = {"dim": d}
        for k in range(3):
            idx = top_main[j, k]
            rec[f"rank{k + 1}"] = comp[idx]
        for k in range(3):
            idx = top_main[j, k]
            rec[f"score{k + 1}"] = float(score_main[idx, j])
        for k in range(3):
            idx = top_main[j, k]
            rec[f"s_direct{k + 1}"] = float(s_direct[idx, j])
        for k in range(3):
            idx = top_main[j, k]
            rec[f"s_graph{k + 1}"] = float(s_graph[idx, j])
        for k in range(3):
            rec[f"boot_freq{k + 1}"] = float(freq[j, k])
        top_rows.append(rec)
    top_df = pd.DataFrame(top_rows)
    cols = (["dim"] + [f"rank{k}" for k in (1, 2, 3)]
            + [f"score{k}" for k in (1, 2, 3)]
            + [f"s_direct{k}" for k in (1, 2, 3)]
            + [f"s_graph{k}" for k in (1, 2, 3)]
            + [f"boot_freq{k}" for k in (1, 2, 3)])
    top_df = top_df[cols]

    # 验收 1/2 硬断言
    if len(top_df) != N_EXPECT_DIMS:
        stop(f"Top-3 表行数 {len(top_df)} != {N_EXPECT_DIMS}")
    if top_df[["rank1", "rank2", "rank3"]].isna().any().any():
        stop("Top-3 表存在空化合物名")
    if top_df[["rank1", "rank2", "rank3"]].nunique(axis=1).min() != 3:
        stop("某维 Top-3 化合物名重复")
    if top_df.isna().any().any():
        stop("Top-3 表存在 NA")
    if not set(comp[i] for i in top_main.ravel()) <= set(comp):
        stop("Top-3 出现候选池外化合物")
    if set(comp[i] for i in top_main.ravel()) & set(EXCLUDED_NODES):
        stop("Top-3 出现被剔除的聚合列")

    # --- 写盘 ---
    top_path = OUT_DIR / "Q2_top3.csv"
    top_df.to_csv(top_path, index=False, encoding="utf-8", lineterminator="\n", float_format=FLOAT_FMT)
    dim_map.to_csv(OUT_DIR / "Q2_维度品类映射.csv", index=False, encoding="utf-8",
                   lineterminator="\n")
    cons.to_csv(OUT_DIR / "Q2_品类一致性明细.csv", index=False, encoding="utf-8", lineterminator="\n")
    lam_df.to_csv(OUT_DIR / "Q2_lambda对照.csv", index=False, encoding="utf-8",
                  lineterminator="\n", float_format=FLOAT_FMT)
    agg_df.to_csv(OUT_DIR / "Q2_聚合列相关.csv", index=False, encoding="utf-8",
                  lineterminator="\n", float_format=FLOAT_FMT)
    rob_df.to_csv(OUT_DIR / "Q2_稳健性.csv", index=False, encoding="utf-8",
                  lineterminator="\n", float_format=FLOAT_FMT)

    md5 = hashlib.md5(top_path.read_bytes()).hexdigest()

    # --- 图 ---
    figs = make_figures(w, comp, dims, origin, freq, jac, inter, rob_df)

    # --- 核验指标 ---
    na_dims = sorted(dim_map.loc[dim_map["是否可比"] == "否", "dim"].tolist())
    # 不可比化合物：Spices / Internal standard solution / NaN（口径冻结）
    op_of = {c: origin[c]["origin_paper"] for c in comp}
    nc_spices = sorted([c for c in comp if op_of[c] == "Spices"])
    nc_internal = sorted([c for c in comp if op_of[c] == "Internal standard solution"])
    nc_nan = sorted([c for c in comp if pd.isna(op_of[c])])
    nc_comp = sorted(nc_spices + nc_internal + nc_nan)
    neighbor_nonempty = int((w.sum(axis=1) > 0).sum())
    na_pairs = cons.loc[cons["判定"] == "不可比"]
    metrics = [
        ("节点数", gstats["nodes"], "2.csv 的 226 个候选节点"),
        ("边数", gstats["edges"], f"|rho|>={TAU} 的无序对"),
        ("正边数", gstats["pos_edges"], "rho>=τ"),
        ("负边数", gstats["neg_edges"], "rho<=-τ；按 |rho| 计入边权"),
        ("密度", f"{gstats['density']:.6f}", "E/(N(N-1)/2)"),
        ("平均度", f"{gstats['mean_degree']:.4f}", "2E/N"),
        ("孤立点数", gstats["isolated"], "度=0 的节点"),
        ("连通分量数", gstats["components"], "无向连通分量"),
        ("最大连通分量", gstats["largest_component"], "节点数"),
        ("τ", f"{TAU:.2f}", "冻结（R21/B19）"),
        ("λ", f"{LAMBDA:.2f}", "预注册 2026-10-24（R21/B21）"),
        ("B", B_BOOT, "bootstrap 次数（R21/B22）"),
        ("种子", SEED, "numpy default_rng"),
        ("λ=0 与 λ=0.70 的 Top-3 平均 Jaccard", f"{jac.mean():.10f}", "mean_d J_d"),
        ("Jaccard 中位数", f"{np.median(jac):.10f}", ""),
        ("Jaccard 最小值", f"{jac.min():.10f}", ""),
        ("Jaccard 最大值", f"{jac.max():.10f}", ""),
        ("重合 0 个的维数", int((inter == 0).sum()), "λ=0 与 λ=0.70 的 Top-3 交集"),
        ("重合 1 个的维数", int((inter == 1).sum()), ""),
        ("重合 2 个的维数", int((inter == 2).sum()), ""),
        ("重合 3 个的维数", int((inter == 3).sum()), ""),
        ("score 与 s_direct 秩相关均值", f"{np.nanmean(rank_corr):.4f}", "50 维跨化合物 Spearman"),
        ("score 与 s_direct 秩相关最小值", f"{np.nanmin(rank_corr):.4f}", ""),
        ("s_graph/s_direct 标准差比", f"{sd_ratio:.4f}", "50 维平均"),
        ("邻域非空节点数", neighbor_nonempty, "226 节点中 s_graph 可由邻居计算的数量"),
        ("稳定性 rank1 平均入选频率", f"{freq[:, 0].mean():.4f}", "boot_freq1"),
        ("稳定性 rank2 平均入选频率", f"{freq[:, 1].mean():.4f}", "boot_freq2"),
        ("稳定性 rank3 平均入选频率", f"{freq[:, 2].mean():.4f}", "boot_freq3"),
        ("boot_freq>=0.80 的格子数", int((freq >= 0.8).sum()), "共 150 格（50 维 × 3 名次）"),
        ("boot_freq>=0.50 的格子数", int((freq >= 0.5).sum()), ""),
        ("boot_freq<0.50 的格子数", int((freq < 0.5).sum()), ""),
        ("boot_freq 最小值", f"{freq.min():.4f}", ""),
        ("全部 boot_freq<0.20", "否" if (freq < 0.2).any() else "是", "任务书⑥稳定性触发条款"),
        ("品类一致数", n_same, "150 个 (维,化合物) 对"),
        ("品类不一致数", n_diff, ""),
        ("品类不可比数", n_na, ""),
        ("品类一致率", f"{rate:.10f}", "一致/(一致+不一致)"),
        ("不可比维度", "; ".join(na_dims), "Category 为 NaN，不用语义补填"),
        ("不可比化合物（Spices）", len(nc_spices), "; ".join(nc_spices)),
        ("不可比化合物（Internal standard solution）", len(nc_internal), "; ".join(nc_internal)),
        ("不可比化合物（NaN）", len(nc_nan), "; ".join(nc_nan) if nc_nan else "无"),
        ("不可比化合物合计", len(nc_comp), "候选池 226 内"),
        ("不可比明细条数", len(na_pairs), "见 Q2_品类一致性明细.csv"),
        ("独立假设参考基线", f"{baseline:.4f}", "Σ p_origin·p_dim，仅解释用，不作验收指标"),
        ("GBM 去重化合物数", len(sel_fields), "50×3 合并去重"),
        ("GBM 重合数", overlap, "与 MDI 231 化合物的交集"),
        ("GBM 占选中比例", f"{share_sel:.6f}", "重合/去重选中"),
        ("GBM 占 MDI 比例", f"{share_mdi:.6f}", "重合/231"),
        ("GBM 选中平均分位", f"{mean_pct_sel:.4f}", "MDI 全局重要度分位（无逐维信息）"),
        ("GBM 226 池平均分位", f"{mean_pct_pool:.4f}", "同口径对照"),
        ("聚合列高于该维 Top-1（同口径 s_direct）的维数", int(exceed_sd.sum()),
         "聚合 |Spearman| vs 该维 Top-1 的 s_direct1"),
        ("聚合列高于该维 Top-1（融合 score）的维数", int(exceed_score.sum()),
         "图平滑会压低 score1，此口径会高估超出面"),
        ("聚合列相关性最大值", f"{corr_agg.max():.6f}", "|Spearman|"),
    ]
    for i, f in enumerate(agg_fields):
        metrics.append((f"聚合 {AGG_LABELS[f]} 超出维数（s_direct）", int((corr_agg[i] > top1_sd).sum()),
                        f"均值 {corr_agg[i].mean():.4f}，最大 {corr_agg[i].max():.4f}"))
    for _, row in rob_df.iterrows():
        metrics.append((f"稳健性 {row['方案']}", f"{row['平均Jaccard']:.4f}",
                        f"{row['备注']}；{row['参数']}"))
    for t in tests:
        metrics.append((f"行为测试::{t['name']}", "通过" if t["ok"] else "失败",
                        f"期望 {t['expected']}；实际 {t['actual']}"))
    metrics.append(("确定性::Q2_top3.csv md5", md5, "同机重跑应一致"))
    pd.DataFrame(metrics, columns=["指标", "数值", "说明"]).to_csv(
        OUT_DIR / "Q2_核验指标.csv", index=False, encoding="utf-8", lineterminator="\n")

    # --- 参数 JSON ---
    params = {
        "task": "TM2-01",
        "role": "编程",
        "milestone": "M2",
        "version": "1.0",
        "date": "2026-10-24",
        "script": "编程/产出/脚本/Q2_共表达.py",
        "inputs": {
            "chemical_abundance": "数据/A/1.csv",
            "compound_correlation": "数据/A/2.csv",
            "sensory_matrix": "数据/A/4.csv",
            "support_package": "数据/A/8.xlsx",
            "candidate_pool": "审阅/规划/T0-Q2候选池.csv",
            "name_alignment_M1": "建模/产出/化合物名称对齐-M1.csv",
            "frozen_plan": "建模/产出/方案-M2.md",
        },
        "graph": {
            "nodes": N_EXPECT_NODES,
            "node_source": "2.csv 的 231 节点剔除 4 个 Total* 与 Caloric value（口径 β/R15）",
            "edge_rule": "i≠j 且 |rho_ij| >= tau 连边；无向简单图；边权 w_ij=|rho_ij|",
            "tau": TAU,
            "tau_basis": "Bonferroni 临界 0.293754 向上取整（方案-M2 §1，台账 R21/B19）",
            "edge_weight": "|rho_ij|",
            "negative_edges": "负边按 |rho| 计入（边权与 s_direct 都取关联强度）",
            "edges": gstats["edges"],
            "positive_edges": gstats["pos_edges"],
            "negative_edges_count": gstats["neg_edges"],
            "mean_degree": round(gstats["mean_degree"], 4),
            "density": round(gstats["density"], 6),
            "isolated_nodes": gstats["isolated"],
            "components": gstats["components"],
            "largest_component": gstats["largest_component"],
        },
        "scoring": {
            "s_direct": "|Spearman(1.csv[c], 4.csv[d])|，按列内可用样本 pairwise，不插补",
            "s_graph_neighborhood": "N(c) = {j != c : |rho_cj| >= 0.30}",
            "s_graph_weight": "w_cj = |rho_cj|",
            "s_graph_exclude_self": True,
            "s_graph_na_policy": "邻居 s_direct 为 NA 时从分子分母同时剔除（重归一化）",
            "s_graph_fallback": "无有效邻居（孤立点或邻居全 NA）时回退为 s_direct",
            "s_graph": "s_graph(c,d) = sum_{j in N(c)} w_cj * s_direct(j,d) / sum w_cj",
            "lambda": LAMBDA,
            "formula": "score(c,d) = (1 - lambda) * s_direct(c,d) + lambda * s_graph(c,d)",
            "tie_break": "score 降序；并列按 2csv 节点名 ASCII 升序",
            "top_k": 3,
        },
        "lambda_preregistration": {
            "value": LAMBDA,
            "date": "2026-10-24",
            "source": "建模/产出/方案-M2.md §2（G-Q2 门材料，经审阅官验收，台账 R21/B21）",
            "earlier_than_results": "是：lambda=0.70 于 2026-10-24 由 G-Q2 门材料预注册，早于任何最终 Top-3；"
                                    "本 JSON 是脚本对该冻结值的机器可读转录，脚本不参与选择 lambda",
            "basis": [
                "10 维主判据半分试点在 lambda=0.70 达峰；0.60/0.80 分别低 0.0075/0.0088",
                "全 50 维敏感性峰值 0.80，0.70/0.75 分别低 0.0043/0.0001，0.70 在平台内",
                "s_graph 跨化合物 SD 约为 s_direct 的 0.51 倍，raw lambda=0.70 的有效标准化权重约 0.54",
            ],
            "not_degenerate": {
                "score_vs_s_direct_rank_corr_mean": round(float(np.nanmean(rank_corr)), 4),
                "score_vs_s_direct_rank_corr_min": round(float(np.nanmin(rank_corr)), 4),
                "nodes_with_nonempty_neighborhood": neighbor_nonempty,
                "note": "秩相关 <1，图项确实改变排序；lambda>0 且邻域非空节点占多数，图项不恒为 0",
            },
        },
        "stability": {
            "method": "甲（bootstrap）",
            "B": B_BOOT,
            "resample_unit": "250 个 beer 行（有放回）",
            "seed": SEED,
            "rng": "numpy.random.default_rng(20261024)",
            "graph_fixed": "题方 2.csv（tau=0.30），bootstrap 只传播 1.csv/4.csv 的样本抽样不确定性",
            "output": "boot_freq1..3 = 全样本该名次化合物进入该维 Top-3 的频率",
            "reason": "甲直接量化最终排序规则在样本扰动下的稳定性；GBM MDI 为 231x2 全局表、"
                      "GBM SHAP 无感官维度列，均不能直接做逐维排序（方案-M2 §3）",
        },
        "dimension_category_mapping": {
            "source": "数据/A/8.xlsx 的 Sensory names sheet",
            "bridge_key": "R_name（与 4.csv 维度名逐字精确匹配）",
            "category_column": "Category",
            "row_number_rule": "Excel 行号（表头第 1 行，数据从第 2 行起）",
            "matched": "50/50",
            "nan_dimensions": na_dims,
            "nan_policy": "记 Category 留空、是否可比=否；不得用 Category_Paper 或名称含义回填",
            "category_counts": {("NaN" if pd.isna(k) else str(k)): int(v)
                                for k, v in dim_cat_series.value_counts(dropna=False).items()},
        },
        "chemical_category_consistency": {
            "compound_side": "8.xlsx/Sensory thresholds 的 origin_paper",
            "bridge": "经 M1 的 231/231 对齐表（1csv字段 ↔ 2csv节点名）桥接，禁用 chemical_name 直接匹配",
            "rules": {
                "一致": "origin_paper == 该维 Category",
                "不可比": "origin_paper in {Spices, Internal standard solution, NaN} 或该维 Category 为 NaN",
                "不一致": "其余",
            },
            "rate": "一致 / (一致 + 不一致)，分母不含不可比",
            "counts": {"一致": n_same, "不一致": n_diff, "不可比": n_na},
            "rate_value": round(float(rate), 10),
            "noncomparable_dimensions": na_dims,
            "noncomparable_compounds": nc_comp,
            "noncomparable_breakdown": {
                "Spices": nc_spices,
                "Internal standard solution": nc_internal,
                "NaN": nc_nan,
            },
        },
        "gbm_global_comparison": {
            "table": "8.xlsx/GBM importance MDI（header=None 232 行，首行占位；去占位后 231 化合物 × 2 列）",
            "unique_selected_compounds": len(sel_fields),
            "overlap": overlap,
            "share_of_selected": round(float(share_sel), 6),
            "share_of_mdi": round(float(share_mdi), 6),
            "mean_mdi_percentile_selected": round(float(mean_pct_sel), 4),
            "mean_mdi_percentile_pool226": round(float(mean_pct_pool), 4),
            "notice": "仅全局层面；该表无逐维信息，不作逐维对照",
        },
        "aggregate_columns": {
            "columns": AGG_FIELDS,
            "labels": [AGG_LABELS[f] for f in agg_fields],
            "excluded_from_top3": True,
            "dims_exceeding_top1_sdirect": int(exceed_sd.sum()),
            "dims_exceeding_top1_score": int(exceed_score.sum()),
            "comparison_note": "主口径按同度量 |Spearman| 与该维 Top-1 的 s_direct1 比较；"
                               "与融合 score1 比较的结果另列，图平滑会压低 score1 从而高估超出面",
            "max_abs_spearman": round(float(corr_agg.max()), 6),
        },
        "robustness_checks": {
            "T1_tau_0.25": round(float(rob_df.loc[rob_df["方案"] == "T1 τ=0.25", "平均Jaccard"].iloc[0]), 6),
            "T1_tau_0.35": round(float(rob_df.loc[rob_df["方案"] == "T1 τ=0.35", "平均Jaccard"].iloc[0]), 6),
            "T2_positive_only": round(float(rob_df.loc[rob_df["方案"] == "T2 正边-only", "平均Jaccard"].iloc[0]), 6),
            "T3_lambda_0.30": round(float(rob_df.loc[rob_df["方案"] == "T3 λ=0.30", "平均Jaccard"].iloc[0]), 6),
            "T3_lambda_0.50": round(float(rob_df.loc[rob_df["方案"] == "T3 λ=0.50", "平均Jaccard"].iloc[0]), 6),
            "note": "不改主结果，只报与主口径 Top-3 的平均 Jaccard",
        },
        "results": {
            "mean_jaccard_lambda0_vs_lambda_star": round(float(jac.mean()), 10),
            "median_jaccard": round(float(np.median(jac)), 10),
            "jaccard_min": round(float(jac.min()), 10),
            "jaccard_max": round(float(jac.max()), 10),
            "overlap_count_distribution": {
                "0": int((inter == 0).sum()), "1": int((inter == 1).sum()),
                "2": int((inter == 2).sum()), "3": int((inter == 3).sum()),
            },
            "stability_mean_freq": {
                "rank1": round(float(freq[:, 0].mean()), 4),
                "rank2": round(float(freq[:, 1].mean()), 4),
                "rank3": round(float(freq[:, 2].mean()), 4),
            },
            "stability_cells_ge_0.80": int((freq >= 0.8).sum()),
            "stability_cells_ge_0.50": int((freq >= 0.5).sum()),
            "consistency_rate": round(float(rate), 10),
            "lambda_comparison_table": "编程/产出/Q2_lambda对照.csv",
            "md5_Q2_top3": md5,
            "figures": figs,
        },
        "determinism": {
            "rng": "numpy.random.default_rng(20261024)",
            "tie_break": "2csv 节点名 ASCII 升序",
            "float_format": FLOAT_FMT,
            "md5_Q2_top3": md5,
        },
        "forbidden_metrics": ["Pearson", "欧氏距离", "PCA"],
        "environment": "python3 + pandas + numpy + scipy + matplotlib + networkx（版本见 编程/产出/环境/requirements.txt）",
    }
    with open(OUT_DIR / "Q2_参数.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(params, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    say(f"已写盘：Q2_top3.csv（50 行）md5={md5}")
    say(f"图：{len(figs)} 张 -> 图集/M2/")
    say(f"总耗时 {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
