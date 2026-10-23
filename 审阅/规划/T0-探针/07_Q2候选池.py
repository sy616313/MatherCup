# -*- coding: utf-8 -*-
"""07 Q2 Top-3 候选池：**226 个节点**（口径 β，R15 已拍板）。

口径变更沿革：
  - R13：Q2 候选池剔除 4 个 `*_sum`
  - R14：发现 2.csv 另含 `Caloric value`，指出应为 227（R13 字面）
  - **R15（人类 2026-10-23 22:30 拍板）：采用 β —— `Caloric value` 与 4 个 `*_sum`
    同属派生指标，均不进入 Q2 主 Top-3。候选池 = 226。原始数据仍保留。**

因此本脚本现在产出 **226** 行，并保留 α（227）作为对照列，便于审计。

不变的裁决：
  - `1.csv` 原始数据**保留全部 231 个特征**（R13）
  - Q1 的 F0/F1/F2 三组对照实验**不变**（R13）

产出：审阅/规划/T0-Q2候选池.csv（226 行）
运行：python 07_Q2候选池.py
"""
import re
import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "数据" / "A"
OUT = ROOT / "审阅" / "规划" / "T0-Q2候选池.csv"
META = ("beer", "beer_id", "tasting_category_fine")

AGG_PREFIX = "total"
AGG_NAMES = ["Total ester compounds", "Total hop aroma compounds",
             "Total acids", "Total sulfur compounds"]
CALORIC = "Caloric value"
ADOPTED = "beta"          # R15 拍板：β = 226


def norm(s: str) -> str:
    s = str(s).lower()
    for a, b in (("α", "alpha"), ("β", "beta"), ("γ", "gamma")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", s)


def main() -> int:
    d2 = pd.read_csv(BASE / "2.csv", encoding="utf-8-sig", index_col=0)
    nodes = [str(c).strip() for c in d2.columns]
    assert len(nodes) == 231, f"2.csv 节点应为 231，实际 {len(nodes)}"

    d1 = pd.read_csv(BASE / "1.csv", encoding="utf-8-sig", nrows=1)
    feats = [c for c in d1.columns if c not in META]
    assert len(feats) == 231, f"1.csv 建模特征应为 231，实际 {len(feats)}"

    agg = [n for n in nodes if n in AGG_NAMES]
    assert len(agg) == 4, f"应有 4 个聚合节点，实际 {len(agg)}：{agg}"
    extra = [n for n in nodes if n.lower().startswith(AGG_PREFIX) and n not in agg]
    assert not extra, f"存在未登记的 Total 前缀节点：{extra}"
    assert CALORIC in nodes, f"2.csv 未找到 {CALORIC}"

    alpha = [n for n in nodes if n not in agg]                 # 227
    beta = [n for n in alpha if n != CALORIC]                  # 226
    pool = beta if ADOPTED == "beta" else alpha

    print("=== 候选池口径（定义在 2.csv 节点名上）===")
    print(f"  2.csv 节点总数                       = {len(nodes)}")
    print(f"  剔除的 4 个聚合节点                  = {agg}")
    print(f"  剔除的派生属性                       = ['{CALORIC}']")
    print(f"  口径 α（含热量值，已否决）            = {len(alpha)}")
    print(f"  口径 β（R15 拍板，采用）              = {len(beta)}")

    checks = []

    def ck(cond, msg):
        checks.append(cond)
        print(f"  [{'OK' if cond else 'FAIL'}] {msg}")

    print("\n=== 断言校验 ===")
    ck(ADOPTED == "beta", "采用的池口径为 β（R15）")
    ck(len(agg) == 4, "识别出 4 个聚合节点")
    ck(len(alpha) == 227, "口径 α = 227（对照值）")
    ck(len(beta) == 226, "口径 β = 226（采用值）")
    ck(pool == beta and len(pool) == 226, "输出池 = 226")
    ck(all(a not in pool for a in agg), "输出池已剔除 4 个聚合节点")
    ck(CALORIC not in pool, "输出池已剔除 Caloric value")
    ck(len(set(pool)) == 226, "输出池无重复节点")
    ck(len(pool) + 4 + 1 == len(nodes), "226 + 4 聚合 + 1 热量值 = 231（无遗漏）")

    n2 = {norm(x): x for x in nodes}
    matched = sum(1 for f in feats if norm(f) in n2)
    print(f"\n=== 附：1.csv ↔ 2.csv 名称匹配 ===")
    print(f"  自动匹配 {matched}/231；其余 {231 - matched} 个需 M1 人工字典（M1 第 5 件）")

    ok = all(checks)
    print(f"\n断言结果：{sum(checks)}/{len(checks)} 通过 -> {'全部通过' if ok else '存在失败项'}")

    df = pd.DataFrame({
        "序号": range(1, len(pool) + 1),
        "2csv节点名": pool,
        "类别": "单化合物",
        "进入主Top3候选": "是",
    })
    df.to_csv(OUT, index=False, encoding="utf-8", lineterminator="\n")
    print(f"\n已保存 {len(df)} 行 -> {OUT}")
    print("口径：β（R15）。α=227 仅作对照，不再使用。")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
