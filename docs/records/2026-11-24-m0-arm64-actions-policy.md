# 2026-11-24 M0 arm64 私有工作流权限、环境与并发

## 验收口径

在专用 UTM arm64 来宾上使用 Gitea 28.2.0、Runner 5.2.4 和合成私有仓库 `owner/private-source`。普通写者派发，独立读者回查 Issue、run、attempt、job 和日志。原始 `m0-policy.yml` 的 SHA-256 是 `1692c74b21e64759d6abb9b8baf1dd2a3e8455daee678910ebc5fb3d899d9570`。显式写入对照与原件共用提交和仓库。 [原始工作流](../../tests/contracts/m0/compat/m0-policy.yml) · [操作单](../../tests/contracts/m0/compat/runner-runbook.md#arm64-权限环境与并发)

## 受保护环境

GitHub 的原始预期要求在批准前阻止 job 执行，批准后才允许 job 访问环境级 canary。Gitea 的官方对照将 `jobs.<job_id>.environment` 列为忽略字段。28.2.0 对应源码 `829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1` 的 OpenAPI 有 342 个路径，其中无环境配置或待审批部署接口。OpenAPI 文件的 SHA-256 为 `c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`。 [GitHub 部署环境](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments) · [Gitea 官方对照](https://docs.gitea.com/usage/actions/comparison/) · [固定版 OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json)

在本批实例上，普通所有者读取私有仓库为 200，读取该仓库的环境列表和指定环境均为 404，仓库秘密为 0 条。判定该候选原生不支持样例要求的受保护环境。因无法建立审批规则和环境级秘密，环境分支派发 0 次，批准前后的运行对照留待具备保护条件的目标。 [脱敏 API 回读](2026-11-24-m0-arm64-actions-policy-results.json)

## job 权限

只读 job 的验收断言失败，显式授权写入的正向对照成功。已用独立读者复核实际对象、run / attempt / job 和日志。该权限边界阻塞首版承诺，根因待核实。维护者持有本地限权证据，摘要收录在脱敏结果中。恢复条件为确认有效权限配置，并在修正或受控替代方案下取得真实拒绝、零副作用和独立写入对照。 [安全报告方式](../../SECURITY.md) · [脱敏结果](2026-11-24-m0-arm64-actions-policy-results.json)

## 同组并发取消

两次 `workflow_dispatch` 均由普通写者在 `refs/heads/main` 派发，提交为 `3967a534f036cd9a1f9a5c1c63c867510f140696`。两次 HTTP 200 回执的 ID 分别为 3 和 4。下表为北京时间，run / attempt / job ID 仅属于本批实例。

| run / attempt / job | 独立读者观察 | 终态 |
| --- | --- | --- |
| 3 / 1 / 9 | 21:09:33.025 出现 `concurrency-start`。21:09:36.576 再次读到 run 和 job 均在执行。第二次派发始于 21:09:36.614。旧 job 于 21:09:44 结束，日志只有开始标记。 | run、attempt、job 均为 `cancelled` |
| 4 / 1 / 12 | 21:09:46.867 出现 `concurrency-start`，21:10:46.873 出现 `concurrency-finish`。 | run、attempt、job 均为 `success` |

手动取消请求为 0。普通读者两次读取两份日志的摘要一致，仓库外账号读两个 run、attempt 和日志均为 404。原件同组替换已得到实测，Runner 容量为 1，多执行槽互斥及双端等价继续待验。 [日志摘要与时序](2026-11-24-m0-arm64-actions-policy-results.json)

## 环境、清理与交接

本地基线 `6b15b67`，合成仓库源码 SHA 单列于上表。UTM VM `RadishForge-M0-policy-Chx7O3` 使用 aarch64 硬件虚拟化和 UEFI，4 vCPU、6 GiB 内存、12 GiB 根虚盘，关闭共享目录。来宾使用 Debian arm64、PostgreSQL 18.6、Engine 26.1.5+dfsg1，Runner 绑定单个私有仓库，对照仓库的 Runner 数为 0。job 使用 internal 网络，Runner 配置禁用 job Docker socket 与 privileged。Debian 镜像和来宾清理前接收字节合计约 1.27 GiB。

删除仓库变量及注销 Runner 均返回 204，原对象读回 404，变量、仓库秘密、Runner 和来宾运行容器均为 0。按 UUID 删除本批 VM 后，UTM 清单恢复到原有五台停止的 VM。临时虚盘、seed、密钥已删除，宿主 `127.0.0.1:28422` 可重新绑定。

M0 保持进行中。先收口 job 权限边界，确认环境审批采用可强制执行的方案或由所有者明确调整承诺。受控 fork PR 的权限对照、原生 amd64 和 GitHub 参考端运行各自保留。 [四份原始样例](../architecture/github-compatibility.md#m0-s04-四份原始样例的证据范围) · [阶段出口](../planning/acceptance.md#m0-exit)
