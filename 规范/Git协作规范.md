# Git 协作规范 v1.0

> 目标：让多个队友、多个 AI 会话通过 GitHub 协作，同时保持“文件唯一写者”和可回滚。

## 1. 分支

- `main` 为唯一集成分支，受保护：禁止直接 push、禁止 force push。
- 一个任务一个分支：`task/<任务号>-<角色>`，例如 `task/T1-001-model`。
- 返工沿用原分支，不新开分支。
- 里程碑通过后打 annotated tag：`M1`、`M2`……

## 2. 提交

- 一个任务 = 一个 PR = 一个 squash 提交（PR 内可多次提交）。
- 提交信息格式：

```text
[T1-001][建模] 一句话说明

Task: T1-001
Role: 建模
Model: <模型名/版本>
Session: <会话标识>
Evidence: <快照/结果/图集路径>
```

- 只提交自己写域内的文件；共享文件（状态板/台账/任务书）只由大脑改。

## 3. PR

- 开 Draft PR 表示“进行中”；转 Ready for review 表示“已交审”。
- PR 标题：`[T1-001][建模] 主题`
- PR 描述使用 `.github/PULL_REQUEST_TEMPLATE.md`。
- 审阅官只评论，不 push、不改交付物。
- 裁决写入 `审阅/Mx/Mx裁决.md`；PR 评论不构成裁决。

## 4. 合并与回滚

- 大脑合并 PR；合并后状态改为“已验收”，打 tag。
- 禁止对 `main` 执行 `reset --hard` 或 force push。
- 回滚用 `git revert <commit>`，或从 tag 开修复分支。

## 5. 多 AI 会话

- 同一台电脑上多个 AI 会话不要共用同一个工作目录；每个角色用独立 `git worktree` 或独立 clone。
- 同一角色并行任务：一任务一分支，禁止两个会话改同一文件。

## 6. 赛时轻量模式

- 日常：本地 commit，按任务推进。
- 里程碑：开 PR、审阅、合并、打 tag。
- 不要在 4.5 天赛期内对每个小改动都做完整评审。
