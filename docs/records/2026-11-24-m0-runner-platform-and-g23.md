# 2026-11-24 M0 本机 Runner 平台核实与 G23 拒绝验证

## 本机 Runner 平台

核实范围为这台 Mac 和已配置的三个 Docker context。以下为启动 G23 环境前的只读结果。

| 读取项 | 实际结果 |
| --- | --- |
| `uname -m` | `arm64` |
| `docker context ls`、context endpoint 与 socket 解析 | 当前 context 为 `orbstack`。`default` 的 socket 解析到同一 OrbStack socket。`desktop-linux` 配置的本机 socket 不存在。三个 context 均指向本机 Unix socket。 |
| `docker --context orbstack info` 与 Compose 版本 | Linux aarch64，Engine 29.8.2、Compose 5.5.0。经 `default` 读取服务端版本同为 Linux arm64、Engine 29.8.2。 |

现有本机环境缺少首批工作流要求的原生 Linux amd64 执行目标和任务独享的 Docker daemon。另建 Compose 项目仍共享该 daemon 的管理权限。基础 Runner 挂起，本批无 Runner 下载、注册或工作流派发。正式仓库的 GitHub PR CI 属于治理验收。

恢复时先取得可用的原生 Linux amd64 执行位置及专属 daemon，确认归属、context、资源、执行窗口和清理责任。在该目标回读平台及固定镜像，按操作单核对仓库级注册、挂载与网络隔离、运行命令和本批授权，再由普通写者派发固定私有样例。操作单候选预算为 4 vCPU、6 GiB 内存、12 GiB 空闲磁盘、2 GiB 外部下载及 90 分钟。 [分步恢复条件](../planning/m0-s01-baseline.md#runner-resumption) · [基础操作单](../../tests/contracts/m0/compat/runner-runbook.md)

## G23 目标提交缺失

在 `dev` 的 `dc26ca2` 基线上使用工作树中的定向探针。批次 `rf-m0-local-4c9edf2e` 复用固定 arm64 缓存镜像，回读 Gitea 28.2.0、PostgreSQL 18.6，两套 Gitea 的 Actions 均关闭。沿用任务 CA、回环 HTTPS 和合成私有仓库。模式为 `release-missing-target`，实际执行源码摘要随请求记录归档。 [脱敏 JSON](2026-11-24-m0-release-missing-target-results.json)

普通协作者 Bob 的仓库角色回读为 `write`。同一 `release_write` 凭据按完整 SHA 成功读取已知提交 `5c4b4694872045019c5d0beb83483215d8485242`，随后创建指向 40 个 `f` 的合成草稿。草稿回读确认目标与作者，再调用既有发布前检，允许按目标 SHA 新建 Tag。

| 请求归属 | 对象 | 实际响应 |
| --- | --- | --- |
| 写者前检 GET | 原 Release ID `1` | 200，草稿 |
| 写者前检 GET | Tag `m0-g23-missing-target` | 404 |
| 写者前检 GET | 目标提交 `ffffffffffffffffffffffffffffffffffffffff` | 404，前检拒绝发布 |
| 普通仓库所有者 Alice 独立 GET | 原 Release ID `1` | 200，仍为草稿，目标、Tag 名、作者及其余受检字段与创建后相同 |
| 同一所有者 GET | 原 Tag | 404 |

探针退出 0，5 条通过记录、26 条脱敏 HTTP 请求。前检只有表中前三次 GET，整批发布 PATCH 为零。此批补齐目标提交 404 的受控拒绝证据。403、500、超时或提交回包不匹配仍由本地模拟覆盖。直接向原生端点发布无效 target 的历史 500 继续列为 G23 差异。 [既有正向与模拟证据](2026-11-17-m0-release-target-preflight.md) · [原生差异](2026-11-04-m0-release-validation.md#保留的五项差异)

脱敏 JSON 导出后与原始结果逐字节核对，SHA-256 为 `8736410e454399566dbf3da42524fb262d98b84a8554da678f1ae2324691202a`。清理后按本批项目标签独立回查，容器、卷、网络均为零，`.local/m0` 已移除，回环端口 18443、19443、18543 均可重新绑定。本批仅用前两个端口。19 项 Release 定向测试和 70 项全量本地测试通过。
