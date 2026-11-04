# GitHub 兼容策略

状态：目标与验收设计，尚无已通过 GitHub 等价验收的兼容项；已有 Gitea 原生身份 / Issue 证据及下列 M0 差异基线。以减少用户修改工作流和调用脚本为目标；每个承诺必须对应精确版本与行为证据。

## 三个独立层面

1. 工作流语法及 Action：文件发现、事件、表达式、context、job / step、Runner 与 Action 运行时。
2. API 与 Webhook：路径、字段、分页、状态码、认证、签名、事件语义及客户端使用。
3. 权限与部署语义：Token scope、fork PR、环境保护、并发、取消、审批与身份令牌。

某个 Action 跑通不证明 GitHub API 兼容；YAML 被解析不证明权限与环境字段生效；OIDC 用户登录也不等于 Actions 的工作负载 OIDC。

## 记录方式

每条记录包含：GitHub 文档 / REST API version、Gitea 和 Runner 精确版本、Action 仓库及 commit、运行平台、原始样例、改动 diff、预期 / 实际、证据、限制与负责人。状态限定为：待验证、直接兼容、需配置、需适配、不支持。只有原始行为验证通过才能标“直接兼容”；仅替换 endpoint / Token 的情况标“需配置”。

M0 固定首批样例清单，M3 完成首版验收。2026-10-29 官方文档列出 `2026-03-10` 与 `2022-11-28` 两个受支持 REST 版本；新契约优先以 `2026-03-10` 为候选，现有脚本按需要增加 `2022-11-28` profile，不混用两者响应预期。M0 再核对支持状态和客户端版本，当前未冻结长期 API 版本。资料入口见[来源核查](../references/source-review.md)。

## 首批工作流测试矩阵

| 能力 | 样例 / 必查结果 | 初始状态 |
| --- | --- | --- |
| 文件发现 | `.github/workflows` 与 `.gitea/workflows` 的发现 / 优先级；避免双触发 | 待验证 |
| 触发器 | push、tag、PR、schedule、workflow_dispatch 及输入类型、分支 / 路径过滤 | 待验证 |
| 基本执行 | needs、if、matrix、env、outputs、服务容器、失败传播与取消 | 待验证 |
| 表达式 / context | github / gitea context 的实际字段、SHA、ref、actor、event payload | 待验证 |
| Checkout | actions/checkout 精确版；私有仓库、submodule、LFS、fetch-depth | 待验证 |
| 工具链 | setup-go、setup-node 精确版；Node 运行时、缓存与出网 | 待验证 |
| 镜像构建 | docker/login-action、setup-buildx-action、build-push-action；精确 Digest 输出 | 待验证 |
| 缓存 / 附件 | cache、upload-artifact、download-artifact 各版本协议、下载权限和保留期 | 待验证 |
| 复用 | composite Action、reusable workflow、输入 / 秘密传递 | 待验证 |
| 发布 | release 创建 / 更新 / 附件；常用 gh / Octokit 调用按指定命令验收 | 待验证 |
| 权限语义 | permissions、environment、concurrency、fork PR 秘密与 Token 权限 | 待验证 |
| 工作负载 OIDC | id-token 请求、issuer / audience / subject 与目标云信任 | 待验证，首版不默认承诺 |

Action 的主版本标签仅用于发现，验收及发行锁定具体提交；分别记录 JavaScript、Docker、composite 的运行时条件。官方对照页可能随主线变化，不把旧文档中的“忽略字段”列表或新文档中的支持声明直接套到所有版本。

发现静默忽略的权限 / 环境 / 并发字段时视为失败。可在工作台受控模板中拒绝执行，或以自有部署授权 / 锁补足并标记“需适配”；不能声称已覆盖用户直接推送的任意 YAML。若底座不能强制关键边界，首版限制工作流与 Runner 信任范围，而不是仅靠 UI 提醒。

## API 与 Webhook

Gitea 原生 API 是独立契约，不能直接把 `/api/v1` 重命名为 GitHub API。工作台继续使用自有 API；常用自动化脚本则通过独立兼容入口适配已经验收的子集，建议独立 origin 的 `/repos/...` 路径，精确地址在 M0 冻结。

