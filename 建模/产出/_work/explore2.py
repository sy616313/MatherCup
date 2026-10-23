# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 探查 2：1.csv vs 8.xlsx 校准表，逐列 MAE(log10) / MAE(ln)。"""
import numpy as np
import pandas as pd

BASE = "数据/A/"
df1 = pd.read_csv(BASE + "1.csv", encoding="utf-8-sig")
cal = pd.read_excel(BASE + "8.xlsx", sheet_name="Calibrated chemical dataset")

df1 = df1.set_index("beer", drop=False)
cal = cal.set_index("beer", drop=False)
common_beer = df1.index.intersection(cal.index)
print("matched beers:", len(common_beer), "of", len(df1), "/", len(cal))

feat1 = [c for c in df1.columns if c not in ("beer", "beer_id", "tasting_category_fine")]
featc = [c for c in cal.columns if c not in ("beer", "beer_id", "tasting_category_fine")]
shared = [c for c in feat1 if c in featc]
print("1.csv features:", len(feat1), " cal features:", len(featc), " shared:", len(shared))

rows = []
for c in shared:
    x = pd.to_numeric(df1.loc[common_beer, c], errors="coerce")
    y = pd.to_numeric(cal.loc[common_beer, c], errors="coerce")
    m = x.notna() & y.notna() & (y > 0)
    if m.sum() < 5:
        rows.append((c, int(m.sum()), np.nan, np.nan))
        continue
    xv, yv = x[m].to_numpy(float), y[m].to_numpy(float)
    mae10 = float(np.mean(np.abs(xv - np.log10(yv))))
    maeln = float(np.mean(np.abs(xv - np.log(yv))))
    rows.append((c, int(m.sum()), mae10, maeln))

r = pd.DataFrame(rows, columns=["field", "n", "mae_log10", "mae_ln"])
r["better"] = np.where(r.mae_log10 < r.mae_ln, "log10", "ln")
r["exact10"] = r.mae_log10 < 1e-6
r["exact_ln"] = r.mae_ln < 1e-6
print("\ncolumns compared:", len(r))
print("log10 better:", int((r.better == "log10").sum()), "/ ln better:", int((r.better == "ln").sum()))
print("exact log10:", int(r.exact10.sum()), " exact ln:", int(r.exact_ln.sum()))
print("\n-- worst 10 by mae_log10 --")
print(r.sort_values("mae_log10", ascending=False).head(10).to_string(index=False))
print("\n-- best exact log10 list --")
print(", ".join(r.loc[r.exact10, "field"].tolist()))
print("\n-- n range --", r.n.min(), r.n.max())
print("\n-- cal value ranges (first 5 shared) --")
for c in shared[:5]:
    y = pd.to_numeric(cal[c], errors="coerce").dropna()
    print(f"{c:28s} min={y.min():.4g} med={y.median():.4g} max={y.max():.4g}")
r.to_csv("建模/产出/_work/base_check.csv", index=False, encoding="utf-8")
