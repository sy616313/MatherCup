# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""补充事实：identity 列是否有负值；缺失分布；barnyard 对照。"""
import json

import numpy as np
import pandas as pd

BASE = "数据/A/"
meta = ("beer", "beer_id", "tasting_category_fine")
df1 = pd.read_csv(BASE + "1.csv", encoding="utf-8-sig")
feats = [c for c in df1.columns if c not in meta]
b = pd.read_csv("建模/产出/_work/base_table.csv")
ident = b[~b.exact10]
print("33 cols:", len(ident))
neg = {c: int((df1[c] < 0).sum()) for c in ident.field}
print("negatives in 33 cols:", {k: v for k, v in neg.items() if v})
print("max neg:", max(neg.values()))

miss = df1[feats].isna().sum()
print("\ncols with NA:", miss[miss > 0].to_dict())
print("total NA:", int(miss.sum()))

out = {
    "ident_neg_total": int(sum(neg.values())),
    "miss_by_col": {k: int(v) for k, v in miss[miss > 0].items()},
}
json.dump(out, open("建模/产出/_work/facts2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
