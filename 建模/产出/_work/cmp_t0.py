# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""与 T0-字段映射.csv 逐行比对（验收第 10 条）。"""
import re

import pandas as pd

ref = pd.read_csv("审阅/规划/T0-字段映射.csv", encoding="utf-8-sig")
mine = pd.read_csv("建模/产出/_work/map50.csv", encoding="utf-8")


def cell_of(s):
    m = re.search(r"\$([A-Z]+)\$(\d+)", str(s))
    return f"{m.group(1)}{m.group(2)}" if m else str(s).strip()


same, diffs = 0, []
for _, r in mine.iterrows():
    rr = ref[ref.iloc[:, 2].astype(str).str.strip() == r["c4"]]
    if rr.empty:
        diffs.append((r["c4"], "ref 无此行"))
        continue
    ref_cell = cell_of(rr.iloc[0, 5])
    if ref_cell == r["cell"]:
        same += 1
    else:
        diffs.append((r["c4"], f"ref={ref_cell} mine={r['cell']}"))
print("一致:", same, "/", len(mine))
print("差异:", diffs)
