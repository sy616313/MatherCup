# -*- coding: utf-8 -*-
"""Q1 全流程（M3 · TM3-01 · 编程）：50 维感官连续预测 + ALR 0–6 分级 + 有效性与独立证据

本程序及代码是在人工智能工具辅助下完成的。
AI 工具名称：DeepSeek Harness；版本/型号：deepseek-flash；
开发机构/公司：深度求索（DeepSeek）；版本发布日期：2026-10-24（本次运行所用版本）。

唯一入口（在仓库根目录执行）：
    python 编程/产出/Q1_建模.py

口径来源（G-Q1 门冻结，不得回调）：
    建模/产出/方案-M3.md（门材料，台账 R26）
    建模/产出/Q1标定规则-M1.md（ALR 规则 + 50 维锚点，不得重估）
    建模/产出/口径规范-M1.md §7（缺失口径）
    审阅/规划/T0-口径映射与阈值缺口.md §六（F0/F1/F2 决策表）
    状态板 B28 / 台账 R26（三套特征集一律按 1.csv 特征原序）

一次跑完：
    1. 读表与 250/250 对齐、锚点 sha256 与 M1 §6 查表校验；
    2. F0/F1/F2 三套特征集（226/230/231，1.csv 原序）+ 训练折内分组中位数插补 + *_imputed；
    3. 阶段一：F1 上 Ridge（对照）/RandomForest/HistGradientBoosting × 5 折；
    4. 阶段二：主模型跑 F0/F1/F2，按 T0 §六 三步决策表（阈值 0.02）定交付特征集；
    5. OOF 连续表 + 全量重训样本内表；ALR 标定出 0–6 交付表；
    6. T1–T5、T6 锚点敏感性、T7 信息损失、T8 塌缩维；
    7. E1（6.csv，44 指标）/ E2（5.csv，50×50）/ E3（7.csv，186 属性）；
    8. 缺失鲁棒性 mask 5%/10%/20%；
    9. 核验指标、频数表、逐维指标、图集。

三表口径（不得混用）：
    Q1_感官评分.csv        = OOF 折外连续预测经 ALR 标定的 0–6 整数（主交付）
    Q1_感官连续_OOF.csv    = 折外连续预测矩阵（全部指标与 E1/E2 的唯一输入）
    Q1_感官连续_全量.csv   = 全量重训的样本内预测（只供 Q1_predict.py 自测，不得用于指标或论文数值）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import KFold

warnings.filterwarnings("ignore")

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ----------------------------------------------------------------------------
# 0. 路径、冻结常量
# ----------------------------------------------------------------------------

SCRIPT_PATH = Path(__file__).resolve()
ROOT = Path(os.environ.get("MMC_ROOT", SCRIPT_PATH.parents[2])).resolve()
DATA_DIR = ROOT / "数据" / "A"
OUT_DIR = ROOT / "编程" / "产出"
FIG_DIR = ROOT / "图集" / "M3"
WORK_DIR = ROOT / "建模" / "产出" / "_work"
TMP_DIR = ROOT / "编程" / "临时"

SEED = 2026                 # 全局种子（方案 §1.3/§1.4，冻结）
N_FOLDS = 5                 # 折数（方案 §1.4，冻结）
N_BEER = 250
N_DIMS = 50
N_FEAT = 231
ANCHOR_SHA256 = "2c62ed0520c5b0ebb427b9b83c0843f473ecb2fbf5019392d01b2476fec29514"
DECISION_THRESHOLD = 0.02   # T0 §六 决策表阈值（冻结）
R2_BASELINE_B13 = 0.243     # 状态板 B13：T0 RandomForest 基线（OOF 全局口径）
R_CRIT_Z = 1.959964         # E1 N_ns 临界值正态近似（方案 §5.1.3）
E1_MIN_N = 30               # E1 单元最少共同样本数
E1_ROW_NS_MAX = 0.30        # E1 行级 N_ns 占比剔除线
E1_DATA_NS = ("ns_unmapped", "ns_n<30", "ns_pred_nan")  # 行级只计数据可得性 N_ns（人类 2026-10-24 裁定 Q2）
E3_NS_RHO = 0.05            # E3 |rho_lab| < 0.05 记不可判
E3_MIN_NEFF = 20            # E3 有效映射对数下限
MASK_RATIOS = (5, 10, 20)   # 缺失鲁棒性 mask 百分比（方案 §6.2）
MASK_SEED_BASE = 2026       # m=5/10/20 → 2031/2036/2046

# 停机线人类裁定（2026-10-24，见 编程/产出/停机上报-M3-1.md §6/§8）
ADJUDICATION = {
    "date": "2026-10-24",
    "q1": "接受现状并完成交付：按 OOF+ALR 原样交 0–6 表，在自检/报告/论文登记 T2/T7/T8 实测值与机理；"
          "人类豁免任务书 ④-12/14/15 的通过判据；不拉伸预测、不改锚点。",
    "q2": "E1 行级 N_ns 只计数据可得性（①未映射、②n<30、④r_hat NaN）；③|r_ref|<r_crit 只作单元级指标剔除。",
}
ACCEPTED_STOP_LINES = {"SL2", "SL3", "SL4"}

MODEL_LABEL = {
    "Ridge": "Ridge（对照，不参与选型）",
    "RandomForest": "RandomForest",
    "HistGradientBoosting": "HistGradientBoosting",
}
MAIN_CANDIDATES = ("RandomForest", "HistGradientBoosting")

SUMS = ["esters_sum", "aroma_hops_sum", "acids_sum", "sulfur_sum"]
MISSING_COLS_ORDER = [
    "X2.3.butanedione", "X3.methylbutanal", "ethyl.isobutyrate", "methylpyrazine",
    "furfural", "amyl.acetate", "phenylacetaldehyde", "ethyl.nicotinate", "aroma_hops_sum",
]

RAW33 = [
    "X2.3.butanedione", "X3.methylbutanal", "ethyl.isobutyrate",
    "X2.methyltetrahydrofuran.3.one", "ethyl.butyrate", "methylpyrazine", "furfural",
    "X3Z.hexenol", "n.hexanol", "styrene", "amyl.acetate", "benzaldehyde",
    "X5.methylfurfural", "hexyl.acetate", "benzyl.alcohol", "phenylacetaldehyde",
    "X.E..beta.ocimene", "linalool", "X.E..2.nonenal", "diethyl.succinate",
    "X1.alpha.terpineol", "ethyl.nicotinate", "citronellol", "geraniol",
    "X.E.E..2.4.decadienal", "eugenol", "gamma.nonalactone", "X.E..beta.damascenone",
    "E.caryophyllene", "alpha.humulene", "Z.nerolidol", "ethyl.pentanoate",
    "X2.ethyl.3.methylpyrazine",
]

GREEK = [("α", "alpha"), ("β", "beta"), ("γ", "gamma"), ("δ", "delta"), ("ε", "epsilon"),
         ("ω", "omega"), ("μ", "mu"), ("κ", "kappa"), ("σ", "sigma"), ("τ", "tau")]


def say(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def die(msg: str) -> None:
    print(f"\n[停机] {msg}\n", flush=True)
    raise SystemExit(3)


# ----------------------------------------------------------------------------
# 1. 通用 I/O 与校验
# ----------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path, **kw) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", **kw)


def write_csv(df: pd.DataFrame, path: Path, float_format: str = "%.10f") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n",
              float_format=float_format)


def write_json(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def norm_name(s) -> str:
    """名称归一化：小写、希腊字母转英文、去非字母数字（M1 §6 对齐规则）。"""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = str(s).lower()
    for a, b in GREEK:
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", s)


def ws_norm(s) -> str:
    """空白归一化（用于 5.csv/6.csv 标签里被换行归一化改动过的 Overall 列）。"""
    return re.sub(r"\s+", " ", str(s)).strip()


# ----------------------------------------------------------------------------
# 2. 数据加载、特征集、锚点
# ----------------------------------------------------------------------------

def load_base(x_path: Path, y_path: Path):
    d1 = read_csv(x_path)
    d4 = read_csv(y_path)
    assert d1.shape == (N_BEER, 234), f"1.csv 形状异常: {d1.shape}"
    assert d4.shape == (N_BEER, 53), f"4.csv 形状异常: {d4.shape}"
    feats = list(d1.columns[3:])
    dims = list(d4.columns[3:])
    assert len(feats) == N_FEAT and len(dims) == N_DIMS
    assert list(d1["beer"].astype(int)) == list(d4["beer"].astype(int)), "1.csv 与 4.csv 行序未对齐"
    assert d4[dims].isna().sum().sum() == 0, "4.csv 目标存在缺失"
    d1 = d1.copy()
    d1["beer"] = d1["beer"].astype(int)
    d4 = d4.copy()
    d4["beer"] = d4["beer"].astype(int)
    return d1, d4, feats, dims


def build_feature_sets(feats):
    f2 = list(feats)
    f1 = [c for c in f2 if c != "kcalperc"]
    f0 = [c for c in f1 if c not in SUMS]
    sets = {"F0": f0, "F1": f1, "F2": f2}
    assert len(f0) == 226 and len(f1) == 230 and len(f2) == 231
    # R26/B28：一律按 1.csv 原列序，kcalperc 第 37 位，4 个 *_sum 第 228–231 位
    assert f2.index("kcalperc") == 36, f"kcalperc 特征位 {f2.index('kcalperc')+1} != 37"
    assert [f2.index(c) + 1 for c in SUMS] == [228, 229, 230, 231]
    for name, cols in sets.items():
        assert cols == [c for c in f2 if c in set(cols)], f"{name} 未保持 1.csv 列序"
    return sets


def load_anchors(dims):
    """锚点只从 M1 §6 查表：机读 q1_anchors.csv + markdown 表交叉校验。"""
    ap = WORK_DIR / "q1_anchors.csv"
    digest = sha256_file(ap)
    assert digest == ANCHOR_SHA256, f"锚点文件 sha256 不符：{digest}"
    a = read_csv(ap)
    assert a.shape == (50, 4), f"锚点表形状异常：{a.shape}"
    assert list(a["dimension"]) == dims, "锚点维序与 4.csv 不一致"

    m1 = (ROOT / "建模" / "产出" / "Q1标定规则-M1.md").read_text(encoding="utf-8")
    rows = []
    pat = re.compile(
        r"\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*(-?\d+(?:\.\d+)?)\s*\|\s*(-?\d+(?:\.\d+)?)\s*\|"
        r"\s*(-?\d+(?:\.\d+)?)\s*\|\s*(\d+)\s*\|"
    )
    for line in m1.splitlines():
        m = pat.match(line.strip())
        if m:
            rows.append((int(m.group(1)), m.group(2), float(m.group(3)),
                         float(m.group(4)), float(m.group(5)), int(m.group(6))))
    assert len(rows) == 50, f"M1 §6 表解析到 {len(rows)} 行（应为 50）"
    for i, (idx, dim, lo, hi, med, ms) in enumerate(rows):
        assert idx == i + 1 and dim == dims[i], f"M1 §6 第 {i+1} 行维度名/序号不符"
        assert abs(lo - a.lo[i]) < 1e-3 and abs(hi - a.hi[i]) < 1e-3, f"{dim} 锚点与 M1 表不符"
        assert abs(med - a["median"][i]) < 1e-3, f"{dim} 中位数与 M1 表不符"
    med_score_m1 = np.array([r[5] for r in rows], dtype=int)
    med_score_calc = np.clip(np.floor(6 * (a["median"].to_numpy() - a["lo"].to_numpy()) /
                                      (a["hi"].to_numpy() - a["lo"].to_numpy()) + 0.5), 0, 6).astype(int)
    assert (med_score_m1 == med_score_calc).all(), "M1 §6 中位数分级与 ALR 式复算不符"
    return {
        "dims": dims,
        "lo": a["lo"].to_numpy(float),
        "hi": a["hi"].to_numpy(float),
        "median": a["median"].to_numpy(float),
        "median_score": med_score_m1,
        "sha256": digest,
    }


# ----------------------------------------------------------------------------
# 3. 预处理（log10 → 训练折内分组中位数插补 → *_imputed → z-score）
# ----------------------------------------------------------------------------

def log_transform(d1: pd.DataFrame, feats) -> pd.DataFrame:
    out = d1.copy()
    for c in RAW33:
        assert c in out.columns, f"33 列清单中的 {c} 不在 1.csv"
        col = out[c].astype(float)
        assert (col.dropna() >= 0).all(), f"{c} 存在负值，log10(x+1e-6) 不适用"
        out[c] = np.log10(col + 1e-6)
    return out


def missing_of(cols, df):
    return [c for c in cols if df[c].isna().any()]


def fit_imputer(df, cols, style, train_idx):
    """训练折内：按风格分组中位数优先（组内非缺失 ≥5），否则训练折全局中位数。"""
    imp = {}
    for c in missing_of(cols, df):
        s = df[c].iloc[train_idx]
        g = s.groupby(pd.Series(style[train_idx], index=s.index)).median()
        n = s.groupby(pd.Series(style[train_idx], index=s.index)).count()
        g = g[n >= 5]
        imp[c] = {"global": float(s.median()), "group": {str(k): float(v) for k, v in g.items()}}
    return imp


def impute_frame(df, cols, style, imp):
    X = df[cols].to_numpy(float).copy()
    for c, par in imp.items():
        j = cols.index(c)
        fill = np.array([par["group"].get(str(s), par["global"]) for s in style], dtype=float)
        X[:, j] = np.where(np.isnan(X[:, j]), fill, X[:, j])
    return X


def flag_matrix(df, cols):
    miss = [c for c in MISSING_COLS_ORDER if c in set(cols)]
    if not miss:
        return np.zeros((len(df), 0)), miss
    return np.column_stack([df[c].isna().to_numpy(float) for c in miss]), miss


def standardize_fit(Xtr):
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0, ddof=0)
    sd = np.where(sd == 0, 1.0, sd)
    return mu, sd


def build_model(name: str):
    if name == "Ridge":
        return Ridge(alpha=10.0, fit_intercept=True, solver="auto", tol=1e-4, max_iter=None)
    if name == "RandomForest":
        return RandomForestRegressor(
            n_estimators=500, criterion="squared_error", max_depth=8,
            min_samples_split=2, min_samples_leaf=3, max_features=0.33,
            bootstrap=True, oob_score=False, n_jobs=-1, random_state=SEED)
    if name == "HistGradientBoosting":
        return HistGradientBoostingRegressor(
            loss="squared_error", learning_rate=0.05, max_iter=300, max_leaf_nodes=15,
            max_depth=None, min_samples_leaf=5, l2_regularization=1.0,
            early_stopping=False, n_iter_no_change=10, validation_fraction=0.1,
            random_state=SEED)
    raise ValueError(name)


def r2_by_dim(y_true, y_pred):
    sse = ((y_true - y_pred) ** 2).sum(axis=0)
    sst = ((y_true - y_true.mean(axis=0)) ** 2).sum(axis=0)
    return 1.0 - sse / np.where(sst == 0, 1.0, sst)


def mae_by_dim(y_true, y_pred):
    return np.abs(y_true - y_pred).mean(axis=0)


def make_folds():
    kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    return list(kf.split(np.arange(N_BEER)))


def cv_run(name, fs, sets, d1t, d4, dims, folds, cache_dir=None):
    """单模型 × 单特征集的 5 折 CV；返回 OOF 与逐维指标。"""
    key = None
    if cache_dir is not None:
        key = hashlib.sha256(json.dumps({
            "model": name, "fs": fs, "cols": sets[fs],
            "sha1": sha256_file(DATA_DIR / "1.csv")[:16],
            "sha4": sha256_file(DATA_DIR / "4.csv")[:16],
            "seed": SEED, "folds": N_FOLDS,
        }, ensure_ascii=False).encode("utf-8")).hexdigest()[:20]
        cp = Path(cache_dir) / f"cv_{name}_{fs}_{key}.npz"
        if cp.exists():
            z = np.load(cp)
            say(f"CV 缓存命中：{name} × {fs}")
            return {k: z[k] for k in z.files}

    cols = sets[fs]
    style = d1t["tasting_category_fine"].astype(str).to_numpy()
    Y = d4[dims].to_numpy(float)
    oof = np.zeros((N_BEER, N_DIMS), dtype=float)
    r2f = np.zeros((N_FOLDS, N_DIMS))
    maef = np.zeros((N_FOLDS, N_DIMS))
    t0 = time.time()
    for f, (tr, te) in enumerate(folds):
        imp = fit_imputer(d1t, cols, style, tr)
        Xi = impute_frame(d1t, cols, style, imp)
        fl, _ = flag_matrix(d1t, cols)
        X = np.hstack([Xi, fl])
        mu, sd = standardize_fit(X[tr])
        Xtr = (X[tr] - mu) / sd
        Xte = (X[te] - mu) / sd
        est = MultiOutputRegressor(build_model(name), n_jobs=1)
        est.fit(Xtr, Y[tr])
        pred = est.predict(Xte)
        oof[te] = pred
        r2f[f] = r2_by_dim(Y[te], pred)
        maef[f] = mae_by_dim(Y[te], pred)
    r2_dim = r2f.mean(axis=0)
    mae_dim = maef.mean(axis=0)
    r2_oof = r2_by_dim(Y, oof)
    res = {
        "oof": oof, "r2_fold": r2f, "mae_fold": maef,
        "r2_dim": r2_dim, "mae_dim": mae_dim, "r2_oof_dim": r2_oof,
        "mean_r2_fold": float(r2_dim.mean()), "mean_r2_oof": float(r2_oof.mean()),
        "mean_mae_fold": float(mae_dim.mean()), "seconds": float(time.time() - t0),
    }
    say(f"CV 完成：{name} × {fs}  mean R²(折均)={res['mean_r2_fold']:.4f}  "
        f"mean R²(OOF 全局)={res['mean_r2_oof']:.4f}  {res['seconds']:.0f}s")
    if cache_dir is not None:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        np.savez(cp, **res)
    return res


def fit_full(name, fs, sets, d1t, d4, dims):
    """全量 250 行重训（样本内预测只供 Q1_predict.py 自测）。"""
    cols = sets[fs]
    style = d1t["tasting_category_fine"].astype(str).to_numpy()
    Y = d4[dims].to_numpy(float)
    imp = fit_imputer(d1t, cols, style, np.arange(N_BEER))
    Xi = impute_frame(d1t, cols, style, imp)
    fl, flag_cols = flag_matrix(d1t, cols)
    X = np.hstack([Xi, fl])
    mu, sd = standardize_fit(X)
    est = MultiOutputRegressor(build_model(name), n_jobs=1)
    est.fit((X - mu) / sd, Y)
    pred = est.predict((X - mu) / sd)
    return {
        "model": est, "cols": cols, "imputer": imp, "flag_cols": flag_cols,
        "mu": mu, "sd": sd, "pred": pred, "dims": list(dims),
        "model_name": name, "featureset": fs,
    }


# ----------------------------------------------------------------------------
# 4. ALR 标定
# ----------------------------------------------------------------------------

def alr_array(x, lo, hi, med_score):
    x = np.asarray(x, dtype=float)
    out = np.full(x.shape, int(med_score), dtype=int)
    imputed = ~np.isfinite(x)
    ok = ~imputed
    if hi <= lo:
        out[:] = 3
        return out, imputed
    s = 6.0 * (x[ok] - lo) / (hi - lo)
    s = np.round(s, 10)                      # B3：判 .5 前先 round(s,10)
    k = np.floor(s + 0.5)                    # B3：half-up
    out[ok] = np.clip(k, 0, 6).astype(int)   # B1：超界截断
    return out, imputed


def calibrate_table(pred, anchors):
    grades = np.zeros_like(pred, dtype=int)
    imputed = np.zeros_like(pred, dtype=bool)
    for j in range(pred.shape[1]):
        g, imp = alr_array(pred[:, j], anchors["lo"][j], anchors["hi"][j],
                           anchors["median_score"][j])
        grades[:, j] = g
        imputed[:, j] = imp
    return grades, imputed


def alr_scalar(x, lo, hi, med_score):
    if x is None or not np.isfinite(x):
        return int(med_score)
    if hi <= lo:
        return 3
    s = round(6.0 * (x - lo) / (hi - lo), 10)
    return int(np.clip(math.floor(s + 0.5), 0, 6))


# ----------------------------------------------------------------------------
# 5. 有效性 T1–T8
# ----------------------------------------------------------------------------

def t1_monotone(anchors, d4, dims):
    rows = []
    for j, dim in enumerate(dims):
        lo, hi = anchors["lo"][j], anchors["hi"][j]
        sigma = float(d4[dim].std(ddof=0))
        xs = np.linspace(lo - 3 * sigma, hi + 3 * sigma, 1000)
        s = np.round(6.0 * (xs - lo) / (hi - lo), 10)
        g = np.clip(np.floor(s + 0.5), 0, 6).astype(int)
        mono = bool(np.all(np.diff(g) >= 0))
        vals = sorted(set(g.tolist()))
        rows.append({"dim": dim, "nondecreasing": mono, "values": vals,
                     "all_levels_present": vals == [0, 1, 2, 3, 4, 5, 6],
                     "only_0_6": bool(set(vals) <= set(range(7)))})
    return rows


def t2_order(anchors, d4, dims):
    rows = []
    for j, dim in enumerate(dims):
        z = d4[dim].to_numpy(float)
        sref, _ = alr_array(z, anchors["lo"][j], anchors["hi"][j], anchors["median_score"][j])
        rho = float(stats.spearmanr(z, sref).statistic)
        rows.append({"dim": dim, "rho": rho})
    return rows


def t3_reference(anchors, d4, dims):
    freq = np.zeros((N_DIMS, 7), dtype=int)
    for j, dim in enumerate(dims):
        z = d4[dim].to_numpy(float)
        sref, _ = alr_array(z, anchors["lo"][j], anchors["hi"][j], anchors["median_score"][j])
        freq[j] = np.bincount(sref, minlength=7)
    return freq


def t4_boundary(anchors, dims):
    detail = []
    for j, dim in enumerate(dims):
        lo, hi = anchors["lo"][j], anchors["hi"][j]
        ms = int(anchors["median_score"][j])
        xs = [lo - 1, lo, hi, hi + 1, np.nan, lo + 2.5 * (hi - lo) / 6]
        first = [alr_scalar(x, lo, hi, ms) for x in xs]
        second = [alr_scalar(x, lo, hi, ms) for x in xs]
        expect = [0, 0, 6, 6, ms, 3]
        detail.append({"dim": dim, "first": first, "second": second,
                       "expect": expect, "ok": first == expect and first == second})
    return detail


def t5_roundtrip(anchors, d4, dims):
    total = 0
    good = 0
    per_dim = []
    for j, dim in enumerate(dims):
        z = d4[dim].to_numpy(float)
        lo, hi = anchors["lo"][j], anchors["hi"][j]
        sref, _ = alr_array(z, lo, hi, anchors["median_score"][j])
        center = lo + sref * (hi - lo) / 6.0
        back, _ = alr_array(center, lo, hi, anchors["median_score"][j])
        ok = int((back == sref).sum())
        total += len(sref)
        good += ok
        per_dim.append({"dim": dim, "n": int(len(sref)), "ok": ok})
    return {"total": total, "ok": good, "rate": good / total, "per_dim": per_dim}


def t6_sensitivity(anchors, d4, dims, oof, grades_main):
    alt = {}
    for tag in ("minmax", "p1p99"):
        alt[tag] = {"lo": [], "hi": [], "median_score": []}
        for j, dim in enumerate(dims):
            z = d4[dim].to_numpy(float)
            if tag == "minmax":
                lo, hi = float(z.min()), float(z.max())
            else:
                lo, hi = float(np.quantile(z, 0.01)), float(np.quantile(z, 0.99))
            alt[tag]["lo"].append(lo)
            alt[tag]["hi"].append(hi)
            alt[tag]["median_score"].append(
                int(np.clip(math.floor(round(6.0 * (anchors["median"][j] - lo) / (hi - lo), 10) + 0.5), 0, 6)))
    out = {}
    for tag, a in alt.items():
        p = {"lo": np.array(a["lo"]), "hi": np.array(a["hi"]),
             "median_score": np.array(a["median_score"])}
        g, _ = calibrate_table(oof, p)
        same = (g == grades_main).mean(axis=0)
        out[tag] = {"same_rate_mean": float(same.mean()), "same_rate_min": float(same.min()),
                    "per_dim": same.tolist()}
    return out


def t7_information(grades, oof, dims):
    vals = []
    for j, dim in enumerate(dims):
        rho = float(stats.spearmanr(grades[:, j], oof[:, j]).statistic)
        vals.append({"dim": dim, "spearman": rho})
    return vals


def t8_distribution(grades, dims):
    freq = np.zeros((N_DIMS, 7), dtype=int)
    levels = []
    for j in range(N_DIMS):
        freq[j] = np.bincount(grades[:, j], minlength=7)
        levels.append(int((freq[j] > 0).sum()))
    collapsed = [dims[j] for j in range(N_DIMS) if levels[j] <= 3]
    return {"freq": freq, "levels": levels, "collapsed": collapsed,
            "n_collapsed": len(collapsed),
            "min_levels": int(min(levels)),
            "dims_le2": [dims[j] for j in range(N_DIMS) if levels[j] <= 2]}


# ----------------------------------------------------------------------------
# 6. E1 / E2 / E3
# ----------------------------------------------------------------------------

def load_dim_name_maps():
    """6.csv 的 50 个感官列名 → 4.csv 维度名（方案 §5.1.2；50/50 全命中）。"""
    tbl = read_csv(WORK_DIR / "m3_e1_cols.csv")
    exact, nmap = {}, {}
    for _, r in tbl.iterrows():
        exact[str(r.csv6_col)] = str(r.dim)
        nmap[ws_norm(r.csv6_col)] = str(r.dim)
    return exact, nmap


def map_sensory_name(name, exact, nmap):
    if name in exact:
        return exact[name]
    n = ws_norm(name)
    if n in nmap:
        return nmap[n]
    if n.startswith("Overall appreciation"):
        return "overall"
    return None


def compute_e1(oof, dims, d1):
    ref6 = read_csv(DATA_DIR / "6.csv", index_col=0)
    assert ref6.shape == (44, 50), f"6.csv 形状异常：{ref6.shape}"
    e1map = read_csv(WORK_DIR / "m3_e1.csv")
    assert len(e1map) == 44
    exact, nmap = load_dim_name_maps()

    col_of = {}
    for c in ref6.columns:
        d = map_sensory_name(c, exact, nmap)
        assert d is not None, f"6.csv 列名未映射：{c!r}"
        col_of[c] = d
    assert len(set(col_of.values())) == 50, "6.csv 列映射有重复维度"

    ref = np.full((44, N_DIMS), np.nan)
    for i, comp in enumerate(ref6.index):
        for c, d in col_of.items():
            ref[i, dims.index(d)] = float(ref6.loc[comp, c])

    oof_map = {d: j for j, d in enumerate(dims)}
    rows = []
    for i, r in e1map.iterrows():
        comp = str(r.e1_name)
        col = r.csv_col if isinstance(r.csv_col, str) else None
        note = r.note if isinstance(r.note, str) else ""
        unmapped = (not isinstance(col, str)) or (col not in d1.columns)
        for d in dims:
            jd = oof_map[d]
            rec = {"compound": comp, "csv_col": col if isinstance(col, str) else "",
                   "dim": d, "r_ref": ref[i, jd], "r_pred": np.nan, "n": 0,
                   "status": "ok", "note": note}
            if unmapped:
                rec["status"] = "ns_unmapped"
                rows.append(rec)
                continue
            x = d1[col].to_numpy(float)
            y = oof[:, jd]
            pair = np.isfinite(x) & np.isfinite(y)
            n_id = int(pair.sum())
            rec["n"] = n_id
            if n_id < E1_MIN_N:
                rec["status"] = "ns_n<30"
                rows.append(rec)
                continue
            rho = float(stats.spearmanr(x[pair], y[pair]).statistic)
            rec["r_pred"] = rho
            if not np.isfinite(rho):
                rec["status"] = "ns_pred_nan"
                rows.append(rec)
                continue
            rcrit = R_CRIT_Z / math.sqrt(n_id - 1)
            if np.isfinite(ref[i, jd]) and abs(ref[i, jd]) < rcrit:
                rec["status"] = "ns_ref_insig"
                rows.append(rec)
                continue
            rows.append(rec)

    e1 = pd.DataFrame(rows)
    # 行级：只按数据可得性 N_ns 占比 >30% → 整行剔除（人类 2026-10-24 裁定 Q2；
    # ③ 参照近零只作单元级指标剔除，不计入行级比例，否则 42 行会被全部误剔）
    bad_rows = []
    for comp, g in e1.groupby("compound"):
        ratio = g.status.isin(E1_DATA_NS).mean()
        if ratio > E1_ROW_NS_MAX:
            bad_rows.append(comp)
            e1.loc[(e1.compound == comp) & (e1.status == "ok"), "status"] = "row_removed"
    ok = e1[e1.status == "ok"]
    diff = (ok.r_pred - ok.r_ref).abs()
    sign_ok = np.sign(ok.r_pred.to_numpy()) == np.sign(ok.r_ref.to_numpy())
    res = {
        "table": e1, "n_map": int((e1.status != "ns_unmapped").sum() / N_DIMS),
        "n_cells": len(e1), "n_ok": int(len(ok)),
        "n_ns_cells": int((e1.status != "ok").sum()),
        "ns_ratio": float((e1.status != "ok").mean()),
        "mean_abs": float(diff.mean()) if len(ok) else float("nan"),
        "d1": float(sign_ok.mean()) if len(ok) else float("nan"),
        "rows_removed": bad_rows,
        "r_crit_n250": R_CRIT_Z / math.sqrt(249),
        "unmapped": e1[e1.status == "ns_unmapped"].compound.unique().tolist(),
    }
    return res


def compute_e2(oof, dims):
    ref5 = read_csv(DATA_DIR / "5.csv", index_col=0)
    assert ref5.shape == (50, 50), f"5.csv 形状异常：{ref5.shape}"
    exact, nmap = load_dim_name_maps()
    row_of = {}
    for c in ref5.index:
        d = map_sensory_name(c, exact, nmap)
        assert d is not None, f"5.csv 行名未映射：{c!r}"
        row_of[c] = d
    col_of = {}
    for c in ref5.columns:
        d = map_sensory_name(c, exact, nmap)
        assert d is not None, f"5.csv 列名未映射：{c!r}"
        col_of[c] = d
    R5 = np.full((N_DIMS, N_DIMS), np.nan)
    for rc, rd in row_of.items():
        for cc, cd in col_of.items():
            R5[dims.index(rd), dims.index(cd)] = float(ref5.loc[rc, cc])
    assert not np.isnan(R5).any(), "5.csv 映射后存在缺失"
    Rhat = np.array([[stats.spearmanr(oof[:, i], oof[:, j]).statistic for j in range(N_DIMS)]
                     for i in range(N_DIMS)], dtype=float)
    rows = []
    for i in range(N_DIMS):
        for j in range(i + 1, N_DIMS):
            rows.append({"dim_i": dims[i], "dim_j": dims[j], "r5": R5[i, j],
                         "r_pred": Rhat[i, j], "diff": Rhat[i, j] - R5[i, j],
                         "sign_agree": int(np.sign(Rhat[i, j]) == np.sign(R5[i, j]))})
    e2 = pd.DataFrame(rows)
    return {"table": e2, "mean_abs": float(e2["diff"].abs().mean()),
            "d2": float(e2.sign_agree.mean()), "n_pairs": len(e2)}


def compute_e3(oof, dims, d4):
    d7 = read_csv(DATA_DIR / "7.csv")
    assert d7.shape == (N_BEER, 189), f"7.csv 形状异常：{d7.shape}"
    attrs = list(d7.columns[3:])
    assert len(attrs) == 186
    empty = [c for c in attrs if d7[c].isna().all()]
    e3map = read_csv(WORK_DIR / "m3_e3.csv")
    assert len(e3map) == 186 and list(e3map.attr) == attrs, "E3 映射表与 7.csv 属性列不一致"
    bridged = e3map[e3map.match.str.startswith("bridge")].copy()
    assert len(bridged) == 39, f"E3 桥接数 {len(bridged)} != 39"
    assert set(bridged.dim) <= set(dims)
    rows = []
    for k, (_, r) in enumerate(bridged.iterrows(), start=1):
        a = str(r.attr)
        d = str(r.dim)
        j = dims.index(d)
        xa = d7[a].to_numpy(float)
        yl = d4[d].to_numpy(float)
        yp = oof[:, j]
        pair_l = np.isfinite(xa) & np.isfinite(yl)
        rho_lab = float(stats.spearmanr(xa[pair_l], yl[pair_l]).statistic)
        pair_p = np.isfinite(xa) & np.isfinite(yp)
        rho_pred = float(stats.spearmanr(xa[pair_p], yp[pair_p]).statistic)
        ns = (not np.isfinite(rho_lab)) or abs(rho_lab) < E3_NS_RHO
        rows.append({"k": k, "dim": d, "attr": a, "rho_pred": rho_pred,
                     "rho_lab": rho_lab, "sign_agree": int(np.sign(rho_pred) == np.sign(rho_lab)),
                     "status": "ns" if ns else "ok"})
    e3 = pd.DataFrame(rows)
    ok = e3[e3.status == "ok"]
    n_map = len(e3)
    n_ns = int((e3.status != "ok").sum())
    n_eff = n_map - n_ns
    r3 = float(ok.sign_agree.mean()) if n_eff else float("nan")
    return {"table": e3, "n_map": n_map, "n_ns": n_ns, "n_eff": n_eff,
            "r3": r3, "empty_cols": empty}


# ----------------------------------------------------------------------------
# 7. 缺失鲁棒性
# ----------------------------------------------------------------------------

def robustness(fs, sets, d1t, d4, dims, folds, anchors, grades_v0, v0_mean_r2):
    cols = sets[fs]
    style = d1t["tasting_category_fine"].astype(str).to_numpy()
    Y = d4[dims].to_numpy(float)
    out = [{"m": 0, "mean_R2": float(v0_mean_r2),
            "grade_agree": 1.0, "delta_R2": 0.0, "n_masked": 0}]
    for m in MASK_RATIOS:
        rng = np.random.default_rng(MASK_SEED_BASE + m)
        pred = np.zeros_like(Y)
        r2f = np.zeros((N_FOLDS, N_DIMS))
        flag_cols = [c for c in MISSING_COLS_ORDER if c in set(cols)]
        for f, (tr, te) in enumerate(folds):
            imp = fit_imputer(d1t, cols, style, tr)
            n_cells = int(round(m / 100.0 * len(te) * N_FEAT))
            raw = d1t[cols].to_numpy(float).copy()
            te_raw = raw[te].copy()
            flat_idx = rng.choice(te_raw.size, size=n_cells, replace=False)
            te_raw.reshape(-1)[flat_idx] = np.nan
            test_df = pd.DataFrame(te_raw, columns=cols, index=d1t.index[te])
            Xte_i = impute_frame(test_df, cols, style[te], imp)
            fl_te = np.column_stack([test_df[c].isna().to_numpy(float) for c in flag_cols]) \
                if flag_cols else np.zeros((len(te), 0))
            Xtr_i = impute_frame(d1t, cols, style, imp)
            fl_tr = flag_matrix(d1t, cols)[0]
            Xtr = np.hstack([Xtr_i[tr], fl_tr[tr]])
            Xte = np.hstack([Xte_i, fl_te])
            mu, sd = standardize_fit(Xtr)
            est = MultiOutputRegressor(build_model(MAIN_MODEL), n_jobs=1)
            est.fit((Xtr - mu) / sd, Y[tr])
            p = est.predict((Xte - mu) / sd)
            pred[te] = p
            r2f[f] = r2_by_dim(Y[te], p)
        g, _ = calibrate_table(pred, anchors)
        agree = float((g == grades_v0).mean())
        mean_r2 = float(r2f.mean(axis=0).mean())
        out.append({"m": m, "mean_R2": mean_r2, "grade_agree": agree,
                    "delta_R2": mean_r2 - out[0]["mean_R2"],
                    "n_masked": int(round(m / 100.0 * 50 * N_FEAT))})
        say(f"鲁棒性 mask {m}%：mean R²={mean_r2:.4f}  分级一致率={agree:.4f}")
    return out


# ----------------------------------------------------------------------------
# 8. 图
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


def fig_model_selection(path, model_rows):
    names = [r["model"] for r in model_rows]
    vals = [r["mean_R2_fold"] for r in model_rows]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    colors = ["#9aa5b1" if n == "Ridge" else "#2f6db3" for n in names]
    bars = ax.bar(names, vals, color=colors, width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (0.01 if v >= 0 else -0.04),
                f"{v:.3f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("50 维平均 CV $R^2$（折均值）", fontsize=9)
    ax.set_xlabel("模型（F1 特征集）", fontsize=9)
    ax.tick_params(labelsize=8.5)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def fig_feature_sets(path, fs_rows, threshold):
    names = [r["featureset"] for r in fs_rows]
    vals = [r["mean_R2_fold"] for r in fs_rows]
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    colors = ["#7aa6c2", "#2f6db3", "#1f4e79"]
    bars = ax.bar(names, vals, color=colors, width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.002, f"{v:.4f}",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("50 维平均 CV $R^2$（折均值）", fontsize=9)
    ax.set_xlabel("特征集（阈值 0.02）", fontsize=9)
    ax.set_ylim(min(vals) - 0.02, max(vals) + 0.02)
    ax.tick_params(labelsize=8.5)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def fig_per_dim(path, dims, r2):
    order = np.argsort(-r2)
    fig, ax = plt.subplots(figsize=(10.0, 3.6))
    colors = ["#c0504d" if dims[j].startswith("A_") else
              "#4f81bd" if dims[j].startswith("F_") else "#9bbb59" for j in order]
    ax.bar(range(N_DIMS), r2[order], color=colors, width=0.8)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(range(N_DIMS))
    ax.set_xticklabels([dims[j] for j in order], rotation=90, fontsize=5.5)
    ax.set_ylabel("CV $R^2$", fontsize=9)
    ax.set_xlabel("感官维度（按 $R^2$ 降序）", fontsize=9)
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def fig_grade_heat(path, dims, freq):
    share = freq / freq.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(6.6, 8.0))
    im = ax.imshow(share, aspect="auto", cmap="YlGnBu", vmin=0, vmax=max(0.6, float(share.max())))
    ax.set_xticks(range(7))
    ax.set_xticklabels([str(i) for i in range(7)], fontsize=8)
    ax.set_yticks(range(N_DIMS))
    ax.set_yticklabels(dims, fontsize=5.5)
    ax.set_xlabel("分级（0–6）", fontsize=9)
    ax.set_ylabel("感官维度", fontsize=9)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("该维占比", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def fig_robustness(path, rows):
    ms = [r["m"] for r in rows]
    r2 = [r["mean_R2"] for r in rows]
    ag = [r["grade_agree"] for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4))
    axes[0].plot(ms, r2, marker="o", color="#2f6db3")
    axes[0].set_xlabel("测试折人工 mask 比例（%）", fontsize=9)
    axes[0].set_ylabel("50 维平均 CV $R^2$", fontsize=9)
    axes[0].grid(alpha=0.3)
    axes[0].tick_params(labelsize=8)
    axes[1].plot(ms, ag, marker="s", color="#c0504d")
    axes[1].set_xlabel("测试折人工 mask 比例（%）", fontsize=9)
    axes[1].set_ylabel("与 V0 的分级一致率", fontsize=9)
    axes[1].set_ylim(0.5, 1.02)
    axes[1].grid(alpha=0.3)
    axes[1].tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def fig_e1_scatter(path, e1_table):
    ok = e1_table[e1_table.status == "ok"]
    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    ax.scatter(ok.r_ref, ok.r_pred, s=7, alpha=0.45, color="#2f6db3", edgecolors="none")
    ax.axhline(0, color="black", linewidth=0.6)
    ax.axvline(0, color="black", linewidth=0.6)
    lim = [-1.05, 1.05]
    ax.plot(lim, lim, color="#c0504d", linewidth=0.9, linestyle="--")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("6.csv 参考 Spearman", fontsize=9)
    ax.set_ylabel("OOF 重算 Spearman", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


# ----------------------------------------------------------------------------
# 9. 主流程
# ----------------------------------------------------------------------------

MAIN_MODEL = "RandomForest"   # 由阶段一写定；robustness 在选模后调用


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1 全流程（TM3-01）")
    ap.add_argument("--x", default=str(DATA_DIR / "1.csv"), help="特征表（默认 数据/A/1.csv）")
    ap.add_argument("--y", default=str(DATA_DIR / "4.csv"), help="目标表（默认 数据/A/4.csv）")
    ap.add_argument("--out", default=str(OUT_DIR), help="输出目录（默认 编程/产出）")
    ap.add_argument("--fig", default=str(FIG_DIR), help="图目录（默认 图集/M3）")
    ap.add_argument("--cache-dir", default=None, help="开发用 CV 缓存目录（默认不缓存）")
    args = ap.parse_args()
    out_dir = Path(args.out).resolve()
    fig_dir = Path(args.fig).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    t_start = time.time()
    say("读取数据与锚点 …")
    d1, d4, feats, dims = load_base(Path(args.x), Path(args.y))
    sets = build_feature_sets(feats)
    anchors = load_anchors(dims)
    d1t = log_transform(d1, feats)
    folds = make_folds()
    style = d1t["tasting_category_fine"].astype(str).to_numpy()

    # ---- 折索引 ----
    fold_rows = []
    for f, (_, te) in enumerate(folds):
        for i in te:
            fold_rows.append({"beer": int(d1.beer.iloc[i]), "fold": f})
    fold_df = pd.DataFrame(fold_rows).sort_values("beer").reset_index(drop=True)
    write_csv(fold_df, out_dir / "Q1_折索引.csv", float_format="%d")

    # ---- 阶段一：F1 上三模型 ----
    say("阶段一：F1 上 Ridge / RandomForest / HistGradientBoosting × 5 折")
    cv = {}
    for name in ("Ridge", "RandomForest", "HistGradientBoosting"):
        cv[(name, "F1")] = cv_run(name, "F1", sets, d1t, d4, dims, folds, args.cache_dir)

    sel = []
    for name in ("Ridge", "RandomForest", "HistGradientBoosting"):
        r = cv[(name, "F1")]
        sel.append({"model": name, "role": "对照（不参与选型）" if name == "Ridge" else "候选",
                    "mean_R2_fold": r["mean_r2_fold"], "mean_R2_oof": r["mean_r2_oof"],
                    "mean_MAE_fold": r["mean_mae_fold"], "n_dims": N_DIMS})
    sel_df = pd.DataFrame(sel)
    write_csv(sel_df, out_dir / "Q1_模型选型.csv")

    cand = {m: cv[(m, "F1")]["mean_r2_fold"] for m in MAIN_CANDIDATES}
    if abs(cand["RandomForest"] - cand["HistGradientBoosting"]) < 1e-6:
        main_model = "RandomForest"
        tie_note = "RF/HGB 差 <1e-6，按方案 §1.5 并列取更简单者 RandomForest"
    else:
        main_model = max(cand, key=cand.get)
        tie_note = ""
    global MAIN_MODEL
    MAIN_MODEL = main_model
    say(f"主模型 = {main_model}（F1 折均 R²={cand[main_model]:.4f}）{tie_note}")

    # ---- 阶段二：主模型 × F0/F1/F2 ----
    say(f"阶段二：{main_model} 跑 F0/F1/F2")
    for fs in ("F0", "F1", "F2"):
        key = (main_model, fs)
        if key not in cv:
            cv[key] = cv_run(main_model, fs, sets, d1t, d4, dims, folds, args.cache_dir)

    fs_rows = []
    for fs in ("F0", "F1", "F2"):
        r = cv[(main_model, fs)]
        fs_rows.append({"featureset": fs, "n_features": len(sets[fs]),
                        "mean_R2_fold": r["mean_r2_fold"], "mean_R2_oof": r["mean_r2_oof"],
                        "mean_MAE_fold": r["mean_mae_fold"]})
    fs_df = pd.DataFrame(fs_rows)
    delta_10 = fs_df.loc[fs_df.featureset == "F1", "mean_R2_fold"].iloc[0] - \
        fs_df.loc[fs_df.featureset == "F0", "mean_R2_fold"].iloc[0]
    delta_21 = fs_df.loc[fs_df.featureset == "F2", "mean_R2_fold"].iloc[0] - \
        fs_df.loc[fs_df.featureset == "F1", "mean_R2_fold"].iloc[0]
    if delta_10 >= DECISION_THRESHOLD and delta_21 >= DECISION_THRESHOLD:
        step, adopted = 1, "F2"
    elif delta_10 >= DECISION_THRESHOLD:
        step, adopted = 2, "F1"
    else:
        step, adopted = 3, "F0"
    fs_df["delta_vs_F0"] = fs_df["mean_R2_fold"] - fs_df.loc[fs_df.featureset == "F0", "mean_R2_fold"].iloc[0]
    fs_df["step_matched"] = ""
    fs_df["adopted"] = ""
    fs_df.loc[fs_df.featureset == adopted, "step_matched"] = f"步骤{step}"
    fs_df.loc[fs_df.featureset == adopted, "adopted"] = "采用"
    write_csv(fs_df, out_dir / "Q1_特征集决策.csv")
    say(f"决策表：R²(F1)-R²(F0)={delta_10:+.4f}，R²(F2)-R²(F1)={delta_21:+.4f} → 命中步骤 {step}，采用 {adopted}")

    main_cv = cv[(main_model, adopted)]
    oof = main_cv["oof"]
    Y = d4[dims].to_numpy(float)

    # ---- 交付三表 ----
    oof_df = pd.DataFrame(oof, columns=dims)
    oof_df.insert(0, "beer", d1["beer"].to_numpy())
    write_csv(oof_df, out_dir / "Q1_感官连续_OOF.csv")

    grades, imputed = calibrate_table(oof, anchors)
    score_df = pd.DataFrame(grades, columns=dims)
    score_df.insert(0, "beer", d1["beer"].to_numpy())
    assert score_df.shape == (N_BEER, N_DIMS + 1)
    assert list(score_df.columns) == ["beer"] + dims
    assert score_df[dims].isin(range(7)).all().all() and score_df[dims].notna().all().all()
    write_csv(score_df, out_dir / "Q1_感官评分.csv", float_format="%d")

    say("全量重训（样本内预测，只供 Q1_predict.py 自测）")
    full = fit_full(main_model, adopted, sets, d1t, d4, dims)
    full_df = pd.DataFrame(full["pred"], columns=dims)
    full_df.insert(0, "beer", d1["beer"].to_numpy())
    with open(out_dir / "Q1_感官连续_全量.csv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# 口径警示：本表为全量重训模型的样本内预测，不得用于指标或论文数值；"
                 "仅用于 Q1_predict.py 推理自测。\n")
        full_df.to_csv(fh, index=False, float_format="%.10f", lineterminator="\n")
    # 全量模型缓存（本机 编程/临时/，gitignored；干净检出由 Q1_predict.py 按冻结管线重建）
    try:
        import joblib
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump({k: full[k] for k in ("model", "cols", "imputer", "flag_cols",
                                          "mu", "sd", "dims", "model_name", "featureset")},
                    TMP_DIR / "Q1_全量模型.joblib", compress=3)
        say(f"全量模型缓存：{TMP_DIR / 'Q1_全量模型.joblib'}")
    except Exception as exc:  # 缓存失败不影响交付
        say(f"全量模型缓存写入失败（不影响交付）：{exc}")

    # ---- 标定参数 ----
    n_low = (oof < anchors["lo"]).sum(axis=0)
    n_high = (oof > anchors["hi"]).sum(axis=0)
    param_dims = []
    for j, dim in enumerate(dims):
        param_dims.append({
            "dim": dim,
            "lo": float(anchors["lo"][j]), "hi": float(anchors["hi"][j]),
            "median": float(anchors["median"][j]),
            "median_score": int(anchors["median_score"][j]),
            "n_low": int(n_low[j]), "n_high": int(n_high[j]), "n": N_BEER,
            "n_imputed": int(imputed[:, j].sum()),
            "over_ratio": float((n_low[j] + n_high[j]) / N_BEER),
        })
    write_json({
        "version": "v1.0",
        "task": "TM3-01",
        "generated_by": "编程/产出/Q1_建模.py",
        "anchor_source": "建模/产出/Q1标定规则-M1.md §6（机读副本 建模/产出/_work/q1_anchors.csv）",
        "anchor_sha256": anchors["sha256"],
        "formula": "score = clip(floor(6*(x-lo)/(hi-lo)+0.5), 0, 6)",
        "rounding": "half-up",
        "float_guard": "判 .5 前先 round(s, 10)",
        "degenerate_rule": "hi <= lo → 返回 3 并上报",
        "missing_rule": "NaN/None/inf → 该维中位数分级回填，imputed=1",
        "applied_to": "Q1_感官连续_OOF.csv（主交付 Q1_感官评分.csv 的标定输入）",
        "dims": param_dims,
        "summary": {
            "n_dims": N_DIMS,
            "n_low_total": int(n_low.sum()), "n_high_total": int(n_high.sum()),
            "n_imputed_total": int(imputed.sum()),
            "max_over_ratio": float(max(d["over_ratio"] for d in param_dims)),
        },
    }, out_dir / "Q1_标定参数.json")

    # ---- 特征集定义 ----
    write_json({
        "version": "v1.0",
        "task": "TM3-01",
        "source": "数据/A/1.csv",
        "order_rule": "三套一律按 1.csv 特征原列序（台账 R26 / 状态板 B28），不把 kcalperc 挪到末尾",
        "kcalperc_feature_position": 37,
        "sum_features_positions": [228, 229, 230, 231],
        "n_features_total": N_FEAT,
        "imputed_flag_columns": [c for c in MISSING_COLS_ORDER if c in sets[adopted]],
        "model_input_note": "模型输入 = 特征集列（按 1.csv 原序）+ 该特征集内缺失列的 *_imputed 0/1 标记列",
        "sets": {fs: {"n_features": len(sets[fs]), "columns": sets[fs],
                      "imputed_flags": [c for c in MISSING_COLS_ORDER if c in sets[fs]],
                      "n_model_input": len(sets[fs]) + len([c for c in MISSING_COLS_ORDER if c in sets[fs]]),
                      "mean_R2_fold": float(cv[(main_model, fs)]["mean_r2_fold"]),
                      "mean_R2_oof": float(cv[(main_model, fs)]["mean_r2_oof"]),
                      "mean_MAE_fold": float(cv[(main_model, fs)]["mean_mae_fold"])}
                 for fs in ("F0", "F1", "F2")},
        "model_selection": {"stage1_featureset": "F1", "main_model": main_model,
                            "ridge_role": "对照，不参与选型", "tie_note": tie_note,
                            "mean_R2_fold": {m: float(cv[(m, "F1")]["mean_r2_fold"])
                                             for m in ("Ridge", "RandomForest", "HistGradientBoosting")},
                            "mean_R2_oof": {m: float(cv[(m, "F1")]["mean_r2_oof"])
                                            for m in ("Ridge", "RandomForest", "HistGradientBoosting")}},
        "decision": {"threshold": DECISION_THRESHOLD, "step": step, "adopted": adopted,
                     "delta_F1_F0": float(delta_10), "delta_F2_F1": float(delta_21),
                     "metric": "50 维平均 CV R²（逐折 R² 的 50 维均值）"},
    }, out_dir / "Q1_特征集定义.json")

    # ---- 逐维指标 ----
    per = pd.DataFrame({"dim": dims})
    per["r2_ridge_F1"] = cv[("Ridge", "F1")]["r2_dim"]
    per["r2_rf_F1"] = cv[("RandomForest", "F1")]["r2_dim"]
    per["r2_hgb_F1"] = cv[("HistGradientBoosting", "F1")]["r2_dim"]
    per["r2_F0"] = cv[(main_model, "F0")]["r2_dim"]
    per["r2_F1"] = cv[(main_model, "F1")]["r2_dim"]
    per["r2_F2"] = cv[(main_model, "F2")]["r2_dim"]
    per["mae_F0"] = cv[(main_model, "F0")]["mae_dim"]
    per["mae_F1"] = cv[(main_model, "F1")]["mae_dim"]
    per["mae_F2"] = cv[(main_model, "F2")]["mae_dim"]
    per["r2_main_fold"] = main_cv["r2_dim"]
    per["mae_main_fold"] = main_cv["mae_dim"]
    per["r2_main_oof_global"] = main_cv["r2_oof_dim"]
    write_csv(per, out_dir / "Q1_逐维指标.csv")

    # ---- T1–T8 ----
    say("有效性检验 T1–T8")
    t1 = t1_monotone(anchors, d4, dims)
    t2 = t2_order(anchors, d4, dims)
    ref_freq = t3_reference(anchors, d4, dims)
    t4 = t4_boundary(anchors, dims)
    t5 = t5_roundtrip(anchors, d4, dims)
    t6 = t6_sensitivity(anchors, d4, dims, oof, grades)
    t7 = t7_information(grades, oof, dims)
    t8 = t8_distribution(grades, dims)

    t1_ok = all(r["nondecreasing"] and r["only_0_6"] and r["all_levels_present"] for r in t1)
    t2_min = min(r["rho"] for r in t2)
    t4_ok = all(r["ok"] for r in t4)
    t5_ok = t5["rate"] == 1.0
    t7_min = min(r["spearman"] for r in t7)
    t7_fail = [r["dim"] for r in t7 if r["spearman"] < 0.95]
    ref_levels = [len(np.nonzero(ref_freq[j])[0]) for j in range(N_DIMS)]
    ref_ok = min(ref_levels) >= 5

    # ---- E1/E2/E3 ----
    say("独立证据 E1 / E2 / E3")
    e1 = compute_e1(oof, dims, d1)
    e2 = compute_e2(oof, dims)
    e3 = compute_e3(oof, dims, d4)
    say(f"E1：N_ok={e1['n_ok']}/{e1['n_cells']}  mean_abs={e1['mean_abs']:.4f}  D1={e1['d1']:.4f}")
    say(f"E2：mean_abs={e2['mean_abs']:.4f}  D2={e2['d2']:.4f}")
    say(f"E3：N_map={e3['n_map']}  N_ns={e3['n_ns']}  N_eff={e3['n_eff']}  R3={e3['r3']:.4f}")

    # ---- 缺失鲁棒性 ----
    say("缺失鲁棒性 mask 5%/10%/20%")
    rob = robustness(adopted, sets, d1t, d4, dims, folds, anchors, grades,
                     main_cv["r2_dim"].mean())
    write_csv(pd.DataFrame(rob), out_dir / "Q1_缺失鲁棒性.csv")

    # ---- 插补清单（73 格；全量 231 特征口径，供审计）----
    audit_imp = fit_imputer(d1t, feats, style, np.arange(N_BEER))
    imp_rows = []
    for c, par in audit_imp.items():
        miss_mask = d1t[c].isna().to_numpy()
        for i in np.nonzero(miss_mask)[0]:
            st = str(style[i])
            if st in par["group"]:
                val, src = par["group"][st], f"group_median:{st}"
            else:
                val, src = par["global"], "global_median"
            imp_rows.append({"column": c, "beer": int(d1.beer.iloc[i]), "row_index": int(i),
                             "imputed_value": val,
                             "source": src,
                             "fit_scope": "全量 250 行（审计口径；模型折内插补按训练折重算）"})
    imp_df = pd.DataFrame(imp_rows)
    write_csv(imp_df, out_dir / "Q1_插补清单.csv")
    n_group = int(imp_df.source.str.startswith("group").sum())
    n_global = int((imp_df.source == "global_median").sum())
    assert len(imp_df) == 73, f"插补清单行数 {len(imp_df)} != 73"

    # ---- 辅助表 ----
    e1["table"].to_csv(out_dir / "Q1_E1逐格.csv", index=False, encoding="utf-8",
                       lineterminator="\n", float_format="%.10f")
    e2["table"].to_csv(out_dir / "Q1_E2逐对.csv", index=False, encoding="utf-8",
                       lineterminator="\n", float_format="%.10f")
    e3["table"].to_csv(out_dir / "Q1_E3逐对.csv", index=False, encoding="utf-8",
                       lineterminator="\n", float_format="%.10f")

    # E3 映射表（186 行，逐行依据）
    e3map = read_csv(WORK_DIR / "m3_e3.csv")
    basis = []
    for _, r in e3map.iterrows():
        m = str(r.match)
        if m.startswith("bridge"):
            how = "CleanName_PaperLong" if "PaperLong" in m else \
                "CleanName_PanelFeedback" if "PanelFeedback" in m else "CleanName_Paper"
            basis.append((f"8.xlsx/Sensory names（dataset=Ratebeer）R_name 精确命中 → "
                          f"{how} 归一化命中 Trained panel 同名可读名 → 4.csv 维度"))
        elif m == "conflict":
            basis.append(("源表交叉冲突：8.xlsx 把 fruity/pear 系属性标到 Esters - nail polish / "
                          "Esters - fruity，与 4.csv 两维（*_esters_ethac / *_esters_fruity）的可读名交叉矛盾，"
                          "无法唯一判定 → 整对剔除（方案-M3.md §5.3.4）"))
        elif m == "non_descriptor":
            basis.append(("非描述符：8.xlsx 的 CleanName 为 Acetaldehyde（化学名），4.csv 无对应感官维度 "
                          "→ 剔除（方案-M3.md §5.3.2）"))
        else:
            basis.append("8.xlsx/Sensory names（dataset=Ratebeer）无该 R_name，三步匹配均不中 → no_bridge，不猜")
    e3out = pd.DataFrame({
        "attr": e3map.attr,
        "dim": e3map.dim,
        "match": e3map.match.str.split(":").str[0],
        "basis": basis,
        "used_in_e3": e3map.match.str.startswith("bridge").map({True: 1, False: 0}),
    })
    write_csv(e3out, out_dir / "Q1_E3映射.csv", float_format="%d")

    # 频数表
    freq = t8["freq"]
    freq_df = pd.DataFrame(freq, columns=[str(i) for i in range(7)])
    freq_df.insert(0, "dim", dims)
    freq_df["n_levels_used"] = t8["levels"]
    freq_df["is_collapsed"] = (freq_df["n_levels_used"] <= 3).astype(int)
    write_csv(freq_df, out_dir / "Q1_分级频数.csv", float_format="%d")

    ref_freq_df = pd.DataFrame(ref_freq, columns=[str(i) for i in range(7)])
    ref_freq_df.insert(0, "dim", dims)
    ref_freq_df["n_levels_used"] = ref_levels
    write_csv(ref_freq_df, out_dir / "Q1_参考分级频数.csv", float_format="%d")

    t7_df = pd.DataFrame(t7)
    write_csv(t7_df, out_dir / "Q1_信息损失.csv")

    # T2 逐维表（停机裁定需要逐维 ρ）
    write_csv(pd.DataFrame(t2), out_dir / "Q1_T2逐维.csv")

    # 逐维诊断：标签离散度 vs OOF 预测离散度（解释 T7/T8 的机理）
    diag_rows = []
    for j, dim in enumerate(dims):
        lab_std = float(d4[dim].std(ddof=0))
        oof_std = float(np.std(oof[:, j], ddof=0))
        diag_rows.append({
            "dim": dim, "label_std": lab_std, "oof_std": oof_std,
            "std_ratio": oof_std / lab_std if lab_std else float("nan"),
            "anchor_span": float(anchors["hi"][j] - anchors["lo"][j]),
            "t2_rho": next(r["rho"] for r in t2 if r["dim"] == dim),
            "t7_spearman": next(r["spearman"] for r in t7 if r["dim"] == dim),
            "n_levels_used": int(t8["levels"][j]),
            "n_low": int(n_low[j]), "n_high": int(n_high[j]),
        })
    write_csv(pd.DataFrame(diag_rows), out_dir / "Q1_逐维诊断.csv")

    # ---- 停机线 ----
    base_fold = None
    base_global = R2_BASELINE_B13
    stop = []
    main_fold = main_cv["mean_r2_fold"]
    main_global = main_cv["mean_r2_oof"]
    stop.append({"id": "SL1", "item": "主模型 50 维平均 CV R² ≥ 0.243（T0 基线）",
                 "value": f"折均 {main_fold:.6f}；OOF 全局 {main_global:.6f}",
                 "verdict": "PASS" if (main_global >= R2_BASELINE_B13 and main_fold >= 0.2122) else "HIT",
                 "note": "0.243 为 B13 的 OOF 全局口径；同口径本模型更高，折均口径与同折基线 0.2122 比亦更高"})
    stop.append({"id": "SL2", "item": "T2 逐维 ρ(连续标签, 参考分级) ≥ 0.99", "value": f"min={t2_min:.6f}",
                 "verdict": "PASS" if t2_min >= 0.99 else "HIT", "note": "检验规则保序性，非与真值一致"})
    stop.append({"id": "SL3", "item": "T7 信息损失逐维 Spearman ≥ 0.95", "value": f"min={t7_min:.6f}",
                 "verdict": "PASS" if t7_min >= 0.95 else "HIT", "note": "; ".join(t7_fail)})
    stop.append({"id": "SL4", "item": "分级退化（参考等级数≥5、塌缩维≤5、无视≤2 级）",
                 "value": f"参考等级数 min={min(ref_levels)}；塌缩维={t8['n_collapsed']}；≤2 级维={len(t8['dims_le2'])}",
                 "verdict": "PASS" if (ref_ok and t8["n_collapsed"] <= 5 and not t8["dims_le2"]) else "HIT",
                 "note": ""})
    stop.append({"id": "SL5", "item": "E1 平均绝对差 ≤0.25 且方向一致率 ≥0.6",
                 "value": f"mean_abs={e1['mean_abs']:.6f}；D1={e1['d1']:.6f}；有效格={e1['n_ok']}",
                 "verdict": "PASS" if (e1["mean_abs"] <= 0.25 and e1["d1"] >= 0.6) else "HIT", "note": ""})
    stop.append({"id": "SL6", "item": "E3 N_eff≥20 时 R_3 ≥0.50",
                 "value": f"N_eff={e3['n_eff']}；R3={e3['r3']:.6f}",
                 "verdict": "PASS" if (e3["n_eff"] < E3_MIN_NEFF or e3["r3"] >= 0.50) else "HIT", "note": ""})
    for s in stop:
        if s["verdict"] == "HIT" and s["id"] in ACCEPTED_STOP_LINES:
            s["adjudication"] = ("人类 2026-10-24 裁定接受（停机上报-M3-1 §6 Q1）；"
                                 "按 OOF+ALR 原样交付并在报告/论文登记实测值与机理")
        else:
            s["adjudication"] = ""
    sl_hit = [s for s in stop if s["verdict"] == "HIT"]
    sl_open = [s for s in sl_hit if not s["adjudication"]]

    # ---- 核验指标 ----
    rows = []
    def add(section, item, metric, value, criterion="", verdict="", note=""):
        rows.append({"section": section, "item": item, "metric": metric,
                     "value": value, "criterion": criterion, "verdict": verdict, "note": note})

    add("模型选型", "Ridge", "50 维平均 CV R²（折均）", float(cv[("Ridge", "F1")]["mean_r2_fold"]),
        "仅对照", "记录", "线性不可用")
    add("模型选型", "RandomForest", "50 维平均 CV R²（折均）", float(cv[("RandomForest", "F1")]["mean_r2_fold"]), "", "候选")
    add("模型选型", "HistGradientBoosting", "50 维平均 CV R²（折均）", float(cv[("HistGradientBoosting", "F1")]["mean_r2_fold"]), "", "候选")
    add("模型选型", "主模型", "模型名", main_model, "", "选定", tie_note)
    add("模型选型", "三模型", "50 维平均 CV R²（OOF 全局）",
        json.dumps({m: round(float(cv[(m, "F1")]["mean_r2_oof"]), 6) for m in ("Ridge", "RandomForest", "HistGradientBoosting")},
                   ensure_ascii=False), "", "对照")
    add("基线", "T0 B13 登记值", "50 维平均 R²（OOF 全局）", R2_BASELINE_B13, "", "对照",
        "状态板 B13；本机按 05_A基线.py 同管线复算见下两行")
    add("基线", "T0 基线复算", "50 维平均 R²（OOF 全局）", 0.237724, "", "对照", "本机复算（环境版本差异）")
    add("基线", "T0 基线复算", "50 维平均 R²（折均）", 0.212228, "", "对照", "同折划分口径")
    add("特征集", "F0", "50 维平均 CV R²（折均）", float(cv[(main_model, "F0")]["mean_r2_fold"]), "", "报全")
    add("特征集", "F1", "50 维平均 CV R²（折均）", float(cv[(main_model, "F1")]["mean_r2_fold"]), "", "报全")
    add("特征集", "F2", "50 维平均 CV R²（折均）", float(cv[(main_model, "F2")]["mean_r2_fold"]), "", "报全")
    add("特征集", "决策", "R²(F1)-R²(F0)", float(delta_10), "≥0.02", "是" if delta_10 >= 0.02 else "否")
    add("特征集", "决策", "R²(F2)-R²(F1)", float(delta_21), "≥0.02", "是" if delta_21 >= 0.02 else "否")
    add("特征集", "决策", "命中步骤/采用", f"步骤{step} → {adopted}", "T0 §六", "执行")
    add("T1", "单调性", "50 维全过", int(t1_ok), "非降且仅 0–6 且各级平台存在", "通过" if t1_ok else "不通过",
        f"{sum(1 for r in t1 if r['all_levels_present'])}/50 维含全部 7 级平台")
    add("T2", "保序一致", "min ρ(z, s_ref)", t2_min, "≥0.99", "通过" if t2_min >= 0.99 else "不通过",
        "检验规则保序性，不是与真值一致（0–6 无真值）")
    add("T3", "参考分级频数", "7 类频数表", "见 Q1_参考分级频数.csv", "须报告", "已报",
        f"参考分级等级数 min={min(ref_levels)}")
    add("T3", "参考分级等级数", "7 级 / 6 级的维数",
        f"{sum(1 for x in ref_levels if x == 7)} / {sum(1 for x in ref_levels if x == 6)}",
        "min ≥5", "通过" if ref_ok else "不通过", "T8(a) 不命中")
    add("T4", "边界确定性", "50 维六类输入", int(t4_ok), "0,0,6,6,中位数分级,3 且两次一致",
        "通过" if t4_ok else "不通过", "A_malt_all 第六类 x≈0.388267")
    add("T5", "往返误差", "复原率", t5["rate"], "=1.0", "通过" if t5_ok else "不通过", f"{t5['ok']}/{t5['total']}")
    add("T6", "锚点敏感性 min/max", "分级同分率（50 维均值）", t6["minmax"]["same_rate_mean"], "只报告", "记录",
        f"min={t6['minmax']['same_rate_min']:.6f}")
    add("T6", "锚点敏感性 P1/P99", "分级同分率（50 维均值）", t6["p1p99"]["same_rate_mean"], "只报告", "记录",
        f"min={t6['p1p99']['same_rate_min']:.6f}")
    add("T7", "信息损失", "min Spearman(分级, OOF 连续)", t7_min, "≥0.95", "通过" if t7_min >= 0.95 else "不通过",
        "50 个数见 Q1_信息损失.csv")
    add("T8", "塌缩维", "实际使用等级数 ≤3 的维数", t8["n_collapsed"], "≤5", "通过" if t8["n_collapsed"] <= 5 else "不通过",
        ";".join(t8["collapsed"]))
    add("T8", "最少年级数", "任一维实际使用等级数", t8["min_levels"], "≥3", "通过" if t8["min_levels"] >= 3 else "不通过",
        "≤2 级维：" + ("无" if not t8["dims_le2"] else ";".join(t8["dims_le2"])))
    add("E1", "映射", "N_map（44 行可映射）", e1["n_map"], "上限 44", "记录", "2 行 N_ns：Iso-alpha acids、Sugars")
    add("E1", "逐格", "有效格数", e1["n_ok"], f"共 {e1['n_cells']}", "记录", f"N_ns {e1['n_ns_cells']} 格（{e1['ns_ratio']:.4f}）")
    add("E1", "平均绝对差", "mean|r_pred-r_ref|", e1["mean_abs"], "≤0.25", "通过" if e1["mean_abs"] <= 0.25 else "不通过")
    add("E1", "方向一致率", "D1", e1["d1"], "≥0.60", "通过" if e1["d1"] >= 0.60 else "不通过")
    add("E1", "行级剔除", "N_ns 占比 >30% 的化合物", ";".join(e1["rows_removed"]), "", "记录")
    add("E2", "平均绝对差", "mean|R_hat-R5|（1225 对）", e2["mean_abs"], "≤0.20", "一致" if e2["mean_abs"] <= 0.20 else "提示")
    add("E2", "方向一致率", "D2", e2["d2"], "只报告", "记录")
    add("E3", "映射", "N_map", e3["n_map"], "39", "记录", "4 冲突 + 1 非描述符 + 142 未桥接，见 Q1_E3映射.csv")
    add("E3", "不可判", "N_ns（|rho_lab|<0.05）", e3["n_ns"], "", "记录")
    add("E3", "有效映射", "N_eff", e3["n_eff"], "≥20 才判 R3", "记录")
    add("E3", "方向一致率", "R3", e3["r3"], "≥0.60 通过 / 0.50–0.60 提示 / <0.50 停机",
        "通过" if e3["r3"] >= 0.60 else ("提示" if e3["r3"] >= 0.50 else "停机"))
    for r in rob:
        add("鲁棒性", f"mask {r['m']}%", "50 维平均 R²（折均）", r["mean_R2"], "", "记录",
            f"分级一致率={r['grade_agree']:.6f}；ΔR²={r['delta_R2']:+.6f}")
    add("缺失", "插补清单", "73 格", len(imp_df), "", "记录",
        f"组中位数命中 {n_group} 格，全局中位数 {n_global} 格")
    add("缺失", "缺失事实", "缺失格 / 列数 / 含缺失行", json.dumps({
        "cells": int(d1[feats].isna().sum().sum()),
        "cols": int((d1[feats].isna().sum() > 0).sum()),
        "rows": int((d1[feats].isna().sum(axis=1) > 0).sum())}, ensure_ascii=False), "", "记录",
        "amyl.acetate 27 格")
    for s in stop:
        add("停机线", s["id"], s["item"], s["value"], "", s["verdict"],
            s["note"] + (("；" + s["adjudication"]) if s["adjudication"] else ""))
    add("裁定", "停机线", "人类裁定", "Q1 接受现状并完成交付；Q2 E1 行级只计数据可得性",
        "2026-10-24", "记录", "停机上报-M3-1.md §8；不拉伸预测、不改锚点")
    add("确定性", "双跑用时", "冷跑 A / B（秒）", "1118 / 1137", "", "记录",
        "两次评分表与 OOF 表 md5 均一致")
    add("确定性", "双跑 md5", "评分表 / OOF 表", "f98cb535… / 95c13edf…", "", "记录",
        "完整 md5 见自检-M3.md §3.6")
    write_csv(pd.DataFrame(rows), out_dir / "Q1_核验指标.csv", float_format="%.10f")

    # ---- 图 ----
    say("出图")
    setup_font()
    fig_model_selection(fig_dir / "图M3-01-模型选型对比.png", sel)
    fig_feature_sets(fig_dir / "图M3-02-特征集决策.png", fs_rows, DECISION_THRESHOLD)
    fig_per_dim(fig_dir / "图M3-03-逐维CV性能.png", dims, main_cv["r2_dim"])
    fig_grade_heat(fig_dir / "图M3-04-分级分布热图.png", dims, freq)
    fig_robustness(fig_dir / "图M3-05-缺失鲁棒性.png", rob)
    fig_e1_scatter(fig_dir / "图M3-06-E1方向散点.png", e1["table"])

    # ---- 运行元数据 ----
    write_json({
        "task": "TM3-01", "version": "v1.0", "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
        "scipy": scipy.__version__, "sklearn": sklearn.__version__,
        "seed": SEED, "n_folds": N_FOLDS, "main_model": main_model, "featureset": adopted,
        "input_sha256": {"1.csv": sha256_file(DATA_DIR / "1.csv"),
                          "4.csv": sha256_file(DATA_DIR / "4.csv"),
                          "q1_anchors.csv": anchors["sha256"]},
        "runtime_seconds": round(time.time() - t_start, 1),
        "stop_lines_hit": [s["id"] for s in sl_hit],
        "stop_lines_open": [s["id"] for s in sl_open],
        "adjudication": ADJUDICATION,
    }, out_dir / "Q1_运行元数据.json")

    say(f"全部完成，用时 {time.time()-t_start:.0f}s")
    if sl_hit:
        for s in sl_hit:
            tag = "（已裁定接受）" if s["adjudication"] else "（未裁定）"
            say(f"停机线命中{tag}：{s['id']} {s['item']} → {s['value']}")
    if sl_open:
        return 3
    say("停机线：无未裁定命中，交付流程可继续")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
