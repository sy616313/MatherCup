# -*- coding: utf-8 -*-
# 本程序及代码是在人工智能工具辅助下完成的。
# AI 工具名称：DeepSeek Harness；模型：deepseek-flash；开发机构/公司：DeepSeek。
"""TM1-01 生成 Q1标定规则-M1.md。"""
import numpy as np
import pandas as pd

df4 = pd.read_csv("数据/A/4.csv", encoding="utf-8-sig")
meta = ("beer", "beer_id", "tasting_category_fine")
cols = [c for c in df4.columns if c not in meta]

L = []
A = L.append

A("# Q1 标定规则 M1（0–6 分级）\n")
A("> 版本：v1.0　任务：TM1-01　作者：建模　日期：2026-10-24")
A("> 用途：把 Q1 的连续预测值（50 个感官维度）机械地转成 **0–6 整数分级**，作为 M3 的交付格式合同。")
A("> 本文件只定规则，不产出结果；实现属 M3（编程线）。\n")

A("## 1. 依据（为什么规则长这样）\n")
A("| 事实 | 来源 | 对规则的约束 |")
A("|---|---|---|")
A("| 评分卡是 **7 档**（0–6）人工打分 | `数据/A/3.xlsx` beer_1 第 46/51/55/59/63/69/73/77/83/87/91/95 行：`O=6, S=0, U=1, W=2, Y=3, AA=4, AC=5, AE=6` | 输出必须是 **0..6 的整数**，不是连续值 |")
A("| 50 个感官维度定义在 `4.csv`，取值 **−2.15 ~ 6.17**（250 样本、连续、每列 106~250 个唯一值） | `数据/A/4.csv` 实测 | 不能直接四舍五入（会得到 0 或负数），必须先做**锚定映射** |")
A("| 每维度的参考分布只有 `4.csv` 一份（250 样本） | `数据/A/4.csv` | 锚点取该列 **P0.5 / P99.5**，抗离群 |")
A("| 4.csv 无缺失（250×50 全满） | `数据/A/4.csv` 实测 | 锚点稳定，不需要插补 |\n")

A("## 2. 规则（唯一候选，R15 减范围）\n")
A("**规则名：分维锚定线性映射 + 四舍五入（Anchor-Linear-Round，ALR）**\n")
A("对维度 $d$：")
A("1. 取参考锚点 $lo_d = Q_{0.005}(z_d)$、$hi_d = Q_{0.995}(z_d)$（$z_d$ 取自 `4.csv` 该列 250 个值）。")
A("2. 线性映射到 0–6：$s_d = 6 \\cdot \\dfrac{x - lo_d}{hi_d - lo_d}$。")
A("3. 四舍五入到整数，**.5 一律向上**（half-up）：`floor(s + 0.5)`。")
A("4. 截断到 $[0, 6]$。")
A("")
A("写成一行：`score = clip(floor(6*(x-lo)/(hi-lo) + 0.5), 0, 6)`\n")
A("> 选型理由：ALR 与参考分布同形、单调、可逆查，且允许品评员整列打 0 或 6（不强制每级等量）。")
A("> 本文件**只定义上述 1 种候选规则**；设计时对比过的其他分级思路仅作排除说明、不作为候选，实现时不得引入。\n")

A("## 3. 伪代码（可直接照抄实现）\n")
A("```python")
A("def calibrate(x, lo, hi):")
A("    if x is None or not is_finite(x):          # 边界 B2：缺失/非有限")
A("        return REFERENCE_MEDIAN_SCORE           # 见 §4-B2")
A("    if hi <= lo:                                # 退化维度保护")
A("        return 3")
A("    s = 6.0 * (x - lo) / (hi - lo)")
A("    s = floor(s + 0.5)                          # 边界 B3：.5 half-up")
A("    if s < 0: return 0                          # 边界 B1：下超界")
A("    if s > 6: return 6                          # 边界 B1：上超界")
A("    return int(s)")
A("```\n")

