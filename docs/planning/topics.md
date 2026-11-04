# 专题与子专题索引

本页连接整体规划、能力专题和可交付子专题，不另建任务状态表。产品范围以[产品规划](../product-plan.md)为准，推进顺序以[路线图](roadmap.md)为准，任务状态只维护在[任务清单](tasks.md)，通过标准维护在[验收矩阵](acceptance.md)。

## 层级与读取方式

| 层级 | 管理内容 | 正式入口 |
| --- | --- | --- |
| 整体规划 | 产品目标、首版范围、优先级与阶段出口 | 产品规划、路线图 |
| 大专题 | 能力边界、权威数据、跨阶段依赖与子专题清单 | 本页路由到既有架构 / 治理专题 |
| 子专题 | 一个明确功能或工作包的输入、方案、成功 / 失败边界及分期任务与验收 | 近期子专题计划或稳定章节；远期临近实施再展开 |
| 执行与证据 | 任务状态、当前重点、已执行结果与限制 | tasks、current、records |

M0—M6 是时间与依赖维度，专题是能力维度，两者不是同一棵目录。一个专题可以跨阶段，一个跨能力子专题也可以关联多个专题；每项任务只指定一个牵头专题，协同关系通过链接表达。

读取近期工作时，从 [current](../status/current.md) 进入活跃或下一项子专题，再按需读取其设计依据、任务和验收。历史来源和长输出需要追溯时再读 records / references。子专题允许分期，任务和实施切片不另立专题层级；每个子专题保留一个牵头大专题，其他关联列为协同。最小内容、状态语义与完成口径见[文档治理](../governance/documentation.md)。

## 大专题与阶段对应

下列 ID 为稳定路由标识，不代表新增业务模块。各设计正文继续在原文件维护。

| 专题 | 能力边界与设计入口 | 阶段 / 任务 | 验收 |
| --- | --- | --- | --- |
| TOP-BASE 底座与工程基础 | [总体架构](../architecture/overview.md)、[领域模型](../architecture/domain-model.md)、[上游来源](../governance/upstream-and-licensing.md)；独立底座、公开协议、工具链、自有事实和事件基础 | M0-01、M0-03；M1-01、M1-04 | BASE-01、BASE-02、EVENT-01 |
| TOP-IAM 身份与访问 | [身份与访问](../architecture/identity-access.md)；OIDC、会话、显式绑定、Token 生命周期与真实用户权限 | M0-02；M1-02 | IAM-01、IAM-02 |
| TOP-WORKBENCH 项目、工作台与 Issue | [工作台与 Issue](../architecture/workbench-and-issues.md)、领域模型；项目关联、仓库只读、Issue 主路径和完整交互 | M1-03；M2-01、M2-02 | REPO-01、ISSUE-01、UI-01 |
| TOP-COMPAT Actions 与 GitHub 兼容 | [GitHub 兼容](../architecture/github-compatibility.md)；工作流执行、API / Webhook 和权限语义分别取证 | M0-04；M3-01、M3-03、M3-04 | BUILD-01、COMP-01、COMP-02、COMP-03 |
| TOP-DELIVERY 制品、发布与部署 | [交付链路](../architecture/delivery-flow.md)；OCI 来源、不可变清单、发布恢复、受控部署及回退记录 | M3-02；M4-01、M4-02；M5-01、M5-02 | ART-01、REL-01、REL-02、DEP-01、DEP-02、SEC-01 |
| TOP-OPS 自部署与生命周期 | [部署与恢复](../deployment/strategy.md)、[许可](../governance/upstream-and-licensing.md)；独立安装、迁移、备份、恢复、升级和发行声明 | M6-01—M6-05 | OPS-01、OPS-02、UPG-01、LIC-01、E2E-01 |
| TOP-GOV 开发与仓库治理 | [开发原则](../development/principles.md)、[仓库治理](../governance/repository-governance.md)、[Rulesets](../governance/rulesets.md)、[文档治理](../governance/documentation.md)；协作、Git、真实 CI 与证据管理 | P0；G0-01—G0-03，贯穿后续阶段 | DOC-01、GOV-01—GOV-04 |

跨专题依赖：IAM 使用 BASE 确认的接口；WORKBENCH 使用 IAM 的身份与权限；COMPAT 的真实构建为 DELIVERY 提供来源；DELIVERY 的清单与权限成立后才执行 CD；OPS 以已实现能力开展安装与恢复验收。G0 可独立于 M0 推进，G0-03 仍依赖 G0-02 与真实 CI 证据。

## 近期子专题

近期四项集中在[M0 子专题计划](m0-validation.md)，复用既有设计，不提前创建业务工程。子专题 ID 用于范围和证据关联；原任务 / 验收 ID 保持不变。

