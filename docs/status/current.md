# 当前状态

更新日期：2026-11-01（Asia/Shanghai）。

## 当前事实

- 项目名为 RadishForge（萝卜锻坊），P0 规划与治理基础已落地。
- 已完成 P0-07 文档整合：以[专题索引](../planning/topics.md)连接整体规划、能力专题与阶段 / 任务 / 验收，细化[M0-S01—M0-S04](../planning/m0-validation.md)；本轮未冻结候选版本、未启动真实 M0 验证或业务实现，见[整合记录](../records/2026-11-01-planning-integration.md)。
- 原有产品、架构与阶段规划之外，已补齐协作 / 安全 / 贡献规则、Git 基础文件、PR / Issue 模板、仓库设置、分阶段 Rulesets 模板及 ADR 0002。
- 已专项复核五个兄弟项目的十份 AGENTS / CLAUDE，根协作入口由 88 行细化至 133 行，补齐通用执行条件和专题细则；除首行标题外保持一致。
- 本地治理检查工具使用 Python 3.9+ 标准库，产品栈不变；检查器和故障回归结果见[治理记录](../records/2026-10-29-governance-foundation.md)。
- Gitea v28.2.0 仅作为静态接口参考；Runner、产品工具链、镜像 Digest 与 GitHub 兼容组合未冻结。
- 尚无业务代码、产品依赖、数据库、Docker / Compose、运行服务、活动 workflow 或真实功能验收。
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

2026-11-01 用户要求结合既有讨论与当前进度先整合项目，本批范围为规划与文档层级、近期子专题和对应验收整理，不包含新的提交 / 推送或远端设置操作。保持“暂不写业务代码”的边界，不扩大到依赖安装、镜像下载、环境启动、测试 PR、发布或部署。后续只读官方来源核查可先行；需要环境的验证先列明版本、命令、目录、端口、资源与清理影响，核对对应授权。

## 当前验证入口

```bash
python3 scripts/check-repo.py
python3 -B -m unittest discover -s scripts/tests -v
```

仅验证本地治理；现在已包含工作树与暂存区 Git 空白检查，回归中的无 Git 场景使用临时副本。范围与限制见[检查说明](../../scripts/README.md)。

## 下一步

本批活跃工作为 P0-07 规划整合，已完成本地文档交付；下一项为[M0-S01：底座组合与隔离验证准备](../planning/m0-validation.md)，先核对官方来源、选择可复现候选并形成隔离方案。当前尚无运行中的产品子专题。

首个真实执行批次收敛到候选组合与 M0-S02 的一条普通用户私有资源权限链路；随后由 M0-S03 验证 Issue / Actions / OCI / Release，M0-S04 固定首批兼容范围及缺口决策。准备完成不等于阶段验收通过，组合依据真实证据最终冻结；关键权限或接口语义不满足时先决策，再进入 M1 业务工程初始化。

治理线：G0-01 已完成；G0-02 的推送、配套设置和基础 Ruleset 已完成配置读回，安全报告渠道与独立权限 / PR 行为验收待补，不能关闭完整 GOV-02。G0-03 尚未开始，按 G0-02 依赖推进，真实 CI 经过成功与故障传播验证后再升级同一规则。治理收尾不替代 M0 产品证据，也不阻塞 M0 只读准备。

仍待决定 / 取证：精确版本、首批 Action / API 范围、目标平台、自有许可、本项目安全报告渠道、真实域名和发行渠道。不以这些未定项阻止本地治理交付。

详细任务见[任务清单](../planning/tasks.md)；历史证据见[规划记录](../records/2026-10-29-planning-bootstrap.md)、[治理记录](../records/2026-10-29-governance-foundation.md)、[本地初始化记录](../records/2026-10-29-local-git-bootstrap.md)和[远端配置记录](../records/2026-10-29-remote-governance.md)。
