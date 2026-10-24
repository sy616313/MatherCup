# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 计算全部口径数字：三分计数、底数、负值、阈值表、50 维映射骨架。"""
import json
import re

import numpy as np
import openpyxl
import pandas as pd

BASE = "数据/A/"
meta = ("beer", "beer_id", "tasting_category_fine")
df1 = pd.read_csv(BASE + "1.csv", encoding="utf-8-sig")
cal = pd.read_excel(BASE + "8.xlsx", sheet_name="Calibrated chemical dataset")

# ---------- 1. 三分计数 ----------
num_cols = [c for c in df1.columns if pd.api.types.is_numeric_dtype(df1[c])]
feat_cols = [c for c in df1.columns if c not in meta]
facts = {
    "shape": list(df1.shape),
    "n_numeric": len(num_cols),
    "n_feature": len(feat_cols),
    "n_samples": int(df1.shape[0]),
    "n_sum": len([c for c in feat_cols if c.endswith("_sum")]),
    "sum_names": [c for c in feat_cols if c.endswith("_sum")],
    "n_kcal": len([c for c in feat_cols if c == "kcalperc"]),
    "n_single": len(feat_cols) - len([c for c in feat_cols if c.endswith("_sum")]) - 1,
    "n_missing": int(df1[feat_cols].isna().sum().sum()),
    "miss_rate": float(df1[feat_cols].isna().sum().sum() / (df1.shape[0] * len(feat_cols))),
    "n_cols_with_na": int((df1[feat_cols].isna().sum() > 0).sum()),
    "n_neg_cells": int((df1[feat_cols] < 0).sum().sum()),
}

# ---------- 2. 底数：逐列 MAE ----------
d1 = df1.set_index("beer")
c1 = cal.set_index("beer")
shared = [c for c in feat_cols if c in c1.columns]
base_rows = []
for c in shared:
    x = pd.to_numeric(d1[c], errors="coerce")
    y = pd.to_numeric(c1[c], errors="coerce")
    m = x.notna() & y.notna() & (y > 0)
    xv, yv = x[m].to_numpy(float), y[m].to_numpy(float)
    d = xv - np.log10(yv)
    base_rows.append(dict(field=c, n=int(m.sum()),
                          mae_log10=float(np.abs(d).mean()),
                          mae_ln=float(np.abs(xv - np.log(yv)).mean()),
                          mean=float(d.mean()), median=float(np.median(d)),
                          std0=float(d.std(ddof=0)), std1=float(d.std(ddof=1)) if len(d) > 1 else 0.0,
                          n_neg_in_x=int((xv < 0).sum())))
bdf = pd.DataFrame(base_rows)
bdf["exact10"] = bdf.mae_log10 < 1e-6
bdf.to_csv("建模/产出/_work/base_table.csv", index=False, encoding="utf-8", lineterminator="\n")

neg_examples = []
for c in bdf.loc[bdf.exact10, "field"].head(0):
    pass
for c in ["acetaldehyde", "ethyl_acetate", "linalool"]:
    x = pd.to_numeric(d1[c], errors="coerce")
    y = pd.to_numeric(c1[c], errors="coerce")
    m = x.notna() & y.notna() & (x < 0)
    if m.any():
        i = x[m].index[0]
        neg_examples.append(dict(field=c, beer=int(i), x=float(x[i]), y=float(y[i]),
                                 log10=float(np.log10(y[i]))))

facts.update({
    "n_shared": len(shared),
    "n_exact10": int(bdf.exact10.sum()),
    "n_log10_better": int((bdf.mae_log10 < bdf.mae_ln).sum()),
    "inexact_mean_min": float(bdf.loc[~bdf.exact10, "mean"].min()),
    "inexact_mean_max": float(bdf.loc[~bdf.exact10, "mean"].max()),
    "inexact_std0_min": float(bdf.loc[~bdf.exact10, "std0"].min()),
    "inexact_std0_max": float(bdf.loc[~bdf.exact10, "std0"].max()),
    "inexact_median_le15": int((bdf.loc[~bdf.exact10, "median"].abs() <= 1.5).sum()),
    "neg_examples": neg_examples,
    "cal_shape": list(cal.shape),
})

# ---------- 3. 阈值表 ----------
wb8 = openpyxl.load_workbook(BASE + "8.xlsx", data_only=True)
ws = wb8["Sensory thresholds"]
hdr = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
idx = {h: i + 1 for i, h in enumerate(hdr)}
rows = []
for r in range(2, ws.max_row + 1):
    tm = ws.cell(r, idx["threshold_mean"]).value
    tm2 = ws.cell(r, idx["threshold_median"]).value
    if isinstance(tm, (int, float)) or isinstance(tm2, (int, float)):
        rows.append(dict(row=r,
                         field_py=ws.cell(r, idx["field_name_python"]).value,
                         field_R=ws.cell(r, idx["field_name_R"]).value,
                         chem=ws.cell(r, idx["chemical_name"]).value,
                         unit=ws.cell(r, idx["unit"]).value,
                         calibrated=ws.cell(r, idx["calibrated"]).value,
                         off=ws.cell(r, idx["off_flavors"]).value,
                         tmean=tm, tmedian=tm2))
tdf = pd.DataFrame(rows)
facts["n_threshold_rows"] = len(tdf)
facts["threshold_preview"] = tdf.head(10).to_dict("records")

# ---------- 4. 50 维映射骨架 ----------
wb3 = openpyxl.load_workbook(BASE + "3.xlsx", data_only=False)
ws3 = wb3["summary"]
sum_hdr = [(openpyxl.utils.get_column_letter(c), ws3.cell(1, c).value, ws3.cell(2, c).value)
           for c in range(2, 52)]
df4 = pd.read_csv(BASE + "4.csv", encoding="utf-8-sig")
cols4 = [c for c in df4.columns if c not in meta]
map_rows = []
for i, c4 in enumerate(cols4):
    letter, sh, formula = sum_hdr[i]
    cell = re.search(r"\$([A-Z]+)\$(\d+)", formula or "")
    map_rows.append(dict(i=i + 1, c4=c4, summary=sh, letter=letter,
                         cell=f"{cell.group(1)}{cell.group(2)}" if cell else "",
                         formula=formula))
mdf = pd.DataFrame(map_rows)
facts["n_map"] = len(mdf)
facts["spelling_diff"] = mdf[mdf.c4 != mdf.summary][["c4", "summary"]].to_dict("records")

# ---------- 5. barnyard ----------
ax = ws3.cell(2, 51).value  # AX2
ar = ws3.cell(2, 45).value  # AR2
facts["barnyard_formula"] = ax
facts["stale_formula"] = ar

with open("建模/产出/_work/facts.json", "w", encoding="utf-8") as f:
    json.dump(facts, f, ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: v for k, v in facts.items() if k not in ("threshold_preview",)}, ensure_ascii=False, indent=1)[:2500])
