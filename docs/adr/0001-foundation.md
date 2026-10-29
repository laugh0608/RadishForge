# ADR 0001：独立 Gitea 底座与 Go / React 工作台

- 日期：2026-10-29
- 状态：方向已确认，实施待开始

## 背景

用户要建立 RadishForge（萝卜锻坊），以 Go + TypeScript + React 串联 Git、Issue、CI/CD、镜像与 Release，支持 OIDC，并尽可能兼容 GitHub 的工作流、Actions 与 API。产品需自部署，尽量减少底座升级负担。

## 决定

1. 首版采用 Gitea 独立服务，目标零核心补丁；自有模块化 Go 服务通过公开接口与协议集成，React 提供主工作台。
2. 不重写 Git 存储、通用流水线执行器和完整代码评审 UI；高级 PR 与实时日志可进入原生页面。
3. Git、Issue、PR、Actions、Packages、Release 权威数据归底座；自有库维护身份绑定、项目关联、冻结清单和部署记录。
4. OIDC 身份认证与 Gitea API 操作授权分离；不得以同邮箱或全局管理员 Token 偷渡资源权限。
5. GitHub 兼容分层定义，以版本和样例验收，不承诺全量 API 或官方 Runner 协议兼容。
6. 参考 Radish 的固定镜像、环境分层、显式迁移、备份和恢复，保留自身 Go / PostgreSQL 架构。
7. Forgejo 作为后续独立适配；自有代码最终许可未选定，第三方遵守各自许可。

## 替代方案

- 直接修改 Gitea 核心与全站模板：前期局部改动方便，但统一 React 与上游升级长期耦合较深。
- 嵌入 Gitea Go 包、直读数据库：看似少接口工作，却使 schema、内部类型及权限逻辑成为隐式契约，因此不采用。
- 基于 Harness 大规模二开：前期讨论已发现许可边界和 UI 依赖清理工作；本项目方向已转为 Gitea，不继续复制该底座。
- 同时支持 Gitea / Forgejo：初期验证面翻倍；先实现真实 Gitea 用例，再依据需求抽取差异。

## 代价与复核条件

需要自行实现会话、聚合接口、状态对账与交付编排；无法跨系统原子写入，必须处理结果未知和恢复。GitHub 兼容缺口可能影响 M0 的范围与预算。若必须突破公开接口、包权限隔离或关键安全语义，新增 ADR 记录证据和选择，不暗改本决定。

相关：[架构](../architecture/overview.md)、[兼容](../architecture/github-compatibility.md)、[上游与许可](../governance/upstream-and-licensing.md)。
