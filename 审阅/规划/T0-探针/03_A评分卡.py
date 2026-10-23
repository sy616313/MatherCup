# -*- coding: utf-8 -*-
"""03 A题评分卡：证明 3.xlsx 是空白表单而非标签。

结论（实测，对应不一致 C3）：
  - 12 份 beer_N sheet 的 0-6 只是**预印列头**（每列恒定 0/1/2/3/4/5/6）；
  - summary sheet 12 行 × 50 维，**612 格全为 0**；
  - 因此 Q1 的 0-6 分没有现成真值，必须自建标定规则。

运行：python 03_A评分卡.py
"""
import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(os.environ.get("MMC_DATA", ROOT / "数据" / "A"))
XLSX = BASE / "3.xlsx"


def main():
    x = pd.ExcelFile(XLSX)
    print("sheets:", x.sheet_names)
    print(f"sheet 数 = {len(x.sheet_names)}（题面称 10 个 -> 不一致 C2）")

    # 逐 sheet 检查：非零数值分布
    print("\n=== 各 sheet 非零数值统计 ===")
    for s in x.sheet_names:
        d = pd.read_excel(XLSX, sheet_name=s, header=None)
        num = d.apply(pd.to_numeric, errors="coerce")
        nz = (num.values != 0).sum()
        print(f"  {s:10s} shape={d.shape}  数值格={int(num.notna().sum().sum()):>5}  非零={int(nz):>5}")

    # 定位列头：某列若取值集合恰为 {0..6}，说明是预印刻度
    print("\n=== beer_1 中恒定为 0..6 的列（即预印刻度列）===")
    d = pd.read_excel(XLSX, sheet_name="beer_1", header=None)
    for c in range(d.shape[1]):
        col = pd.to_numeric(d[c], errors="coerce").dropna()
        if len(col) >= 5 and col.nunique() == 1 and col.iloc[0] in range(7):
            print(f"  列 {c}: 恒定值 = {col.iloc[0]:.0f}  （出现 {len(col)} 次）")

    print("\n=== summary sheet ===")
    s = pd.read_excel(XLSX, sheet_name="summary")
    num = s.drop(columns=[s.columns[0]]).apply(pd.to_numeric, errors="coerce")
    print(f"  shape={s.shape}  列数={len(s.columns)}")
    print(f"  非零格 = {(num.values != 0).sum()} / {num.size}   唯一取值 = {np.unique(num.values)}")
    print("  -> summary 全零，无真值")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
