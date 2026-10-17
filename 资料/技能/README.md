# 数学建模竞赛 Skill 库（17 个）

本目录是仓库内唯一的技能源。每个 `shumo-*` 文件夹内有一份 `SKILL.md`，直接读取全文即可，**不依赖任何 AI 工具的“技能自动加载”机制**。

## 怎么用（工具无关）

1. 打开对应的 `SKILL.md`，从第一行读到末尾。
2. 如果工具支持自动发现技能目录，可以把 `资料/技能/` 配成技能目录；不支持也没关系。
3. 如果工具不能读本地文件，就把 `SKILL.md` 全文粘贴进对话。

| 工具 | 推荐用法 |
|---|---|
| ZCode | 打开仓库根目录；支持 `.agents/skills` 就映射过去，不支持就直接打开 `SKILL.md` |
| Codex CLI | 直接让模型读取 `资料/技能/<名称>/SKILL.md`；或复制到 `$CODEX_HOME/skills/` |
| Cursor / Claude Code | 在项目里打开 `SKILL.md`，或加入项目规则/上下文 |
| 纯聊天工具 | 复制 `SKILL.md` 全文粘贴 |

> 所有路径都以**仓库根目录**为基准。不要使用盘符绝对路径或用户主目录绝对路径。

## 技能地图

| # | Skill | 干什么 | 典型触发语 |
|---|---|---|---|
| 1 | shumo-workflow | 流程总控：时间线/分工/每日节奏 | "比赛开始了""现在该干什么" |
| 2 | shumo-problem-reading | 读题与题型识别、拆题四步法 | "帮我分析这道题" |
| 3 | shumo-topic-selection | 选题决策：打分表/题位人设 | "选哪道题/A题还是C题" |
| 4 | shumo-data-prep | 数据预处理与 EDA 流水线 | "处理数据/缺失值/特征工程" |
| 5 | shumo-optimization | 优化规划建模（LP/IP/NLP/图网络等） | "建个优化模型/排产调度" |
| 6 | shumo-forecasting | 预测建模（回归/ARIMA/灰色等） | "预测/时间序列/灰色预测" |
| 7 | shumo-evaluation | 综合评价决策（AHP/TOPSIS/熵权） | "综合评价/打分排序" |
| 8 | shumo-mechanism | 机理微分方程建模 | "微分方程/传染病/稳定性" |
| 9 | shumo-ml-modeling | 统计与机器学习建模 | "分类/聚类/影响因素" |
| 10 | shumo-metaheuristics | 智能优化算法（GA/SA/PSO/MC） | "遗传算法/蒙特卡洛" |
| 11 | shumo-model-validation | 模型检验/灵敏度/稳健性 | "灵敏度分析/结果合理性" |
| 12 | shumo-coding-solvers | 编程工具与求解器 | "用什么工具/LINGO/求解报错" |
| 13 | shumo-paper-writing | 论文写作（结构/摘要/图表公式） | "写论文/写摘要" |
| 14 | shumo-formatting | 格式规范与模板 | "格式要求/模板/LaTeX" |
| 15 | shumo-ai-compliance | AI 使用合规 | "AI 规定/怎么标注" |
| 16 | shumo-award-patterns | 获奖论文套路库 | "优秀论文怎么做/这问怎么破" |
| 17 | shumo-submission | 提交前检查（MD5/自查清单） | "提交前检查/MD5" |

## 外部资料

- 技能正文是自包含的；末尾“深入阅读”只是可选索引，**未随仓库分发**。
- 如果你本地有原始资料库，放到 `资料/原始资料/外部资料/`，目录名保持 `skill资料整理/`、`MathModel-master/`。
- 找不到外部资料就跳过，不要因此停机；技能正文仍可正常使用。

## 维护

- 更新技能时直接改对应 `SKILL.md`，不再依赖仓库外底稿。
- 新增技能：建 `资料/技能/<name>/SKILL.md`，文件头保留 `name` 与 `description` 两个字段。
