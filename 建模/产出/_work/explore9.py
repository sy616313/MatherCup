# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 探查 9：阈值表 43 行明细 + 50 维映射（按名匹配）。"""
import openpyxl
import pandas as pd

BASE = "数据/A/"
wb8 = openpyxl.load_workbook(BASE + "8.xlsx", data_only=True)
ws = wb8["Sensory thresholds"]
hdr = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
idx = {h: i + 1 for i, h in enumerate(hdr)}
rows = []
for r in range(2, ws.max_row + 1):
    tm = ws.cell(r, idx["threshold_mean"]).value
    tm2 = ws.cell(r, idx["threshold_median"]).value
    if isinstance(tm, (int, float)) or isinstance(tm2, (int, float)):
        rows.append([ws.cell(r, idx[k]).value for k in
                     ("field_name_python", "field_name_R", "chemical_name", "calibrated",
                      "origin_paper", "unit", "off_flavors", "threshold_mean", "threshold_median")] + [r])
t = pd.DataFrame(rows, columns=["py", "R", "chem", "calib", "origin", "unit", "off", "mean", "median", "row"])
print("rows with numeric threshold:", len(t))
print(t.to_string(index=False, max_colwidth=28))
