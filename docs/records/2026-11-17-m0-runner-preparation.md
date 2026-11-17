# 2026-11-17 M0 基础 Runner 准备

按 Asia/Shanghai 记录。所有者同意推进首轮基础 Runner 准备，以[操作单](../../tests/contracts/m0/compat/runner-runbook.md)记录 M0-01、M0-03、M0-04 的执行输入、证据及停止条件。

- 只读执行 `uname -srm`、`docker context ls`、`docker --context orbstack info` 和 `docker --context orbstack compose version --short`。本机 Darwin / arm64，当前 `orbstack` daemon 为 Linux aarch64、Engine 29.8.2、Compose 5.5.0。仓库无已确认的 amd64 宿主记录。其他 context 保持未连接，待所有者提供可用宿主及归属。
- 读取 Gitea 28.2.0 提交的公开 OpenAPI、Actions 配置及 Runner 5.2.4 固定示例。已确认原生派发的 `return_run_details` 位于 query，以及 run、attempt、job 和日志的公开回读入口。证书、配置、响应语义和权限留待真实链路读回。 [固定 OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json) · [固定 Runner 配置](https://gitea.com/gitea/runner/src/commit/ffd80101a317d6c3ef922dfb4856b629b3d60064/internal/pkg/config/config.example.yaml)
- 读取 Gitea 官方 job 镜像的公开 Registry 元数据。首个 Registry 地址返回 403，改用官方说明列出的 Docker Hub 镜像地址。校验 OCI index 和子 manifest 响应摘要、amd64 配置摘要与平台。读取的内容为 index、manifest 和配置元数据，无镜像层。
- 修订内容是文档。Runner / Actions 仍暂停，暂无新工作流结果或阶段验收，不涉及服务启停、容器拉取、设置变更、正式仓库写入、Git 暂存 / 提交 / 推送。

本地验证通过。治理检查覆盖 123 个文本文件及 722 个本地文件链接，工作树与暂存区空白检查通过。复核原工具链样例 SHA-256、补充夹具 YAML 解析、`bash -n` 及 8 项纯本地脚本分支，等待分支用本地替身校验时长参数。Gitea 调度和状态转换留待目标机取证。

## 待所有者确认的产品承诺

| 取舍 | 要确认的输入 | 决定后的定向验收 |
| --- | --- | --- |
| G26 · 镜像保留 | 建议先评估私有发布命名空间内的受控保留。确定保留对象、回退窗口、例外删除角色和删后恢复目标。如果要求保留期内拒绝常规写者覆盖或删除，明确强制保护范围。 | 以独立读取凭据按原 Digest 验证 Manifest 与 Blob。分别验收有效发布引用、清理、覆盖、删除和恢复。若要求强制保留，确认范围内的破坏操作均被拒绝。 |
| G27 · 单凭据撤销 | 确认产品侧停用是否足够，或须承诺远端在明确上限内拒绝旧凭据。若要求远端上限，明确起算事件、最长允许时长、是否允许等待已签 Bearer 自然到期。 | 产品侧停用路线保留已复制 Bearer 仍能访问、换发的残余风险；远端有界路线测量停止签发有效后继与旧凭据读写失效的实际时点，并验证独立凭据继续可用。 |

两项取舍各自确认。已删除 PAT 的旧 Bearer 可换发有效后继，目前原生路径无可承诺的远端上限。首版关于 G26 / G27 的正式承诺及下一批验收沿用 [ADR 0006](../adr/0006-oci-authorization-and-digest-retention.md)。
