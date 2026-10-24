# -*- coding: utf-8 -*-
"""比较题目原始附件与仓库 数据/A 的语义差异（忽略换行差异）。

在仓库根目录运行：python 建模/产出/_work/cmp_desktop.py
路径可用环境变量覆盖（缺省值按仓库根目录解析，不写死本机盘符路径）：
  DESKTOP_ATTACH  原始附件目录，缺省 ../题目/_extracted/A/附件
  REPO_DATA       仓库数据目录，缺省 数据/A
"""
import hashlib
import os
import pathlib

import pandas as pd

A = pathlib.Path(os.environ.get("DESKTOP_ATTACH", "../题目/_extracted/A/附件"))
B = pathlib.Path(os.environ.get("REPO_DATA", "数据/A"))

for name in ["1.csv", "2.csv", "4.csv", "5.csv", "6.csv", "7.csv"]:
    a = pd.read_csv(A / name, encoding="utf-8-sig")
    b = pd.read_csv(B / name, encoding="utf-8-sig")
    same = a.shape == b.shape and a.equals(b)
    print(f"{name:14s} shape {a.shape} == {b.shape} | 内容相同: {same}")

ta = (A / "数据说明.txt").read_text(encoding="utf-8-sig", errors="replace")
tb = (B / "数据说明.txt").read_text(encoding="utf-8-sig", errors="replace")
print("\n数据说明.txt 相同:", ta.strip() == tb.strip(), "len", len(ta), len(tb))
if ta.strip() != tb.strip():
    import difflib
    for line in difflib.unified_diff(tb.splitlines(), ta.splitlines(), "repo", "desktop", lineterm="", n=1):
        print(line)

raw_a = (A / "1.csv").read_bytes()
raw_b = (B / "1.csv").read_bytes()
print("\n1.csv bytes:", len(raw_a), len(raw_b), "| CRLF a/b:", b"\r\n" in raw_a, b"\r\n" in raw_b)
