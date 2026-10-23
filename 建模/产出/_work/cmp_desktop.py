# -*- coding: utf-8 -*-
"""比较桌面附件与仓库 数据/A 的语义差异（忽略换行差异）。"""
import hashlib
import pathlib

import pandas as pd

A = pathlib.Path(r"C:\Users\33836\Desktop\附件")
B = pathlib.Path(r"C:\Users\33836\Documents\deepseek-harness\default-workspace\MatherCup\数据\A")

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
