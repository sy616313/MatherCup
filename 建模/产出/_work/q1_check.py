# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""Q1 标定依据：4.csv 50 维的取值范围与分布。"""
import pandas as pd

df4 = pd.read_csv("数据/A/4.csv", encoding="utf-8-sig")
meta = ("beer", "beer_id", "tasting_category_fine")
cols = [c for c in df4.columns if c not in meta]
d = df4[cols]
print("shape:", d.shape)
print("global min/max:", float(d.min().min()), float(d.max().max()))
print("per-col min/max ranges: min=%.4f max=%.4f" % (d.min().min(), d.max().max()))
print("count of values <0:", int((d < 0).sum().sum()), " >6:", int((d > 6).sum().sum()))
print("integer-valued share:", float((d.round(6) % 1 == 0).mean().mean()))
print("\nfirst 5 cols describe:")
print(d.iloc[:, :5].describe().round(3).to_string())
print("\nNA:", int(d.isna().sum().sum()))
