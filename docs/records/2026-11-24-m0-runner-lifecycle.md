# 2026-11-24 M0 arm64 Runner 触发与生命周期

本批从本地 `2151b93` 新建独立 UTM VM。合成私有仓库为 `owner/private-source`，写者有仓库 write 权限，读者有 read 权限。两次 Git push、三次手动派发产生五个 run，同一 run 重跑后共有六个 job。下表的 run、attempt 和 job ID 属于本批 Gitea 实例。上一批实例的 run 1 单独存档。 [脱敏 API、日志摘要与时序](2026-11-24-m0-runner-lifecycle-results.json) · [首条私有工具链工作流](2026-11-24-m0-runner-arm64.md) · [生命周期夹具](../../tests/contracts/m0/compat/m0-runner-lifecycle.yml)

| 场景 | 真实 ref 与提交 SHA | run / attempt / job | 上游读回 |
| --- | --- | --- | --- |
| 新分支 push | `refs/heads/m0-base-push` · `d84c7c229313353fe509a7cd5dcad264ade8e5da` | 1 / 1 / 1 | `success`，运行中使用的完整 ref 与 SHA 均见读者日志 |
| 轻量 Tag push | `refs/tags/m0-base-tag` · `513eebb9e903434455141b2680c1c9fddc5520cb` | 2 / 1 / 2 | `success`，Tag 指向 commit。run 省略 `head_branch`，`path` 保留完整 Tag ref |
| 主动失败 | `refs/heads/main` · `5e5509cf2d2a249e51184fdca1cd0776a5c1f7c7` | 3 / 1 / 3 | 日志先输出 marker，再报告退出码 17。run、attempt 和 job 均为 `failure` |
| 普通写者取消 | 同一 `main` SHA | 4 / 1 / 4 | 运行中读到 marker 后提交一次取消，HTTP 200，run、attempt 和 job 均为 `cancelled` |
| 同一 run 重跑 | 同一 `main` SHA | 4 / 2 / 5 | 普通写者请求一次，HTTP 201；第二个 job 执行完 150 秒等待，三个终态均为 `success` |
| Runner 执行中失联 | 同一 `main` SHA | 5 / 1 / 6 | Runner 离线后上游转为 `failure`，job 容器先行结束。时序见下文 |

读者按 Git refs 接口精确匹配分支或 Tag，再按完整 SHA 读取两份工作流。生命周期 YAML 的 SHA-256 为 `0890edfacb32a7580337f07a995fdbeb53e8e0351d0dbbfb4aa9387b74ac6c96`，工具链 YAML 仍为 `b23089bdfcd477055e324a323c4996bed422af0ae7b57e835a8b949ae4768894`。两个 push 使用不同提交，均按推送前的 run 集合、事件、工作流、SHA 和含完整 ref 的日志关联。手动派发保留写者回执 ID。沿用仓库路径和嵌套仓库 ID 核验归属，顶层 `repository_id=0` 在本批再次出现。

重跑前先保存 job 4 的取消状态和日志。第二次 attempt 成功后再次读取第一次 attempt 的 job，仍为 `cancelled`，3,912 字节日志的 SHA-256 两次均为 `1a5fa46f5adfe169a70f4fe62e653d9fedfc08591fa960bb5ecdeeb1b76f24c7`。第二次 attempt 的 job 5 有独立的 marker 时间和日志摘要。

## Runner 失联

以下时刻均为北京时间。20:28:23，读者日志出现 `m0-base-lost`、完整 `main` ref 与 SHA。20:28:28，再读 run 5 / attempt 1 / job 6 均为 `in_progress`，仓库级 Runner 1 为 `online`、`busy=true`。按实际 job 容器 ID 核对镜像、网络、挂载和 socket 后，再次确认 job 正在运行。20:28:29 仅向本批 Runner 容器发送一次 KILL，容器退出码为 137。

- 20:28:34，Gitea 仍返回 `online`、`busy=false`，job 容器里还在运行本次 shell 和等待进程。
- 20:29:35，首次采到 Runner 为 `offline`，run、attempt 和 job 均为 `in_progress`。
- 20:31:06，job 容器仍在运行，进程清单只余 `sleep`。Gitea 没有收到该步的成功回报。运行期间的 `completed_at` 为 Unix 纪元，job 接口省略 `updated_at`。取证分别保存服务端可用时刻和读者采样时刻。
- 20:36:23，Docker 对同一 job 容器记录 `die`（退出码 0）和 `destroy`。20:36:24 首次采到容器已移除，Gitea 仍返回 `in_progress`。此时尚无工作流终态。
- 20:39:43，Gitea 记录 run / attempt / job 终态为 `failure`，距 Runner 退出 11 分 14 秒。20:39:55 读者采到该结果，Runner 仍离线，原 job 的日志可读。介入后共采集 46 次状态，未对失联运行发送取消或重跑。

来宾配置显式采用固定版本示例值，`ZOMBIE_TASK_TIMEOUT=10m`，`cron.stop_zombie_tasks` 启用且每 5 分钟扫描一次。失联期间 Gitea、数据库保持运行，观察期按同一 run / attempt / job 读回。 [固定版本配置](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/custom/conf/app.example.ini) · [上游超时处理](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/actions/clear_tasks.go)

## 环境、复核与清理

- 新 VM 为 `RadishForge-M0-arm64-WUkALi`，UUID `E8B0203E-C280-44D0-8CE0-7E74EE6E5523`。UTM 回读 aarch64、硬件虚拟化、UEFI、4 vCPU、6 GiB、两个 VirtIO 盘、共享关闭，来宾根盘 12 GiB。Debian 和四个 arm64 镜像按[操作单](../../tests/contracts/m0/compat/runner-runbook.md)核验。本批 Gitea 28.2.0、PostgreSQL 18.6、Runner 5.2.4，来宾 Engine 26.1.5+dfsg1。下载的 Debian 镜像为 431,816,704 字节，清理前来宾网卡累计接收 929,313,957 字节，两项合计约 1.27 GiB。
- 仓库级 Runner 容量 1，对照仓库可用 Runner 为 0。job 网络为 internal，仅连 VM 内服务。取消及失联前均在真实 job 容器内核对 aarch64 和 Docker socket 缺失，容器非 privileged。唯一 bind mount 为只读 CA，另外两个可写卷由 job 使用。
- 普通读者在结束前按每个 attempt 和 job 再取日志，六份均为 HTTP 200，摘要与各自取证时一致。仓库外账号按相同路径查询 run、attempt、日志均为 404。导出 JSON 的 SHA-256 为 `ec340e2e413f231d8de5f1078cfa2431508b54f3a3c05b9601a63f5184bb2e2e`。
- 专用 Runner 注销返回 204，列表 0 条、原 ID 详情 404。来宾运行容器为 0。按 UUID 和名称核对停机后移除本批 VM、临时磁盘、seed 和任务密钥。UTM 清单回到原有五台停止 VM，宿主回环端口 `28422` 已通过绑定复查。
- 下一批在专用 arm64 构建环境中验证单镜像 Digest 与 Release 的来源关联。原生 amd64 工作流及 GitHub 双端兼容分别待验，M0 继续进行。
