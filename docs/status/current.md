# 当前状态

更新日期：2026-11-09（Asia/Shanghai）。

规划阅读链：[整体范围](../product-plan.md) / [阶段路线图](../planning/roadmap.md) → [大专题与子专题](../planning/topics.md) → [任务状态](../planning/tasks.md) / [验收标准](../planning/acceptance.md)。本文汇总当前重点，任务状态不在此另建副本；规则统一及本批验证见[记录](../records/2026-11-01-planning-rules-alignment.md)。

2026-11-09 已完成 M0-S04 的 G26 / G27、G06、G19 / G20 与 G24 / G25 静态核查。本批确认包按所有者授权，Registry 签发保留实际 package scope，并登记 G27 旧 Bearer 换发待证。G26 / G27 的取舍保留。Runner 和 Actions 继续暂停，阶段保持 M0。 [G24 / G25 核查记录](../records/2026-11-09-m0-package-access-mechanisms.md)

2026-11-04 收工时，生命周期、Issue、静态准备、Release 与 OCI 已分别由 `78d11a2`、`a6eca0d`、`c825fb2`、`c77b29e`、`01eb1b0` 保存，records 保留各自导出快照。63 项本地测试通过，最终 OCI / Release / Issue / profiles 真实流程分别保留 4 / 5 / 12 / 1 条差异退出 2，七批资源清理读回通过。当日提交与代码 / 文档复核见[收工回顾](../records/2026-11-04-day-review.md)。

## 当前事实

