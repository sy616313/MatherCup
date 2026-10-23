# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""Q1 标定依据 2：4.csv 每列唯一值个数 / 是否 7 级离散。"""
import numpy as np
import pandas as pd

df4 = pd.read_csv("数据/A/4.csv", encoding="utf-8-sig")
meta = ("beer", "beer_id", "tasting_category_fine")
cols = [c for c in df4.columns if c not in meta]
d = df4[cols]
print("nunique per col: min", int(d.nunique().min()), "median", int(d.nunique().median()), "max", int(d.nunique().max()))
print(d.nunique().head(10).to_dict())
c = cols[0]
v = np.sort(d[c].unique())
print(f"\n{c}: {len(v)} unique; first 12:", np.round(v[:12], 3))
print("gaps between consecutive uniques (first 10):", np.round(np.diff(v)[:10], 3))
print("per-col 0.5%/99.5% quantiles sample:", d[cols[:3]].quantile([0.005, 0.995]).round(3).to_dict())
