# 文档索引

本目录是 RadishForge 的正式文档源。产品与设计说明目标，current 记录现实，records 保留证据；三者不能互相替代。

## 产品与架构

- [产品规划](product-plan.md)
- [总体架构](architecture/overview.md)
- [领域模型与权威数据](architecture/domain-model.md)
- [OIDC、账号绑定与访问控制](architecture/identity-access.md)
- [React 工作台与 Issue](architecture/workbench-and-issues.md)
- [GitHub 兼容策略](architecture/github-compatibility.md)
- [构建、镜像、Release 与部署](architecture/delivery-flow.md)
- [自部署与恢复](deployment/strategy.md)

## 开发与治理

- [开发原则](development/principles.md)
- [验证分层](development/validation.md)
- [协作与授权](governance/collaboration.md)
- [仓库、分支与 CI](governance/repository-governance.md)
- [Rulesets 与远端设置](governance/rulesets.md)
- [本地治理检查](../scripts/README.md)
- [安全报告](../SECURITY.md)与[协作行为](../CODE_OF_CONDUCT.md)
- [文档治理](governance/documentation.md)：三级规划职责、专题最小内容、单一状态来源与分期验收口径。
- [上游与许可](governance/upstream-and-licensing.md)
- [产品版本与发行标识](governance/versioning.md)

## 推进与证据

- [路线图](planning/roadmap.md)
- [专题与子专题索引](planning/topics.md)
- [M0 底座可行性子专题计划](planning/m0-validation.md)
- [M0-S01 候选组合与隔离验证方案](planning/m0-s01-baseline.md)
- [M0 本机上游配置与操作](../tests/contracts/m0/README.md)
- [阶段任务](planning/tasks.md)
- [验收矩阵](planning/acceptance.md)
- [当前状态](status/current.md)
- [ADR 0001：底座与扩展边界](adr/0001-foundation.md)
- [ADR 0002：分支、PR 与分阶段保护](adr/0002-repository-governance.md)
- [ADR 0003：Gitea 授权组合与在线复核](adr/0003-gitea-authorization-profiles.md)
- [ADR 0004：Issue 输入校验与写入结果对账](adr/0004-issue-validation-and-reconciliation.md)
- [ADR 0005：Release 授权、固定引用与附件对账](adr/0005-release-authorization-and-reconciliation.md)
- [ADR 0006：OCI 授权、Digest 保留与未知上传](adr/0006-oci-authorization-and-digest-retention.md)
- [来源核查](references/source-review.md)
- [五个兄弟项目治理提炼](references/governance-review.md)
- [2026-10-29 规划建立记录](records/2026-10-29-planning-bootstrap.md)
- [2026-10-29 治理基础记录](records/2026-10-29-governance-foundation.md)
- [2026-10-29 本地 Git 初始化与协作复核](records/2026-10-29-local-git-bootstrap.md)
- [2026-10-29 远端推送与基础保护](records/2026-10-29-remote-governance.md)
- [2026-11-01 规划层级与近期子专题整合](records/2026-11-01-planning-integration.md)
- [2026-11-01 M0-S01 官方来源核查](records/2026-11-01-m0-s01-review.md)
- [2026-11-01 本机 Docker 与身份 / 权限 / Issue API 验证](records/2026-11-01-m0-local-validation.md)
- [2026-11-01 scope 组合收敛与身份生命周期验证](records/2026-11-01-m0-auth-profile-validation.md)
- [2026-11-01 三级规划规则统一](records/2026-11-01-planning-rules-alignment.md)
- [2026-11-01 提交回顾与收工交接](records/2026-11-01-day-review.md)
- [2026-11-04 身份生命周期边界与负例](records/2026-11-04-m0-lifecycle-validation.md)
- [2026-11-04 Issue 契约与响应丢失验证](records/2026-11-04-m0-issue-validation.md)
- [2026-11-04 M0 差异基线与 Release / OCI 静态准备](records/2026-11-04-m0-gap-and-delivery-preparation.md)
- [2026-11-04 Release 隔离取证](records/2026-11-04-m0-release-validation.md)
- [2026-11-04 OCI 隔离取证](records/2026-11-04-m0-oci-validation.md)
- [2026-11-04 提交回顾与收工交接](records/2026-11-04-day-review.md)
