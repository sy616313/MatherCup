# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 交付前机械自查（写进 自检-M1.md 的证据来源）。"""
import pathlib
import re

import pandas as pd

OUT = pathlib.Path("建模/产出")
files = ["口径规范-M1.md", "维度映射-M1.md", "Q1标定规则-M1.md", "缺陷阈值表-M1.csv",
         "化合物名称对齐-M1.csv", "缺陷阈值缺口-M1.md", "阈值检索-M1.md"]

print("== 文件存在与编码 ==")
for f in files:
    p = OUT / f
    raw = p.read_bytes()
    print(f"{f:28s} {len(raw):7d} B  BOM={raw.startswith(b'\xef\xbb\xbf')}  CRLF={b'\r\n' in raw}")

print("\n== 验收 1：三分口径复算 ==")
d1 = pd.read_csv("数据/A/1.csv", encoding="utf-8-sig")
num = [c for c in d1.columns if pd.api.types.is_numeric_dtype(d1[c])]
miss = int(d1[[c for c in d1.columns if c not in ("beer", "beer_id", "tasting_category_fine")]].isna().sum().sum())
print("shape", d1.shape, "numeric", len(num), "features", d1.shape[1] - 3,
      "missing", miss, "rate%% %.4f" % (miss / (250 * 231) * 100))

print("\n== 验收 5：维度映射 50 行 / 字段与列序 ==")
df4 = pd.read_csv("数据/A/4.csv", encoding="utf-8-sig")
cols4 = [c for c in df4.columns if c not in ("beer", "beer_id", "tasting_category_fine")]
txt = (OUT / "维度映射-M1.md").read_text(encoding="utf-8")
sec1 = txt.split("## 二")[0]          # 只统计 §一
rows = [l for l in sec1.splitlines() if re.match(r"\| \d+ \|", l)]
ok = all(f"`{c}`" in rows[i] for i, c in enumerate(cols4))
print("表行数:", len(rows), "| 字段与列序逐行一致:", ok, "| 行数==50:", len(rows) == 50)
print("§二 是否残留占位 ?:", "?" in txt.split("## 三")[0].split("## 二")[1])

print("\n== 验收 10：231 行对齐 ==")
al = pd.read_csv(OUT / "化合物名称对齐-M1.csv", encoding="utf-8")
print("行数:", len(al), "空值:", int(al.isna().sum().sum()), "去重后:", al["2csv节点名"].nunique())
print("匹配方式:", al["匹配方式"].value_counts().to_dict())

print("\n== 验收 9：阈值表 + 缺口区 ==")
th = pd.read_csv(OUT / "缺陷阈值表-M1.csv", encoding="utf-8")
print("主表行数:", len(th), "(应为 9 = 7 原生 + 2 外部)；缺单位:", int(th["单位"].isna().sum()), "缺出处:", int(th["出处"].isna().sum()),
      "| 来源分级:", th["来源分级"].value_counts().to_dict())
gap = (OUT / "缺陷阈值缺口-M1.md").read_text(encoding="utf-8")
print("缺口区行数(G1-G3):", gap.count("| G"))

print("\n== 验收 11：未决措辞扫描 ==")
bad_words = ["待定", "略", "同上", "见前文", "TODO", "TBD"]
for f in files:
    t = (OUT / f).read_text(encoding="utf-8")
    hits = {w: t.count(w) for w in bad_words if w in t}
    print(f"{f:28s} {hits if hits else 'clean'}")

print("\n== 验收 2/3/4 支撑数据 ==")
b = pd.read_csv(OUT / "_work/base_table.csv")
print("可比列:", len(b), "log10 更优:", int((b.mae_log10 < b.mae_ln).sum()), "精确:", int(b.exact10.sum()))
print("非精确列:", int((~b.exact10).sum()),
      "mean范围: %.3f~%.3f" % (b.loc[~b.exact10, "mean"].min(), b.loc[~b.exact10, "mean"].max()),
      "std0范围: %.3f~%.3f" % (b.loc[~b.exact10, "std0"].min(), b.loc[~b.exact10, "std0"].max()),
      "最小 n:", int(b.n.min()), "对应列:", b.loc[b.n.idxmin(), "field"])
