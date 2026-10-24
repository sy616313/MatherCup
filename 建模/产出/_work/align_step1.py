# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 构建 231↔231 化合物名称对齐（自动 + 8.xlsx 桥接 + 人工字典）。"""
import json
import re

import openpyxl
import pandas as pd

BASE = "数据/A/"
df1 = pd.read_csv(BASE + "1.csv", encoding="utf-8-sig", nrows=1)
feats = [c for c in df1.columns if c not in ("beer", "beer_id", "tasting_category_fine")]
df2 = pd.read_csv(BASE + "2.csv", encoding="utf-8-sig", index_col=0)
nodes = list(df2.columns)


def norm(s):
    s = str(s).strip().lower()
    s = (s.replace("α", "alpha").replace("β", "beta").replace("γ", "gamma")
          .replace("’", "'").replace("–", "-").replace("—", "-")
          .replace("î²", "beta"))
    return re.sub(r"[^a-z0-9]+", "", s)


inv_node = {}
for c in nodes:
    inv_node.setdefault(norm(c), []).append(c)

# 1) 归一化精确匹配
mapping = {}
for f in feats:
    if norm(f) in inv_node:
        mapping[f] = inv_node[norm(f)][0]

# 2) 8.xlsx/Sensory thresholds 桥接：field_name_R -> chemical_name -> 节点
wb8 = openpyxl.load_workbook(BASE + "8.xlsx", data_only=True)
ws8 = wb8["Sensory thresholds"]
hdr = [ws8.cell(1, c).value for c in range(1, ws8.max_column + 1)]
iR = hdr.index("field_name_R")
iC = hdr.index("chemical_name")
bridge = {}
for r in range(2, ws8.max_row + 1):
    rname = ws8.cell(r, iR + 1).value
    chem = ws8.cell(r, iC + 1).value
    if rname and chem:
        bridge[norm(rname)] = str(chem)

for f in feats:
    if f in mapping:
        continue
    chem = bridge.get(norm(f))
    if chem and norm(chem) in inv_node:
        mapping[f] = inv_node[norm(chem)][0]

print("after auto+bridge:", len(mapping))
rest = [f for f in feats if f not in mapping]
print("rest:", len(rest))
for f in rest:
    print("  ", f, "->", bridge.get(norm(f)))
