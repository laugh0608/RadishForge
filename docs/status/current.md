# 当前状态

更新日期：2026-10-29（Asia/Shanghai）。

## 当前事实

- 项目名为 RadishForge（萝卜锻坊），P0 规划与治理基础已落地。
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

用户已创建指定 GitHub 空仓库，并授权推送提交、按本项目规则设置远端 Rulesets，可使用本机 gh；此前暂不创建远端或推送的限制已由本轮明确要求更新。授权覆盖本次 origin、分支推送、配套仓库设置、基础保护及相应记录提交。保持“暂不写业务代码”的边界，不扩大到依赖安装、镜像下载、环境启动、测试 PR、发布或部署。

## 当前验证入口

```bash
python3 scripts/check-repo.py
python3 -B -m unittest discover -s scripts/tests -v
```

仅验证本地治理；现在已包含工作树与暂存区 Git 空白检查，回归中的无 Git 场景使用临时副本。范围与限制见[检查说明](../../scripts/README.md)。

## 下一步

G0-01 已完成；G0-02 的推送、配套设置和基础 Ruleset 已完成配置读回。后续补齐安全报告渠道与独立权限 / PR 行为验收，不能以本轮 API 成功关闭完整 GOV-02。G0-03 尚未开始，真实 CI 经过成功与故障传播验证后再升级同一规则。

产品实施仍从 M0 开始：冻结 Gitea / Runner / 工具链组合，在隔离环境验证 OIDC 与 OAuth 权限、Issue、Actions、镜像、Release，形成首批 GitHub 兼容矩阵。关键权限或接口语义不满足时先形成差异决策，再进入业务工程初始化。

仍待决定 / 取证：精确版本、首批 Action / API 范围、目标平台、自有许可、本项目安全报告渠道、真实域名和发行渠道。不以这些未定项阻止本地治理交付。

详细任务见[任务清单](../planning/tasks.md)；历史证据见[规划记录](../records/2026-10-29-planning-bootstrap.md)、[治理记录](../records/2026-10-29-governance-foundation.md)、[本地初始化记录](../records/2026-10-29-local-git-bootstrap.md)和[远端配置记录](../records/2026-10-29-remote-governance.md)。
