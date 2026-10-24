# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""列出 97 个未自动匹配的特征名。"""
import re

import pandas as pd

df1 = pd.read_csv("数据/A/1.csv", encoding="utf-8-sig", nrows=1)
feats = [c for c in df1.columns if c not in ("beer", "beer_id", "tasting_category_fine")]
df2 = pd.read_csv("数据/A/2.csv", encoding="utf-8-sig", index_col=0)


def norm(s):
    s = str(s).strip().lower()
    s = (s.replace("α", "alpha").replace("β", "beta").replace("γ", "gamma")
          .replace("’", "'").replace("–", "-").replace("—", "-"))
    return re.sub(r"[^a-z0-9]+", "", s)


inv = {}
for c in df2.columns:
    inv.setdefault(norm(c), []).append(c)

miss = [f for f in feats if norm(f) not in inv]
print(len(miss))
for i, f in enumerate(miss, 1):
    print(f"{i:3d} {f}")