- 项目名为 RadishForge（萝卜锻坊），P0 规划与治理基础已落地。
- 已完成 P0-07 文档整合并提交 `bac115e`：以[专题索引](../planning/topics.md)连接整体规划、能力专题与阶段 / 任务 / 验收，细化[M0-S01—M0-S04](../planning/m0-validation.md)，见[整合记录](../records/2026-11-01-planning-integration.md)；该记录保留当批未提交状态，后续提交见[M0-S01 记录](../records/2026-11-01-m0-s01-review.md)。
- 原有产品、架构与阶段规划之外，已补齐协作 / 安全 / 贡献规则、Git 基础文件、PR / Issue 模板、仓库设置、分阶段 Rulesets 模板及 ADR 0002。
- 已专项复核五个兄弟项目的十份 AGENTS / CLAUDE，根协作入口由 88 行细化至 133 行，补齐通用执行条件和专题细则；除首行标题外保持一致。
- 本地治理检查工具使用 Python 3.9+ 标准库，产品栈不变；检查器和故障回归结果见[治理记录](../records/2026-10-29-governance-foundation.md)。
- M0-S01 已选择[首个候选组合](../planning/m0-s01-baseline.md)：Gitea 28.2.0-rootless、PostgreSQL 18.6-bookworm 已在本机原生 Linux arm64 镜像运行并取得部分真实证据；Runner 5.2.4 仅为后续候选，本批未下载 / 注册 / 启动。Go 1.27.3、Node 24.22.2 / npm 11.19.1、Engine 29.9.2 / Compose 5.6.1 的发行组合仍未最终冻结。
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
- 固定版包清理规则约束计划清理，直接覆盖和显式删除另走包写权限。Registry JWT 校验不回查来源 PAT，旧 Bearer 能否换出后继及真实到期均待实测。当前证据无法界定总体远端失效窗口。两个缺口及所有者取舍继续保留。 [ADR 0006 核查补充](../adr/0006-oci-authorization-and-digest-retention.md#2026-11-09-包可见性与-registry-scope-核查)
- 11 月 1 日及 11 月 4 日任务资源均已清理；先前生命周期 / Issue / Release 各批和本批 OCI / 共享回归七批的容器 / 网络 / 卷读回均为 0，本批任务镜像标签 / 镜像读回为 0。`.local/m0` 凭据 / 证书 / 客户端 / Buildx 状态已移除，18443 / 19443 / 18543 已释放，无本任务运行服务。共享镜像与 BuildKit 缓存保留，未触碰其他项目资源。尚无自有业务工程、产品依赖、自有数据库、产品容器发行配置或活动 CI。
- 本地初始共同基线为 `c2764aa278cbed9aab3faf6f43a0556e80e623f4`，已推送 master / dev；当前在 dev，后续远端配置记录提交沿 dev 推进，master 保持初始基线。见[初始化记录](../records/2026-10-29-local-git-bootstrap.md)与[远端记录](../records/2026-10-29-remote-governance.md)。
- origin 为 `https://github.com/laugh0608/RadishForge.git`，保持用户创建的 public 可见性；本地 master / dev 分别跟踪 origin/master / origin/dev。没有 PR、Tag、镜像或 Release，候选域名未配置。
- 远端默认分支为 master，基础 Ruleset `26129324` 已 active 并读回：只保护 master，禁止删除 / force push、要求 PR 与会话解决、0 个额外审批、无 bypass；允许 merge / rebase、禁 squash，关闭自动合并和自动删源分支。dev 无有效 Ruleset。
- 两份本地 Ruleset JSON 仍为 disabled 模板，与远端 active 的差异已记录。当前不要求 Candidate Quality，真实 CI 与来源绑定未建立；未进行 PR 阻断或破坏性负向行为验收。
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

2026-11-09 用户分别授权并提交 OCI 公开机制、单用户 grant 撤销、Release 草稿权限与空字段清除的静态核查，形成 `4d3468d`、`58d5eaa`、`0add8d3`。本批接续包所有者和 Registry scope 静态核查与文档同步。四批均未启动隔离环境或推送。后续补证前复核资源归属及相同目标的既有授权，服务、权限或外部目标发生实质变化时再核对授权。

保持“暂不写业务代码”的边界。当前范围不包含 Runner、安装 / 升级宿主工具、新 VM、全局设置 / 系统信任、真实仓库或生产凭据、GitHub 远端测试 PR、远端设置、对外发行或部署。

## 当前验证入口

```bash
python3 scripts/check-repo.py
python3 -B -m unittest discover -s scripts/tests -v
```

以上验证本地治理及 M0 scope、Issue / Release / OCI 输入 / 对账、客户端隔离、二进制和 HTTP 失败决策，当前共 63 项本地测试，包含工作树 / 暂存区空白检查，不启动服务；上游协议另用[M0 契约入口](../../tests/contracts/m0/README.md)，有 Docker / 网络 / 合成数据写入副作用，仅在对应授权下执行。结果层级不能混用。

## 下一步

继续 M0-S04。M0-S03 未覆盖能力继续保留。详细输入、交付物和完成标准见 [M0-S04 接续事项](../planning/m0-validation.md#接续事项)。

1. 由所有者分别确认制品保留与回退要求、单凭据远端失效要求和可接受窗口。G27 先验证旧 Bearer 换发，再根据结果确定到期观察范围，长时窗口另预算。 [OCI 补证条件](../planning/m0-validation.md#oci-补证条件)
2. 接下来准备精确 GitHub REST / 客户端及 Action 样例，先固定调用、版本、预期和失败判定。G06、G19 / G20 和 G24 / G25 继续按已登记条件补证，未运行样例保持待验证。 [M0-S04 补证入口](../planning/m0-validation.md#接续事项)
3. 保持 Runner 暂停 / Actions 关闭；没有真实 run / attempt 不填占位，不把合成 Release 或个人仓库证据外推为五组件清单、完整发布冻结、组织权限、恢复或整个 M0 通过；M1 / M2 产品实现仍未开始。

Runner 持续暂停，当前配置明确关闭 Actions。M0-S03 的 Actions、Release / OCI 的完整产品能力及 M0-S04 的完整兼容样例 / 缺口决定仍未完成；原始差异继续保留，受控处理不冒充上游修复，不进入 M1 业务工程初始化。

治理线：G0-01 已完成；G0-02 的推送、配套设置和基础 Ruleset 已完成配置读回，安全报告渠道与独立权限 / PR 行为验收待补，不能关闭完整 GOV-02。G0-03 尚未开始，按 G0-02 依赖推进，真实 CI 经过成功与故障传播验证后再升级同一规则。治理收尾不替代 M0 产品证据，也不阻塞 M0 只读准备。

仍待决定 / 取证：候选组合其余能力与最终支持冻结、发行目标平台验收、job 镜像及首批 Action / API 范围、自有许可、安全报告渠道、真实域名和发行渠道。本机 arm64 的部分运行证据已经取得，不外推发行支持。不以这些未定项阻止本地治理交付。

详细任务见[任务清单](../planning/tasks.md)；历史证据见[规划记录](../records/2026-10-29-planning-bootstrap.md)、[治理记录](../records/2026-10-29-governance-foundation.md)、[本地初始化记录](../records/2026-10-29-local-git-bootstrap.md)和[远端配置记录](../records/2026-10-29-remote-governance.md)。
