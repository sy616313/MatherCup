# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 探查 8：1.csv 231 特征 vs 2.csv 231 节点名，看自动匹配率。"""
import re
import pandas as pd

BASE = "数据/A/"
df1 = pd.read_csv(BASE + "1.csv", encoding="utf-8-sig", nrows=1)
feats = [c for c in df1.columns if c not in ("beer", "beer_id", "tasting_category_fine")]
df2 = pd.read_csv(BASE + "2.csv", encoding="utf-8-sig", index_col=0)
nodes = [c for c in df2.columns]
print("1.csv feats:", len(feats), " 2.csv nodes:", len(nodes), " shape:", df2.shape)

def norm(s):
    s = str(s).strip().lower()
    s = (s.replace("α", "alpha").replace("β", "beta").replace("γ", "gamma")
           .replace("’", "'").replace("’", "'").replace("–", "-").replace("—", "-"))
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s

n1 = {f: norm(f) for f in feats}
n2 = {c: norm(c) for c in nodes}
inv2 = {}
for c, k in n2.items():
    inv2.setdefault(k, []).append(c)

auto = {}
for f, k in n1.items():
    if k in inv2:
        auto[f] = inv2[k][0]
print("exact-normalized auto:", len(auto))

miss = [f for f in feats if f not in auto]
print("missing:", len(miss))
print("first 40 missing:", miss[:40])
print("\nfirst 20 2.csv nodes:", nodes[:20])