首批优先级：仓库 / 提交只读，Issue 列表与创建 / 评论 / 状态，Release 与附件，Actions 工作流触发 / runs 查询 / 取消 / 重跑。每项对照字段、分页与 Link、错误体、状态码、权限、时间格式、上传域名、速率限制及未知字段行为。无法等价映射时明确拒绝或公布差异，不返回看似成功但语义改变的结果。

使用用户自己的 RadishForge 兼容 Token（设计候选）或经验证的授权映射；不能把任意 GitHub Token 当作 Gitea 凭据。Token 必须可撤销、限定 scope，并绑定真实上游用户权限。禁止把 Token 透传至任意用户提供的地址。

Webhook 另验收 event 名、action、payload、投递 ID、HMAC、重放与重试。接收 Gitea webhook 和对外提供 GitHub 形状事件是不同通道，保留来源，不伪造为 github.com 发出的事件。

## M0 现有差异基线

本节是 M0-S04 的已取证输入，不是新的兼容状态矩阵或阶段放行。`M0-G01`—`M0-G27` 仅为差异引用编号，不增加任务 / 验收项；执行状态仍由 [tasks](../planning/tasks.md)维护。前三项 scope、两项生命周期、一个公开撤销接口缺口及十二项 Issue 差异的原始输入见[基线记录](../records/2026-11-04-m0-gap-and-delivery-preparation.md)；接续五项 Release 与四项 OCI 差异分别见[Release 记录](../records/2026-11-04-m0-release-validation.md)和[OCI 记录](../records/2026-11-04-m0-oci-validation.md)。原始来源和命名记录可定位，不按复现批次数重复计数；先前导出快照不回写。

表中处理沿用 [ADR 0003](../adr/0003-gitea-authorization-profiles.md) / [ADR 0004](../adr/0004-issue-validation-and-reconciliation.md) / [ADR 0005](../adr/0005-release-authorization-and-reconciliation.md) / [ADR 0006](../adr/0006-oci-authorization-and-digest-retention.md)的 M0 约束和后续实现契约；没有新增自动远端撤销、生产幂等、强制制品保留或任意工作流兼容承诺，也未批准缩减关键权限要求。

