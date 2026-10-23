# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 生成 缺陷阈值缺口-M1.md（缺口区 + 停机上报记录）。"""

L = []
A = L.append

A("# 缺陷阈值缺口 M1（缺口区 · 资料未覆盖 · 停机上报）\n")
A("> 版本：v1.0　任务：TM1-01　作者：建模　日期：2026-10-24")
A("> 本文件是 `缺陷阈值表-M1.csv` 的**缺口区**：该表只放实测可用项 7 行，缺阈值者单列于此。")
A("> 依据：任务书 TM1-01 ⑤-1（不得猜测阈值，查不到出处即写「资料未覆盖」并触发停机）、`建模/角色卡.md` §8、台账 R14 §4。\n")

A("## 一、缺口清单（3 项）\n")
A("| # | 化合物 | `field_name_python` | 单位 | 检索范围与定位 | 检索结果 | 处置 |")
A("|---|---|---|---|---|---|---|")
A("| G1 | trans-2-nonenal | `X.E..2.nonenal` | mg/L | `8.xlsx/Sensory thresholds` 第 **55** 行：`('(E)-2-nonenal','X.E..2.nonenal','E-2-nonenal','mg/L')` | `threshold_mean = NA`、`threshold_median = NA`、`off_flavors` **未标记** | **资料未覆盖 → 停机上报**（见 §三） |")
A("| G2 | Methanethiol (MeSH) | `MeSH` | ug/L | `8.xlsx/Sensory thresholds` 第 **157** 行：`('MeSH','MeSH','Methanethiol','ug/L')` | `threshold_mean = NA`、`threshold_median = NA`；`off_flavors` 有标记（`putrefaction, drains, rotting vegetables, estery`） | **资料未覆盖 → 停机上报**（见 §三） |")
A("| G3 | Stale hops | —（无化学项） | — | `8.xlsx/Sensory thresholds` **261 个数据行**按 `field_name_python`/`field_name_R`/`chemical_name` 反查 `stale`：**0 命中**；该维度只存在于 `8.xlsx/Sensory names` 第 **49** 行（`Trained panel / stale_hops / Taste / Stale hops`），属**感官维度**，非化合物 | 无对应化学项，无任何阈值数值 | **资料未覆盖 → 停机上报**（见 §三） |")
A("")
A("## 二、检索记录（做了什么）\n")
A("| 步骤 | 范围 | 结果 |")
A("|---|---|---|")
A("| 1 | `8.xlsx/Sensory thresholds` 全表 261 行，逐行读 `field_name_python`/`field_name_R`/`chemical_name`/`calibrated`/`unit`/`off_flavors`/`threshold_mean`/`threshold_median` | 43 行有数值；`off_flavors` 有标记且**无**数值者 = MeSH（第 157 行）1 项；`off_flavors` 无标记且无数值者含 t2n（第 55 行） |")
A("| 2 | 按 `stale` 关键词在 261 行全表模糊检索（前三列） | 0 命中 |")
A("| 3 | `8.xlsx/Sensory names`（101 行，Trained panel 50 + Ratebeer 51） | `stale_hops` 仅出现在第 49 行，`Category=Others`，无化学对应 |")
A("| 4 | 其他 sheet（`Calibrated chemical dataset`、`GBM importance MDI`、`GBM SHAP Values`、`Beer Prices`、`Sheet2`） | 均无阈值信息（只有浓度、重要度、价格） |")
A("")
A("结论：三项在**仓库内全部资料**中均无可用阈值，属「资料未覆盖」，按 ⑤-1 必须停机上报，不得由建模自行放行。\n")

A("## 三、停机上报（S1）\n")
A("| 项 | 内容 |")
A("|---|---|")
A("| 触发条款 | 任务书 TM1-01 ⑤-1「不得猜测阈值。查不到出处就写『资料未覆盖』并触发停机」 |")
A("| 上报对象 | 大脑（再由大脑决定是否升级人类） |")
A("| 上报时间 | 2026-10-24 |")
A("| 事实 | 题面点名的缺陷化合物中，`trans-2-nonenal`、`Stale hops`、`Methanethiol` 三项在 `8.xlsx` 无阈值数值；其中 `Stale hops` 根本没有化学项 |")
A("| 影响面 | 仅 M5（Q3 全流程）的超阈值判定：7 项可用阈值照常可用，缺 3 项；不影响 M2（Q2 名称对齐）与 M3（Q1 标定） |")
A("| 需要的裁决 | ① 是否允许 Q3 只用 7 项、把 3 项缺口在论文中如实标注「资料未覆盖」；② 或采用 `阈值检索-M1.md` 建议甲：`t2n` 与 `MeSH` 补外部文献值（0.11 µg/L、1 µg/L，标注「外部文献、非数据集原生」），`stale hops` 维持缺口 |")
A("| 检索进展 | 仓库内（技能 17 份 + 精选 PDF 33 份 + 8.xlsx 全 sheet）**0 命中**；外部检索已完成，见 `建模/产出/阈值检索-M1.md`（三项逐项给出处与原文摘录，并做了与数据集体例的同量级校准）；**待大脑裁决后落表** |")
A("| 未做（禁止） | 未用 `4.csv` 感官列反推化学阈值；未用「以感官列替代」「不纳入 Q3」「M5 另定」等写法放行 |")
A("")
A("> 本停机项登记在 `口径规范-M1.md` §10.1（S1）；`自检-M1.md` §4/§6 已同步为「有停机项，待裁决」。\n")

open("建模/产出/缺陷阈值缺口-M1.md", "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("written")
