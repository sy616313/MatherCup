# -*- coding: utf-8 -*-
"""04 A题相关阵判别：2.csv 到底是 Spearman 还是 Pearson？

结论（实测，对应不一致 C1）：
  用 1.csv 复算可映射化合物的相关阵，与 2.csv 逐格比较：
    Spearman 平均绝对差 ≈ 0.0005
    Pearson  平均绝对差 ≈ 0.0735
  => 2.csv 是 **Spearman**。题面写的"皮尔逊"错误，数据说明.txt 正确。
  Q2 的共表达图必须按 Spearman 建。

运行：python 04_A相关阵.py
"""
import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(os.environ.get("MMC_DATA", ROOT / "数据" / "A"))


def main():
    d1 = pd.read_csv(BASE / "1.csv", encoding="utf-8-sig")
    d2 = pd.read_csv(BASE / "2.csv", encoding="utf-8-sig", index_col=0)
    x8 = pd.read_excel(BASE / "8.xlsx", sheet_name="Sensory thresholds")

    print(f"2.csv shape={d2.shape}")
    print(f"  对称={np.allclose(d2.values, d2.values.T, equal_nan=True)}  "
          f"对角全1={np.allclose(np.diag(d2.values), 1)}  "
          f"范围=[{np.nanmin(d2.values):.3f}, {np.nanmax(d2.values):.3f}]")

    # 用 8.xlsx 的 chemical_name <-> field_name_python 映射把 2.csv 列名对到 1.csv 列名
    mp = x8.dropna(subset=["field_name_python", "chemical_name"])
    name2py = {str(k).strip().lower(): str(v).strip()
               for k, v in zip(mp["chemical_name"], mp["field_name_python"])}

    meta = ["beer", "beer_id", "tasting_category_fine"]
    X = d1.drop(columns=meta).select_dtypes(include=[np.number])
    X = X.fillna(X.median())

    py_cols = [name2py.get(str(c).strip().lower()) for c in d2.columns]
    keep = [(i, c) for i, c in enumerate(py_cols) if c in X.columns]
    print(f"\n2.csv 可映射 {sum(c is not None for c in py_cols)}/{len(py_cols)}；"
          f"其中能在 1.csv 找到的 {len(keep)} 个")

    if len(keep) < 5:
        print("!! 可匹配化合物过少，无法判别")
        return 1

    idx = [i for i, _ in keep]
    cols = [c for _, c in keep]
    sub = X[cols]

    P = np.corrcoef(sub.values.T)
    S = spearmanr(sub.values).statistic
    ref = d2.values[np.ix_(idx, idx)]

    dp = np.nanmean(np.abs(P - ref))
    ds = np.nanmean(np.abs(S - ref))
    print(f"\nPearson  与 2.csv：平均|差|={dp:.4f}  最大={np.nanmax(np.abs(P - ref)):.4f}")
    print(f"Spearman 与 2.csv：平均|差|={ds:.4f}  最大={np.nanmax(np.abs(S - ref)):.4f}")
    print(f"\n=> 2.csv 更接近：{'Spearman' if ds < dp else 'Pearson'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
