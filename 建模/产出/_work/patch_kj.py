# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""按方案甲更新 gen_kj.py（整行替换 S1 + 追加 §8.1）。"""
import pathlib

p = pathlib.Path("建模/产出/_work/gen_kj.py")
lines = p.read_text(encoding="utf-8").splitlines(True)

NEW_S1 = (
    'A("| S1 | 3 项缺陷阈值查不到出处 | `8.xlsx/Sensory thresholds` 中 `trans-2-nonenal`（第 55 行）、'
    '`MeSH`（第 157 行）有字段但 `threshold_mean/median` 均为 `NA`；`Stale hops` 无对应化学项'
    '（全表 261 行无反查命中）。三者均属题面点名的缺陷化合物 | '
    '按 ⑤-1 与角色卡 §8：先写「资料未覆盖」并停机上报；**2026-10-24 已裁决为方案甲**——'
    '`t2n`（0.11 µg/L）与 `MeSH`（1 µg/L）补外部文献值并标注来源，`stale hops` 维持缺口、'
    'Q3 以感官维度评估。记录见 `缺陷阈值缺口-M1.md`、`阈值检索-M1.md` |")\n'
)

out = []
done_s1 = False
for ln in lines:
    if ln.startswith('A("| S1 |'):
        out.append(NEW_S1)
        done_s1 = True
        continue
    out.append(ln)

assert done_s1, "未替换 S1 行"

# 在 §8 接口表末行之后插入 8.1
final = []
inserted = False
for ln in out:
    final.append(ln)
    if ln.startswith('A("| M5（编程·Q3）'):
        final.append('\n')
        final.append('A("### 8.1 阈值来源分级（方案甲裁决后新增）\\n")\n')
        final.append('A("| 级别 | 含义 | 现有条目 | 论文引用要求 |")\n')
        final.append('A("|---|---|---|---|")\n')
        final.append('A("| 数据集原生 | `8.xlsx/Sensory thresholds` 直接给出 `threshold_mean` | '
                     '7 项（Acetaldehyde、Diacetyl、4-vinylguaiacol、DES、DMS、H2S、SO2） | '
                     '标注「数据集原生阈值」 |")\n')
        final.append('A("| 外部文献 | 数据集无值，取公开文献并标注来源 | '
                     '2 项（trans-2-nonenal 0.11 µg/L；Methanethiol 1 µg/L） | '
                     '必须标文献出处（见 `阈值检索-M1.md` §二），不得写成数据集原生 |")\n')
        final.append('A("| 缺口 | 无化学项或无可算代理 | 1 项（Stale hops） | '
                     '论文写「资料未覆盖」，Q3 以感官维度评估 |")\n')
        inserted = True

assert inserted, "未插入 8.1"
p.write_text("".join(final), encoding="utf-8", newline="\n")
print("patched gen_kj")
