# -*- coding: utf-8 -*-
"""5.csv / 6.csv 表头差异逐项列出。

在仓库根目录运行：python 建模/产出/_work/diff_labels.py
路径可用环境变量覆盖（缺省值按仓库根目录解析，不写死本机盘符路径）：
  DESKTOP_ATTACH  原始附件目录，缺省 ../题目/_extracted/A/附件
  REPO_DATA       仓库数据目录，缺省 数据/A
"""
import os
import pathlib

import pandas as pd

A = pathlib.Path(os.environ.get("DESKTOP_ATTACH", "../题目/_extracted/A/附件"))
B = pathlib.Path(os.environ.get("REPO_DATA", "数据/A"))

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
