# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 探查 1：1.csv 三分口径 + 8.xlsx 校准表可比列。只读 数据/A/。"""
import sys
import pandas as pd

BASE = "数据/A/"
df1 = pd.read_csv(BASE + "1.csv", encoding="utf-8-sig")
print("1.csv shape:", df1.shape)
print("columns[:5]:", list(df1.columns[:5]))
print("last 8 cols:", list(df1.columns[-8:]))

meta = [c for c in df1.columns if df1[c].dtype == object]
num = [c for c in df1.columns if c not in meta]
print("meta cols:", meta)
print("numeric cols:", len(num))
print("nan in numeric:", int(df1[num].isna().sum().sum()))
print("sum-like:", [c for c in num if c.endswith("_sum")])
print("kcal:", [c for c in num if "kcal" in c.lower()])

cal = pd.read_excel(BASE + "8.xlsx", sheet_name="Calibrated chemical dataset")
print("\ncalibrated shape:", cal.shape)
print("cal cols:", list(cal.columns)[:12], "...")
print("cal head beer:", cal.iloc[:3, 0].tolist())

print("\n1.csv beer head:", df1["beer"].head(3).tolist())
print("sets equal:", set(df1["beer"]) == set(cal.iloc[:, 0]))
