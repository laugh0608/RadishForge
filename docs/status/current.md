# 当前状态

更新日期：2026-10-29（Asia/Shanghai）。

## 当前事实

- 项目名为 RadishForge（萝卜锻坊），P0 规划与治理基础已落地。
- 原有产品、架构与阶段规划之外，已补齐协作 / 安全 / 贡献规则、Git 基础文件、PR / Issue 模板、仓库设置、分阶段 Rulesets 模板及 ADR 0002。
- 已专项复核五个兄弟项目的十份 AGENTS / CLAUDE，根协作入口由 88 行细化至 133 行，补齐通用执行条件和专题细则；除首行标题外保持一致。
- 本地治理检查工具使用 Python 3.9+ 标准库，产品栈不变；检查器和故障回归结果见[治理记录](../records/2026-10-29-governance-foundation.md)。
- Gitea v28.2.0 仅作为静态接口参考；Runner、产品工具链、镜像 Digest 与 GitHub 兼容组合未冻结。
- 尚无业务代码、产品依赖、数据库、Docker / Compose、运行服务、活动 workflow 或真实功能验收。
- 已使用用户现有 Git 身份建立本地 Git 和首个共同基线提交，master / dev 指向同一提交，当前位于 dev；交付时暂存区与工作树无遗留。精确提交与检查方式见[初始化记录](../records/2026-10-29-local-git-bootstrap.md)。
- 未创建远端或 upstream，未推送；没有 PR、Tag、镜像或 Release，候选域名未配置。
- 两份 Ruleset JSON 均为 disabled 待启用模板；远端保护、真实 Candidate Quality 与来源绑定均未建立。
- 五个指定兄弟项目仅只读参考，未修改其文件；差异提炼见[治理来源](../references/governance-review.md)。

## 已确认方向与本地规则

产品方向：独立 Gitea + Go 模块化单体 + TypeScript / React；首版纳入 OIDC、Issue、Actions / API 兼容子集、镜像与 Release、Compose CD，尽量不修改 Gitea 核心。见[ADR 0001](../adr/0001-foundation.md)。

本地治理基线：dev 日常开发、master 稳定主线，远端建立后作为默认分支并经 PR 晋级；允许 merge / rebase，禁用 squash，主线合并后先回流 dev。基础保护先行，真实 CI 后升级 required check；单人阶段零额外审批、无 CODEOWNERS、默认无 bypass。见[ADR 0002](../adr/0002-repository-governance.md)。本地分支已存在，远端设置尚未启用。

## 当前授权与停止线

本轮明确授权：补充通用协作约束，使用用户现有 Git 身份初始化本地仓库、完成首个提交、建立 master / dev 并切到 dev。用户明确要求先不创建远端或推送。保持“暂不写业务代码”的边界，不扩大到依赖安装、镜像下载、环境启动、PR、发布或部署。目标、范围和影响不变的既有授权持续有效。

## 当前验证入口

```bash
python3 scripts/check-repo.py
python3 -B -m unittest discover -s scripts/tests -v
```

仅验证本地治理；现在已包含工作树与暂存区 Git 空白检查，回归中的无 Git 场景使用临时副本。范围与限制见[检查说明](../../scripts/README.md)。

## 下一步

G0-01 已完成；G0-02 / G0-03 暂不执行。后续用户允许远端操作时，再确定 host / owner / 可见性、安全报告渠道与基础保护；真实 CI 验证后升级 CI 版规则。没有远端不阻止后续获授权的本地 dev 工作。

产品实施仍从 M0 开始：冻结 Gitea / Runner / 工具链组合，在隔离环境验证 OIDC 与 OAuth 权限、Issue、Actions、镜像、Release，形成首批 GitHub 兼容矩阵。关键权限或接口语义不满足时先形成差异决策，再进入业务工程初始化。

仍待决定 / 取证：精确版本、首批 Action / API 范围、目标平台、自有许可、远端与可见性、本项目安全报告渠道、真实域名和发行渠道。不以这些未定项阻止本地治理交付。

详细任务见[任务清单](../planning/tasks.md)；历史证据见[规划记录](../records/2026-10-29-planning-bootstrap.md)、[治理记录](../records/2026-10-29-governance-foundation.md)和[本地初始化记录](../records/2026-10-29-local-git-bootstrap.md)。
