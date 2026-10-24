#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 方案-M3.md 的可替换片段（特征清单、E1/E3 映射表、缺失表）。

AI 使用声明：本脚本由建模角色在 AI 辅助下编写（2026-10-24，TM3-00），
只读 数据/A/ 与 _work 下探针产物，不训练模型。

用法（仓库根目录）：python 建模/产出/_work/gen_m3_tables.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "数据" / "A"
WORK = Path(__file__).resolve().parent
ID_COLS = ("beer", "beer_id", "tasting_category_fine")

# 口径规范-M1.md §5 的 33 个原始量纲列（本脚本按 1.csv 列序过滤，不重算）
RAW33 = {
    "n.hexanol", "X1.alpha.terpineol", "citronellol", "diethyl.succinate", "ethyl.butyrate",
    "hexyl.acetate", "geraniol", "styrene", "ethyl.pentanoate", "X3Z.hexenol",
    "ethyl.isobutyrate", "alpha.humulene", "X.E..beta.ocimene", "Z.nerolidol",
    "X2.ethyl.3.methylpyrazine", "phenylacetaldehyde", "X.E..2.nonenal", "ethyl.nicotinate",
    "furfural", "benzaldehyde", "linalool", "X3.methylbutanal", "eugenol", "benzyl.alcohol",
    "amyl.acetate", "E.caryophyllene", "X5.methylfurfural", "X.E.E..2.4.decadienal",
    "methylpyrazine", "X2.3.butanedione", "X.E..beta.damascenone",
    "X2.methyltetrahydrofuran.3.one", "gamma.nonalactone",
}

E3_NNS_REASON = {
    "stale_hops": "7.csv 的 `stale` 属性经桥接落到 t2n（Aging taste - cardboard），与 t2n 维冲突；stale_hops 维无独立属性",
    "orange": "8.xlsx 中 orange 的长名是 Hops taste - citrus，与 F_hops_citrus 同名，无法唯一判定",
    "clove": "7.csv 的 `clove` 属性经桥接落到 X4vg（4-vinyl guaiacol），与 X4vg 维冲突；clove 维无独立属性",
    "lactic": "7.csv 有 `lactic` 后缀，但 8.xlsx 的 Ratebeer 表无该 R 名，桥接不上",
    "acetic": "7.csv 有 `acetic` 后缀，但 8.xlsx 的 Ratebeer 表无该 R 名，桥接不上",
    "body": "7.csv 的 62 个后缀中没有 body，无属性可用",
    "overall": "7.csv 只有 overall_20（RateBeer 总分），不是感官描述符；无属性可用",
    "A_esters_ethac": "8.xlsx 把 `aroma_fruity`/`taste_fruity` 标到 Esters - nail polish，4.csv 该维可读名却是 Esters - fruity；源表交叉表自相矛盾，不采用",
    "A_esters_fruity": "8.xlsx 把 `aroma_pear`/`taste_pear` 标到 Esters - fruity，与 4.csv 该维撞名，无法唯一判定",
    "F_esters_ethac": "同 A_esters_ethac：8.xlsx 的 `taste_fruity` 标到 Esters - nail polish，与 4.csv 可读名冲突",
    "F_esters_fruity": "同 A_esters_fruity：8.xlsx 的 `taste_pear` 标到 Esters - fruity，与 4.csv 撞名",
}


def wrap(names, per_line=5):
    lines = []
    for i in range(0, len(names), per_line):
        lines.append(", ".join(names[i:i + per_line]))
    return ",\n".join(lines)


def main():
    d1 = pd.read_csv(DATA / "1.csv", encoding="utf-8-sig")
    d4 = pd.read_csv(DATA / "4.csv", encoding="utf-8-sig")
    feats = [c for c in d1.columns if c not in ID_COLS]
    dims = [c for c in d4.columns if c not in ID_COLS]
    sums = [c for c in feats if c.endswith("_sum")]
    f0 = [c for c in feats if c not in sums and c != "kcalperc"]
    f1 = [c for c in feats if c != "kcalperc"]
    raw33 = [c for c in feats if c in RAW33]

    e1 = pd.read_csv(WORK / "m3_e1.csv")
    e3 = pd.read_csv(WORK / "m3_e3.csv")
    e1_cols = pd.read_csv(WORK / "m3_e1_cols.csv")

    rows = ["| # | 6.csv 行名（英文指标） | 1.csv 列名 | 匹配方式 |", "|---|---|---|---|"]
    for i, r in e1.iterrows():
        note = r.note if isinstance(r.note, str) else ""
        method = {"auto": "归一化直配", "syn": "同义词典", "N_ns": "N_ns（无对应列）", "FAIL": "失败"}[r.match]
        rows.append(f"| {i + 1} | {r.e1_name} | {r.csv_col if isinstance(r.csv_col, str) else '—'} | {method}；{note} |")
    e1_table = "\n".join(rows)

    bridge = e3[e3.match.str.startswith("bridge", na=False)]
    rows = ["| # | 4.csv 维度 | 7.csv 属性 | 桥接路径 |", "|---|---|---|---|"]
    for i, (_, r) in enumerate(bridge.iterrows()):
        rows.append(f"| {i + 1} | `{r.dim}` | `{r.attr}` | {r.match.split(':', 1)[1]} 归一化命中 |")
    e3_table = "\n".join(rows)

    covered = set(bridge.dim)
    rows = ["| 4.csv 维度 | 剔除理由 |", "|---|---|"]
    for d in dims:
        if d not in covered:
            rows.append(f"| `{d}` | {E3_NNS_REASON[d]} |")
    e3_nns = "\n".join(rows)

    e1_cols_table = "\n".join(
        f"| {i + 1} | {r.csv6_col.replace(chr(10), ' ')} | `{r.dim}` | {r.match} |"
        for i, (_, r) in enumerate(e1_cols.iterrows())
    )

    facts = {
        "F0_LIST": wrap(f0),
        "F1_EXTRA": ", ".join(sums),
        "F2_EXTRA": "kcalperc",
        "RAW33_LIST": wrap(raw33),
        "E1_TABLE": e1_table,
        "E3_TABLE": e3_table,
        "E3_NNS": e3_nns,
        "E1_COLS_TABLE": e1_cols_table,
        "N_F0": len(f0), "N_F1": len(f1), "N_F2": len(feats), "N_RAW33": len(raw33),
        "SUMS": sums,
    }
    with open(WORK / "m3_snippets.json", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(facts, ensure_ascii=False, indent=1))
    print({k: (v if isinstance(v, int) else f"<{len(str(v))} chars>") for k, v in facts.items() if not k.endswith("_TABLE") and k not in ("F0_LIST", "RAW33_LIST", "E3_NNS")})
    print("raw33 count", len(raw33), "f0", len(f0), "f1", len(f1))


if __name__ == "__main__":
    main()
