# -*- coding: utf-8 -*-
"""5.csv / 6.csv 表头差异逐项列出。"""
import pathlib

import pandas as pd

A = pathlib.Path(r"C:\Users\33836\Desktop\附件")
B = pathlib.Path(r"C:\Users\33836\Documents\deepseek-harness\default-workspace\MatherCup\数据\A")

for name in ["5.csv", "6.csv"]:
    a = pd.read_csv(A / name, encoding="utf-8-sig", index_col=0)
    b = pd.read_csv(B / name, encoding="utf-8-sig", index_col=0)
    print("==", name)
    if list(a.index) != list(b.index):
        print("  index 差异:")
        for x, y in zip(a.index, b.index):
            if x != y:
                print(f"    desktop={x!r}   repo={y!r}")
    if list(a.columns) != list(b.columns):
        print("  columns 差异:")
        for x, y in zip(a.columns, b.columns):
            if x != y:
                print(f"    desktop={x!r}   repo={y!r}")