| 编号 | 已取证的原始行为 | 现有处理与仍须保留的边界 |
| --- | --- | --- |
| M0-G01 | public-only 原身份组合 UserInfo 403 | 使用显式 `read:user` 完整身份组合并复核私有资源仍拒绝；原组合不宣称可用 |
| M0-G02 | 常见 OIDC scope 能读私有仓库 | 身份与资源客户端 / 凭据分离，校验完整组合；不保证任意第三方应用受限 |
| M0-G03 | 未知 scope 被接受并能读私有仓库 | 联网前拒绝未知组合、回读实际 grant；不宣称上游已拒绝原始请求 |
| M0-G04 | 旧配置过期 Token introspection 401 | 受控实例禁用查询 / 表单资源鉴权后 inactive；错误 secret 和原因未知的 401 仍拒绝，不伪造 inactive |
| M0-G05 | 禁用账号仍可 refresh / active | 在线账号复核拒绝后停止使用；恢复账号不自动恢复已终止的本地授权，M1 尚须实现 |
| M0-G06 | 固定公开 REST / Discovery 无单用户 grant 撤销端点 | 原生 UI 撤销已实测；自动远端撤销路径 / 承诺仍待决定，不调用私有页面请求或删除共享应用代替 |
| M0-G07 | 外仓库标签添加 200、无改变 | 当前目录前检 + 写后核对；原始接口仍忽略输入 |
| M0-G08 | 不存在标签添加 200、无改变 | 明确拒绝失效 ID，不把 200 当作分类已完成 |
| M0-G09 | 小数标签 ID 200 且 labels 改变 | 仅接受真正整数，拒绝小数 / 布尔 / 重复 ID；不沿用数值截断 |
| M0-G10 | 外仓库里程碑编辑 500 | 核对当前仓库归属，错误后回读；不将其标为正确 4xx |
| M0-G11 | 不存在里程碑编辑 500 | 前检及结果核对；删除竞态仍可能使前检过期 |
| M0-G12 | 不存在负责人编辑 500 | 当前可分配目录校验，角色授权另查；不自动重试 |
| M0-G13 | 复合编辑 500 后标题已变 | 回读并呈现部分完成、保留草稿；不承诺整个 PATCH 原子性 |
| M0-G14 | 外仓库标签参与创建 201，分类丢失 | 前检及逐字段回读；Issue 已创建，不能因分类缺失再创建一条 |
| M0-G15 | 外仓库里程碑参与创建 201，分类丢失 | 同上；不宣称整体请求成功或自动删除补偿 |
| M0-G16 | 无效标签筛选 200，结果变宽 | 失效约束明确失败，不移除约束回退；没有证据证明跨用户泄漏 |
| M0-G17 | 无效里程碑筛选 200，结果变宽 | 同上；目录前检不能替代结果 / 权限核对 |
| M0-G18 | 仓库读者创建 Issue 201，分类字段被忽略 | 区分正文创建与分类权限；不能从 scope 或创建成功推导分类管理权 |
| M0-G19 | 只读 scope 的草稿元数据 404，两种附件下载路径 200 | 受控草稿操作要求 Release 写用途与单元写权限；原生差异保留，没有证明跨用户泄漏 |
| M0-G20 | Release PATCH 空 name / body 为 200，原值未清除 | 不报告清空成功；公开清空路径仍待决定，不用空格 / 删除重建伪造 |
| M0-G21 | Tag POST 文档 200，处理器 / 实测 201 | 精确版本接受 201 并保留声明 gap，不扩为任意 2xx |
| M0-G22 | 已有 Tag 与 target 不同仍发布 200，Tag 指向原提交 | 发布前查精确 Tag / SHA，不符拒绝；发布后再查，不能宣称竞态已消除 |
| M0-G23 | 无效 target 发布 500 | 回读草稿 / Tag 并保留原错误；本例未发布不外推所有 500 无副作用 |
| M0-G24 | 公开个人包关联私有仓库后其他用户仍可 pull | 按包所有者 / 组织可见性及直接 Registry 权限判断，不把 link 当 ACL；私有组织边界已单独取证 |
| M0-G25 | Registry 请求 pull，但 write:package PAT 仍可上传 | 实际范围依赖 PAT scope 和当前资源权限，不宣传 query scope 已收窄凭据 |
| M0-G26 | 覆盖最后一个 Tag 后原 Manifest Digest 404 | 固定 Digest 仍要验证保留 / 存在；缺失阻断，不取 latest 或重新构建冒充原制品；强制保留待决定 |
| M0-G27 | 删除 PAT 后旧 Registry Token 仍能读写 | 本地停止 / 丢弃缓存不等于已复制 Token 远端立即失效；不以禁用整个账号或改全局签名密钥代替单凭据撤销 |

已有正文 `content_version` 冲突 409、只读 / 越权 / 撤权拒绝、删除和响应丢失回查是相应原生切片证据。它们与上述 gap 一同保留，不把正确拒绝再计为差异，也不把正确主路径抵消失败。组织继承标签、自定义单元权限、产品会话 / 草稿 / 请求持久化，以及 GitHub REST 字段 / Link / 错误体与指定客户端的双端对照仍待验收；上方兼容矩阵不因本表改成“直接兼容”。

Release / OCI 已取得相应原生切片证据，仍需完整范围取舍与 Action / API 精确样例。Runner 暂停期间不冻结未经执行的 Action commit / 运行时支持，不启动 Actions；GitHub REST 对照版本的当前支持与客户端版本也须在相应取证时复核。M0-G06 自动化方案、M0-G19 / G20、G24—G27 的能力边界、关键权限 / 保留 / 未知结果处理和完整阶段出口未收口前，不放行 M1。

## 缺口处理顺序与边界

先验证底座原生能力，再提供明确配置、少量工作流 / API 适配，必要时向上游贡献；不为追求兼容直接重写底座执行器。全量 GitHub GraphQL、GitHub Apps 安装协议、官方 Runner 注册协议、市场全部 Action 和所有 gh 子命令不在首版承诺内。

若关键样例无法在既定底座和零核心补丁目标下满足，M0 提交带成本的差异决策，不能静默降级需求或直接开始维护大分叉。Forgejo 加入时重新执行本矩阵，不继承 Gitea 的通过结果。
