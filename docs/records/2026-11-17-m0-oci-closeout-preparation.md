# 2026-11-17 M0 OCI 首版决策与验证准备

所有者分别确认 G26 的 30 天受控保留与 G27 的产品侧停用 / 原 PAT 交换拒绝。决定归 [ADR 0006](../adr/0006-oci-authorization-and-digest-retention.md#first-release-oci-decisions)。G26 采用成功切换时点作为上一可回退版本窗口起点的验证口径，避免用镜像创建时间缩短实际回退窗口。

- 已整理 [G24—G26 操作单](../../tests/contracts/m0/compat/oci-retention-runbook.md)。两个可写构建组织与一个隔离发布组织对照同一写 Bearer，独立读 PAT 验证 scope 与对象权限。发布短测覆盖保留引用、实际清理、例外删除和原字节恢复。G27 复用已取得的原 PAT 拒绝及旧 Bearer 换发证据。
- 只读确认 `orbstack` 为 Linux aarch64 / Engine 29.8.2，Compose 5.5.0；`.local/m0/owner.json` 不存在，未发现固定 Gitea / PostgreSQL 镜像在本地可用。核对固定 arm64 manifest 的响应摘要并计算压缩层，两个镜像合计 220,447,464 字节，约 210 MiB。只获取公开元数据，镜像层等待本批拉取授权。 [镜像来源与 Digest](2026-11-01-m0-s01-sources.json)
- 固定源码核对包清理的版本创建时间、保留模式和实际运行入口。测试用年龄过滤 0，区分应保留 A / B 与应清理 C 的引用。窗口的 30 天口径、环境引用和自动释放保护归产品验收。 [固定清理实现](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/packages/cleanup/cleanup.go) · [Cron 执行入口](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/v1/admin/cron.go)

本地治理检查覆盖 125 个文本文件和 739 个本地文件链接，Git 空白检查通过。核对多环境留存期限样例、合计镜像压缩层大小、固定清理入口及 G24—G27 原有编号。

本次仅同步承诺、验证准备和只读预检。Runner / Actions 暂停，M0 尚未通过。此次没有镜像下载、运行服务或 Git 暂存 / 提交 / 推送。
