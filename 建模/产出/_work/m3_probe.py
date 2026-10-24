#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3-00 探针：只读 数据/A/，产出方案-M3 所需的形状、映射与缺失证据。

AI 使用声明：本脚本由建模角色在 AI 辅助下编写（2026-10-24，TM3-00），
仅用于生成方案文档中的实测数字与映射表，不训练模型、不产出结果文件。

用法（仓库根目录）：python 建模/产出/_work/m3_probe.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "数据" / "A"
OUT = Path(__file__).resolve().parent

ID_COLS = ("beer", "beer_id", "tasting_category_fine")

# E1：6.csv 行名（英文）→ 1.csv 列名的人工同义词典（仅 23 条不规则项）
E1_SYNONYM = {
    "isoamyl acetate": "isopentyl_acetate",
    "ethyl 3-methylbutyrate": "ethyl_isovalerate",
    "ethanol": "ethanol..v.v.",
    "alpha-humulene": "alpha.humulene",
    "caryophyllene": "E.caryophyllene",
    "alpha-terpineol": "X1.alpha.terpineol",
    "diacetyl": "X2.3.butanedione",
    "4-vinylguaiacol": "X4VG",
    "acetic acid": "acetic_acid.g.L.",
    "lactic acid": "lactic_acid.mg.L.",
    "carbon disulfide": "CS2",
    "dimethyl sulfide": "DMS",
    "diethyl sulfide": "DES",
    "hydrogen sulfide": "H2S",
    "methanethiol": "MeSH",
    "sulfur dioxide": "SO2.mg.L.",
    "carbon dioxide": "CO2.PSI.",
    "ammonia": "ammonia.mg.L.",
    "betaglucan": "betaglucan.mg.L.",
    "color": "color.EBC.",
    "protein": "protein.g.L.",
    "caloric value": "kcalperc",
    "z-nerolidol": "Z.nerolidol",
}

# E1：6.csv 里无 1.csv 对应列的化合物（有实测证据，见方案 §5）
E1_UNMAPPED = {
    "Iso-alpha acids": "1.csv 无 iso-alpha acids 列； bitterness 为苦度值，不是同一种化学量",
    "Sugars": "1.csv 无 sugars 列； unfermentables 为未发酵糖残留，量纲与定义不同",
}

# E3：8.xlsx 交叉表把 fruity 系属性标成 nail polish，与 4.csv 可读名冲突，整维剔除
E3_CONFLICT_DIMS = {"A_esters_ethac", "A_esters_fruity", "F_esters_ethac", "F_esters_fruity"}


def norm(s: str) -> str:
    s = str(s).lower()
    s = s.replace("alpha", "a").replace("beta", "b").replace("gamma", "g")
    s = s.replace("α", "a").replace("β", "b").replace("γ", "g")
    return re.sub(r"[^a-z0-9]", "", s)


def load():
    d1 = pd.read_csv(DATA / "1.csv", encoding="utf-8-sig")
    d4 = pd.read_csv(DATA / "4.csv", encoding="utf-8-sig")
    d6 = pd.read_csv(DATA / "6.csv", encoding="utf-8-sig")
    d7 = pd.read_csv(DATA / "7.csv", encoding="utf-8-sig")
    sn = pd.read_excel(DATA / "8.xlsx", sheet_name="Sensory names")
    return d1, d4, d6, d7, sn


def e1_map(d1, d6):
    feats = [c for c in d1.columns if c not in ID_COLS]
    idx = {norm(c): c for c in feats}
    rows = []
    for name in d6["Unnamed: 0"]:
        if name in E1_UNMAPPED:
            rows.append((name, "", "N_ns", E1_UNMAPPED[name]))
        elif name.lower() in E1_SYNONYM:
            rows.append((name, E1_SYNONYM[name.lower()], "syn", ""))
        elif norm(name) in idx:
            rows.append((name, idx[norm(name)], "auto", ""))
        else:
            rows.append((name, "", "FAIL", "未命中，需人工"))
    return rows


def e1_cols(d6, d4, sn):
    """6.csv 的 50 个感官列名 → 4.csv 50 维。"""
    dims = [c for c in d4.columns if c not in ID_COLS]
    tp = sn[sn["dataset"] == "Trained panel"]
    name2dim = {}
    for _, r in tp.iterrows():
        for col in ("R_name", "CleanName_Paper", "CleanName_PaperLong", "CleanName_PanelFeedback"):
            if isinstance(r[col], str):
                name2dim.setdefault(norm(r[col]), r["R_name"])
    out = []
    for c in d6.columns[1:]:
        if c.startswith("Overall appreciation"):
            out.append((c, "overall", "prefix"))
            continue
        key = norm(c)
        out.append((c, name2dim.get(key, ""), "auto" if key in name2dim else "FAIL"))
    return out, dims