A("## 4. 三类边界情形（逐条给判据）\n")
A("**B1 超界**：$x < lo_d$ 或 $x > hi_d$。")
A("- 处理：截断为 0 或 6，**不报错、不丢弃**。")
A("- 记录：每维度输出超界计数 `n_low` / `n_high`，写入结果表附表；超界比例 >5% 时提示锚点需重估（阈值可调，默认 5%）。\n")
A("**B2 缺失**：输入为 `NaN` / `None` / `inf`。")
A("- 处理：用该维度参考分布的**中位数分级**回填（即把 `4.csv` 的中位数过同一条规则得到的分级），并置 `imputed=1`。")
A("- 理由：Q1 的输入（`1.csv`）存在 73 个缺失格（见 `口径规范-M1.md` §7），必须让下游有确定行为，而不是让 `NaN` 穿透。\n")
A("**B3 并列（恰在 .5 上）**：$s$ 的小数部分精确等于 0.5。")
A("- 处理：**一律向上**（half-up，例如 2.5→3、5.5→6）。")
A("- 禁止：随机取整、银行家舍入、按样本排序取整——三者都会让同一输入在不同次运行得到不同输出。")
A("- 复核：浮点误差会制造伪 .5，实现时必须先 `round(s, 10)` 再判 .5。\n")

A("## 5. 有效性检验设计（M3 落地时必须跑）\n")
A("| 编号 | 检验 | 做法 | 通过判据 |")
A("|---|---|---|---|")
A("| T1 | 单调性 | 在 $[lo-3\\sigma, hi+3\\sigma]$ 上取 1000 个等距点过规则 | 输出非降、取值仅 0–6；平台出现在**各整数级**（0–6 每级一段），端点 0/6 含超界样本 |")
A("| T2 | 保序一致 | 用 `4.csv` 真值过规则得参考分级 $s^{ref}$；与 $z$ 求 Spearman | $\\rho \\ge 0.99$ |")
A("| T3 | 分布合理性 | 参考分级 $s^{ref}$ 的 7 类频数 vs 均匀分布做卡方 | 允许偏离均匀（评分卡本就不均匀），但需报告频数表；若某级 <2% 需说明 |")
A("| T4 | 边界确定性 | 构造 $x=lo-1,\\ lo,\\ hi,\\ hi+1,\\ NaN,\\ s=2.5$ 六类输入（第 6 类取 $x=lo+2.5(hi-lo)/6$，以 `A_malt_all` 计 $x\\approx0.388267$） | 输出分别为 0, 0, 6, 6, 中位数分级, 3；两次运行结果完全一致。**注**：不得直接把 $x=2.5$ 当输入——$x$ 是原始量纲，2.5 在不同维度会得 4/5/6 |")
A("| T5 | 往返误差 | 用 $s^{ref}$ 反推中心值再前向过规则 | 100% 复原（规则是确定映射） |\n")

A("> T1–T5 全部是**可脚本化**的，M3 只需把本文件 §3 的伪代码照抄，再跑 T1–T5 把输出贴进报告。\n")

A("## 6. 锚点表（50 维，M3 直接查用）\n")
A("| # | 维度 | lo (P0.5) | hi (P99.5) | 中位数 | 中位数分级 |")
A("|---|---|---|---|---|---|")
for i, c in enumerate(cols, 1):
    z = df4[c].to_numpy(float)
    lo, hi = float(np.quantile(z, 0.005)), float(np.quantile(z, 0.995))
    med = float(np.median(z))
    s = int(np.clip(np.floor(6 * (med - lo) / (hi - lo) + 0.5), 0, 6)) if hi > lo else 3
    A(f"| {i} | `{c}` | {lo:.4f} | {hi:.4f} | {med:.4f} | {s} |")
A("")
A("> 锚点由 `4.csv` 全 250 样本算出（脚本 `建模/产出/_work/gen_q1.py` 与本文件同批产出，锚点数据另存 `_work/q1_anchors.csv`），M3 不得自行改锚点；")
A("> 若 M3 发现某维度锚点退化（hi≈lo），按 §3 的退化保护返回 3 并上报。\n")

open("建模/产出/Q1标定规则-M1.md", "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")

# 同步产出锚点 CSV，便于编程线直接读取
rows = []
for c in cols:
    z = df4[c].to_numpy(float)
    lo, hi = float(np.quantile(z, 0.005)), float(np.quantile(z, 0.995))
    rows.append(dict(dimension=c, lo=round(lo, 6), hi=round(hi, 6), median=round(float(np.median(z)), 6)))
pd.DataFrame(rows).to_csv("建模/产出/_work/q1_anchors.csv", index=False, encoding="utf-8", lineterminator="\n")
print("Q1 doc written; anchors:", len(rows))
