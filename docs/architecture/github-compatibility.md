# GitHub 兼容策略

状态：目标与验收设计，当前没有任何已实测兼容项。以减少用户修改工作流和调用脚本为目标；每个承诺必须对应精确版本与行为证据。

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

## 缺口处理顺序与边界

先验证底座原生能力，再提供明确配置、少量工作流 / API 适配，必要时向上游贡献；不为追求兼容直接重写底座执行器。全量 GitHub GraphQL、GitHub Apps 安装协议、官方 Runner 注册协议、市场全部 Action 和所有 gh 子命令不在首版承诺内。

若关键样例无法在既定底座和零核心补丁目标下满足，M0 提交带成本的差异决策，不能静默降级需求或直接开始维护大分叉。Forgejo 加入时重新执行本矩阵，不继承 Gitea 的通过结果。
