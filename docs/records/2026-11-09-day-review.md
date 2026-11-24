# 2026-11-09 提交回顾与收工交接

按 Asia/Shanghai 日界和本地可见的 Git 引用核对，文档收尾前共有 12 个提交，涉及 35 个不同路径。起点为 `ec46dc1`，工作区的 G27 撤销方案先由 `1252719` 保存。下表按提交顺序记录本地 `dev` 的实际交付，收工回顾由独立的 `docs(status)` 提交保存。

## 当日提交

| 提交 | 交付及验收边界 |
| --- | --- |
| `4d3468d` | 核查 G26 / G27 固定版公开机制。计划清理规则、直接覆盖 / 删除和 PAT / Registry JWT 各有不同边界，强制保留与单凭据失效待取舍。 [OCI 公开机制](2026-11-09-m0-oci-public-mechanisms.md) |
| `58d5eaa` | 区分 G06 原生单用户 grant 撤销、产品侧停用和公开自动化。固定版公开自动化接口仍有缺口。 [单用户 grant 撤销](2026-11-09-m0-oauth-grant-revocation.md) |
| `0add8d3` | 核查 G19 草稿详情与附件权限、G20 REST 空字段和原生编辑路径。记录需实测的组合及产品约束。 [Release 公开机制](2026-11-09-m0-release-public-mechanisms.md) |
| `dce1be7` | 核查 G24 包所有者、仓库 link 与直连可见性，以及 G25 Registry 签发与 scope。跨命名空间行为及逐仓库隔离待补。 [包权限与 scope](2026-11-09-m0-package-access-mechanisms.md) |
| `9f2b734` | 固定 GitHub REST `2026-03-10`、gh `v2.96.0`、四份工作流及六个 Action 提交。工作流运行与完整客户端验收仍待。 [兼容样例](2026-11-09-m0-compat-reference-samples.md) |
| `10d4511` | 保存确定性 Git / 附件夹具和双端手册。在授权的 GitHub 私有测试仓库取得所有者及匿名参考，覆盖仓库、Issue / PR、Release 和实际附件。 [REST 夹具准备](2026-11-09-m0-rest-fixture-preparation.md) · [GitHub 参考](2026-11-09-m0-github-rest-reference.md) |
| `d6bd77a` | 增加固定 Gitea `--mode rest`。最终批取得 175 条 HTTP 轨迹、14 个命名结果，保留 G19 / G20 两条差异，退出 2。首批退出 1 后只读对账并清理，最终批使用新实例。 [Gitea REST 对照](2026-11-09-m0-gitea-rest-comparison.md) |
| `aa8556f` | 保存 GitHub 所有者只读 PAT 探针。两类写入均为 403，独立回读无新增对象。设置与安全日志确认删除后，同一 PAT 请求为 401，既有凭据为 200。精确失效时刻和普通角色撤权待证。 [只读 PAT 实测](2026-11-09-m0-github-owner-pat.md) |
| `5e6e39c` | G20 原生页面可以保存空草稿说明，空标题返回 400，提交的说明未写入。公开 REST 的空值清除缺口保留。 [草稿原生编辑](2026-11-09-m0-release-native-edit.md) |
| `10b58b7` | G19 同一普通写者降权或撤权后，原有效凭据按 Tag 查草稿和两路下载均为 404。证据限个人私有仓库及本地附件存储。 [草稿角色切换](2026-11-09-m0-release-draft-role-transitions.md) |
| `f0fb928` | G27 删除来源 PAT 后，原 PAT 交换 401，原 Bearer 可换发声明到期晚 3 秒的后继。后继能按 Digest 读取和开启上传，真实到期及连续换发待证。 [Bearer 换发实测](2026-11-09-m0-registry-bearer-reissue.md) |
| `1252719` | 核查 Harbor 短期 Bearer 和逐请求撤销入口的适用条件，补齐窗口、身份隔离和旁路验收。两条路径均为静态候选。 [G27 撤销方案](2026-11-09-m0-registry-revocation-options.md) |

## 代码与文档复核

- `m0_contracts.py` 的 `rest` 分支要求受控环境，校验 Gitea Actions 状态，复用原有授权用途。 `m0_rest.py` 用 Git 夹具摘要和三个 refs 约束导入，按独立角色比较 Issue / PR 集合、撤权和 Release。Issue 评论使用单次有界 GET，Issue / PR 集合仍逐页检查。契约入口与探针一致，工具索引补上了该模式。 [工具索引](../../scripts/README.md) · [本机 REST 入口](../../tests/contracts/m0/README.md#m0-s04-同源-rest-对照)
- `m0_github_scope.py` 固定 GitHub 私有测试目标，区分默认权限负例与三种只读模式。确认删除由操作者完成，`--check-revoked` 的结果依赖操作者输入同一值。工具索引和验证专题明确了这个独立入口及结果范围。 [GitHub 取证手册](../../tests/contracts/m0/compat/rest-runbook.md#github-单账号凭据对照) · [验证分层](../development/validation.md)
- 路线图与兼容样例原有“REST 待验证”措辞已更新，分别呈现 GitHub 所有者及匿名、只读 PAT、Gitea 普通角色和仍待验的 GitHub 普通角色。四份 YAML 的提交引用与样例表一致，工作流仍保存在契约目录。接续事项给出两项 OCI 取舍、分支验收和等待取舍期间可独立准备的 G24 / G25 对照。 [路线图](../planning/roadmap.md) · [兼容专题](../architecture/github-compatibility.md) · [接续事项](../planning/m0-validation.md#接续事项)

## 验证与交接

- 收尾复核当日提交标题、diff 空白、治理检查和 63 项本地测试，三份变更的 Python 文件通过语法编译。现有探针和 Git 夹具的四项 SHA-256 与各自最后实测记录一致。三个 GitHub PAT 脱敏结果的 SHA-256 与记录一致，文件权限为 0600，留在忽略目录。原始历史回执按实际批次保留。 [REST 探针摘要](2026-11-09-m0-gitea-rest-comparison.md#批次与复现) · [PAT 探针与结果摘要](2026-11-09-m0-github-owner-pat.md)
- 本机复核未见 `rf-m0-local-` 测试容器、卷或网络，`.local/m0` 已移除，回环 18443 / 19443 / 18543 无任务监听。GitHub 私有测试仓库和合成夹具保留供后续对照，测试 PAT 已撤销。收尾仅做本地复核和文档提交。 [GitHub 夹具留存](2026-11-09-m0-github-rest-reference.md#留存与补证)
- 下次从 M0-S04 接续，先确认 G26 的保留与回退要求、G27 的失效窗口，再执行相应候选的隔离验收。等待取舍期间可准备 G24 / G25。GitHub 普通角色验证依赖独立测试身份，Runner 和 Actions 保持暂停，阶段保持 M0。 [当前下一步](../status/current.md#下一步) · [接续事项](../planning/m0-validation.md#接续事项)
