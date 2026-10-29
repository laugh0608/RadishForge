# 仓库、分支与 PR 治理

本页定义 RadishForge 自身仓库规则，不是产品内所有托管仓库的默认政策。当前是否已有 Git、远端或强制门禁，以[当前状态](../status/current.md)为准；理由见 [ADR 0002](../adr/0002-repository-governance.md)。

## 规则与实现的职责

根协作入口约束启动、授权和红线；本页维护分支与 PR 政策。[Rulesets 专题](rulesets.md)定义目标保护与启用验收；`.github/` 是 GitHub 适配模板，不表示远端已配置。[本地检查](../../scripts/README.md)验证文件契约，不能取代人的范围、权限、许可和行为审查。

长期决定进入 ADR，当前事实进入 current，历史证据进入 records；规则与实现漂移时一起修正。

## 分支与初始化

| 分支 | 用途 | 进入方式 |
| --- | --- | --- |
| `master` | 默认稳定主线 | 初始化共同基线后，只接受阶段晋级或 hotfix PR |
| `dev` | 常态开发与集成 | 普通串行任务直接推进；主题分支按需 PR 合入 |
| `feature/*`、`fix/*`、`docs/*`、`chore/*`、`experiment/*` | 外部贡献、并行写入或确有隔离价值的工作 | 通常指向 `dev` |
| `hotfix/*` | 必须修复稳定主线的问题 | 从最新 `master` 建立，经 PR 合入后回流 |

不同时维护 `main` 和 `master` 两条稳定主线，不为普通任务自动建立主题分支 / worktree。单人阶段 `dev` 不启用远端强制保护，但共享历史仍禁止 reset、rebase、force push 和删除。持续多人协作或出现检查绕过问题时，再评估 dev 保护与审批责任。

Git 初始化、首个提交、远端创建与 push 各需对应授权。获授权后先复核文件、用户 Git 身份和许可状态，在 master 建立唯一初始提交，再从同一提交建立 dev；不能分别建立无共同祖先的初始历史。首个基线是 PR 规则的引导步骤，必须记录，不成为以后直推主线的例外。不修改全局 Git 配置。

默认分支计划为 master，普通贡献打开 PR 时显式选择 dev。默认分支不是日常工作分支。关闭自动删除 PR 源分支，避免阶段 PR 后误删长期 dev；临时分支确认归属与合并情况后再清理。

## 提交与审查

提交格式为 `type(scope)!: 摘要`，scope 与 `!` 可省略。类型使用 `feat`、`fix`、`docs`、`refactor`、`test`、`chore`、`ci`、`build`、`perf`、`revert`；摘要可用中文。复杂变更补充原因、验证与破坏性变化。真实多父提交可使用 Git 自动生成的 merge 标题；单父提交不能用 `Merge ...` 逃避规范。

使用当前用户 Git 身份，不添加 AI 协作者署名。提交前复核工作树、暂存区、未跟踪文件和 diff，精确暂存本批文件，不混入用户或并行改动。提交授权不自动覆盖 push、合并、tag 或发布。

PR 使用[模板](../../.github/PULL_REQUEST_TEMPLATE.md)，说明最终问题与行为、任务 / 验收、真实证据、风险和恢复。单人阶段审批数为 0，仍由维护者审查实际差异和解决 review conversation；不创建无真实责任人的 CODEOWNERS。多人评审形成后再要求独立审批者。

| RadishForge 变更 | 必须审查的边界 |
| --- | --- |
| Gitea 接口 / Issue / 仓库 | 公开接口、权威数据、上游权限、分页与并发 |
| OIDC / Token / 账号绑定 | issuer 与 subject、显式绑定、撤权与后台权限 |
| Actions / API 兼容 | 精确版本、实际样例、静默忽略与不支持行为 |
| 事件 / 命令 | 重复、乱序、丢失、超时、未知结果及对账 |
| 制品 / Release / 部署 | SHA / Digest、不可变清单、授权、迁移与恢复 |
| UI | PC / 窄屏、键盘、焦点、长内容与失败态 |
| 治理 / CI / 依赖 | 门禁没有放宽、来源许可、最小权限与真实验证 |

## 合并与回流

允许 merge commit 和 rebase merge，禁用 squash；阶段 `dev -> master` 优先 merge commit。不启用 linear history，因为它与保留 merge commit 冲突。短主题分支使用 rebase merge 时仍遵守共享历史约束。

每次合入 master（包括 hotfix）后，在下一批开发前回流 dev：

1. 在已有授权范围内更新远端引用，检查工作区和两侧拓扑；先保存或协调未完成改动，不强切分支。
2. dev 可快进时，在 dev 用 `git merge --ff-only origin/master` 回流。
3. rebase merge 或并发提交导致真正分叉时，先审查差异，再普通 merge 主线；禁止 reset、rebase 或 force push 共享分支。不要把所有快进失败都自动判成可合并冲突。
4. 文件树未变时只核对拓扑和先前检查对应内容；解决冲突或内容变化时，执行受影响验证。
5. 用 `git merge-base --is-ancestor origin/master dev` 验证本地回流。具备 push 授权后推送 dev，刷新引用并核对 `origin/master` 是 `origin/dev` 的祖先；不要求 SHA 永远相等。
6. 记录主线 SHA、dev SHA、验证和推送结果。没有 push 授权时记为“本地已回流、远端待推送”，完成远端回流前不继续下一批集成开发。

命令是未来操作说明，前提是仓库存在、当前位于 dev、远端确实命名为 origin 且操作已授权；本页不触发操作。回流不自动创建 tag、Release 或部署。

## CI 与发行

本地使用 `python3 scripts/check-repo.py`，仅覆盖治理文件；无 Git 时明确跳过 Git 检查。尚无真实业务实现时，不添加名为 Go / Web Build 的空成功 job。

后续真实 CI 采用 PR 到 dev / master 与手动入口，普通 dev push 不自动触发。稳定聚合 job `Candidate Quality` 必须等待所有应执行组件，只有 success 才通过；失败、取消、缺失、意外跳过均阻断。聚合本身不得路径跳过；若以后做影响范围路由，先有可审查的适用性判定，不能把所有 skipped 算成功。

本地治理检查可成为首个真实组件，但不证明 Go 构建、权限或部署通过。业务落地后按风险加入 Go、TypeScript / React、真实底座契约与交付检查。required context 必须先真实运行，再配置远端要求。

PR CI 默认只读源码；外部贡献不能接触生产秘密、CD Runner 或宿主 Docker socket，不用 pull_request_target 执行不可信代码。第三方 Action 固定可审查版本 / 提交并记录来源；PR 内容不直接拼进 shell 命令。发布与部署使用独立受控入口，按[版本规则](versioning.md)与[交付设计](../architecture/delivery-flow.md)另行实现。

这些规则只约束本项目开发。产品对用户仓库的 push / PR / tag / schedule / 手动事件、审批与分支策略必须按公开能力和用户配置执行。

## 同步矩阵

| 变更 | 同批复核 |
| --- | --- |
| 分支、合并、回流 | 本页、ADR、Rulesets、PR 模板、仓库设置模板 |
| CI 与 required context | 检查实现、Rulesets、验证文档和远端证据 |
| 协作授权 | AGENTS / CLAUDE、协作专题、贡献入口 |
| 产品 / 权限 / 数据 | 对应架构专题、ADR、任务与验收 |
| 许可 / 安全入口 | 上游许可专题、SECURITY、贡献入口 |
| 已执行状态 | tasks、current、records；不改写历史事实 |
