# ADR 0002：分支、PR 与分阶段仓库保护

- 日期：2026-10-29
- 状态：本地治理与 Git 初始化已完成；远端基础保护已配置并读回，完整行为验收与 CI 升级待执行
- 适用：RadishForge 自身仓库

## 背景

前期已有产品、架构与简要协作规划，本轮要求参考 Radish、RadishMind、RadishCatalyst、RadishFlow、RadishAxiom 建立通用基础。它们普遍采用 dev 日常开发、稳定主线 PR 晋级、禁用 squash 与合并后回流，但技术栈、门禁、授权习惯和当前阶段不同，不能整包移植。

## 决定

1. master 为默认稳定主线，dev 为常态集成线；普通串行任务不自动建立主题分支 / worktree。仅初始化共同基线允许引导式建立 master，随后主线只经 PR。
2. 允许 merge / rebase，阶段 PR 优先 merge，禁用 squash；每次主线合并后先回流 dev。快进优先，分叉普通 merge，不重写共享历史。
3. 单维护者审批数为 0，要求解决 review conversation；没有实际所有权结构时不创建 CODEOWNERS。
4. GitHub 规则仅匹配 master，基础保护与真实 CI 门禁分阶段启用。本地模板 disabled；远端应用需授权、最小差异与读回验收。
5. 默认无 bypass；紧急例外仅按明确授权临时使用 PR 内 bypass 并恢复，不照搬管理员常驻例外。
6. 不强制线性历史、签名提交、merge queue 或远端提交标题正则；Conventional Commits 的多父 merge 例外由本地范围检查判定。
7. 提供不依赖第三方包的 Python 治理检查工具，不改变 Go + TypeScript + React 产品栈。本轮不建立活动 workflow、空业务工程或发行流水线。
8. 不复制兄弟项目许可证、邮箱、角色 ID、工具链或业务检查；自有许可仍待决定。GitHub 配置不冒充 Gitea 兼容实现。

## 取舍与复核

直接在 dev 工作降低单维护者流程成本，也意味着本地验证是日常质量入口；真实 CI 建立前，基础 Ruleset 只有 PR 与历史保护，不能声称强制自动验收。未来多人协作或出现绕过问题时，再审视 dev 保护、独立审批与 CODEOWNERS。

常驻 bypass 容易变成常态绕过，故默认空列表；没有真实 CI 就要求 context 会锁住合并，故采用两阶段。merge commit 保留晋级拓扑，因此不使用 linear history 或强制 squash。

本决定不授权初始化 Git、提交、创建远端、修改远端设置或部署。实际任务与证据见[current](../status/current.md)和[治理记录](../records/2026-10-29-governance-foundation.md)。后续改变长期策略时补充新 ADR，不改写既有验收事实。
