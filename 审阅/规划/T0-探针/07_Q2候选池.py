# -*- coding: utf-8 -*-
"""07 Q2 Top-3 候选池：227 个节点清单 + 数量断言（R13 字面口径）。

第 2 轮审阅第 1 条指出候选池应为 227 而非 226。本脚本确立并断言该口径。

重要口径判断：
  Q2 的共表达图由 2.csv 构建，因此**候选池必须定义在 2.csv 的节点名上**。
  实测 2.csv 共 231 个节点 = 226 个单化合物 + 1 个 Caloric value + 4 个 Total 聚合节点。
  剔除 4 个 Total 聚合节点后 -> **227 个候选节点**（含 Caloric value）。

  口径 α（R13 字面，采用）：剔除 4 个 `Total*` -> 227
  口径 β（需人类出 R14 变更）：再剔除 Caloric value -> 226

另附一项 M1 待办（不阻塞选口径）：
  1.csv 与 2.csv 命名体系不同（如 `X2.3.butanedione` vs `2,3-butanedione`），
  自动可匹配 151/231，其余 80 个需人工字典。该字典列为 M1 交付项。

产出：审阅/规划/T0-Q2候选池.csv（227 行）
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

AGG_PREFIX = "total"        # 2.csv 的聚合节点以 Total 开头
AGG_NAMES = ["Total ester compounds", "Total hop aroma compounds",
             "Total acids", "Total sulfur compounds"]
CALORIC = "Caloric value"


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

    # 聚合节点：优先用已知名单，再用 Total 前缀兜底
    agg = [n for n in nodes if n in AGG_NAMES]
    assert len(agg) == 4, f"应有 4 个聚合节点，实际 {len(agg)}：{agg}"
    extra_agg = [n for n in nodes if n.lower().startswith(AGG_PREFIX) and n not in agg]
    assert not extra_agg, f"存在未登记的 Total 前缀节点：{extra_agg}"

    alpha = [n for n in nodes if n not in agg]                       # 227
    beta = [n for n in alpha if n != CALORIC]                        # 226

    print("=== 候选池口径（定义在 2.csv 节点名上）===")
    print(f"  2.csv 节点总数                 = {len(nodes)}")
    print(f"  剔除的 4 个聚合节点            = {agg}")
    print(f"  口径 α（R13 字面，含热量值）    = {len(alpha)}")
    print(f"  口径 β（需 R14，剔除热量值）    = {len(beta)}")

    checks = []

    def ck(cond, msg):
        checks.append(cond)
        print(f"  [{'OK' if cond else 'FAIL'}] {msg}")

    print("\n=== 断言校验 ===")
    ck(len(agg) == 4, "识别出 4 个聚合节点")
    ck(len(alpha) == 227, "口径 α = 227")
    ck(len(beta) == 226, "口径 β = 226")
    ck(all(a not in alpha for a in agg), "α 已剔除全部 4 个聚合节点")
    ck(CALORIC in alpha, "α 保留 Caloric value（R13 字面口径）")
    ck(CALORIC not in beta, "β 已剔除 Caloric value")
    ck(len(set(alpha)) == 227, "α 无重复节点")
    ck(len(alpha) + 4 == len(nodes), "α + 4 = 231（无遗漏）")

    # 1.csv <-> 2.csv 名称匹配情况（M1 待办，不作阻塞断言）
    n2 = {norm(x): x for x in nodes}
    matched = sum(1 for f in feats if norm(f) in n2)
    print(f"\n=== 附：1.csv ↔ 2.csv 名称匹配情况 ===")
    print(f"  自动匹配 {matched}/231；其余 {231 - matched} 个需 M1 人工字典（M1 交付项）")

    ok = all(checks)
    print(f"\n断言结果：{sum(checks)}/{len(checks)} 通过 -> {'全部通过' if ok else '存在失败项'}")

    df = pd.DataFrame({
        "序号": range(1, len(alpha) + 1),
        "2csv节点名": alpha,
        "类别": ["派生-热量值" if n == CALORIC else "单化合物" for n in alpha],
        "口径α保留": "是",
        "口径β保留": ["否" if n == CALORIC else "是" for n in alpha],
    })
    df.to_csv(OUT, index=False, encoding="utf-8", lineterminator="\n")
    print(f"\n已保存 {len(df)} 行 -> {OUT}")
    print("提示：本文件按口径 α（227）生成。若人类裁定 β（226），须先出 R14 再改本脚本重跑。")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