| 子专题 | 牵头 / 协同专题 | 任务 / 验收 | 交付边界 |
| --- | --- | --- | --- |
| [M0-S01 底座组合与隔离验证准备](m0-s01-baseline.md) | TOP-BASE；TOP-OPS、TOP-GOV | M0-01 / BASE-01 的版本、来源与环境部分 | 候选版本、Digest、来源许可、最小工具链和隔离执行方案；全阶段取证后才能最终冻结支持组合 |
| M0-S02 身份与私有权限可行性 | TOP-IAM；TOP-BASE | M0-02 / IAM-01、IAM-02 的上游部分 | OIDC / OAuth、账号标识与绑定前提、scope、普通用户权限及撤权证据；不冒充工作台会话验收 |
| M0-S03 Issue 与交付接口最小验证 | TOP-BASE；TOP-WORKBENCH、TOP-COMPAT、TOP-DELIVERY | M0-03 / BASE-01 | 真实 Issue、Actions、OCI、Release 最小操作及失败结果；不冒充完整产品或 CD |
| M0-S04 首批兼容范围与缺口决策 | TOP-COMPAT；TOP-IAM、TOP-DELIVERY | M0-04 / COMP-01 的样例和差异基线 | 固定样例、版本、预期和差异处理；未运行项保持待验证，M3 完成兼容验收 |

治理收尾复用[Rulesets 启用与验收方案](../governance/rulesets.md)：G0-02 补安全报告渠道与独立权限 / PR 行为证据；G0-03 接入真实治理检查与聚合失败传播后，才升级同一规则。两项的状态仍以 tasks 为准，不因本次规划整理关闭。

## 近期状态与验收读取链

本表只登记来源，不维护第二份任务状态。各 TOP-* 的本期完成条件由上表关联的阶段任务、验收及跨专题依赖共同确定；M0 部分上游证据不能关闭 M1—M6 的产品验收。

| 子专题 | 阶段 / 设计范围 | 唯一任务状态 | 验收标准 | 实际证据入口 |
| --- | --- | --- | --- | --- |
| M0-S01 | M0；[准备与冻结范围](m0-validation.md#m0-s01底座组合与隔离验证准备)、[候选方案](m0-s01-baseline.md) | [tasks](tasks.md)：M0-01 | [矩阵](acceptance.md)：BASE-01 的来源 / 环境部分 | [来源](../records/2026-11-01-m0-s01-review.md)、[本机结果](../records/2026-11-01-m0-local-validation.md) |
| M0-S02 | M0；[身份 / 权限范围](m0-validation.md#m0-s02身份与私有权限可行性) | [tasks](tasks.md)：M0-02 | [矩阵](acceptance.md)：IAM-01 / IAM-02 的上游部分 | [首轮 scope 差异](../records/2026-11-01-m0-local-validation.md)、[受控组合与生命周期](../records/2026-11-01-m0-auth-profile-validation.md)、[生命周期差异定位与负例](../records/2026-11-04-m0-lifecycle-validation.md)、[ADR 0003](../adr/0003-gitea-authorization-profiles.md) |
| M0-S03 | M0；[Issue 与交付接口](m0-validation.md#m0-s03issue-与交付接口最小验证) | [tasks](tasks.md)：M0-03 | [矩阵](acceptance.md)：BASE-01 | [本机 Issue 部分结果](../records/2026-11-01-m0-local-validation.md)；其余结果取得后登记 |
| M0-S04 | M0；[兼容范围与缺口](m0-validation.md#m0-s04首批兼容范围与缺口决策) | [tasks](tasks.md)：M0-04 | [矩阵](acceptance.md)：COMP-01 的样例 / 差异部分 | 尚无本项完成证据；后续结果由 tasks 链接 |

任务已实现、待验收或已完成的语义分别见[状态词](../governance/documentation.md#状态词)。S01 准备、S02 身份 / 权限、S03 Issue / Actions / OCI / Release 可分批取证，整项完成必须覆盖本计划要求的全部范围；S04 的样例冻结不代替 M3 完整兼容验收。

## 后续子专题清单

以下是后续拆分边界，尚未细化为可执行子专题，也不创建占位文件。临近相应阶段时，在牵头专题内展开，任务过大或有独立交付边界时再建立子专题文档。

| 牵头专题 | 待展开范围 | 对应任务 |
| --- | --- | --- |
| TOP-BASE | Go / React / OpenAPI 与显式迁移基础；事件持久化、去重与对账 | M1-01、M1-04 |
| TOP-IAM | OIDC 会话；显式账号绑定；Token 保护、刷新与撤销；失权和后台授权 | M1-02 |
| TOP-WORKBENCH | 项目与仓库关联 / 只读；Issue 主路径；分类分配与并发失败交互 | M1-03、M2-01、M2-02 |
| TOP-COMPAT | 构建运行与日志；Action / 权限样例；兼容 REST / Webhook 子集 | M3-01、M3-03、M3-04 |
| TOP-DELIVERY | OCI 来源与包权限；多组件清单；发布幂等与恢复；部署授权与环境锁；健康、晋级与回退 | M3-02、M4-01、M4-02、M5-01、M5-02 |
| TOP-OPS | 干净安装；备份迁移与恢复；底座升级；随包声明；完整用户场景 | M6-01—M6-05 |

跨阶段通过标准仍按验收矩阵执行。M0 的协议证据可作为 M1—M6 的输入，不能代替自有实现、浏览器交互、完整恢复或生产验证。
