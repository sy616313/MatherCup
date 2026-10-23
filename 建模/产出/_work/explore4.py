# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 探查 4：三个假设同测 —— x=log10 y / x=ln y / x=y（原始量纲）。"""
import numpy as np
import pandas as pd

BASE = "数据/A/"
df1 = pd.read_csv(BASE + "1.csv", encoding="utf-8-sig").set_index("beer")
cal = pd.read_excel(BASE + "8.xlsx", sheet_name="Calibrated chemical dataset").set_index("beer")
feat1 = [c for c in df1.columns if c not in ("beer_id", "tasting_category_fine")]
shared = [c for c in feat1 if c in cal.columns]

rows = []
for c in shared:
    x = pd.to_numeric(df1[c], errors="coerce")
    y = pd.to_numeric(cal[c], errors="coerce")
    m = x.notna() & y.notna()
    xv, yv = x[m].to_numpy(float), y[m].to_numpy(float)
    pos = yv > 0
    mae_id = float(np.mean(np.abs(xv - yv)))
    mae10 = float(np.mean(np.abs(xv[pos] - np.log10(yv[pos])))) if pos.sum() else np.nan
    maeln = float(np.mean(np.abs(xv[pos] - np.log(yv[pos])))) if pos.sum() else np.nan
    rows.append(dict(field=c, n=int(m.sum()), n_pos=int(pos.sum()), mae_id=mae_id,
                     mae_log10=mae10, mae_ln=maeln))

r = pd.DataFrame(rows)
def tag(row):
    if row.mae_log10 < 1e-6:
        return "log10"
    if row.mae_id < 1e-9:
        return "identity"
    return "neither"
r["kind"] = r.apply(tag, axis=1)
print(r.kind.value_counts().to_string())
print("\n-- neither columns --")
print(r[r.kind == "neither"][["field", "n", "mae_id", "mae_log10", "mae_ln"]].to_string(index=False, float_format=lambda v: f"{v:10.4g}"))
print("\n-- identity columns --")
print(", ".join(r.loc[r.kind == "identity", "field"].tolist()))
r.to_csv("建模/产出/_work/base_3hyp.csv", index=False, encoding="utf-8")
