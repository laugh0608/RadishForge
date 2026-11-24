# 2026-11-24 提交回顾与收工交接

按北京时间的提交日期核对。收工文档提交前，`dev` 历史中有 9 个当日提交，含主线合入 PR #1 的 merge commit。另有 3 个仅用于草稿 PR #2 的临时负例提交。开始回顾时工作区干净，最后一批实测已经保存在 `162d0e7`。

## 当日提交

| 提交 | 交付与证据 |
| --- | --- |
| `399755a` | 接入 GitHub PR 工作流。治理检查使用源提交与 PR 共同祖先，Python 测试运行在 PR 合并候选树上，两项都成功才通过 `Candidate Quality`。 [工作流](../../.github/workflows/pr-checks.yml) |
| `3a8e7d7` | 记录正常及三组负例的 check run，并核实主线 strict 必需检查绑定 GitHub Actions App `15368`。 [门禁取证](2026-11-24-candidate-quality.md) |
| `dd88e4b` | PR #1 通过必需检查后合入 `master`。合并树与已审查的第二父提交 `3a8e7d7` 相同，随后 `dev` 快进回流。 [合入与回流](2026-11-24-candidate-quality.md#主线合入回流与手动验证) |
| `dc26ca2` | 记录 `dev` 在 `dd88e4b` 上的手动 CI 通过，完成 G0-03。该次远端运行验证了当时的 70 项 Python 测试。 [手动运行记录](2026-11-24-candidate-quality.md#主线合入回流与手动验证) |
| `f8b467c` | OrbStack 上实测 G23。目标提交 404 时，写者前检只发三次 GET，整批零发布 PATCH。独立账号回读原草稿未变，Tag 仍为 404。 [G23 拒绝路径](2026-11-24-m0-runner-platform-and-g23.md#g23-目标提交缺失) |
| `2151b93` | 专用 UTM arm64 VM 跑通首条私有工作流。普通写者派发，独立读者核对提交 SHA、run / attempt / job 及日志。 [首条工作流](2026-11-24-m0-runner-arm64.md) |
| `6b15b67` | 分支和 Tag 触发、主动失败、取消与同一 run 重跑、执行中失联均有独立读回。失联后 job 容器先结束，11 分 14 秒后上游才记录失败。 [生命周期](2026-11-24-m0-runner-lifecycle.md) |
| `f4ea207` | arm64 单镜像经构建、按 Digest 晋级、私有 Release 附件关联后，由独立读者核对原始字节。同组自动取消通过，原件的只读 job 断言失败。权限配置重启后保留，停用 Actions 时新手动派发为 403、零新增 run。 [单镜像与 Release](2026-11-24-m0-arm64-image-release.md) · [权限与并发](2026-11-24-m0-arm64-actions-policy.md) · [权限配置](2026-11-24-m0-actions-settings.md) |
| `162d0e7` | 固定模板成功读取一个私有仓库的 Issue 列表，写请求在独立入口被拒。独立读者确认零新增，授权写者随后返回 201。首版是否接受此适配范围仍待决定。 [只读入口](2026-11-24-m0-arm64-readgate.md) |

草稿 PR #2 的三个提交也已逐个核对。`5fbf953` 加入失效链接与失败测试，`cd7e750` 令治理组件跳过，`eccca40` 为取消测试组件留出观察窗口。三次聚合均失败。这些提交未进入 `dev` 或 `master`，草稿 PR 已关闭，临时分支及工作树已清理。 [三次运行与结果](2026-11-24-candidate-quality.md#工作流与验证结果)

## 代码与文档复核

- 对照 PR 工作流、治理检查器和已归档的远端读回，在 Rulesets 专题补上实际生效的规则与来源，在本地检查说明与 DOC-01 统一两份根协作文件全文一致的要求。 [Rulesets](../governance/rulesets.md) · [工具索引](../../scripts/README.md) · [DOC-01](../planning/acceptance.md)
- 按 G23 的入档提交复算探针记录的 14 份源码及配置摘要，全部匹配。对照共享 Release 附件上传与下载实现，在契约手册补上合成 JSON 文件名、客户端 HTTPS 来源和路径校验。 [请求与源码摘要](2026-11-24-m0-release-missing-target-results.json) · [附件契约](../../tests/contracts/m0/README.md#release-契约与附件)
- 复算工具链、生命周期、arm64 镜像、权限原件、只读模板五份 YAML 和只读入口配置的 SHA-256，均与对应运行记录一致。构建与发布位置的独立读回记录具有相同 Manifest Digest，镜像内源码 SHA 与 Release 的 SHA 一致。在工具索引补上离线镜像校验器的输入和核对范围。 [Runner 操作单](../../tests/contracts/m0/compat/runner-runbook.md) · [镜像读回记录](2026-11-24-m0-arm64-image-release-results.json)

## 收工与接续

收工时 73 项本地测试全部通过。以当日首个提交的父提交 `8f7860e` 为基线，仓库治理、提交标题及 diff 空白检查通过。另行核对本批文档链接使用的本地标题锚点，均可定位。

G23、首条工作流和生命周期三份 JSON 的文件摘要与各自公布值一致。按各批清理回执，OrbStack 探针资源及 UTM 临时来宾、虚盘和密钥均已清理。收工复核使用本地 Git 对象和已归档证据，未重新启动环境。

下次先评审首版是否接受受控模板。若采纳，验证模板和 Runner 配置在调度前可强制约束，再单独验收环境审批。原生 amd64 兼容、GitHub 普通角色及撤权分别保留恢复条件。项目继续处于 M0。 [接续事项](../planning/m0-validation.md#接续事项) · [当前状态](../status/current.md#下一步) · [M0 出口](../planning/acceptance.md#m0-exit)
