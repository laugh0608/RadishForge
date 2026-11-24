# 当前状态

更新日期：2026-11-24（主线 CI、G23 拒绝路径、arm64 工作流与单镜像 Release、M0-S04 权限及只读入口）。

规划阅读链：[整体范围](../product-plan.md) / [阶段路线图](../planning/roadmap.md) → [大专题与子专题](../planning/topics.md) → [任务状态](../planning/tasks.md) / [验收标准](../planning/acceptance.md)。本文汇总当前重点，任务状态不在此另建副本；规则统一及本批验证见[记录](../records/2026-11-01-planning-rules-alignment.md)。

11 月 24 日收工。主线 CI 门禁已验收，G23 目标缺失时零发布 PATCH，专用 arm64 VM 上的私有工作流已贯通至单镜像和 Release 附件。`162d0e7` 记录了固定模板的只读入口。M0 继续进行，下次先评审首版是否接受受控模板。 [当日提交与证据复核](../records/2026-11-24-day-review.md) · [接续事项与验收条件](../planning/m0-validation.md#接续事项)

2026-11-17 收工前已保存 12 个提交，完成基础 Runner 操作单、OCI 与 Release 定向取证、G06 自助撤销重启复测及 GitHub 参考权限复查。70 项本地测试通过，OrbStack 本批资源已清理。 [提交回顾与收工交接](../records/2026-11-17-day-review.md)

2026-11-09 收工时，M0-S04 已取得固定版 Gitea 同源 REST、GitHub 所有者和匿名参考及所有者只读 PAT 证据。G19 补证确认普通写者降权和撤权后，原凭据按 Tag 查草稿及两路下载均为 404。G20 确认原生页面可清空草稿说明。G27 确认删除来源 PAT 后仍能换发可用后继，撤销候选已完成静态核查。OCI 两项取舍和 GitHub 普通角色验收继续保留，Runner 和 Actions 持续暂停，阶段保持 M0。 [当日提交与收工交接](../records/2026-11-09-day-review.md)

2026-11-04 收工时，生命周期、Issue、静态准备、Release 与 OCI 已分别由 `78d11a2`、`a6eca0d`、`c825fb2`、`c77b29e`、`01eb1b0` 保存，records 保留各自导出快照。63 项本地测试通过，最终 OCI / Release / Issue / profiles 真实流程分别保留 4 / 5 / 12 / 1 条差异退出 2，七批资源清理读回通过。当日提交与代码 / 文档复核见[收工回顾](../records/2026-11-04-day-review.md)。

2026-11-10 所有者确认按“关键取舍 → 最小 Runner 链路 → 定向补证与组合 → 阶段评审”收口，保留原 M0-S01—S04。G26 / G27 具体取舍仍待确认；当前 Runner / Actions 仍暂停，不进入 M1。本次只更新文档，未恢复环境操作或提交 / 推送授权。 [规划记录](../records/2026-11-10-m0-closeout-planning.md)

2026-11-17 已交付[基础 Runner 操作单](../../tests/contracts/m0/compat/runner-runbook.md)，固定首轮样例和候选 job 镜像的 amd64 Digest，写明私有检出、触发关联、失败、取消 / 重跑、失联、权限与清理。只读确认本机 OrbStack daemon 为 Linux arm64；实际 amd64 宿主、执行配置及运行授权待确认。 [静态准备记录](../records/2026-11-17-m0-runner-preparation.md)

同日所有者确认 G26 验证 30 天受控保留，G27 承诺产品侧停用和删除 PAT 后拒绝该 PAT 交换，并接受已复制 Bearer 的风险。已按本批授权在 OrbStack 拉取两个固定镜像，完成 G24—G26 权限、真实清理和原 Digest 恢复。原生 G25 差异复现，最终批退出 2，三批资源清理及端口读回通过。30 天实时时间窗、产品逻辑及真实交付组合待验。 [首版决定](../adr/0006-oci-authorization-and-digest-retention.md#first-release-oci-decisions) · [隔离实测](../records/2026-11-17-m0-oci-retention-validation.md)

G19 已补私有组织仓库的 `repo.releases` 写到读、移出 team 的证据。同一有效凭据在降权后草稿列表不含夹具，详情和两路附件下载为 404；移出后草稿与已发布对照均被拒。独立读 team 始终可读取已发布 Release 及附件。两批资源已清理，Runner / Actions 暂停。 [G19 组织仓库实测](../records/2026-11-17-m0-release-org-role-transitions.md)

G19 已提交 `041cd88`。后续 G20 同源草稿字段补证完成，两个混合 PATCH 返回 200 且只写入非空字段，草稿状态、附件和 Tag / SHA 回读一致。G20 差异保留，探针退出 2，本批资源已清理。 [G20 字段实测](../records/2026-11-17-m0-release-edit-fields.md)

G20 已提交 `2a1bf3e`。G06 已补正常自助撤销在单独重启资源 Gitea 后的持久性，目标授权仍缺失，原 access token 在自然到期前仍被拒绝，其他独立授权仍可用。本批退出 0，资源已清理；公开自动撤销缺口保留，产品侧停用仍在 M1。 [G06 重启实测](../records/2026-11-17-m0-oauth-restart-validation.md)

G06 重启补证已提交 `d3cd475`。尚未兑换的授权码与在途刷新仍缺上游实测。M1 防护验收要求晚到结果无法复活已停用的授权或覆盖新凭据，验收边界已提交 `596d1b7`。 [撤销时序证据复核](../records/2026-11-17-m0-oauth-revocation-timing-review.md)

COMP-01 已复核双端 REST 证据，并只读确认 GitHub 个人私有测试仓库的固定引用、已发布 Release 和附件元数据。Actions 关闭，协作者列表只有所有者。补齐 GitHub 普通角色证据待确认独立测试账号与获准目标。 [REST 证据复核](../records/2026-11-17-m0-rest-evidence-review.md)

## 当前事实

- 项目名为 RadishForge（萝卜锻坊），P0 规划与治理基础已落地。
- 已完成 P0-07 文档整合并提交 `bac115e`：以[专题索引](../planning/topics.md)连接整体规划、能力专题与阶段 / 任务 / 验收，细化[M0-S01—M0-S04](../planning/m0-validation.md)，见[整合记录](../records/2026-11-01-planning-integration.md)；该记录保留当批未提交状态，后续提交见[M0-S01 记录](../records/2026-11-01-m0-s01-review.md)。
- 原有产品、架构与阶段规划之外，已补齐协作 / 安全 / 贡献规则、Git 基础文件、PR / Issue 模板、仓库设置、分阶段 Rulesets 模板及 ADR 0002。
- 已专项复核五个兄弟项目的十份 AGENTS / CLAUDE，根协作入口由 88 行细化至 133 行，补齐通用执行条件和专题细则。当前两份入口逐字节一致。
- 本地治理检查工具使用 Python 3.9+ 标准库，产品栈不变；检查器和故障回归结果见[治理记录](../records/2026-10-29-governance-foundation.md)。
- M0-S01 已选择[首个候选组合](../planning/m0-s01-baseline.md)：Gitea 28.2.0-rootless、PostgreSQL 18.6-bookworm 已在本机原生 Linux arm64 镜像运行并取得部分真实证据；后续 UTM 专用 VM 已用 Runner 5.2.4 跑通[首条 arm64 私有工作流](../records/2026-11-24-m0-runner-arm64.md)。Go 1.27.3、Node 24.22.2 / npm 11.19.1、Engine 29.9.2 / Compose 5.6.1 的发行组合仍未最终冻结。
- 本机实际 context 为已运行的 OrbStack `orbstack`，daemon Engine 29.8.2 / Compose 5.5.0；保留现有版本，不改全局 context。已新增[M0 隔离配置与探针](../../tests/contracts/m0/README.md)，仅回环端口、独立项目 / 网络 / 卷、任务专用 CA，无 Runner / socket / privileged。不是专用 VM 或 amd64 / 发行组合通过证据。
- [本机验证](../records/2026-11-01-m0-local-validation.md)已覆盖 TLS、PKCE / ID Token 签名与声明、普通用户私有资源、Issue 创建 / 评论 / 关闭 / 回读、只读 scope、跨用户隔离、资源撤权及删除 OAuth 应用后的 Token 拒绝。两发行方同邮箱身份输入可区分，但自有绑定 / 会话没有实现。
- 原始三项 scope 差异仍保留，并在无 cookie 的 API 传输下回归复现：public-only 原组合 UserInfo 403，常见 OIDC / 未知 scope 均可读私有仓库。不能以受控客户端通过改写上游行为或标整项 IAM / BASE / COMP 通过。
- 已按[ADR 0003](../adr/0003-gitea-authorization-profiles.md)收敛三种[授权组合](../../tests/contracts/m0/gitea-auth-profile.json)：身份登录、资源只读、Issue 写入；M0 工具在联网前拒绝未知 / 缺失 / 额外 scope、错误用途 / issuer，并回读 confidential client、callback、同意设置与实际 grant scope。身份组合 UserInfo 200 / 私有资源 403，资源组合的只读 / 写入边界已验证；这些控制尚未进入 M1 Go 服务。
- Release 切片新增第四种独立 `release_write = openid read:user write:repository`，原三种组合和客户端 / 安全 / TTL 设置逐项核对未变。新用途的显式同意、实际 grant、在线账号、阶段刷新与普通角色均实测；它是宽于 Release 按钮的仓库 scope，不授权 package / OCI。边界及未实现部分见[ADR 0005](../adr/0005-release-authorization-and-reconciliation.md)。
- [11 月 1 日生命周期证据](../records/2026-11-01-m0-auth-profile-validation.md)覆盖拒绝同意、client secret、callback、刷新客户端绑定 / 轮换 / 重放 / 不扩权、资源撤权 / 应用删除和真实 access token 过期，保留禁用账号仍可 refresh 与过期 introspection 401 两项差异，流程完成但退出 2；该历史结果不改写。
- [11 月 4 日对照验证](../records/2026-11-04-m0-lifecycle-validation.md)复现两项差异，并定位 introspection 正文 `token` 被通用鉴权先处理的问题。受控 JSON schema 2 要求新实例关闭表单 / 查询串资源鉴权并回读配置；过期目标 Token 返回 inactive，错误客户端 secret 401。禁用账号仍可刷新 / introspection active，但在线账号 403，凭据复核拒绝；上游签发差异继续保留，不能宣称原生修复。
- 同批已取得一次并发刷新单一成功后继、旧值重放 / 后继只读边界、账号恢复，以及原生 UI 单用户撤销 / 跨 grant 隔离 / 显式重新同意的证据；真实等待 3602.849 秒后 refresh token 自身到期拒绝，同一客户端重新授权有效、旧值仍拒绝。最终源码受控组合 / 旧配置均回归，25 项本地检查通过。四批均保留差异退出 2，不以本批切片关闭完整 M0-02 / IAM 或 M0。
- 固定 OpenAPI、OAuth 路由和两套实例的 Discovery 均无公开单用户 grant 撤销入口。`DELETE /api/v1/token` 删除 PAT，原生设置页由用户撤销自己的 grant，工作台分别报告本地停用和上游状态。公开自动撤销缺口保留，产品解绑和后台任务停止仍在 M1 验收。见 [ADR 0003 撤销边界](../adr/0003-gitea-authorization-profiles.md#2026-11-09-单用户-grant-撤销边界)。
- M0-S03 的[Issue 上游切片](../records/2026-11-04-m0-issue-validation.md)覆盖列表 / 筛选 / 分页排除真实 PR、正文版本冲突、编辑 / 关闭 / 重开、标签 / 负责人 / 里程碑操作，以及只读 scope、仓库读写角色、跨用户 / 撤权和资源删除。最终批次 32 条命名记录保留 12 条 gap：非法输入被忽略 / 转换、无效筛选变宽、部分错误返回 500、复合编辑 500 后标题已改变、创建分类字段被静默丢弃。受控前检不表示上游已修复，也不关闭完整 ISSUE-01 或 M0-03。
- 两种真实 TLS 响应丢失场景均只发一次合成 Issue POST：上游 201 后超时可通过只读回查观察到唯一结果；未转发 / 零匹配及两个匹配仍为 unknown、自动重试为 0。[ADR 0004](../adr/0004-issue-validation-and-reconciliation.md)明确目录与权限、正文版本与复合写入、失败后回读的边界；生产持久化关联与 UI 尚未实现。共享 OAuth 回归保留禁用账号可刷新的既有差异。
- [Release 切片](../records/2026-11-04-m0-release-validation.md)覆盖草稿 / 分页、编辑 / 发布、固定 Tag SHA、raw / multipart 附件与真实字节摘要、普通写者 / 读者 / 外部用户、撤权 / 删除、跨对象关联和重复。创建 / 发布 / 附件的已提交响应丢失均只写一次并经 GET 对账；未转发、半包断开和同名多匹配仍 unknown、自动重试 0。保留五项差异：草稿只读 scope 的元数据 / 下载不一致、空字段清除被忽略、Tag POST 声明 / 实测状态码不一致、已有 Tag 与 target 不同仍发布、无效 target 发布 500；不宣称原生修复或完整发布器通过。
- [OCI 切片](../records/2026-11-04-m0-oci-validation.md)覆盖独立 package PAT / Registry Bearer、私有组织 / team、原始 Blob / Manifest Digest、Docker scratch 构建 / regctl 推拉 / Docker load、撤权 / 删除及九个真实超时 / 半包场景。旧 Registry Token 在团队降权、移出私有组织或禁用账号后受相应限制；四条差异仍保留：公开个人包的仓库 link 不提供隐私、Registry pull 参数不收窄 write PAT、覆盖最后 Tag 后旧 Digest 404、删除 PAT 后旧 JWT 仍可读写。Metadata 声明 24 小时但未真实等待，未证明即时单凭据撤销 / 强制保留，见[ADR 0006](../adr/0006-oci-authorization-and-digest-retention.md)。
- 原四种 OAuth 组合逐字未变；新增[Registry 专用契约](../../tests/contracts/m0/gitea-registry-profile.json)限定 PAT / 固定 origin / service 和 regctl 资产摘要。regctl v0.11.7 darwin/arm64 为任务临时工具，不是产品依赖；使用任务 CA、私密配置且关闭 Docker 凭据 / 证书导入，Buildx 状态在任务目录，无系统 / daemon 信任修改。
- [M0-S04 差异基线](../architecture/github-compatibility.md#m0-现有差异基线)现汇总 3 条 scope、2 条生命周期、1 条公开单用户撤销接口缺口、12 条 Issue、5 条 Release 及 4 条 OCI 差异，共 27 条；26 条定位到原始 gap，接口缺口单列，复现不重复计数。沿用 ADR 0003—0006，尚未冻结完整 GitHub 兼容范围或批准阶段晋级；早先快照不回写。
- 固定版包清理规则约束计划清理，直接覆盖和显式删除另走包写权限。Registry JWT 校验不回查来源 PAT，实测原 Bearer 换出的后继保留用户和 `write:package` scope，`nbf` / `exp` 均晚 3 秒。真实到期、原 JWT 到期后后继的实际可用性及连续换发待验，总体远端失效窗口仍无可承诺上限。后续交付按已确认的 G26 受控保留及 G27 产品侧停用方案推进。 [ADR 0006 首版承诺](../adr/0006-oci-authorization-and-digest-retention.md#first-release-oci-decisions)
- G27 已静态核查 Harbor 项目机器人与逐请求撤销。若未来要求有界远端失效，再验证停用后无法取得有权后继、已签 Bearer 的实际窗口，以及逐请求方案对全部访问路径的控制。 [G27 方案核查](../records/2026-11-09-m0-registry-revocation-options.md)
- 11 月 1 日及 11 月 4 日任务资源均已清理；先前生命周期 / Issue / Release 各批和本批 OCI / 共享回归七批的容器 / 网络 / 卷读回均为 0，本批任务镜像标签 / 镜像读回为 0。`.local/m0` 凭据 / 证书 / 客户端 / Buildx 状态已移除，18443 / 19443 / 18543 已释放，无本任务运行服务。共享镜像与 BuildKit 缓存保留，未触碰其他项目资源。尚无自有业务工程、产品依赖、自有数据库或产品容器发行配置。
- master / dev 的初始共同基线为 `c2764aa278cbed9aab3faf6f43a0556e80e623f4`。origin 为 `https://github.com/laugh0608/RadishForge.git`，保持 public 可见性。本地 master / dev 分别跟踪 origin/master / origin/dev。暂无 Tag、镜像或 Release，候选域名待配置。 [初始化记录](../records/2026-10-29-local-git-bootstrap.md) · [远端记录](../records/2026-10-29-remote-governance.md)
- 2026-11-24，[PR #1](https://github.com/laugh0608/RadishForge/pull/1) 以 merge commit `dd88e4b` 合入 master，dev 已快进回流并推送。回流后在同一提交上手动运行 `PR Checks`，治理检查、70 项 Python 测试与 `Candidate Quality` 均通过。 [手动 CI](https://github.com/laugh0608/RadishForge/actions/runs/45386088275) · [验收记录](../records/2026-11-24-candidate-quality.md)
- 远端默认分支为 master，Ruleset `26129324` 已启用 strict `Candidate Quality`，来源为 GitHub Actions App `15368`。原删除、非快进、PR 和会话解决要求均保留，仍为 0 个额外审批、无 bypass。允许 merge / rebase，禁用 squash，关闭自动合并和自动删源分支。dev 无有效 Ruleset。
- 两份本地 Ruleset JSON 仍为 disabled 模板。GitHub 托管 CI 已验证主 PR 通过以及临时草稿的失败、跳过和取消传播，读回确认主 PR 的检查为必需。 [CI 与规则读回](../records/2026-11-24-candidate-quality.md)
- 五个指定兄弟项目仅只读参考，未修改其文件；差异提炼见[治理来源](../references/governance-review.md)。

## 已确认方向与本地规则

产品方向：独立 Gitea + Go 模块化单体 + TypeScript / React；首版纳入 OIDC、Issue、Actions / API 兼容子集、镜像与 Release、Compose CD，尽量不修改 Gitea 核心。见[ADR 0001](../adr/0001-foundation.md)。

本地治理基线：dev 日常开发、master 稳定主线，远端建立后作为默认分支并经 PR 晋级；允许 merge / rebase，禁用 squash，主线合并后先回流 dev。基础保护先行，真实 CI 后升级 required check；单人阶段零额外审批、无 CODEOWNERS、默认无 bypass。见[ADR 0002](../adr/0002-repository-governance.md)。本地和远端分支均已存在，基础远端设置已启用并读回；配置验收不等于完整行为验收。

## 当前授权与停止线

2026-10-29 用户已创建指定 GitHub 空仓库，并授权推送提交、按本项目规则设置远端 Rulesets，可使用本机 gh；当时暂不创建远端或推送的限制已由该轮明确要求更新。授权覆盖该次 origin、分支推送、配套仓库设置、基础保护及相应记录提交。

2026-11-01 用户先要求整合规划并提交，再推进 M0-S01 静态准备并提交，分别形成 `bac115e`、`9c1e481`。本轮开始时本地 dev 与 origin/dev 引用一致、工作区干净；未 fetch，不据此宣称本轮核对了服务端实时状态。

随后用户明确授权本机 Docker 优先并推进身份、权限和 API 验证，形成 `3be73d3`；后续规划规则统一形成 `fa3ffe8`。本轮开始时工作区干净，保留该批规则变更，未 fetch 或重新核对远端实时状态。

用户随后明确要求处理三项 scope 差异、收敛白名单 / Gitea 授权配置并继续身份权限验证，暂不启动 Runner。该批复用同一 context、固定镜像与回环端口，在说明内存、测试窗口及 cleanup 后启动新的合成数据批次；新增短 Token / refresh rotation 仅作用于本任务 Gitea 新实例。结束已移除任务资源与凭据，无宿主升级、默认 context 或系统信任变更。

收工轮用户明确授权先提交工作区，再审阅今天所有提交并更新文档，最后单独提交文档；代码与证据批次已形成 `d857342`，文档收尾由后续独立提交保存。此次没有 fetch / push 或远端写入，本地引用不能证明服务端实时状态；历史 records 的“当批未提交”与当时结果保留，不回写。

2026-11-04 用户明确要求按接续计划执行两项生命周期差异收口、刷新 / 撤销负例、验证和文档同步，保持 Runner 暂停、不进入 M1。本批沿用相同 context、镜像、回环端口及合成数据，并在说明真实一小时窗口后启动新批次；单用户撤销只操作本机隔离 Gitea 的原生页面。已有 Playwright 缓存 / Chrome 用于任务专用浏览器，沙盒限制按同一任务申请最小放行，没有安装依赖或修改系统信任。验证阶段不含 Git 写入；随后用户明确要求提交工作区更改，本轮授权覆盖本批本地暂存与提交。提交前复核 22 个路径、25 项本地测试及证据摘要；暂存检查发现新模块末尾多余空行，仅做格式清理并确认 Python AST 不变，原始联调摘要与格式调整分别保留。没有重新启动服务、fetch / push 或远端写入，不重跑已完成的一小时取证。

用户随后明确要求接续 M0-S03 Issue 契约验证及文档同步，Runner 继续暂停、不进入 M1。本批复用相同 context、固定缓存镜像与合成账号；说明资源与清理方式后，创建本机隔离 Gitea 的分支 / PR 夹具，并在探针进程临时绑定 127.0.0.1:18543 注入固定 Issue POST 的真实响应丢失。仍使用本批 CA 验证 TLS，不扩大 OAuth issuer 或提供通用代理；监听随场景停止。首轮、最终 Issue 与共享 OAuth 回归三批均已清理，无依赖安装、宿主升级或全局配置变更。随后用户明确要求提交本批工作区更改并继续下一步，19 个路径已由 `a6eca0d` 保存；接续差异汇总与 Release / OCI 静态准备由下一批 `c825fb2` 保存。该批没有 fetch / push 或其他远端写入，也未启动新的服务、扩大授权组合或更改系统信任。

用户随后要求提交接续文档，并按既定计划推进 Release 隔离取证；十个接续路径已由 `c825fb2` 保存。说明资源 / 时长 / 清理后，在相同固定环境中执行普通用户、独立 Release 用途、合成草稿 / 附件 / Tag 与真实超时 / 半包回查，并回归共享 Issue / profiles。前三轮中断保存原始结果后分别清理再新建环境，未删开始标记重放；最终三轮完成但保留差异。仅操作本机隔离 Gitea，没有 GitHub Tag / Release、push、Runner、业务工程、宿主升级或全局信任修改。新探针与证据后由用户另行授权提交，形成 `c77b29e`。

用户随后明确要求提交本批 Release 工作区更改，并按计划执行 OCI 隔离取证，覆盖私有组织包权限、固定 Digest 推拉、撤权及超时先回查，做好验证与文档同步。Release 28 个路径已由 `c77b29e` 保存。说明固定客户端版本、约 12 MB 下载 / 磁盘、临时路径与资源清理后，完成本机合成 OCI 协议 / 客户端、撤权 / 超时及共享回归；Buildx 原全局状态目录写入被拒绝后，仅改任务 `BUILDX_CONFIG`，未关闭验证。前两批中断保存后清理再新建，最终源码在新批重跑；未删标记重放、不向 GitHub / 公共 Registry 推送，不启动 Runner / 业务工程或修改全局信任。用户本次明确要求先提交工作区，再回顾当日全部提交、同步文档和接续事项，最后单独提交文档并收工；OCI 23 个路径已由 `01eb1b0` 保存，文档收尾由本页及[当日回顾](../records/2026-11-04-day-review.md)所在的独立提交保存，实际 SHA 以 Git 历史为准。本次不再运行真实联调，没有 fetch / push 或远端写入。

2026-11-09 用户分别授权并提交 OCI 公开机制、单用户 grant 撤销、Release 草稿权限与空字段清除、包可见性与 Registry scope 的静态核查，形成 `4d3468d`、`58d5eaa`、`0add8d3`、`dce1be7`。首批 COMP-01 样例由 `9f2b734` 保存，随后离线准备双端 REST 夹具。

用户随后授权以其 GitHub 账号创建正式命名的私有测试仓库。该轮仅在新建的 `laugh0608/RadishForge-Test` 关闭 Actions、推送合成 refs 并写入 REST 夹具，正式项目的 `origin` 配置与远端未动。测试仓库及合成数据保留供后续对照。新增测试身份、协作者或组织权限需确认范围。 [GitHub 参考记录](../records/2026-11-09-m0-github-rest-reference.md)

用户要求提交上一批并接续，REST 夹具与 GitHub 参考已由 `10d4511` 保存。接续按既有授权在同一 context、缓存镜像与回环端口建立 Gitea 隔离批次，首批中断经只读对账后清理，最终新批完成并保留两项差异。两个批次的容器、卷、网络、凭据和监听均已清理。GitHub 侧只读确认测试仓库没有额外协作者。 [Gitea 对照记录](../records/2026-11-09-m0-gitea-rest-comparison.md)

Gitea 对照已由 `d6bd77a` 保存。GitHub 所有者只读 PAT 已实测读取成功，创建 Issue 和草稿 Release 均为 403，独立回读未出现对应对象。用户手动删除测试 PAT，列表和安全日志均已确认。删除后同一 PAT 读取仓库为 401，既有所有者凭据对照为 200。普通协作者授权及撤权仍需独立身份。 [单账号实测](../records/2026-11-09-m0-github-owner-pat.md)

2026-11-24 所有者授权将 GitHub 托管 CI 纳入 PR #1、验证后更新现有 master Ruleset，并以 merge commit 合入、回流推送 dev、手动验证 CI。随后授权补记验收结果并提交推送至 dev。 [CI 取证](../records/2026-11-24-candidate-quality.md)

2026-11-24 所有者另行确认 arm64 专用 VM 路线，授权新建并启动一台 UTM VM、执行首条合成私有工作流及清理。首批已提交 `2151b93`，随后按所有者要求完成 arm64 生命周期批和清理。失联样例中 job 容器先结束，Gitea 在 Runner 退出 11 分 14 秒后记录失败。原生 amd64 兼容验收单列。产品业务工程、宿主工具升级、生产凭据、发布与部署仍按原阶段安排。 [arm64 首条私有工作流](../records/2026-11-24-m0-runner-arm64.md)

## 当前验证入口

```bash
python3 scripts/check-repo.py
python3 -B -m unittest discover -s scripts/tests -v
```

以上验证本地治理及 M0 scope、Issue / Release / OCI 输入 / 对账、客户端隔离、二进制和 HTTP 失败决策，当前共 73 项本地测试，无需启动服务。[PR Checks](../../.github/workflows/pr-checks.yml) 复用同一入口。上游协议通过 [M0 契约入口](../../tests/contracts/m0/README.md) 在获准隔离环境中另行取证，涉及 Docker、网络和合成数据写入。

## 下一步

专用 arm64 VM 已跑通普通写者提交 → run / attempt → 私有镜像 Digest → Release / 附件，独立读者已按 Digest 拉取并核对镜像及附件字节。生命周期批已提交 `6b15b67`，制品、权限和设置读回已提交 `f4ea207`。M0-S04 已按四份原件梳理取证范围。同组自动取消通过，job 权限验收失败，候选原生不支持所需环境审批。新仓库继承的权限上限已通过重启读回，停用 Actions 时普通写者手动派发为 403、零新增 run。 [权限配置与手动派发停止条件](../records/2026-11-24-m0-actions-settings.md) · [arm64 权限与并发实测](../records/2026-11-24-m0-arm64-actions-policy.md) · [四份原始样例的证据范围](../architecture/github-compatibility.md#m0-s04-四份原始样例的证据范围) · [arm64 单镜像与 Release 实测](../records/2026-11-24-m0-arm64-image-release.md)

`RadishForge-Test` 权限复查已提交 `3111071`。暂不注册机器账号，普通写者和移除协作者后的访问继续待验证。组织仓库的 `Read` / `Write` 仍按私有组织条件补证。 [角色复查](../records/2026-11-17-m0-rest-evidence-review.md#个人仓库普通写者复查)

G22 隔离实测已提交 `dc33663`。G23 继正向复测后，已在本机固定版 Gitea 验证目标提交 404 时前检仅发 GET、零发布 PATCH。独立普通账号回读原草稿保留、原 Tag 仍缺失，本批资源已清理。其他失败分支沿用本地模拟，原生无效 target 发布 500 的差异保留。 [G22 隔离实测](../records/2026-11-17-m0-release-publication-readback.md#固定版-gitea-隔离实测) · [G23 正向](../records/2026-11-17-m0-release-target-preflight.md) · [G23 拒绝](../records/2026-11-24-m0-runner-platform-and-g23.md#g23-目标提交缺失)

1. **先评审首版是否接受受控模板。** 建议沿固定模板取得的只读证据评估这条适配路径。若采纳，下一批验证获准模板能在固定 Runner 配置上执行，变更模板或配置时在执行前被拒。若要求原样 YAML，等待可验证的上游修正或有效配置。环境审批单独保留。 [接续事项与验收条件](../planning/m0-validation.md#接续事项) · [固定模板实测](../records/2026-11-24-m0-arm64-readgate.md)
2. **收口对应权限与平台条件。** GitHub 普通写者及撤权需要独立测试身份与获准仓库；原生 amd64 工作流需要独享的 Linux amd64 目标。条件具备后做对应实测，调整首版承诺须由所有者明确决定。 [差异分组](../architecture/github-compatibility.md#closeout-disposition)
3. **评审 M0 出口并交接 M1。** 满足[唯一阶段出口](../planning/acceptance.md#m0-exit)才进入原定工程、身份与仓库基础；否则列具名阻塞和解除条件，不新增采用准备阶段。

M0 保持进行中。单镜像和 Release 组合证据已取得，正式支持组合、关键权限承诺及阶段交接仍待评审。原 27 条差异基线继续适用。

每个阻塞先安排一次有界取证；失败后定位并决定定向修正、改选或等待，不用扩展矩阵填补等待。五组件发布、生产 CD、完整安装 / 升级 / 恢复、更广平台 / IdP 与未入选兼容能力按原阶段后置；关键权限及首版承诺的保留 / 撤销保证不能直接后置。原 6—10 人日不作为剩余工期或自动追加预算。

原创内容的使用和贡献授权见[项目许可证](../../LICENSE)，上游与发行产物按[许可专题](../governance/upstream-and-licensing.md#许可)分别核对。

治理线：G0-01 和 G0-03 已完成。G0-02 的推送、配套设置和基础 Ruleset 已完成配置读回，安全报告渠道与独立账号的权限及拒绝行为待验。M0 仍按产品验收证据推进。 [CI 取证](../records/2026-11-24-candidate-quality.md)

仍待决定 / 取证：候选组合其余能力与最终支持冻结、发行目标平台验收、job 镜像及首批 Action / API 范围、安全报告渠道、真实域名和发行渠道。本机 arm64 的部分运行证据已经取得，不外推发行支持。不以这些未定项阻止本地治理交付。

详细任务见[任务清单](../planning/tasks.md)；历史证据见[规划记录](../records/2026-10-29-planning-bootstrap.md)、[治理记录](../records/2026-10-29-governance-foundation.md)、[本地初始化记录](../records/2026-10-29-local-git-bootstrap.md)和[远端配置记录](../records/2026-10-29-remote-governance.md)。
