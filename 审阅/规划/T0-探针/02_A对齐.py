# -*- coding: utf-8 -*-
"""02 A题样本对齐：1.csv / 4.csv / 7.csv 的关联关系与 beer_id 精度问题。

结论（实测，供 T0 选题与 C7 口径用）：
  - 三表均 250 行，`beer` 名可 250/250 完全对齐；
  - `beer_id` 是 13 位 EAN 条码，1.csv 保持整数，4.csv/7.csv 被读成浮点导致精度丢失，
    因此**只能用 `beer` 名关联，禁止用 `beer_id`**。

运行：python 02_A对齐.py
"""
import sys
import os
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(os.environ.get("MMC_DATA", ROOT / "数据" / "A"))


def main():
    d1 = pd.read_csv(BASE / "1.csv", encoding="utf-8-sig")
    d4 = pd.read_csv(BASE / "4.csv", encoding="utf-8-sig")
    d7 = pd.read_csv(BASE / "7.csv", encoding="utf-8-sig")

    print("=== 形状 ===")
    for nm, d in [("1.csv", d1), ("4.csv", d4), ("7.csv", d7)]:
        print(f"  {nm}: {d.shape}")

    print("\n=== beer 名对齐 ===")
    s1, s4, s7 = set(d1["beer"]), set(d4["beer"]), set(d7["beer"])
    print(f"  |1|={len(s1)} |4|={len(s4)} |7|={len(s7)}")
    print(f"  1∩4={len(s1 & s4)}  1∩7={len(s1 & s7)}  4∩7={len(s4 & s7)}")

    print("\n=== beer_id 精度 ===")
    print(f"  1.csv beer_id 例: {d1['beer_id'].head(3).tolist()}")
    print(f"  4.csv beer_id 例: {d4['beer_id'].head(3).tolist()}")
    print(f"  1.csv 唯一 beer_id={d1['beer_id'].nunique()}  4.csv 唯一 beer_id={d4['beer_id'].nunique()}")
    print("  -> 4.csv/7.csv 的 beer_id 已被浮点截断，只能按 beer 名关联")

    print("\n=== 风格分布（1.csv tasting_category_fine）===")
    print(d1["tasting_category_fine"].value_counts().to_string())
    print(f"  共 {d1['tasting_category_fine'].nunique()} 类，平均每类 "
          f"{len(d1) / d1['tasting_category_fine'].nunique():.1f} 个样本（Q3 的数据稀缺依据）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
