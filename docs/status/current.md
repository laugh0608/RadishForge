# 当前状态

更新日期：2026-11-04（Asia/Shanghai）。

规划阅读链：[整体范围](../product-plan.md) / [阶段路线图](../planning/roadmap.md) → [大专题与子专题](../planning/topics.md) → [任务状态](../planning/tasks.md) / [验收标准](../planning/acceptance.md)。本文汇总当前重点，任务状态不在此另建副本；规则统一及本批验证见[记录](../records/2026-11-01-planning-rules-alignment.md)。

2026-11-01 的提交与收工见[当日回顾](../records/2026-11-01-day-review.md)。2026-11-04 已交付 M0-S02 的两项生命周期差异定位、刷新 / 撤销负例与文档同步，见[本批记录](../records/2026-11-04-m0-lifecycle-validation.md)；真实一小时到期与最终源码组合 / 旧配置回归均已执行，四批清理读回通过。本批由包含本文的 `test(iam)` 提交保存，具体 SHA 以 Git 历史为准；验证记录保留导出时的未提交快照。Runner 持续暂停，不进入 M1，未推送。

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
- [11 月 1 日生命周期证据](../records/2026-11-01-m0-auth-profile-validation.md)覆盖拒绝同意、client secret、callback、刷新客户端绑定 / 轮换 / 重放 / 不扩权、资源撤权 / 应用删除和真实 access token 过期，保留禁用账号仍可 refresh 与过期 introspection 401 两项差异，流程完成但退出 2；该历史结果不改写。
- [11 月 4 日对照验证](../records/2026-11-04-m0-lifecycle-validation.md)复现两项差异，并定位 introspection 正文 `token` 被通用鉴权先处理的问题。受控 JSON schema 2 要求新实例关闭表单 / 查询串资源鉴权并回读配置；过期目标 Token 返回 inactive，错误客户端 secret 401。禁用账号仍可刷新 / introspection active，但在线账号 403，凭据复核拒绝；上游签发差异继续保留，不能宣称原生修复。
- 同批已取得一次并发刷新单一成功后继、旧值重放 / 后继只读边界、账号恢复，以及原生 UI 单用户撤销 / 跨 grant 隔离 / 显式重新同意的证据；真实等待 3602.849 秒后 refresh token 自身到期拒绝，同一客户端重新授权有效、旧值仍拒绝。最终源码受控组合 / 旧配置均回归，25 项本地检查通过。四批均保留差异退出 2，不以本批切片关闭完整 M0-02 / IAM 或 M0。
- 固定公开 REST 描述没有单用户 grant 撤销接口，两套实例 Discovery 未公布撤销端点；自动化方案 / 范围留待 M0-S04 确认，不封装私有页面请求或删除共享应用代替。产品解绑、会话、加密存储和后台任务停止仍在 M1。
- 11 月 1 日及 11 月 4 日任务资源均已清理；本批四组标签下容器 / 网络 / 卷读回为 0，`.local/m0` 凭据 / 证书 / 浏览器 profile 已移除，当前无本任务运行服务。共享镜像缓存保留，未触碰其他项目资源。尚无自有业务工程、产品依赖、自有数据库、产品容器发行配置或活动 CI。
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

保持“暂不写业务代码”的边界；新增的是 M0 验证约束与工具，没有产品会话 / 绑定实现。不包含 Runner、安装 / 升级宿主工具、新 VM、全局设置 / 系统信任、真实仓库或生产凭据、测试 PR、远端设置、发布或部署。下次继续时复核资源归属及相同目标的既有授权；服务、权限或外部目标发生实质变化时再核对授权。

## 当前验证入口

```bash
python3 scripts/check-repo.py
python3 -B -m unittest discover -s scripts/tests -v
```

以上验证本地治理及 M0 scope 策略负例，包含工作树 / 暂存区空白检查，不启动服务；上游协议另用[M0 契约入口](../../tests/contracts/m0/README.md)，有 Docker / 网络 / 合成数据写入副作用，仅在对应授权下执行。结果层级不能混用。

## 下一步

当前活跃子专题为 M0-S02 身份 / 权限可行性，具体范围见[M0-S02](../planning/m0-validation.md#m0-s02身份与私有权限可行性)，最新执行与未覆盖见[本批记录](../records/2026-11-04-m0-lifecycle-validation.md)：

1. 下批继续 M0-S03 的 Issue 列表 / 分页、编辑 / 重开、标签 / 负责人 / 里程碑查询与分配，覆盖越权、非法关联对象、资源删除及超时先回查；沿用普通用户和受控组合，不扩大到工作台实现。
2. 将两项差异的受控处理及单用户撤销公开接口缺口纳入既有 M0-S04 差异基线；不将原生页面可撤销等同工作台可自动撤销，不提前关闭整项 IAM 或 M0。产品解绑、会话与后台作业停止仍留在 M1。
3. 保持 M0-S02 已有授权边界；上游版本、Token / scope 配置或方案变化时重跑受影响契约。已有四批原始差异与受控证据保留，后续不能用改状态、重试或服务账号绕过替代。

Runner 持续暂停，当前配置明确关闭 Actions。M0-S03 的 Actions / OCI / Release 和 M0-S04 的完整兼容样例 / 缺口决定仍未完成；原始 scope 与禁用账号可刷新仍保留上游差异，受控处理不冒充上游修复，不进入 M1 业务工程初始化。

治理线：G0-01 已完成；G0-02 的推送、配套设置和基础 Ruleset 已完成配置读回，安全报告渠道与独立权限 / PR 行为验收待补，不能关闭完整 GOV-02。G0-03 尚未开始，按 G0-02 依赖推进，真实 CI 经过成功与故障传播验证后再升级同一规则。治理收尾不替代 M0 产品证据，也不阻塞 M0 只读准备。

仍待决定 / 取证：候选组合其余能力与最终支持冻结、发行目标平台验收、job 镜像及首批 Action / API 范围、自有许可、安全报告渠道、真实域名和发行渠道。本机 arm64 的部分运行证据已经取得，不外推发行支持。不以这些未定项阻止本地治理交付。

详细任务见[任务清单](../planning/tasks.md)；历史证据见[规划记录](../records/2026-10-29-planning-bootstrap.md)、[治理记录](../records/2026-10-29-governance-foundation.md)、[本地初始化记录](../records/2026-10-29-local-git-bootstrap.md)和[远端配置记录](../records/2026-10-29-remote-governance.md)。
