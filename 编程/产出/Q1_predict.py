# -*- coding: utf-8 -*-
"""Q1 推理入口（M3 · TM3-01 · 编程）：载入全量重训模型 → 50 维连续预测

本程序及代码是在人工智能工具辅助下完成的。
AI 工具名称：DeepSeek Harness；版本/型号：deepseek-flash；
开发机构/公司：深度求索（DeepSeek）；版本发布日期：2026-10-24（本次运行所用版本）。

用法（在仓库根目录）：
    python 编程/产出/Q1_predict.py                          # 对 数据/A/1.csv 全表推理
    python 编程/产出/Q1_predict.py --x 某单行.csv --out 编程/临时/单行预测.csv
    python 编程/产出/Q1_predict.py --compare 编程/产出/Q1_感官连续_全量.csv

模型来源（按优先级）：
    1) --model 指定的 joblib；
    2) 编程/临时/Q1_全量模型.joblib（Q1_建模.py 本机缓存，gitignored）；
    3) 编程/产出/模型/Q1_全量模型.joblib（若人工放入）；
    4) 均不存在 → 按 `编程/产出/Q1_特征集定义.json` 的冻结主模型/特征集，
       从 数据/A/1.csv 与 数据/A/4.csv 重建全量模型（确定性，约 20 s）。

口径：输出为 4.csv 原始量纲的连续预测（不做反变换、不做 ALR 分级）；
      与 Q1_感官连续_全量.csv 同口径，可逐格比对。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_PATH = Path(__file__).resolve()
ROOT = Path(os.environ.get("MMC_ROOT", SCRIPT_PATH.parents[2])).resolve()
DATA_DIR = ROOT / "数据" / "A"
OUT_DIR = ROOT / "编程" / "产出"
TMP_DIR = ROOT / "编程" / "临时"
MODEL_CANDIDATES = [
    TMP_DIR / "Q1_全量模型.joblib",
    OUT_DIR / "模型" / "Q1_全量模型.joblib",
]


def say(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_core():
    """动态载入 Q1_建模.py 的冻结管线函数（不执行其 main）。"""
    spec = importlib.util.spec_from_file_location("q1_model_core", OUT_DIR / "Q1_建模.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_package(core, model_arg: str | None):
    import joblib
    if model_arg:
        p = Path(model_arg).resolve()
        assert p.exists(), f"指定的模型文件不存在：{p}"
        say(f"载入模型：{p}")
        return joblib.load(p), str(p)
    for p in MODEL_CANDIDATES:
        if p.exists():
            say(f"载入模型：{p}")
            return joblib.load(p), str(p)
    say("未找到全量模型缓存，按冻结管线重建（确定性）…")
    meta = json.loads((OUT_DIR / "Q1_特征集定义.json").read_text(encoding="utf-8"))
    model_name = meta["model_selection"]["main_model"]
    fs = meta["decision"]["adopted"]
    d1, d4, feats, dims = core.load_base(DATA_DIR / "1.csv", DATA_DIR / "4.csv")
    sets = core.build_feature_sets(feats)
    d1t = core.log_transform(d1, feats)
    full = core.fit_full(model_name, fs, sets, d1t, d4, dims)
    pkg = {k: full[k] for k in ("model", "cols", "imputer", "flag_cols",
                                "mu", "sd", "dims", "model_name", "featureset")}
    return pkg, "重建（无缓存）"


def predict_frame(df: pd.DataFrame, pkg, core) -> pd.DataFrame:
    cols = list(pkg["cols"])
    dims = list(pkg["dims"])
    missing = [c for c in cols if c not in df.columns]
    assert not missing, f"输入缺少特征列：{missing[:5]} …（共 {len(missing)} 列）"
    work = df.copy()
    for c in core.RAW33:
        if c in work.columns:
            work[c] = np.log10(work[c].astype(float) + 1e-6)
    if "tasting_category_fine" in work.columns:
        style = work["tasting_category_fine"].astype(str).to_numpy()
    else:
        style = np.array([""] * len(work))
    Xi = core.impute_frame(work, cols, style, pkg["imputer"])
    flag_cols = [c for c in pkg["flag_cols"]]
    fl = np.column_stack([work[c].isna().to_numpy(float) for c in flag_cols]) \
        if flag_cols else np.zeros((len(work), 0))
    X = np.hstack([Xi, fl])
    X = (X - np.asarray(pkg["mu"])) / np.asarray(pkg["sd"])
    pred = pkg["model"].predict(X)
    out = pd.DataFrame(pred, columns=dims)
    if "beer" in df.columns:
        out.insert(0, "beer", df["beer"].astype(int).to_numpy())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Q1 推理入口（全量模型）")
    ap.add_argument("--x", default=str(DATA_DIR / "1.csv"), help="输入特征表（默认 数据/A/1.csv）")
    ap.add_argument("--out", default=str(TMP_DIR / "Q1_推理输出.csv"),
                    help="输出 CSV（默认 编程/临时/Q1_推理输出.csv，不入库）")
    ap.add_argument("--model", default=None, help="指定全量模型 joblib 路径")
    ap.add_argument("--compare", default=None,
                    help="与参考连续表逐格比对（应指向 编程/产出/Q1_感官连续_全量.csv）")
    args = ap.parse_args()

    core = load_core()
    df = pd.read_csv(args.x, encoding="utf-8-sig")
    say(f"输入：{args.x}（{df.shape[0]} 行 × {df.shape[1]} 列）")
    pkg, src = load_package(core, args.model)
    out = predict_frame(df, pkg, core)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False, encoding="utf-8", lineterminator="\n",
               float_format="%.10f")
    say(f"模型来源：{src}；主模型 {pkg['model_name']} × {pkg['featureset']}")
    say(f"输出：{args.out}（{out.shape[0]} 行 × {out.shape[1]} 列）")

    if args.compare:
        ref = pd.read_csv(args.compare, encoding="utf-8-sig", comment="#")
        # 与落盘文件逐格比（不是与内存全精度数组比），确保比的是"文件对文件"
        written = pd.read_csv(args.out, encoding="utf-8-sig")
        assert ref.shape == written.shape, f"形状不一致：{written.shape} vs {ref.shape}"
        dims = list(pkg["dims"])
        a = written.sort_values("beer")[dims].to_numpy(float)
        b = ref.sort_values("beer")[dims].to_numpy(float)
        exact = int((a == b).sum())
        maxdiff = float(np.abs(a - b).max())
        say(f"逐格比对（文件对文件）：完全相同 {exact}/{a.size} 格；最大绝对差 {maxdiff:.3e}")
        if exact != a.size:
            say("警告：存在非零差异，推理路径未复现全量拟合表")
            return 4
        say("逐格 0 差异：推理入口与 Q1_感官连续_全量.csv 一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
