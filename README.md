# RadishForge · 萝卜锻坊

**从代码到可交付版本的自托管研发工作台。**

RadishForge 计划以 Gitea 为首选底座，使用 Go 业务服务与 TypeScript / React 工作台，连接 Git、Issue、PR、Actions、镜像、Release 和环境部署。优先通过公开协议与接口扩展，首版目标为不修改 Gitea 核心；Forgejo 保留为后续独立验证的适配目标。

当前已有规划文档、仓库治理基础文件、PR / Issue 与 Rulesets 模板、本地治理检查，以及本机 Gitea / PostgreSQL 隔离配置和真实协议探针。已取得部分身份、普通用户权限与 Issue API 证据，形成受控 scope 组合并保留上游及生命周期差异；尚无自有业务工程、产品依赖或可运行的 RadishForge 应用。本地 Git 与 GitHub 远端已建立，日常分支为 dev，远端默认分支 master 已启用基础保护。实际状态、下一步与当前授权边界见[当前状态](docs/status/current.md)。

## 已确认方向

- Go + TypeScript + React；Web-first，桌面和窄屏都纳入验收。
- 支持 OIDC 登录，包括 Radish 等标准发行方；登录身份与 Gitea API 操作授权分开处理。
- Issue 是首版功能：列表、详情、创建、编辑、评论、开关状态、标签、负责人和里程碑；权威数据留在 Gitea。
- 尽可能直接兼容 GitHub 工作流、Actions 与常用 API。以精确版本、真实样例和行为证据定义兼容，不宣传未经验证的全面兼容。
- 复用 Gitea 的 Git、PR、Actions、Packages 和 Release；自有服务保存项目关联、发布清单和部署记录。
- 参考 Radish 的开发 / 本地容器 / 测试 / 生产分层，以及固定镜像、迁移、备份和恢复流程。
- 不要求运行 Radish、RadishNexus 或其他兄弟项目才能自部署。
- 自有代码的最终许可尚待所有者决定；Gitea、Forgejo 和第三方部分分别遵守各自许可。

## 文档入口

| 要解决的问题 | 阅读入口 |
| --- | --- |
| 产品范围、家族分工 | [产品规划](docs/product-plan.md) |
| 技术结构与数据归属 | [总体架构](docs/architecture/overview.md)、[领域模型](docs/architecture/domain-model.md) |
| 登录、权限、账号绑定 | [身份与访问](docs/architecture/identity-access.md) |
| Issue 与 React 页面 | [工作台与 Issue](docs/architecture/workbench-and-issues.md) |
| GitHub 工作流及 API 兼容 | [兼容策略](docs/architecture/github-compatibility.md) |
| 构建、镜像、版本与环境 | [交付链路](docs/architecture/delivery-flow.md) |
| 安装、升级与恢复 | [部署方案](docs/deployment/strategy.md) |
| 整体规划如何拆分到近期工作 | [专题与子专题](docs/planning/topics.md)、[M0 子专题计划](docs/planning/m0-validation.md) |
| 先做什么、怎样算完成 | [路线图](docs/planning/roadmap.md)、[任务清单](docs/planning/tasks.md)、[验收矩阵](docs/planning/acceptance.md) |
| 开发与协作 | [AGENTS.md](AGENTS.md)、[开发原则](docs/development/principles.md)、[仓库治理](docs/governance/repository-governance.md) |
| 本机上游隔离验证 | [M0 契约配置与命令](tests/contracts/m0/README.md)、[首轮结果](docs/records/2026-11-01-m0-local-validation.md)、[授权组合结果](docs/records/2026-11-01-m0-auth-profile-validation.md)、[生命周期差异](docs/records/2026-11-04-m0-lifecycle-validation.md)、[Issue 契约与失败边界](docs/records/2026-11-04-m0-issue-validation.md) |
| PR、分支保护与本地检查 | [Rulesets 策略](docs/governance/rulesets.md)、[检查入口](scripts/README.md)、[治理决定](docs/adr/0002-repository-governance.md) |
| 来源与决策 | [参考核查](docs/references/source-review.md)、[架构决策](docs/adr/0001-foundation.md) |

[全部文档](docs/README.md) · [贡献入口](CONTRIBUTING.md) · [安全策略](SECURITY.md) · [协作行为](CODE_OF_CONDUCT.md)

规划子域名可采用 `forge.radishx.com`，域名尚未配置，产品未上线或发布。现有 M0 工具的执行命令见契约入口；产品工程、发行与部署的示例仍为设计说明。
