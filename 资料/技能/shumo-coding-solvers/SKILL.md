---
name: shumo-coding-solvers
description: 数学建模编程工具与求解器选型：LINGO/Gurobi/MATLAB/Python 按场景选型表、求解失败排查顺序、比赛版代码工程规范（目录结构/随机种子/结果文件命名）、论文-代码接口。当用户说"用什么工具""写代码求解""LINGO怎么写""Gurobi怎么用""求解报错""无可行解""代码怎么组织""结果文件格式"时使用。
---

# 数学建模 · 编程工具与求解器

先按场景选工具（不必追新，队伍熟哪个用哪个），再按比赛版工程规范组织代码。最终交付对齐题目要求的结果文件格式。

## 1. 工具选型总表

| 场景 | 首选 | 备选 | 备注 |
|---|---|---|---|
| 线性/整数规划 | **LINGO**（建模直观）或 Python+Gurobi/PuLP | MATLAB intlinprog、scipy.linprog | 优论实证：LINGO 20.0、Gurobi 都常用 |
| 非线性规划 | MATLAB fmincon | scipy.optimize.minimize(SLSQP) | 非线性约束返回 (c, ceq) |
| 微分方程 | MATLAB ode45/ode15s | scipy.integrate.solve_ivp | 刚性方程用 ode15s |
| 数据处理+ML | **Python**（pandas/sklearn/xgboost/lightgbm） | MATLAB | 大数据赛绝对主流 |
| 统计检验 | SPSS（优论常用）、Python statsmodels | R、Stata（优论用过） | 描述统计/ANOVA/回归 |
| 时间序列 | Python statsmodels、MATLAB | EViews、SPSS | ARIMA 定阶 AIC |
| 图像/深度学习 | Python（PyTorch/ultralytics YOLO） | MATLAB Deep Learning Toolbox | 分割 UNet、检测 YOLOv5/v8 |
| 蒙特卡洛仿真 | Python/MATLAB 均可 | — | 注意随机种子固定可复现 |
| 排队/离散事件 | Python (simpy) 或手写仿真 | MATLAB | 复杂系统 |

- 资料库配套教材：`外部资料/MathModel-master/Matlab入门教程/`（Matlab 入门、线性代数应用、MATLAB 在数学建模中的应用、LINGO 8.0 指南、lindo）。
- 传承习惯：研赛/老题多用 MATLAB+LINGO；大数据赛/近三年优论多用 Python。队伍熟哪个用哪个，**同一模型可多软件互验**（杨祥生建议）。

## 2. 求解器使用要点

- **LINGO**：直接写集合式模型；2024 C 题 c094 五步法（定义变量→…→导出 Excel 结果表）。
- **Gurobi/CPLEX**：Python API，大规模 MILP 快；写清变量集合与约束字典（c063 风格最规范）。
- **Matlab 优化工具箱**：linprog/intlinprog/fmincon/quadprog/ga/simulannealbnd/particleswarm。
- 求解失败排查顺序：无可行解（约束冲突）→ 数值尺度差太大（归一化）→ 非凸（换初值/换算法）→ 规模超限（分解/启发式，触发 shumo-metaheuristics）。

## 3. LINGO/MATLAB 速查增量（课件体系）

- **LINGO 完整语法**：sets（原始集/派生集）、data/init 段、九类函数（算术/逻辑/关系、数学、金融 @fpa/@fna、概率 @p*、变量界定 @bin/@gin/@bnd、集循环 @for/@sum、IO）；6 发点 8 收点最小费用运输问题完整代码可当模板。
- **MATLAB 速查**：绘图（线型/标记/颜色表、TeX 数学标注、legend 定位、subplot）；线性代数命令段（rref 求最大无关组、特征值）。

## 4. 代码工程规范（比赛版）

```
project/
├── data/          # 原始附件（只读）
├── processed/     # 清洗后数据
├── src/           # q1.py q2.py q3.py preprocess.py utils.py
├── results/       # result1_1.xlsx 等按题目要求命名
├── figures/       # 论文用图（300dpi，中文字体）
└── paper/         # 论文模板
```

- 每问一个入口脚本，从预处理到出图一键跑通（最后一天要复现结果时救命）。
- 固定随机种子；保存中间结果（pkl/csv），避免重跑长训练。
- ⚠️ **AI 辅助编程合规**：程序开头加注释声明"本程序在 AI 工具辅助下完成，工具名称/版本/开发机构/发布日期"（附件4 第 5 条），模板见 shumo-ai-compliance。
- 输出对齐题目要求：如 2024 C 题要求 result1_1.xlsx / result2.xlsx，编程前先看清交付格式。

## 5. 论文-代码接口

- 正文只放：算法流程图 + 关键参数表 + 结果图；**不粘贴程序**（杨祥生/格式规范均强调）。
- 简短核心代码可放正文，完整代码放附录；
- 附录代码要能与正文结果对应（评委可能核对）；
- 图的要求：每个坐标轴标注意义、每条曲线有图例、中文不乱码、300dpi。

## 深入阅读（原文库按需点查，不要批量浏览）

> 以下为可选外部资料索引，**未随仓库分发**；找不到就跳过，不影响技能使用。


- LINGO 指南：`外部资料/原文库/补充PDF/lingo使用指南.txt`
- MATLAB 图形处理：`外部资料/原文库/补充PDF/MATLAB图形处理.txt`；MATLAB 教程：`外部资料/原文库/补充PDF/MATLAB教程/`
- 各算法章节内的 Matlab 实现段：`外部资料/原文库/算法章节/*.txt`
- 优论代码实证：c094（LINGO+MATLAB）、c063（Gurobi+贪心）、c038/c0234（Python 自实现 GA）

---
维护说明：本技能为仓库内自包含版本；更新时直接修改本文件。
