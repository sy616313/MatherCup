# -*- coding: utf-8 -*-
"""修正 gen_gap.py / gen_kj.py 中被勘误要求的措辞（S1 检索进展）。"""
import pathlib

GAP = pathlib.Path("建模/产出/_work/gen_gap.py")
KJ = pathlib.Path("建模/产出/_work/gen_kj.py")

g = GAP.read_text(encoding="utf-8")
old = '| 需要的裁决 | ① 是否允许 Q3 只用 7 项、把 3 项缺口在论文中如实标注「资料未覆盖」；② 或由大脑提供仓库外原始资料（如文献阈值）后再补表 |'
new = ('| 需要的裁决 | ① 是否允许 Q3 只用 7 项、把 3 项缺口在论文中如实标注「资料未覆盖」；'
       '② 或采用 `阈值检索-M1.md` 建议甲：`t2n` 与 `MeSH` 补外部文献值（0.11 µg/L、1 µg/L，标注「外部文献、非数据集原生」），`stale hops` 维持缺口 |')
assert old in g, "gen_gap 目标串未找到"
g = g.replace(old, new)
anchor = '| 未做（禁止） |'
add = ('A("| 检索进展 | 仓库内（技能 17 份 + 精选 PDF 33 份 + 8.xlsx 全 sheet）**0 命中**；外部检索已完成，见 `建模/产出/阈值检索-M1.md`（三项逐项给出处与原文摘录，并做了与数据集体例的同量级校准）；**待大脑裁决后落表** |")\n')
assert anchor in g
g = g.replace(anchor, add + anchor, 1)
GAP.write_text(g, encoding="utf-8", newline="\n")

k = KJ.read_text(encoding="utf-8")
old2 = '；Q3 任务书（M5）需由大脑就此三项给出裁决后方可开工 |'
new2 = '；仓库内检索 0 命中，外部检索结论与建议见 `建模/产出/阈值检索-M1.md`，**待裁决后落表** |'
assert old2 in k, "gen_kj 目标串未找到"
k = k.replace(old2, new2)
KJ.write_text(k, encoding="utf-8", newline="\n")
print("patched")
