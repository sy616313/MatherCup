# -*- coding: utf-8 -*-
"""05 A题可行性基线：化合物 -> 50 个感官维度，Ridge / RandomForest 五折 CV R²。

结论（实测，供 T0 选题与 Q1 方法选择）：
  - RidgeCV（标准化）平均 R² = -2.581，44/50 维为负  -> **线性模型不可用**
  - RandomForest 平均 R² = +0.243，7/50 维 > 0.5      -> 必须走非线性
  - 易预测：acidity/alcohol/acetic/lactic/bitternes（理化列直出）
  - 难预测：stale_hops/clove/barnyard/*_esters_flower（痕量香气，信噪比极低）

运行：python 05_A基线.py       （约 2-5 分钟，取决于机器）
"""
import sys
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(os.environ.get("MMC_DATA", ROOT / "数据" / "A"))
META = ["beer", "beer_id", "tasting_category_fine"]


def main():
    d1 = pd.read_csv(BASE / "1.csv", encoding="utf-8-sig")
    d4 = pd.read_csv(BASE / "4.csv", encoding="utf-8-sig")

    chem = d1.drop(columns=META).select_dtypes(include=[np.number])
    chem = chem.fillna(chem.median())
    Y = d4.drop(columns=META)
    print(f"X={chem.shape}  Y={Y.shape}")

    dims = list(Y.columns)
    kf = KFold(5, shuffle=True, random_state=0)
    res = {"ridge": [], "rf": []}

    for c in dims:
        y = Y[c].values
        models = [
            ("ridge", make_pipeline(StandardScaler(),
                                    RidgeCV(alphas=np.logspace(-2, 3, 20)))),
            ("rf", RandomForestRegressor(n_estimators=300, min_samples_leaf=2,
                                         random_state=0, n_jobs=-1)),
        ]
        for nm, mdl in models:
            pred = cross_val_predict(mdl, chem.values, y, cv=kf)
            res[nm].append(r2_score(y, pred))

    print("\n=== 五折 CV R² 汇总 ===")
    for nm, vals in res.items():
        a = np.array(vals)
        print(f"{nm:6s}: mean={a.mean():+.3f}  median={np.median(a):+.3f}  "
              f">0.5 维数={(a > 0.5).sum()}/{len(a)}  <0 维数={(a < 0).sum()}")

    r = np.array(res["rf"])
    print("\nTop 8 易预测维度（RF）:")
    for i in np.argsort(-r)[:8]:
        print(f"   {dims[i]:18s} {r[i]:+.3f}")
    print("\nTop 5 难预测维度（RF）:")
    for i in np.argsort(r)[:5]:
        print(f"   {dims[i]:18s} {r[i]:+.3f}")

    # 风格 one-hot 是否能提升（仅用 Ridge 做快速对照）
    style = pd.get_dummies(d1["tasting_category_fine"]).values.astype(float)
    X2 = np.hstack([chem.values, style])
    r2s = []
    for c in dims:
        pred = cross_val_predict(
            make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20))),
            X2, Y[c].values, cv=kf)
        r2s.append(r2_score(Y[c].values, pred))
    print(f"\nchem+style (Ridge): mean R²={np.mean(r2s):+.3f}  "
          f"vs chem-only Ridge={np.mean(res['ridge']):+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
