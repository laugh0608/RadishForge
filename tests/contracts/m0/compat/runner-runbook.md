# M0 基础 Runner 操作单

对应 M0-01、M0-03、M0-04。2026-11-24 所有者选定本机 UTM 专用 arm64 VM，授权执行第一条合成私有工作流。原生 amd64 的 COMP-01 对照单独保留。后续 arm64 生命周期批沿用同一组固定输入。原生 amd64 对照按下方候选表另行验收。

## arm64 首条私有工作流

UTM 4.7.5 使用 aarch64、硬件虚拟化和 UEFI，从官方 Debian 13 generic arm64 批次 `20261123-2671` 新建临时 VM。下载约 412 MiB 的 qcow2 后，按 SHA-512 `bf83391b5a7b0c6bb33312befe7b092286b719544dd25d62f4acda627841ad192ab252c32d4e756419c276f8ec6e72dae53c917234475bcc687fc7d6fa919e99` 校验，再扩展来宾磁盘。客体内安装 Debian trixie 的 docker.io 和 docker-cli，记录实际版本。 [Debian 官方校验单](https://cloud.debian.org/images/cloud/trixie/20261123-2671/SHA512SUMS)

| 来宾内使用的仓库 | linux/arm64 子 manifest |
| --- | --- |
| `docker.io/gitea/gitea`（28.2.0-rootless） | `sha256:c372a4b5059cae65d148e150eb633327bf0ce19450cead8ff8d7a21ca8b7db2e` |
| `docker.io/library/postgres`（18.6-bookworm） | `sha256:a1ece8fa15f7b526a51ef47a22fb1f373d33de794dc26bf7bff99e61dcb52690` |
| `docker.io/gitea/runner`（5.2.4） | `sha256:039b467de76f4d344f6de21e42e00271a776559d304dd30caaf49ffed3ffb351` |
| `docker.io/gitea/runner-images`（ubuntu-24.04） | `sha256:a07569aee5d38d11492671e25ed64533a1f865c43454e9e4683e72d1a4592915` |

四个子 manifest 均按响应字节复算摘要，压缩层共 801,670,489 字节。按摘要拉取，读回容器平台及实际 job 镜像。沿用原始 `m0-toolchain.yml`、Action 提交及三个工具版本断言。

- **资源上限**　4 vCPU、6 GiB 内存、12 GiB 来宾虚盘、2 GiB 外部下载、90 分钟窗口（预留 15 分钟清理）。容量 1，单 job 上限 8 分钟。所有 Docker 数据仅在新 VM 内。宿主临时镜像、seed 和任务密钥放在本批独立私密目录。
- **隔离**　仅启用 ARM 硬件虚拟化。关闭宿主目录共享，管理 SSH 仅转发至 `127.0.0.1:28422`。Gitea HTTPS 仅在 VM 内使用，数据库使用独立网络。Runner 独占来宾 daemon，平台和 job 不挂 socket。只执行操作单中的首个手动派发样例。
- **验收**　普通写者仅派发一次。回读私有仓库和 ref、run ID、attempt、job 与终态，按 job ID 下载日志，核对 marker、检出的 SHA、版本断言，保留普通读者与无权限账号的独立回读。只将实际观察到的 arm64 结果登记到 BASE-01。
- **停止与清理**　记录新 VM UUID、批次路径和监听。成功或中断均先导出脱敏证据，对已派发请求按只读接口对账。若已注册则注销本批 Runner，再停止任务服务、关闭 VM。仅在 UUID 和名称匹配后移除该 UTM VM、其磁盘及本批临时文件，复查 UTM 清单和宿主端口。其他 VM 保持原状态。

### 已实测的配置和回读顺序

1. 将校验过的 qcow2 用 `qemu-img resize -f qcow2 <本批磁盘> 12G` 扩容。为新实例制作带 `CIDATA` 卷标的 NoCloud seed，包含专用公钥、主机身份、独立 instance ID 和按实际网卡 MAC 匹配的 DHCP 配置。将 seed 用 `qemu-img convert -f raw -O qcow2 <seed.iso> <seed.qcow2>` 转为独立数据盘。UTM 使用两个 VirtIO 盘，回读 boot 盘 ID、aarch64、hypervisor、内存、核心数、共享模式及回环转发后执行 `utmctl start <新 UUID>`。校验 SSH 主机密钥，读取 `uname -m`、`cloud-init status` 及根盘容量。本批首次使用可移动 seed 时 SSH 握手超时，以上 VirtIO 配置已实测成功。
2. 来宾通过 Debian 签名源安装 Docker，记录 Engine 及 API 版本。逐一 `docker pull --platform linux/arm64 <仓库>@<上表摘要>` 并 inspect。为 Gitea / job 与数据库建两个 internal 网络，仅 Gitea 同时接入两网。为 `forge.m0.test` 签发任务证书，runner 和 job 均使用包含公共根和任务 CA 的只读证书文件。job 外部 HTTPS 经来宾内按域名限制的代理访问 GitHub、Go 和 Node 下载源及必要跳转。
3. 以普通所有者建立两个私有仓库并启用 Actions，只向目标仓库授予普通写者与读者权限。写者按 Contents API 提交原始 YAML，读者按 `main` 回读 SHA，再按该 SHA 取回 YAML 校验摘要。以目标仓库注册 Token 文件执行 `gitea-runner register --no-interactive --instance https://forge.m0.test:3000 --token-file <任务文件> --config <本批配置> --name <本批名称>`。标签映射为 `ubuntu-24.04:docker://docker.io/gitea/runner-images@<arm64 子 manifest>`。配置 `runner.patch_actions: false`、`cache.enabled: false`、`container.docker_host: "-"`、`container.privileged: false`，仅允许任务 CA 的只读 bind mount。删除注册输入，启动 daemon，按两仓库 Runner 列表核对范围。
4. 按下方第 1 个场景派发。以仓库专属路径、嵌套仓库 ID 和全名、完整 SHA、回执 ID、run / attempt 与日志输出核对归属。固定版顶层 `repository_id` 在本批返回 0，单独保存与真实 ID 的差异。运行中 `conclusion` 可缺失，等待实际终态。按 job ID 读取最终日志，核对 SHA / marker、版本输出和摘要，以仓库外身份独立回查同一路径。

2026-11-24 首批已完成手动派发，续批在新 VM 实测场景 2—5。两批均已清理。失联样例中 job 容器退出后 Gitea 仍显示运行中，须按同一 attempt 等待上游终态。 [生命周期实测](../../../../docs/records/2026-11-24-m0-runner-lifecycle.md) · [arm64 实测](../../../../docs/records/2026-11-24-m0-runner-arm64.md)

## 固定输入与待回填项

| 输入 | 本批候选与核对方式 |
| --- | --- |
| 执行位置 | 原生 Linux amd64、任务独享的 Docker daemon。回填宿主归属与可用窗口、context、Engine / Compose、CPU / 内存 / 空闲磁盘和退出方式。本机 `orbstack` 已只读核对为 Linux arm64、Engine 29.8.2、Compose 5.5.0。 |
| 底座 | Gitea 28.2.0-rootless、PostgreSQL 18.6-bookworm、Runner 5.2.4 基础镜像。复用[固定 index 与 amd64 子 manifest](../../../../docs/records/2026-11-01-m0-s01-sources.json)，由目标机读回实际平台和版本。 |
| job 镜像 | `docker.io/gitea/runner-images@sha256:2ab47e089354b21919f911cb1d5d633f9ff8e68cc270d5e2abc0c91af32f927a`，对应 `ubuntu-24.04` 的 Linux amd64 子 manifest。只映射 `ubuntu-24.04:docker://` 到该镜像，读回标签、实际容器镜像、Git 版本、Action 启动时可用的 Node 24 路径与版本。 |
| 正向样例 | 原样导入 [m0-toolchain.yml](m0-toolchain.yml) 到 `.github/workflows/m0-toolchain.yml`，SHA-256 为 `b23089bdfcd477055e324a323c4996bed422af0ae7b57e835a8b949ae4768894`。复用[固定 Action 提交](README.md#版本与准入)。工作流内断言 Go 1.27.3、Node 24.22.2、npm 11.19.1。 |
| 数据与权限 | 新建合成私有仓库，初始分支 `main`，Runner 绑定该仓库、单 job。管理员只准备账号、仓库设置与注册。普通写者推送、派发、取消与重跑，普通读取者回查运行和日志，仓库外用户作拒绝对照。登记实际仓库角色、凭据权限及 API 返回；Actions job 只请求 `contents: read`。基础批使用独立测试凭据，无 Registry 写入步骤或生产秘密。 |

job 镜像来源为 Gitea 官方镜像。Docker Hub 返回的 index 为 `sha256:139605d4a6ab61e48dfd7687b11184881c2d7fcf06bf739e9cadb34f73deb51d`，已校验 index / 子 manifest 响应字节、Registry 摘要及镜像配置摘要。配置声明版号 `v26.11.16`、源码修订 `e5e94cda9983fdef6ce541b216d36be73240d8ab` 和 MIT，镜像内组件另循各自许可。amd64 压缩层合计 582,964,476 字节，实际运行时与镜像拉取仍待目标机验证。 [发行说明](https://blog.gitea.com/runner-images-ubuntu-26.04/) · [镜像源码修订](https://gitea.com/gitea/runner-images/src/commit/e5e94cda9983fdef6ce541b216d36be73240d8ab)

## 隔离与操作前检查

1. 候选预算为 4 vCPU、6 GiB 内存、12 GiB 可用磁盘、2 GiB 外部下载、90 分钟总窗口，末段预留 15 分钟导出和清理。Runner 容量 1，单 job 上限建议 8 分钟，失联单批观察上限 15 分钟。根据目标机实际镜像、工具链和链路复核，超预算即停。拉取前明确下载坐标、目标 daemon 的数据目录、缓存归属及清理方式。
2. 用本批独立项目、网络、卷和私密目录启动资源 Gitea 与 PostgreSQL。Gitea 仅在本批启用 Actions，配置 `DEFAULT_ACTIONS_URL=github` 并回读仓库已启用 Actions；数据库网与 job 网隔离。将 `https://forge.m0.test:3000` 作为任务网内唯一 Gitea URL，使用同名 DNS alias、带该 SAN 的任务证书。预检 Git/API 客户端、Runner 与 job 均能解析该域名并验证证书。候选拓扑无对宿主发布端口。现有[本机契约 Compose](../compose.yaml)绑定 arm64 且配套脚本要求关闭 Actions，执行前另审阅本批配置 diff。
3. Runner 可以访问本批专用 daemon，平台与 job 均无 socket。按固定版本配置核对 `container.docker_host: "-"`、非 privileged、无 host network、无工作流可用宿主挂载和共享缓存。任务 CA 以只读方式注入 Runner 和 job，由 Git / Node / Runner 在任务进程内使用。保留公共 HTTPS 校验，仅允许任务所需的 Registry、固定 Action 与工具链来源及必要下载跳转。配置、DNS、证书或隔离检查失败时，停止派发。
4. 固定目标后将完整命令、配置和资源归属加入本批运行授权的范围。拉取固定镜像前读回 daemon 架构与标识，比对任务资源清单；新卷初始化后回读 Gitea 版本、URL、TLS、Actions 设置。使用仓库级注册凭据注册一个可跨多个 job 使用的 Runner，凭据经任务专用文件输入，注册成功后移除输入，Runner 状态另存私密卷。按 Runner ID 回查范围、标签和在线状态，读回其他仓库未获得该 Runner，再允许派发。 [固定 Runner 配置](https://gitea.com/gitea/runner/src/commit/ffd80101a317d6c3ef922dfb4856b629b3d60064/internal/pkg/config/config.example.yaml) · [Gitea 固定配置示例](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/custom/conf/app.example.ini) · [Runner 注册](https://docs.gitea.com/runner/registration/)

## 执行顺序和验收

以下 API 路径以本批 `/api/v1/repos/{owner}/{repo}/actions` 为前缀。先记录工作流 ID、待触发的实际 Git ref / SHA、触发时间和触发前的相关 run 集合。每个场景使用独立 ref 或 marker，写请求各发一次。 [Gitea 28.2.0 OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json)

| 顺序 | 操作 | 通过条件与要留的证据 |
| --- | --- | --- |
| 1 · 私有检出与工具链 | 普通写者调用 `POST /workflows/{workflow_id}/dispatches?return_run_details=true`，`ref=main`，`inputs.marker=m0-toolchain-01`。 | 只有一条可归因的 run。按 ID 查 run、attempt 和 jobs，核对 event、ref、完整 SHA、实际 job、Runner 及终态；下载日志核对 marker、检出的 HEAD 和版本断言。留独立读取者的正向结果及仓库外用户的拒绝。 |
| 2 · push 与 Tag | 导入[生命周期夹具](m0-runner-lifecycle.yml)后，普通写者分别推送一个新分支 `m0-base-push` 和一个轻量 Tag `m0-base-tag`。按事件分别单次推送，以普通读者从 `GET /repos/{owner}/{repo}/git/refs/{ref}` 返回的列表精确匹配完整 ref 和提交 SHA。 | 两次 push 事件各有唯一 run；分支和 Tag 的具体 ref、SHA、run、attempt 与日志逐一对应。记录 Gitea 原始字段，保存两类 ref 的区分证据。 |
| 3 · 失败 | 手动派发补充夹具，`mode=fail`、`marker=m0-base-fail`。 | 日志先有标记，再有主动非零退出；检查 job 与 run 的实际终态。 |
| 4 · 取消与重跑 | 派发 `mode=hold`、`marker=m0-base-cancel`。同一 run 的 job 正在运行且日志有标记时，发送一次 `POST /runs/{run}/cancel`。读到取消终态后，对同一 run 调用一次 `POST /runs/{run}/rerun`。 | 分别记录取消回执与真实终态。重跑保留原 run ID、ref、SHA，出现可定位的新 attempt，检查新 job 日志与成功终态，并保留原 attempt 的取消证据。 |
| 5 · 执行中失联 | 另派发 `mode=hold`、`marker=m0-base-lost`。日志出现标记后，仅终止本批 Runner 容器，保持 Gitea 在线。 | 记录进程终止、Runner 在线状态、同一 run 与 job 最后更新时间及实际终态。由目标配置回读的 zombie timeout 加上调度观测窗口决定何时结束，最多 15 分钟。仍无可信终态时登记失联 / 结果未知。按介入前保存的 job 容器 ID 独立检查残留进程，记录后再清理。 |

回读使用 `GET /runs/{run}`、`GET /runs/{run}/attempts/{attempt}` 和 `GET /runs/{run}/attempts/{attempt}/jobs`。以返回的 job ID 通过 `GET /jobs/{job_id}/logs` 轮询标记，取消和失联只在同一 job 仍运行时触发。若在等待窗口内未观察到标记，记录该用例未达触发条件。`GET /runs/{run}/logs` 打包当前最新 attempt 的日志，重跑前先保存原 attempt 的日志与摘要。派发收到 204、网络超时或回执与实际不符时，按工作流、事件、ref、SHA、时间窗与 marker 对账。零匹配、多匹配、日志不可得且关联尚未成立时记录未知，零自动重试。取消和重跑超时时只查既有 run / attempt，观察期内保留原有结果。 [固定版日志实现](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/common/actions.go)

### 补充工作流夹具

将[生命周期夹具](m0-runner-lifecycle.yml)原样导入隔离仓库的 `.github/workflows/m0-runner-lifecycle.yml`，独立读者按提交 SHA 核对该文件与原工具链工作流的摘要。arm64 续批按场景 2—5 逐一执行，沿用首批镜像、配额与清理步骤。夹具仅使用 shell，各 job 只连接 VM 内的 Gitea。

## 证据和清理

保存实际平台 / 镜像 / 版本、配置和夹具摘要、角色与 run / attempt / job ID、时点、脱敏回执与日志字节摘要。对键不存在、响应与副作用不一致、身份越权及停止后仍有 job 资源分别登记失败或未知。正向原样与补充夹具分别记录，镜像、Release 和 GitHub 双端结果待各自批次取证。

先停止新触发并导出证据；回查已派发 run 和任务 job，停止有明确归属的本批进程。Gitea 在线时按仓库和 Runner ID 注销并读回，移除注册输入及会话凭据。再移除明确归属的容器、任务网络、卷及私密文件，回读本批资源归零，核对宿主监听与本批预先登记的镜像 / 缓存去向。若动作超时或资源归属无法确认，保留 ID、结果与交接，不全局清理或盲重试。候选或目标发生变化时，先核对受影响的输入和边界，再决定重测。
