# 兄弟项目治理提炼

核查日期：2026-10-29（Asia/Shanghai）。本轮只读参考所有者本地 Code 目录中指定的五个项目；没有复制实现、凭据、私密配置、许可证或整套检查器。前期产品与上游参考见[来源核查](source-review.md)。

## 参考基线

读取各项目根 AGENTS、基础 Git / 文本文件、SECURITY、PR 模板、`.github/rulesets/README.md` 与主线 JSON；结合 RadishAxiom 仓库治理专题和 RadishMind 分支 ADR。下列 HEAD 用于定位，读取的上述参考文件未发现工作树差异；不据此声称兄弟项目整个工作区干净或远端规则已生效。

| 项目 | 读取时 HEAD | 主要提炼 |
| --- | --- | --- |
| Radish | `29e7030122bc2462262ebd714964106a00242c65` | 根入口与专题分工、风险分层验证；部署原则沿用已有产品专题 |
| RadishMind | `029f996927481a6587f32ecf3b4d9cf54bd8ea35` | dev 串行开发、PR 晋级、回流闭环，聚合检查与独立发行 |
| RadishCatalyst | `bb8756cc798c74a5932b2a3898e2feccba3e1a25` | 模板、工作流、规则、文档保持一致，运行验证不被静态结果替代 |
| RadishFlow | `041dfa2c9a32a7198be381fd0f3b93d6c14f6545` | 按需隔离、合并后回流与发行分离 |
| RadishAxiom | `5c3c4501efb711d7bc1e7804183d28dd903af60e` | 规则分层、真实检查后启用保护、无提交正则、治理变更同步 |

## 采用与调整

| 原则 / 差异 | RadishForge 处理 | 落点 |
| --- | --- | --- |
| 根入口简短，专题 / current / records 各司其职 | 保留并补充路由；不新建平行周志体系 | AGENTS / CLAUDE、文档治理 |
| 各项目授权习惯不同 | 以当前用户要求和本项目持续授权为准，不移植每轮重批或默认提交权限 | 协作专题 |
| dev 日常开发，主线 PR 晋级 | 默认 master，贡献 PR 显式指向 dev；不兼容一个不存在的 main 分支 | 仓库治理、ADR 0002 |
| merge / rebase，禁 squash，回流主线 | 保留；以祖先关系验证，不以 SHA 相等判定 | 仓库治理、PR 模板 |
| 单人零审批、无 CODEOWNERS | 保留；多人阶段再评估真实责任与独立审批 | Rulesets |
| 兄弟模板多有管理员 PR bypass | 本项目默认空，紧急需要时按事件授权临时配置 | Rulesets、ADR 0002 |
| 部分模板含提交标题正则 | 不采用；真实多父 merge 例外在本地检查处理 | 检查器 |
| 已有 Candidate Quality 及语言组件 | 只采用稳定聚合思路；本地基础保护不要求不存在的 CI，未来成功与故障传播验收后升级 | 两阶段 JSON |
| 文本卫生与本地产物隔离 | 按 Go / TS 与治理脚本需要制定，保留锁文件与合成示例 | 三个点文件 |
| 安全、社区与贡献入口 | 原创简明约定；不挪用兄弟项目邮箱、支持承诺、许可证或 CLA | 根文档 |

## 明确不移植

不引入 Radish 的 .NET / ORM / 前端多壳层、RadishMind 的模型与评测治理、RadishCatalyst 的游戏引擎与资产流程、RadishFlow 的 Rust / COM / staging 包门禁、RadishAxiom 的语言语义 / Evidence / 求解器约束。也不复制这些项目的版本号、工具链、活动 workflow 或临时停止线。

RadishForge 专有边界已进入 PR 审查表和安全策略：独立 Gitea、公开接口、权威数据归属、OIDC 与授权分离、可核实的 GitHub 兼容、事件与命令的未知结果、固定 SHA / Digest 及迁移恢复。规则只约束自身研发，不强加给产品托管的用户仓库。

## 根协作文件专项复核

同日后续按用户要求完整复读五个项目的 AGENTS / CLAUDE，共十份文件；参考 HEAD 与上表相同，所读文件无工作树差异。Radish、RadishMind、RadishFlow、RadishAxiom 的两份文件全文一致；RadishCatalyst 仅首段的协作者名称不同，符合它允许首段差异的本地规则。本项目仍保持“仅首行标题可不同”，不放宽同步检查。

本项目原入口 88 行，主要原则已有，但执行条件和维护细节过于压缩。本次扩展为 133 行，通用内容与本项目长期边界分开；没有增加 Gitea、OIDC 或技术栈专有要求。

| 通用主题 | 参考关注点 | 本项目补充 |
| --- | --- | --- |
| 阅读与事实来源 | 各项目最小路由；Axiom 的文档 / 实现漂移判断 | 不默认展开历史；先判断过期方，不降低检查掩盖差异 |
| 工作区保护 | Axiom 的实际分支与预期差异、用户 / 并行改动 | 不强切 / reset 制造干净起点；区分无 Git、无提交、无远端 |
| 推进与澄清 | Catalyst 的局部结构修正、Mind / Flow 的设计边界 | 明确何时自行判断、何时确认范围；完成独立已授权部分 |
| 操作副作用 | 五项目的依赖、服务、系统与外部动作区分 | 说明版本 / 目录 / 端口 / 资源 / 清理；保留本项目持续授权原则 |
| 资源与秘密 | Axiom 的删除路径和敏感输出；Mind 的后台进程交接 | 路径解析、进程归属、合成数据、秘密不进入参数与提交 |
| 通用工程 | 各项目真实抽象、错误上下文、生成入口与文件职责 | 类型和 schema 优先；兜底有触发条件、可观测结果和停止线 |
| 验证与交付 | 各项目风险分层、真实 UI 与证据层级 | 不用 Mock / 静态结果外推真实环境；复核产物、限制与 Git 状态 |
| 根入口维护 | 五项目启动级约束准入与内容归位 | 四项准入判断、双文件同步、180 / 250 行界限和配套专题 |

没有采用兄弟项目的“每轮重新授权”、默认提交权限、固定构建命令、周志制度、语言专属编码方式、视觉 token 系统或生产准入模型。详细执行方式落在[协作专题](../governance/collaboration.md)，本次本地 Git 动作与证据另见[初始化记录](../records/2026-10-29-local-git-bootstrap.md)。

## 平台核查

本轮另读 GitHub 官方 [Rulesets 概览](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)、[可用规则](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)和 [REST API](https://docs.github.com/en/rest/repos/rules)，核对 enforcement、目标 refs、bypass、PR 合并限制和 strict checks 字段。账号计划、实际 check 来源与组织叠加规则仍需在远端落地时核查；本轮没有远端 API 写入或真实规则行为验收。
