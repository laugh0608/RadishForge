# Rulesets 与远端设置策略

本页是 RadishForge 自身仓库的目标政策。当前无远端，所有 JSON 都是本地待启用模板；GitHub Rulesets 不是 Gitea 分支保护 API，也不代表产品已经实现 Rulesets 兼容。

## 两阶段配置

| 项目 | 基础阶段 | CI 阶段 |
| --- | --- | --- |
| 模板 | `master-protection.json` | `master-protection-ci.json` |
| 目标 | 仅 `refs/heads/master` | 相同 |
| 删除、force push | 禁止 | 相同 |
| PR 与会话解决 | 必须 | 相同 |
| 审批数 / CODEOWNERS / 最后推送审批 | 0 / 关闭 / 关闭 | 单人阶段相同 |
| 合并方式 | merge、rebase；无 squash | 相同 |
| required check | 无；人工复核本地证据 | `Candidate Quality`，strict 开启 |
| bypass | 默认空 | 默认空 |
| 仓库模板 enforcement | `disabled` | `disabled` |

两份模板表示**同一条规则的前后版本**，部署时选择一个、更新原 ID，不能同时创建。基础版先建立 PR 与历史保护；CI 版只在真实检查通过正反向验收后替换，不借“无 CI”长期免除已有功能检查。

模板中的 disabled 防止把未验收配置误称为已启用；实际启用时在审阅的请求副本中改为 active 并读回确认。未来远端 active、本地模板 disabled 是有意区分，比较时记录这一预期差异，其他字段逐项比对。

不预设组织、用户或 App ID。CI 模板暂未绑定 `integration_id`；启用前从真实 check run 查明产生者，在请求中绑定对应 GitHub App 并记录 ID，避免同名状态由任意来源冒充。平台能力或账号计划不支持时记录缺口，不能视为同等保护。CI 版 `do_not_enforce_on_create: false`；已有共同基线后再启用，不依靠创建分支豁免门禁。

默认不授予管理员常驻 bypass。紧急恢复若确需例外，取得针对该事件的授权，记录原因、影响与恢复时间；只允许限定操作者临时在 PR 内 bypass，不开放 always / exempt 或直接 push，完成后移除并读回。管理员仍可改规则，模板不能消除这一平台权限事实。

## 配套设置

[repository-settings.json](../../.github/repository-settings.json)是最小期望字段，不是远端完整导出：默认分支 master，开启 merge / rebase，关闭 squash / auto merge / 自动删除源分支。应用前必须已有 master，明确目标仓库及可见性，读取现有设置后只改获授权字段。

不启用线性历史，不预设签名提交、merge queue、部署门禁或 tag Ruleset。具备签名恢复流程、真实多人评审或发行入口后单独评估。当前不创建 CODEOWNERS，不选择许可证，也不默认公开仓库。

Conventional Commits 通过贡献规范和本地 PR 范围检查约束，不写远端 commit message 正则，避免误拒绝 Git 自动生成的合法 merge 标题。

## 启用与迁移顺序

1. 确认授权、平台、owner / repo、可见性、账号计划与管理权限；先只读获取仓库设置、仓库 / 组织 Rulesets、旧分支保护及主线有效规则。
2. 保留变更前脱敏快照。已有匹配规则时用原 ID 精确更新，不能覆盖未知规则集或重复创建；继承规则冲突先由其管理者处理。
3. 完成共同基线与 master / dev 建立，再配置 merge options。基础版可独立启用，但必须明确没有 CI 强制验收。
4. CI 升级时先提交真实工作流与检查器，用测试 PR 得到同名 job 成功结果，再用故障样例确认失败 / 取消 / 应执行却跳过不能被聚合放行；记录 head / base SHA 与 check 来源。
5. 准备最小请求，选择模板、设为 active；CI 版绑定真实 check 来源。审阅后按授权创建或更新原规则。
6. 读回 ID、enforcement、refs、bypass、PR、strict、context / 来源与 merge options；再核对有效规则，排除组织层叠加影响。
7. 保存证据并更新 current。请求超时先查询实际状态，不能盲重试 POST 造成重复规则。

API 路径见[模板说明](../../.github/rulesets/README.md)。目标与权限未确定前不提供一键远端写入脚本。

## 验收与恢复

| 场景 | 预期 |
| --- | --- |
| 普通有写权限账号直接更新主线 | 拒绝；通过 PR 才能合并 |
| 删除主线 / non-fast-forward 更新 | 拒绝 |
| 未解决 review conversation | 阻断合并 |
| 单维护者 PR、无额外审批 | 其他条件通过即可，不要求自我批准 |
| squash | 不可选；merge / rebase 按政策可用 |
| CI 失败、取消、缺失、应执行却跳过 | CI 阶段阻断 |
| CI 属于旧 head / 过期 base、错误来源 | 不用于当前晋级 |
| 主线合入后回流 | 主线为 dev 祖先，保留共享历史 |

破坏性负向尝试先在专用验证仓库或可丢弃分支复刻规则并取得授权，不在真实 master 上试删或 force push。`git push --dry-run` 不足以证明服务端所有规则生效；生产目标只读核对加真实测试 PR，测试仓库证据不能冒充生产目标完整验收。

规则错误锁住合并时先读回定位，修正字段或缺失 check；不能删断言、关闭检查制造通过。需恢复远端时按授权还原本次已知设置，保留前后快照与有效规则结果，不覆盖他人同步更新。

## 平台迁移

若未来托管在 Gitea，按冻结版本映射 PR、禁止直推 / force push / 删除、审批、状态检查和管理员行为；逐项标记等效、需补偿或不支持，使用隔离非管理员账号验收。不得直接导入 GitHub JSON，或仅凭字段名称相似宣称兼容。产品能力独立进入 [GitHub 兼容矩阵](../architecture/github-compatibility.md)。

2026-10-29 静态依据：[GitHub Rulesets 概览](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)、[可用规则](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)、[Rules REST API](https://docs.github.com/en/rest/repos/rules)。来源说明平台接口与约束，不证明本项目远端已验收。
