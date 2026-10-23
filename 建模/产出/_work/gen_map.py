# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 生成 维度映射-M1.md / 口径规范-M1.md / 缺陷阈值表-M1.csv。"""
import json

import pandas as pd

b = pd.read_csv("建模/产出/_work/base_table.csv")
m = pd.read_csv("建模/产出/_work/map50.csv")
thr = pd.read_csv("建模/产出/_work/thr.csv")
al = pd.read_csv("建模/产出/化合物名称对齐-M1.csv")

exact = b[b.exact10].sort_values("field")
inex = b[~b.exact10].sort_values("mean")

# ============ A. 维度映射 ============
lines = []
lines.append("# 维度映射 M1（4.csv 50 维 ↔ summary 公式 ↔ 评分卡单元格）\n")
lines.append("> 版本：v1.0（TM1-01，2026-10-24）　作者：建模　范围：仅第 1 件与第 4 件交付物相关部分\n")
lines.append("> 权威顺序：`4.csv` 字段名与列序为**唯一权威**；`3.xlsx/summary` 只提供公式与单元格定位；"
             "`8.xlsx/Sensory names` 只提供可读名。任何按位置对齐的做法都不可用（C 组列序不同）。\n")
lines.append("## 一、50 行映射表\n")
lines.append("| # | 4.csv 字段（权威） | summary 列名 | 列字母 | 评分卡单元格(beer_1) | 8.xlsx 可读名 | 备注 |")
lines.append("|---|---|---|---|---|---|---|")
for _, r in m.iterrows():
    note = r["note"] if isinstance(r["note"], str) else ""
    lines.append(f"| {r['序号']} | `{r['c4']}` | `{r['summary']}` | {r['letter']} | `{r['cell']}` | {r['readable']} | {note} |")

lines.append("\n## 二、源表差异登记（3 处拼写 + C 组列序）\n")
lines.append("| # | 4.csv（权威） | summary 写法 | 差异类型 | 处置 |")
lines.append("|---|---|---|---|---|")
lines.append("| 1 | `A_esters_fruity` | `A_ester_fruity` | 拼写（少一个 s） | 取 4.csv 写法；匹配时先做拼写归一 |")
lines.append("| 2 | `F_esters_fruity` | `F_ester_fruity` | 拼写（少一个 s） | 取 4.csv 写法；匹配时先做拼写归一 |")
lines.append("| 3 | `X4vg` | `4vg` | 拼写（缺 X 前缀） | 取 4.csv 写法；8.xlsx 亦作 `X4vg` |")
lines.append("\nC 组（第 31–50 行）在 `summary` 中的列序与 `4.csv` 完全不同：\n")
lines.append("```")
lines.append("4.csv C 组顺序：acidity, bitternes, sweetness, X4vg, diacetyl, dms, metallic, stale_hops, t2n,")
lines.append("                orange, coriander, clove, lactic, acetic, barnyard, alcohol, aftertaste, body, co2, overall")
lines.append("summary 列序  ：body(AF), bitternes(AG), co2(AH), aftertaste(AI), alcohol(AJ), sweetness(AK), acidity(AL), dms(AM),")
lines.append("                metallic(AN), 4vg(AO), t2n(AP), diacetyl(AQ), stale_hops(AR), orange(AS), coriander(AT), clove(AU),")
lines.append("                lactic(AV), acetic(AW), barnyard(AX), overall(AY)")
lines.append("```")
lines.append("\n`5.csv`（50×50 感官相关矩阵）的 C 组列序同样与 `4.csv` 不同，**不得按位置取列**，必须先按名字建索引。\n")

lines.append("## 三、源表缺陷登记（barnyard）\n")
lines.append("| 项 | 内容 |")
lines.append("|---|---|")
lines.append("| 实际公式 | `summary!AX2 = =beer_1!$AG$76`（barnyard） |")
lines.append("| 对照公式 | `summary!AR2 = =beer_1!$AG$76`（stale_hops） |")
lines.append("| 问题 | 两列指向**同一单元格**，barnyard 取到了 stale hops 的分数 |")
lines.append("| 应为 | 按评分卡 `beer_1` 布局，`R89='Barnyard/horsey'`，其分数字母为 `Q90`/`AG90`；"
       "stale hops 在 `R75`，分数 `Q76`/`AG76`。故 barnyard 应为 `=beer_1!$AG$90` |")
lines.append("| 采用口径 | 本队一律以 `4.csv` 的 50 列为准（`4.csv` 中 barnyard 与 stale_hops 是两列独立数据，"
       "已核实二者列相关不恒为 1），`summary` 的公式缺陷**只登记不修复**（`数据/A/` 只读） |")
lines.append("| 影响 | 若有人直接用 `summary` 取 barnyard 维度，会得到 stale hops 的分数；影响面为「按 summary 取数」的一切下游 |")
lines.append("| 证据 | `数据/A/3.xlsx` summary 第 2 行 AX 列与 AR 列公式；`数据/A/3.xlsx` beer_1 第 75/76 行与第 89/90 行布局 |")

open("建模/产出/维度映射-M1.md", "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("维度映射-M1.md rows:", len(m))

# ============ B. 缺陷阈值表（主表只放实测可用项 7 行） ============
tr = []
for _, r in thr.iterrows():
    tr.append({
        "化合物": r["化合物"],
        "field_name_python": r["field_name_python"],
        "数值": round(float(r["数值"]), 6),
        "统计量": "threshold_mean（均值）",
        "单位": r["单位"],
        "变换方式": "log10（1.csv 中为对数值）" if r["field_name_R"] in set(exact.field) else "原始量纲（1.csv 中未取对数）",
        "出处": r["出处"],
        "备注": f"中位数 {r['中位数']}（仅参考，Q3 统一用均值）；用于 Q3 超阈值判定",
    })
usable = pd.DataFrame(tr)
usable.to_csv("建模/产出/缺陷阈值表-M1.csv", index=False, encoding="utf-8", lineterminator="\n")
print("缺陷阈值表 rows:", len(usable))
