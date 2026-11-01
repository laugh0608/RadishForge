# 当前状态

更新日期：2026-11-01（Asia/Shanghai）。

规划阅读链：[整体范围](../product-plan.md) / [阶段路线图](../planning/roadmap.md) → [大专题与子专题](../planning/topics.md) → [任务状态](../planning/tasks.md) / [验收标准](../planning/acceptance.md)。本文汇总当前重点，任务状态不在此另建副本；规则统一及本批验证见[记录](../records/2026-11-01-planning-rules-alignment.md)。

本批只统一规划规则与映射，验证通过后用户已授权分别本地提交，不推送；下文此前批次的外部执行授权仅描述其历史范围。M0 与治理线的现有产品顺位保持。

## 当前事实

- 项目名为 RadishForge（萝卜锻坊），P0 规划与治理基础已落地。
- 已完成 P0-07 文档整合并提交 `bac115e`：以[专题索引](../planning/topics.md)连接整体规划、能力专题与阶段 / 任务 / 验收，细化[M0-S01—M0-S04](../planning/m0-validation.md)，见[整合记录](../records/2026-11-01-planning-integration.md)；该记录保留当批未提交状态，后续提交见[M0-S01 记录](../records/2026-11-01-m0-s01-review.md)。
- 原有产品、架构与阶段规划之外，已补齐协作 / 安全 / 贡献规则、Git 基础文件、PR / Issue 模板、仓库设置、分阶段 Rulesets 模板及 ADR 0002。
- 已专项复核五个兄弟项目的十份 AGENTS / CLAUDE，根协作入口由 88 行细化至 133 行，补齐通用执行条件和专题细则；除首行标题外保持一致。
- 本地治理检查工具使用 Python 3.9+ 标准库，产品栈不变；检查器和故障回归结果见[治理记录](../records/2026-10-29-governance-foundation.md)。
- M0-S01 已选择[首个候选组合](../planning/m0-s01-baseline.md)：Gitea 28.2.0-rootless、PostgreSQL 18.6-bookworm 已在本机原生 Linux arm64 镜像运行并取得部分真实证据；Runner 5.2.4 仅为后续候选，本批未下载 / 注册 / 启动。Go 1.27.3、Node 24.22.2 / npm 11.19.1、Engine 29.9.2 / Compose 5.6.1 的发行组合仍未最终冻结。
- 本机实际 context 为已运行的 OrbStack `orbstack`，daemon Engine 29.8.2 / Compose 5.5.0；保留现有版本，不改全局 context。已新增[M0 隔离配置与探针](../../tests/contracts/m0/README.md)，仅回环端口、独立项目 / 网络 / 卷、任务专用 CA，无 Runner / socket / privileged。不是专用 VM 或 amd64 / 发行组合通过证据。
- [本机验证](../records/2026-11-01-m0-local-validation.md)已覆盖 TLS、PKCE / ID Token 签名与声明、普通用户私有资源、Issue 创建 / 评论 / 关闭 / 回读、只读 scope、跨用户隔离、资源撤权及删除 OAuth 应用后的 Token 拒绝。两发行方同邮箱身份输入可区分，但自有绑定 / 会话没有实现。
- 保留三个 scope 差异：`openid public-only email profile` 的 UserInfo 为 403；常见 OIDC scope 和未知 scope 样例均能读私有仓库。显式增加 `read:user` 的 public-only 变体已验证 UserInfo 200 / 私有仓库 403。探针完整执行后退出 2，不能标整项 IAM / BASE / COMP 通过。
- 本批容器、网络、卷和 `.local/m0` 凭据 / 证书已清理并读回；共享镜像缓存保留，未触碰其他项目资源。尚无自有业务工程、产品依赖、自有数据库、产品容器发行配置或活动 CI；当前无本任务运行服务。
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

随后用户明确授权本机 Docker 优先，调整文档、核查环境、准备隔离配置并推进身份、权限和 API 验证，暂不启动 Runner。本轮已在说明用途、固定版本、回环端口、资源与清理影响后，执行本机隔离镜像拉取、启动、合成数据 / 授权验证和清理；该授权更新原先仅静态准备的停止线，不重复审批同范围步骤。

保持“暂不写业务代码”的边界；新增的是 M0 验证工具，没有产品会话 / 绑定实现。本轮不包含 Runner、安装 / 升级宿主工具、新 VM、全局设置 / 系统信任、真实仓库或生产凭据、测试 PR、远端设置、发布或部署。验证交付后用户已明确授权提交本批工作区改动，覆盖隔离配置、探针、脱敏结果与文档同步，具体提交回执以 Git 记录为准；不包含推送。后续改变服务、权限或外部目标时再核对实际授权。

## 当前验证入口

```bash
python3 scripts/check-repo.py
python3 -B -m unittest discover -s scripts/tests -v
```

以上仅验证本地治理，包含工作树 / 暂存区空白检查；上游协议另用[M0 契约入口](../../tests/contracts/m0/README.md)，有 Docker / 网络 / 合成数据写入副作用，仅在对应授权下执行。结果层级不能混用。

## 下一步

当前活跃子专题为 M0-S02 身份 / 权限可行性，并已推进 M0-S03 的 Issue API 部分。M0-S01 的本机配置可复现，M0-01 仍待最终支持冻结；当前无需另建专用 VM 或外部 HTTPS 主机。下一步根据真实 scope 差异收敛客户端白名单与 Gitea profile，补身份生命周期和 Issue 其他失败边界；方案见[M0 计划](../planning/m0-validation.md)，证据见[本机记录](../records/2026-11-01-m0-local-validation.md)。

Runner 持续暂停，当前配置明确关闭 Actions。M0-S03 的 Actions / OCI / Release 和 M0-S04 的兼容样例 / 缺口决定仍未完成；scope 差异先处理，不因本批部分证据进入 M1 业务工程初始化。

治理线：G0-01 已完成；G0-02 的推送、配套设置和基础 Ruleset 已完成配置读回，安全报告渠道与独立权限 / PR 行为验收待补，不能关闭完整 GOV-02。G0-03 尚未开始，按 G0-02 依赖推进，真实 CI 经过成功与故障传播验证后再升级同一规则。治理收尾不替代 M0 产品证据，也不阻塞 M0 只读准备。

仍待决定 / 取证：候选组合的真实运行 / 最终支持冻结、实际宿主与平台验证、job 镜像及首批 Action / API 范围、自有许可、安全报告渠道、真实域名和发行渠道。不以这些未定项阻止本地治理交付。

详细任务见[任务清单](../planning/tasks.md)；历史证据见[规划记录](../records/2026-10-29-planning-bootstrap.md)、[治理记录](../records/2026-10-29-governance-foundation.md)、[本地初始化记录](../records/2026-10-29-local-git-bootstrap.md)和[远端配置记录](../records/2026-10-29-remote-governance.md)。
