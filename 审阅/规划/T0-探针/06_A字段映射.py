# -*- coding: utf-8 -*-
"""06 A题字段映射生成器（v2：改用 Sensory names 作权威桥接）。

第 2 轮校验指出手写映射表三处硬错误（B 组未展开、字段名写错、C 组顺序不符）。
本脚本改为**从数据生成 + 断言**，不手抄。

三方桥接关系（实测确立）：
  4.csv 的 50 个列名（权威字段名与顺序）
    ↕  8.xlsx/Sensory names：R_name 50/50 精确匹配，CleanName_Paper 给可读名
    ↕  3.xlsx/summary：51 列公式（50 个评分维度 + 1 个 comments），
        但列序与 4.csv 不同、且有 4 处拼写差异

已登记的源表差异（见 T0-口径映射与阈值缺口.md §2-5）：
  - 拼写：4.csv `A_esters_fruity` / `F_esters_fruity` / `X4vg`
           summary `A_ester_fruity` / `F_ester_fruity` / `4vg`
  - 列序：summary 的 C 组顺序与 4.csv 完全不同；5.csv 的 C 组末尾三列
          （Carbonation / Aftertaste / Body）也与 4.csv 顺序不同
  - 公式缺陷：summary 的 barnyard 错引 AG76（与 stale_hops 相同），按评分卡布局应为 AG90

产出：审阅/规划/T0-字段映射.csv
运行：python 06_A字段映射.py
"""
import sys
from pathlib import Path

import openpyxl
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "数据" / "A"
OUT = ROOT / "审阅" / "规划" / "T0-字段映射.csv"
META = ("beer", "beer_id", "tasting_category_fine")

KNOWN_SPELLING = {          # 4.csv（权威） -> summary 写法
    "A_esters_fruity": "A_ester_fruity",
    "F_esters_fruity": "F_ester_fruity",
    "X4vg": "4vg",
}
NORM = {v: k for k, v in KNOWN_SPELLING.items()}


def norm_summary_name(name: str) -> str:
    s = str(name).strip()
    return NORM.get(s, s)


def main() -> int:
    d4 = pd.read_csv(BASE / "4.csv", encoding="utf-8-sig", nrows=1)
    fields = [c for c in d4.columns if c not in META]
    assert len(fields) == 50, f"4.csv 感官列应为 50，实际 {len(fields)}"

    # ---- 权威可读名：8.xlsx/Sensory names ----
    sn = pd.read_excel(BASE / "8.xlsx", sheet_name="Sensory names")
    readname = {str(r).strip(): str(c).strip()
                for r, c in zip(sn["R_name"], sn["CleanName_Paper"])}

    # ---- 集合校验：5.csv 的名称集合应与 4.csv 一致（不作为顺序依据）----
    d5 = pd.read_csv(BASE / "5.csv", encoding="utf-8-sig", index_col=0)
    names5 = [str(c).replace("\r\n", " ").replace("\n", " ").strip() for c in d5.columns]
    assert len(names5) == 50, f"5.csv 列应为 50，实际 {len(names5)}"
    names5_set = set(names5)

    # ---- 3.xlsx/summary：按名匹配，不按位置 ----
    ws = openpyxl.load_workbook(BASE / "3.xlsx", data_only=False)["summary"]
    hdr = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    fml = [ws.cell(row=2, column=c).value for c in range(1, ws.max_column + 1)]
    summary, beer_const = {}, None
    for h, v in zip(hdr, fml):
        if h is None:
            continue
        if str(h).strip() == "Beer":
            beer_const = v
        elif isinstance(v, str) and v.startswith("="):
            summary[norm_summary_name(h)] = (str(h).strip(), v)

    rows = []
    for i, f in enumerate(fields, start=1):
        grp = "A" if f.startswith("A_") else ("B" if f.startswith("F_") else "C")
        note = []
        if f in KNOWN_SPELLING:
            note.append(f"summary 拼写为 {KNOWN_SPELLING[f]}")
        sname, sform = summary.get(f, (None, None))
        if f == "barnyard":
            note.append("summary 公式错引 AG76（与 stale_hops 同），按评分卡布局应为 AG90")
        readable = names5[i - 1] if grp in ("A", "B") else readname.get(f)
        note_extra = ""
        if grp == "C":
            note_extra = "可读名取 Sensory names（5.csv 的 C 组列序与 4.csv 不同，不可按位置取）"
        rows.append({
            "序号": i, "组": grp, "4csv字段": f,
            "可读名": readable,
            "summary列名": sname, "summary公式": sform,
            "备注": "；".join(note + ([note_extra] if note_extra else [])),
        })
    df = pd.DataFrame(rows)

    # ================= 断言 =================
    print("=== 断言校验 ===")
    checks = []

    def ck(cond, msg):
        checks.append((cond, msg))
        print(f"  [{'OK' if cond else 'FAIL'}] {msg}")

    ck(len(df) == 50, "行数 = 50")
    ck(df["4csv字段"].is_unique, "4csv字段 唯一")
    ck(list(df["4csv字段"]) == fields, "顺序与 4.csv 完全一致")
    ck(df["组"].value_counts().to_dict() == {"A": 15, "B": 15, "C": 20},
       "组计数 A15/B15/C20")
    ck(df["summary公式"].notna().all(), "50 个字段全部有 summary 公式引用")
    ck(df["可读名"].notna().all(), "50 个字段全部有可读名")
    ck(len(set(df["可读名"])) == 50, "可读名无重复")
    ck(len(names5_set) == 50, "5.csv 列名无重复")
    ck(set(df[df["组"] == "C"]["可读名"]) <= set(readname.values()),
       "C 组可读名全部取自 Sensory names")
    ck(beer_const == 1, f"summary 的 Beer 列为常量 1（实际 {beer_const!r}）")
    ck(len(summary) == 51, f"summary 公式列 = 51（50 评分 + comments，实际 {len(summary)}）")

    dup = df.groupby("summary公式")["4csv字段"].apply(list)
    dup = {k: v for k, v in dup.items() if len(v) > 1}
    ck(list(dup.keys()) == ["=beer_1!$AG$76"],
       "唯一重复引用为 barnyard/stale_hops -> AG76（已知缺陷）")

    ok = all(c for c, _ in checks)
    print(f"\n断言结果：{sum(c for c, _ in checks)}/{len(checks)} 通过"
          f" -> {'全部通过' if ok else '存在失败项'}")

    df.to_csv(OUT, index=False, encoding="utf-8", lineterminator="\n")
    print(f"\n已保存 {len(df)} 行 -> {OUT}")

    print("\n=== C 组 20 行（按 4.csv 顺序，可读名来自 Sensory names）===")
    for _, r in df[df["组"] == "C"].iterrows():
        print(f"  {r['序号']:2d}. {r['4csv字段']:12s} | {str(r['可读名'])[:24]:26s} | {r['summary公式']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
