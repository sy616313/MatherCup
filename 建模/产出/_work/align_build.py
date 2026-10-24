# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 构建 231↔231 化合物名称对齐并输出 CSV。"""
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
    for a, b in (("α", "alpha"), ("β", "beta"), ("γ", "gamma"), ("î±", "alpha"), ("î²", "beta"),
                 ("’", "'"), ("–", "-"), ("—", "-")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "", s)


inv_node = {}
for c in nodes:
    inv_node.setdefault(norm(c), []).append(c)

mapping, how = {}, {}
for f in feats:
    if norm(f) in inv_node:
        mapping[f], how[f] = inv_node[norm(f)][0], "自动"

wb8 = openpyxl.load_workbook(BASE + "8.xlsx", data_only=True)
ws8 = wb8["Sensory thresholds"]
hdr = [ws8.cell(1, c).value for c in range(1, ws8.max_column + 1)]
iR, iC = hdr.index("field_name_R"), hdr.index("chemical_name")
bridge = {}
for r in range(2, ws8.max_row + 1):
    rn, cn = ws8.cell(r, iR + 1).value, ws8.cell(r, iC + 1).value
    if rn and cn:
        bridge[norm(rn)] = str(cn)

for f in feats:
    if f in mapping:
        continue
    chem = bridge.get(norm(f))
    if chem and norm(chem) in inv_node:
        mapping[f], how[f] = inv_node[norm(chem)][0], "人工"

# 人工兜底（仅剩拼写/希腊字母差异时使用）
MANUAL = {
    "X4.8.alpha.epoxy.caryophyllane": "4,8-α-epoxy-caryophyllane",
    "X.E..alpha.ionone": "E-α-ionone",
    "X14.hydroxy.alpha.humulene": "14-hydroxy-α-humulene",
}
for f, t in MANUAL.items():
    if f not in mapping:
        mapping[f], how[f] = t, "人工"

print("mapped:", len(mapping))
dups = pd.Series([v for v in mapping.values()]).value_counts()
print("duplicated targets:", dups[dups > 1].to_dict())
missing_nodes = [n for n in nodes if n not in set(mapping.values())]
print("nodes not used:", missing_nodes)
print("by method:", pd.Series(how).value_counts().to_dict())

NOTE = {
    "dihydroisocaryophyllene.epoxide": "8.xlsx 该 R 名的 chemical_name 即 Tobacarol（源表命名不一致）",
    "selin.11.en.4.alpha.ol": "8.xlsx 该 R 名的 chemical_name 即 Kongol（源表命名不一致）",
    "X2.ethylhexylsalicylate": "8.xlsx 把 salicylate 写作 acrylate（源表命名不一致）",
}
rows = []
for f in feats:
    if how.get(f) == "人工":
        note = NOTE.get(f, "经 8.xlsx/Sensory thresholds 桥接（field_name_R→chemical_name）")
    else:
        note = "归一化后与 2.csv 节点名完全相同"
    rows.append({"1csv字段": f, "2csv节点名": mapping.get(f, ""), "匹配方式": how.get(f, "未匹配"), "备注": note})
out = pd.DataFrame(rows)
out.to_csv("建模/产出/化合物名称对齐-M1.csv", index=False, encoding="utf-8", lineterminator="\n")
print("written rows:", len(out))
print(out["匹配方式"].value_counts().to_dict())
