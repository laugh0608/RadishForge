# 阶段任务清单

本页是任务状态的单一来源；执行状态为待开始、进行中、待验收、已完成、阻塞；暂停或取消时注明原因与恢复条件 / 去向。方案状态和验证事实按[文档治理](../governance/documentation.md#状态词)另述，不从本地测试推导发布。已完成必须有可定位证据，不能因文档存在而关闭功能任务。牵头专题及协同关系见[专题索引](topics.md)，近期四个子专题见[M0 计划](m0-validation.md)；原任务与验收 ID 保留。

| ID | 牵头专题 / 近期子专题 | 阶段 / 任务 | 依赖 | 验收 | 状态 |
| --- | --- | --- | --- | --- | --- |
| P0-01 | TOP-GOV | 核对兄弟项目与官方接口、记录日期和边界 | 无 | DOC-01 | 已完成 |
| P0-02 | TOP-GOV | 架构、产品、协作、部署、任务和验收文档 | P0-01 | DOC-01 | 已完成 |
| P0-03 | TOP-GOV | 指定目录落盘与文档检查 | P0-02 | DOC-01 | 已完成 |
| P0-04 | TOP-GOV | 提炼五个兄弟项目治理原则，补齐基础文件、规则、模板与 ADR | P0-03 | DOC-01、GOV-01 | 已完成，见[治理记录](../records/2026-10-29-governance-foundation.md) |
| P0-05 | TOP-GOV | 本地治理检查器、故障回归与文档状态同步 | P0-04 | GOV-01 | 已完成，见[治理记录](../records/2026-10-29-governance-foundation.md) |
| P0-06 | TOP-GOV | 专项复核五个兄弟项目 AGENTS / CLAUDE，细化通用执行约束 | P0-05、用户要求 | DOC-01、GOV-01 | 已完成，见[初始化与协作复核记录](../records/2026-10-29-local-git-bootstrap.md) |
| P0-07 | TOP-GOV | 整合整体规划、大专题与近期子专题，建立阶段 / 任务 / 验收对应 | P0-06、用户要求 | DOC-01、GOV-01 | 已完成，见[整合记录](../records/2026-11-01-planning-integration.md) |
| G0-01 | TOP-GOV | Git 共同基线、master / dev 与首个提交 | 对应操作授权、P0-05 | GOV-04 | 已完成，见[初始化记录](../records/2026-10-29-local-git-bootstrap.md) |
| G0-02 | TOP-GOV | 远端目标与可见性、安全报告渠道、基础保护启用 | G0-01、对应远端授权 | GOV-02 | 进行中：推送、基础保护与设置读回已完成；行为验收与安全渠道待补，见[远端记录](../records/2026-10-29-remote-governance.md) |
| G0-03 | TOP-GOV | 接入真实 CI、验证聚合失败传播、升级同一主线规则 | G0-02、真实检查与对应授权 | GOV-03 | 待开始 |
| M0-01 | TOP-BASE / M0-S01 | 选择 Gitea / Runner / 工具链 / 镜像 Digest 组合，记录许可 | 静态核查可先行；下载 / 环境等需对应授权 | BASE-01 | 进行中：候选、本机隔离配置与平台基础验证已交付，最终支持冻结待阶段取证；见[本机记录](../records/2026-11-01-m0-local-validation.md) |
| M0-02 | TOP-IAM / M0-S02 | 隔离环境验证 OIDC、OAuth scope、绑定与私有权限 | M0-01 的候选 / 隔离准备部分 | IAM-01、IAM-02 | 进行中：本批生命周期切片已交付；两项差异已定位并形成受控配置 / 在线账号拒绝边界，真实刷新到期、并发 / 重放、单用户撤销 / 范围隔离和账号恢复均取得证据，最终源码回归及清理通过。公开单用户撤销接口缺口与原始差异纳入 M0-S04 评审，不关闭完整 IAM；产品会话 / 绑定实现验收在 M1，见[本批记录](../records/2026-11-04-m0-lifecycle-validation.md)与[M0-S02](m0-validation.md#m0-s02身份与私有权限可行性) |
| M0-03 | TOP-BASE / M0-S03 | 真实 Issue / Actions / OCI / Release API 最小验证 | M0-01 的候选 / 隔离准备；M0-02 的用户授权部分 | BASE-01 | 进行中：[Issue](../records/2026-11-04-m0-issue-validation.md)保留 12 条 gap，[Release](../records/2026-11-04-m0-release-validation.md)保留 5 条；[OCI 切片](../records/2026-11-04-m0-oci-validation.md)完成私有组织 / team、固定 Digest 协议与真实客户端推拉、撤权 / 删除和真实超时取证，保留 4 条 gap，原生保留 / 即时凭据撤销仍需决定。Actions 受 Runner 暂停约束，不关闭完整 BASE / ART / REL / ISSUE |
| M0-04 | TOP-COMPAT / M0-S04 | 冻结首批 GitHub API / Action 样例及缺口决策 | M0-02、M0-03 | COMP-01 | 进行中：[差异基线](../architecture/github-compatibility.md#m0-现有差异基线)保留 27 条差异 / 接口缺口。已取得 [GitHub 所有者及匿名参考](../records/2026-11-09-m0-github-rest-reference.md)与 [Gitea 同源普通角色对照](../records/2026-11-09-m0-gitea-rest-comparison.md)。[GitHub 所有者只读 PAT](../records/2026-11-09-m0-github-owner-pat.md)已验证拒绝写入和删除后的 API 拒绝，普通角色待补。G19 按 Tag、G20 REST 空正文和[原生手动清空](../records/2026-11-09-m0-release-native-edit.md)已补证，G06、G19 / G20 其余场景及 G24 / G25 待补，G26 / G27 保留所有者取舍与换发补证。 [证据与补证入口](m0-validation.md#接续事项) |
| M1-01 | TOP-BASE | 最小 Go / React / OpenAPI / PostgreSQL / 工具链基础 | M0 | BASE-02 | 待开始 |
| M1-02 | TOP-IAM | OIDC 会话、显式账号绑定、Token 保护与撤销 | M1-01 | IAM-01、IAM-02 | 待开始 |
| M1-03 | TOP-WORKBENCH | 项目 / 组件 / 仓库关联和代码只读页面 | M1-02 | REPO-01、UI-01 | 待开始 |
| M1-04 | TOP-BASE | 事件接收、持久化队列、去重与对账基础 | M1-01 | EVENT-01 | 待开始 |
| M2-01 | TOP-WORKBENCH | Issue 列表、详情、创建、编辑、评论和状态 | M1 | ISSUE-01 | 待开始 |
| M2-02 | TOP-WORKBENCH | 标签 / 负责人 / 里程碑与并发 / 超时交互 | M2-01 | ISSUE-01、UI-01 | 待开始 |
| M3-01 | TOP-COMPAT | 工作流触发、运行 / job、取消 / 重跑、日志下载 | M1 | BUILD-01 | 待开始 |
| M3-02 | TOP-DELIVERY | OCI 镜像来源、Digest、包权限与缺失检测 | M3-01 | ART-01 | 待开始 |
| M3-03 | TOP-COMPAT | 首批 Action 矩阵及不支持字段行为 | M0-04、M3-01 | COMP-01、COMP-02 | 待开始 |
| M3-04 | TOP-COMPAT | GitHub API 子集 / Token 映射 / Webhook 兼容入口 | M0-04、M2-01 | COMP-03 | 待开始 |
| M4-01 | TOP-DELIVERY | 多组件清单、草稿 Release、附件与发布前校验 | M3 | REL-01 | 待开始 |
| M4-02 | TOP-DELIVERY | 发布幂等、未知结果、部分失败及崩溃恢复 | M4-01 | REL-02 | 待开始 |
| M5-01 | TOP-DELIVERY | 环境、授权、锁与固定工作流派发关联 | M4 | DEP-01、SEC-01 | 待开始 |
| M5-02 | TOP-DELIVERY | 测试 / 生产 Compose 部署、健康、回退与迁移边界 | M5-01 | DEP-02 | 待开始 |
| M6-01 | TOP-OPS | 固定镜像发行、运行时配置与干净安装 | M1—M5 | OPS-01 | 待开始 |
| M6-02 | TOP-OPS | 迁移失败注入、同批备份及隔离恢复演练 | M6-01 | OPS-02 | 待开始 |
| M6-03 | TOP-OPS | Gitea / Runner 升级契约及完整链路回归 | M6-01 | UPG-01 | 待开始 |
| M6-04 | TOP-OPS | 随包声明、依赖 / 镜像清单、来源和正式许可 | M6-01 | LIC-01 | 待开始 |
| M6-05 | TOP-OPS | 完整用户场景与交付文档收尾 | 全部首版任务 | E2E-01 | 待开始 |

每项实际执行后在 records 保存证据并在本表添加链接。P0 的记录见[规划建立记录](../records/2026-10-29-planning-bootstrap.md)。当前下一步与授权停止线见[current](../status/current.md)。

2026-11-01 已细化 M0-S01—M0-S04，并从静态准备推进至本机真实上游部分取证；详细状态以上表为准。部分协议证据不等于整项产品验收通过，Runner 暂不启动，M0 不因本批完成而晋级。
