# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 探查 3：不可精确反解列的偏差统计 + 问题列抽样。"""
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
    m = x.notna() & y.notna() & (y > 0)
    xv, yv = x[m].to_numpy(float), y[m].to_numpy(float)
    d = xv - np.log10(yv)
    rows.append(dict(field=c, n=int(m.sum()), mean=d.mean(), median=float(np.median(d)),
                     std=d.std(ddof=1) if len(d) > 1 else 0.0,
                     mae10=float(np.abs(d).mean()), mae_ln=float(np.abs(xv - np.log(yv)).mean())))

r = pd.DataFrame(rows)
r["exact"] = r.mae10 < 1e-6
bad = r[~r.exact].sort_values("mean")
print("total:", len(r), "exact:", int(r.exact.sum()), "inexact:", int((~r.exact).sum()))
print("inexact mean range: %.2f .. %.2f" % (bad["mean"].min(), bad["mean"].max()))
print("inexact std  range: %.2f .. %.2f" % (bad["std"].min(), bad["std"].max()))
print("inexact median<=1.5:", int((bad["median"].abs() <= 1.5).sum()), "/", len(bad))
print("\n-- inexact columns --")
print(bad[["field", "n", "mean", "median", "std", "mae10"]].to_string(index=False, float_format=lambda v: f"{v:9.3f}"))

print("\n-- gamma.nonalactone raw sample --")
c = "gamma.nonalactone"
x = pd.to_numeric(df1[c], errors="coerce").dropna()
y = pd.to_numeric(cal[c], errors="coerce").dropna()
print("1.csv:", x.describe()[["min", "50%", "max"]].round(3).to_dict())
print("8.xlsx:", y.describe()[["min", "50%", "max"]].round(3).to_dict())
print("log10(y)-median:", round(float(np.log10(y.replace(0, np.nan)).median()), 3))
r.to_csv("建模/产出/_work/base_stats.csv", index=False, encoding="utf-8")
