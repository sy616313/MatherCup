# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 探查 6：评分卡 beer_1 布局（含 AG 列行号 ↔ 属性） + 8.xlsx 三个 sheet。"""
import openpyxl

BASE = "数据/A/"
wb3 = openpyxl.load_workbook(BASE + "3.xlsx", data_only=False)
ws1 = wb3["beer_1"]
print("== beer_1 关键单元格（行 40-101，列 P..AH 非空） ==")
for r in range(40, 102):
    vals = []
    for c in range(15, 35):
        v = ws1.cell(r, c).value
        if v is not None:
            vals.append(f"{openpyxl.utils.get_column_letter(c)}{r}={v!r}")
    if vals:
        print(" | ".join(vals))

ws = wb3["summary"]
print("\n== summary 第 12-13 行 ==")
for r in (12, 13):
    vals = [f"{openpyxl.utils.get_column_letter(c)}{r}={ws.cell(r,c).value}" for c in range(1, 8)]
    print(" | ".join(vals))

wb8 = openpyxl.load_workbook(BASE + "8.xlsx", data_only=True)
for sh in ("Sensory names", "Sensory thresholds"):
    ws8 = wb8[sh]
    print(f"\n== 8.xlsx/{sh} dims={ws8.dimensions} ==")
    for r in range(1, min(ws8.max_row, 14) + 1):
        vals = [str(ws8.cell(r, c).value) for c in range(1, min(ws8.max_column, 8) + 1)]
        print(" | ".join(v if v != "None" else "" for v in vals))
