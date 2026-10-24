# -*- coding: utf-8 -*-
"""Q1 可读口径辅助表（M3 补充 · TM3-02 · 编程）：保序刻度还原 → 同锚点 ALR

本程序及代码是在人工智能工具辅助下完成的。
AI 工具名称：DeepSeek Harness；版本/型号：deepseek-flash；
开发机构/公司：深度求索（DeepSeek）；版本发布日期：2026-10-24（本次运行所用版本）。

定位（写死）：
    辅助表 = **可读口径**；与主表**单调同序、仅刻度不同**；
    **主交付仍是 编程/产出/Q1_感官评分.csv（契约口径）**。
    本表只是同一排序换刻度，不改变主表结论，也不替代主表。

做法（只读 + 变换 + 查表，不重训模型、不重算 OOF）：
    对 编程/产出/Q1_感官连续_OOF.csv 逐维做单调仿射
        x' = mu_label + (x - mu_pred) * (SD_label / SD_pred)
    mu/SD 标签端取 数据/A/4.csv 该维 250 个值、预测端取 OOF 表该维 250 个值，逐维独立，ddof=0；
    再把 x' 送进**同一张** ALR 规则（round(s,10) + half-up + clip）与**同一份** 50 维锚点
    （建模/产出/Q1标定规则-M1.md §6 / 建模/产出/_work/q1_anchors.csv，只读不改）。

入口（仓库根目录）：
    python 编程/产出/脚本/Q1_可读口径.py

退出码：0 = 三硬门（主表 md5 未变、逆序对 0、全表 7 级）全过；非 0 = 触发停机条件。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_PATH = Path(__file__).resolve()
ROOT = Path(os.environ.get("MMC_ROOT", SCRIPT_PATH.parents[3])).resolve()
DATA_DIR = ROOT / "数据" / "A"
OUT_DIR = ROOT / "编程" / "产出"
WORK_DIR = ROOT / "建模" / "产出" / "_work"

ANCHOR_SHA256 = "2c62ed0520c5b0ebb427b9b83c0843f473ecb2fbf5019392d01b2476fec29514"
MAIN_SCORE_MD5 = "f98cb535007e13c69a4112cb94bec5c9"
OOF_MD5 = "95c13edf9e9b3a6ad1a20b825c85630a"
N_BEER = 250
N_DIMS = 50
DD = 0  # SD 的自由度：ddof=0（缩放系数对 ddof 不变，只要两端同口径）


def say(msg: str) -> None:
    print(f"[TM3-02] {msg}", flush=True)


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alr_scalar(x, lo, hi, median_score):
    """M1 §3 伪代码的逐格实现（B1 截断、B2 中位数分级、B3 half-up）。"""
    if x is None or not np.isfinite(x):
        return int(median_score)
    if hi <= lo:
        return 3
    s = round(6.0 * (x - lo) / (hi - lo), 10)
    return int(np.clip(math.floor(s + 0.5), 0, 6))


def load_anchors(dims):
    ap = WORK_DIR / "q1_anchors.csv"
    digest = sha256(ap)
    assert digest == ANCHOR_SHA256, f"锚点文件 sha256 不符：{digest}"
    a = pd.read_csv(ap, encoding="utf-8-sig")
    assert a.shape == (N_DIMS, 4), f"锚点表形状异常：{a.shape}"
    assert list(a["dimension"]) == dims, "锚点维序与 4.csv 不一致"
    m1 = (ROOT / "建模" / "产出" / "Q1标定规则-M1.md").read_text(encoding="utf-8")
    pat = re.compile(
        r"\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*(-?\d+(?:\.\d+)?)\s*\|\s*(-?\d+(?:\.\d+)?)\s*\|"
        r"\s*(-?\d+(?:\.\d+)?)\s*\|\s*(\d+)\s*\|"
    )
    rows = []
    for line in m1.splitlines():
        m = pat.match(line.strip())
        if m:
            rows.append((int(m.group(1)), m.group(2), float(m.group(3)),
                         float(m.group(4)), float(m.group(5)), int(m.group(6))))
    assert len(rows) == N_DIMS, f"M1 §6 表解析到 {len(rows)} 行（应为 50）"
    for i, (idx, dim, lo, hi, med, ms) in enumerate(rows):
        assert idx == i + 1 and dim == dims[i], f"M1 §6 第 {i+1} 行维度名/序号不符"
        assert abs(lo - a["lo"][i]) < 1e-3 and abs(hi - a["hi"][i]) < 1e-3, f"{dim} 锚点与 M1 表不符"
        assert abs(med - a["median"][i]) < 1e-3, f"{dim} 中位数与 M1 表不符"
    ms = np.array([r[5] for r in rows], dtype=int)
    calc = np.clip(np.floor(6 * (a["median"].to_numpy(float) - a["lo"].to_numpy(float)) /
                            (a["hi"].to_numpy(float) - a["lo"].to_numpy(float)) + 0.5), 0, 6).astype(int)
    assert (ms == calc).all(), "M1 §6 中位数分级与 ALR 式复算不符"
    return a["lo"].to_numpy(float), a["hi"].to_numpy(float), ms


def inversions(main_g, aux_g):
    """逆序对：符号相反的格对数（并列不算）。O(n^2)，n=250。"""
    a = main_g.astype(float)
    b = aux_g.astype(float)
    total = 0
    for i in range(len(a)):
        total += int((((a[i] - a) * (b[i] - b)) < 0).sum())
    return total // 2


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1 可读口径辅助表（保序刻度还原）")
    ap.add_argument("--oof", default=str(OUT_DIR / "Q1_感官连续_OOF.csv"))
    ap.add_argument("--label", default=str(DATA_DIR / "4.csv"))
    ap.add_argument("--out", default=str(OUT_DIR / "Q1_感官评分_可读口径.csv"))
    ap.add_argument("--json", default=str(OUT_DIR / "Q1_可读口径参数.json"))
    ap.add_argument("--report-json", default=None, help="可选：另存一份校验摘要（不写则免）")
    args = ap.parse_args()

    oof_path = Path(args.oof).resolve()
    label_path = Path(args.label).resolve()
    out_path = Path(args.out).resolve()
    json_path = Path(args.json).resolve()

    # 硬门 1 前值：主表零改动
    main_path = OUT_DIR / "Q1_感官评分.csv"
    main_md5_before = md5(main_path)
    oof_md5_before = md5(oof_path)
    assert main_md5_before == MAIN_SCORE_MD5, f"主表 md5 已变（开工前）：{main_md5_before}"
    assert oof_md5_before == OOF_MD5, f"OOF 表 md5 已变（开工前）：{oof_md5_before}"
    say(f"主表 md5 = {main_md5_before}（契约口径，未动）")

    oof = pd.read_csv(oof_path, encoding="utf-8-sig")
    main = pd.read_csv(main_path, encoding="utf-8-sig")
    d4 = pd.read_csv(label_path, encoding="utf-8-sig")
    dims = list(d4.columns[3:])
    assert oof.shape == (N_BEER, N_DIMS + 1) and main.shape == (N_BEER, N_DIMS + 1)
    assert list(oof.columns) == ["beer"] + dims, "OOF 表列名/列序与 4.csv 不一致"
    assert list(main.columns) == ["beer"] + dims, "主表列名/列序与 4.csv 不一致"
    assert list(oof.beer) == list(main.beer) == list(d4.beer), "三表 beer 行序未对齐"
    assert oof[dims].notna().all().all(), "OOF 表存在缺失"

    lo, hi, ms = load_anchors(dims)
    say("锚点 sha256 与 M1 §6 表交叉校验通过")

    aux = np.zeros((N_BEER, N_DIMS), dtype=int)
    params = []
    for j, dim in enumerate(dims):
        x = oof[dim].to_numpy(float)
        y = d4[dim].to_numpy(float)
        mu_pred = float(x.mean())
        sd_pred = float(x.std(ddof=DD))
        mu_label = float(y.mean())
        sd_label = float(y.std(ddof=DD))
        assert sd_pred > 0 and sd_label > 0, f"{dim} 标准差为 0，仿射退化"
        scale = sd_label / sd_pred
        xp = mu_label + (x - mu_pred) * scale
        for i in range(N_BEER):
            aux[i, j] = alr_scalar(xp[i], lo[j], hi[j], ms[j])
        params.append({
            "dim": dim,
            "mu_pred": mu_pred,
            "SD_pred": sd_pred,
            "mu_label": mu_label,
            "SD_label": sd_label,
            "scale": scale,
            "pred_x_min": float(x.min()), "pred_x_max": float(x.max()),
            "restored_min": float(xp.min()), "restored_max": float(xp.max()),
            "anchor_lo": float(lo[j]), "anchor_hi": float(hi[j]),
            "median_score": int(ms[j]),
        })
    say("逐维仿射 + 同锚点 ALR 完成")

    # 硬门 2：逆序对 = 0；Spearman 如实报告
    inv_per_dim = []
    sp_per_dim = []
    for j, dim in enumerate(dims):
        m = main[dim].to_numpy(int)
        g = aux[:, j]
        inv_per_dim.append(inversions(m, g))
        sp_per_dim.append(float(spearmanr(m, g).statistic))
    inv_total = int(sum(inv_per_dim))
    sp_min = float(min(sp_per_dim))
    sp_max = float(max(sp_per_dim))
    say(f"逆序对总数 = {inv_total}；Spearman(辅助表, 主表) min = {sp_min:.6f}，max = {sp_max:.6f}")

    # 硬门 3：全表 7 级
    freq_total = np.bincount(aux.reshape(-1), minlength=7).astype(int)
    all_levels = bool((freq_total > 0).all())
    level_per_dim = [int(len(set(aux[:, j]))) for j in range(N_DIMS)]
    say(f"全表 0–6 频数 = {freq_total.tolist()}；7 级全出现 = {all_levels}")

    # 落盘辅助表：首行表头注释（可读口径定位），数据区 250×51
    out_df = pd.DataFrame(aux, columns=dims)
    out_df.insert(0, "beer", main["beer"].to_numpy(int))
    assert out_df.shape == (N_BEER, N_DIMS + 1)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# 可读口径（保序刻度还原）；与主表 Q1_感官评分.csv 单调同序、仅刻度不同；"
                 "主交付仍是 Q1_感官评分.csv（契约口径）。本表只作刻度还原展示，不改变主表结论。\n")
        out_df.to_csv(fh, index=False, lineterminator="\n")
    say(f"写出辅助表：{out_path}")

    # 参数 JSON
    freq_table = [[int(v) for v in np.bincount(aux[:, j], minlength=7)] for j in range(N_DIMS)]
    payload = {
        "task": "TM3-02",
        "version": "v1.0",
        "generated_by": "编程/产出/脚本/Q1_可读口径.py",
        "generation_command": "python 编程/产出/脚本/Q1_可读口径.py",
        "positioning": "可读口径（保序刻度还原）；主交付仍是 Q1_感官评分.csv（契约口径）；两表单调同序、仅刻度不同",
        "formula": "x' = mu_label + (x - mu_pred) * (SD_label / SD_pred)；再送同一 ALR：clip(floor(round(6(x'-lo)/(hi-lo),10)+0.5),0,6)",
        "ddof": DD,
        "input": {
            "oof": str(oof_path.relative_to(ROOT)).replace(os.sep, "/"),
            "label": str(label_path.relative_to(ROOT)).replace(os.sep, "/"),
            "anchors": "建模/产出/_work/q1_anchors.csv",
            "anchor_sha256": sha256(WORK_DIR / "q1_anchors.csv"),
        },
        "md5": {"main_score": main_md5_before, "oof": oof_md5_before,
                "main_score_after": md5(main_path), "oof_after": md5(oof_path)},
        "dims": [{**p, "freq": freq_table[j], "n_levels_used": level_per_dim[j],
                  "inversions": inv_per_dim[j], "spearman_vs_main": sp_per_dim[j]}
                 for j, p in enumerate(params)],
        "freq_50x7": {"dims": dims, "counts": freq_table},
        "freq_total": {str(k): int(v) for k, v in enumerate(freq_total)},
        "checks": {
            "inversions_total": inv_total,
            "spearman_min": sp_min,
            "spearman_max": sp_max,
            "spearman_dims_below_0_999": int(sum(1 for v in sp_per_dim if v < 0.999)),
            "all_seven_levels_present": all_levels,
            "levels_per_dim_min": int(min(level_per_dim)),
            "levels_per_dim_max": int(max(level_per_dim)),
        },
        "spearman_note": (
            "按任务书指定公式（全方差对齐，SD_label/SD_pred≈2.27）后，辅助表与主表是对同一 OOF 排序的"
            "不同量化：主表弱维只用 2–3 级，把 6 级填满必然改变大量并列/切点，故逐维 Spearman 不可能达到 0.999；"
            "实测 min=0.416757。单调同序由逆序对=0（50/50 维）精确证明。"
            "人类 2026-10-24 裁定：按公式交付并如实报告该值，不改公式、不改锚点。"
        ),
        "adjudication": {
            "date": "2026-10-24",
            "question": "硬门 2 的 Spearman≥0.999 与硬门 3 的『全表 7 级都出现』在指定公式下互斥",
            "ruling": "按公式交付并如实报告（逆序对=0 作为同序证据；Spearman 作为描述统计报最小值）",
        },
    }
    with open(json_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    say(f"写出参数：{json_path}")

    if args.report_json:
        with open(Path(args.report_json), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload["checks"], fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    # 硬门复核（写完后）
    main_md5_after = md5(main_path)
    oof_md5_after = md5(oof_path)
    if main_md5_after != MAIN_SCORE_MD5 or oof_md5_after != OOF_MD5:
        say(f"停机：主表/OOF 表 md5 变化 {main_md5_after} / {oof_md5_after}")
        return 3
    if inv_total > 0:
        say(f"停机：逆序对 {inv_total} > 0，仿射不单调或参数算错")
        return 3
    if not all_levels:
        say(f"如实报告：全表仍有等级为空，频数 {freq_total.tolist()}（任务书 ⑥：不停机，须写明原因）")
        return 4
    say("三硬门复核：主表 md5 未变、逆序对 0、全表 7 级均出现")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