def e3_map(d7, d4, sn):
    """7.csv 186 属性 → 4.csv 50 维（经 8.xlsx Sensory names 桥接）。"""
    dims = [c for c in d4.columns if c not in ID_COLS]
    tp = sn[sn["dataset"] == "Trained panel"]
    rb = sn[sn["dataset"] == "Ratebeer"]
    name2dim = {}
    for _, r in tp.iterrows():
        for col in ("R_name", "CleanName_Paper", "CleanName_PaperLong", "CleanName_PanelFeedback"):
            if isinstance(r[col], str):
                name2dim.setdefault(norm(r[col]), r["R_name"])
    bridge = {}
    for _, r in rb.iterrows():
        if not isinstance(r["R_name"], str) or not r["R_name"].startswith(("aroma_", "palate_", "taste_")):
            continue
        tgt, how = "", ""
        for col in ("CleanName_PaperLong", "CleanName_PanelFeedback", "CleanName_Paper"):
            if isinstance(r[col], str) and norm(r[col]) in name2dim:
                tgt, how = name2dim[norm(r[col])], col
                break
        bridge[r["R_name"]] = (tgt, how)
    attrs = [c for c in d7.columns if c not in ID_COLS]
    rows = []
    for a in attrs:
        if a in bridge:
            tgt, how = bridge[a]
            if tgt in E3_CONFLICT_DIMS:
                rows.append((a, tgt, "conflict"))
            elif tgt:
                rows.append((a, tgt, "bridge:" + how))
            else:
                rows.append((a, "", "non_descriptor"))
        else:
            rows.append((a, "", "no_bridge"))
    return rows, bridge, dims


def main():
    d1, d4, d6, d7, sn = load()
    feats = [c for c in d1.columns if c not in ID_COLS]
    dims = [c for c in d4.columns if c not in ID_COLS]
    e1 = e1_map(d1, d6)
    e1c, _ = e1_cols(d6, d4, sn)
    e3, bridge, _ = e3_map(d7, d4, sn)

    miss = d1[feats].isna().sum()

    # 硬校验：映射目标必须真实存在（返工 1 的教训，防止点号/下划线笔误）
    bad_e1 = [(r[0], r[1]) for r in e1 if r[1] and r[1] not in feats]
    bad_e1c = [(r[0], r[1]) for r in e1c if r[1] and r[1] not in dims]
    bad_e3 = [(r[0], r[1]) for r in e3 if r[2].startswith("bridge") and r[1] not in dims]
    assert not bad_e1, f"E1 目标列不存在: {bad_e1}"
    assert not bad_e1c, f"E1 感官列目标不存在: {bad_e1c}"
    assert not bad_e3, f"E3 目标维度不存在: {bad_e3}"

    facts = {
        "shapes": {
            "1.csv": list(d1.shape), "4.csv": list(d4.shape), "5.csv": list(pd.read_csv(DATA / "5.csv", encoding="utf-8-sig").shape),
            "6.csv": list(d6.shape), "7.csv": list(d7.shape),
        },
        "n_feats": len(feats), "n_dims": len(dims),
        "e1_mapped": sum(1 for r in e1 if r[1]),
        "e1_unmapped": [r[0] for r in e1 if not r[1]],
        "e1_cols_fail": [r[0] for r in e1c if not r[1]],
        "e3_attrs": len(e3),
        "e3_bridge": sum(1 for r in e3 if r[2].startswith("bridge")),
        "e3_conflict": [r[0] for r in e3 if r[2] == "conflict"],
        "e3_no_bridge": sum(1 for r in e3 if r[2] == "no_bridge"),
        "e3_non_desc": [r[0] for r in e3 if r[2] == "non_descriptor"],
        "e3_dims_covered": len({r[1] for r in e3 if r[1] and r[2].startswith("bridge")}),
        "e3_dims_uncovered": [d for d in dims if d not in {r[1] for r in e3 if r[1] and r[2].startswith("bridge")}],
        "miss_cells": int(miss.sum()),
        "miss_cols": {k: int(v) for k, v in miss[miss > 0].items()},
        "rows_any_miss": int(d1[feats].isna().any(axis=1).sum()),
        "d7_all_nan": [c for c in d7.columns if c not in ID_COLS and d7[c].isna().all()],
    }
    with open(OUT / "m3_facts.json", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(facts, ensure_ascii=False, indent=2))
    print(json.dumps(facts, ensure_ascii=False, indent=2))

    pd.DataFrame(e1, columns=["e1_name", "csv_col", "match", "note"]).to_csv(OUT / "m3_e1.csv", index=False, encoding="utf-8", lineterminator="\n")
    pd.DataFrame(e1c, columns=["csv6_col", "dim", "match"]).to_csv(OUT / "m3_e1_cols.csv", index=False, encoding="utf-8", lineterminator="\n")
    pd.DataFrame(e3, columns=["attr", "dim", "match"]).to_csv(OUT / "m3_e3.csv", index=False, encoding="utf-8", lineterminator="\n")


if __name__ == "__main__":
    main()
