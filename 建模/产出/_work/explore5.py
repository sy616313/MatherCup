# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 探查 5：3.xlsx/summary 公式布局 + 8.xlsx 感官名/阈值表。"""
import openpyxl

BASE = "数据/A/"
wb3 = openpyxl.load_workbook(BASE + "3.xlsx", data_only=False)
ws = wb3["summary"]
print("summary dims:", ws.dimensions, "max_row", ws.max_row, "max_col", ws.max_column)
for r in range(1, ws.max_row + 1):
    vals = []
    for c in range(1, ws.max_column + 1):
        v = ws.cell(r, c).value
        if v is not None:
            vals.append(f"{openpyxl.utils.get_column_letter(c)}{r}={v}")
    if vals:
        print(" | ".join(vals))
    if r > 6:
        print("... (只打印前 6 行)")
        break

print("\n===== beer_1 布局前 8 行 =====")
ws1 = wb3["beer_1"]
print("dims:", ws1.dimensions)
for r in range(1, 9):
    vals = []
    for c in range(1, 8):
        v = ws1.cell(r, c).value
        if v is not None:
            vals.append(f"{openpyxl.utils.get_column_letter(c)}{r}={v}")
    print(" | ".join(vals))
