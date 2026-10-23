# -*- coding: utf-8 -*-
"""01 A题体检：各附件表的形状、缺失、取值范围。

用途：T0 选题判据（数据友好度）。
运行：python 01_A体检.py
依赖：pandas / numpy
数据：题目/_extracted/A/附件/  （相对仓库根目录）
"""
import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 相对仓库根目录定位；允许用环境变量 MMC_DATA 覆盖
ROOT = Path(__file__).resolve().parents[3]
BASE = Path(os.environ.get("MMC_DATA", ROOT / "数据" / "A"))


def main():
    print(f"数据目录: {BASE}")
    if not BASE.exists():
        print("!! 数据目录不存在，请先解压赛道 A 附件，或用 MMC_DATA 指定")
        return 1

    for name in ["1.csv", "2.csv", "4.csv", "5.csv", "6.csv", "7.csv"]:
        f = BASE / name
        if not f.exists():
            print(f"=== {name} === 缺失")
            continue
        df = pd.read_csv(f, encoding="utf-8-sig")
        print(f"=== {name} === shape={df.shape}")
        print("  前8列 :", [str(c)[:26] for c in df.columns[:8]])
        print("  后4列 :", [str(c)[:26] for c in df.columns[-4:]])
        num = df.select_dtypes(include=[np.number])
        if num.shape[1]:
            miss = df.isna().sum().sum()
            print(f"  数值列={num.shape[1]}  缺失={miss} ({miss / df.size * 100:.2f}%)")
            print(f"  取值范围: min={np.nanmin(num.values):.3f}  max={np.nanmax(num.values):.3f}")

    x3 = pd.ExcelFile(BASE / "3.xlsx")
    print(f"=== 3.xlsx === sheets={x3.sheet_names}")
    x8 = pd.ExcelFile(BASE / "8.xlsx")
    print(f"=== 8.xlsx === sheets={x8.sheet_names}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
