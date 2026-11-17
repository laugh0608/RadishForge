# M0 基础 Runner 操作单

2026-11-17 静态准备。对应 M0-01、M0-03、M0-04，目标为 BASE-01 的 Actions 证据及 COMP-01 的固定样例行为记录。实际宿主待确认，Runner / Actions 暂停。启动前按[恢复条件](../../../../docs/planning/m0-s01-baseline.md#runner-resumption)回填实际环境和命令，取得本批运行授权。

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
| 2 · push 与 Tag | 导入下方补充夹具后，普通写者分别推送一个新分支 `m0-base-push` 和一个轻量 Tag `m0-base-tag`。按事件分别单次推送、独立回读实际远端 ref。 | 两次 push 事件各有唯一 run；分支和 Tag 的具体 ref、SHA、run、attempt 与日志逐一对应。记录 Gitea 原始字段，保存两类 ref 的区分证据。 |
| 3 · 失败 | 手动派发补充夹具，`mode=fail`、`marker=m0-base-fail`。 | 日志先有标记，再有主动非零退出；检查 job 与 run 的实际终态。 |
| 4 · 取消与重跑 | 派发 `mode=hold`、`marker=m0-base-cancel`。同一 run 的 job 正在运行且日志有标记时，发送一次 `POST /runs/{run}/cancel`。读到取消终态后，对同一 run 调用一次 `POST /runs/{run}/rerun`。 | 分别记录取消回执与真实终态。重跑保留原 run ID、ref、SHA，出现可定位的新 attempt，检查新 job 日志与成功终态，并保留原 attempt 的取消证据。 |
| 5 · 执行中失联 | 另派发 `mode=hold`、`marker=m0-base-lost`。日志出现标记后，仅终止本批 Runner 容器，保持 Gitea 在线。 | 记录进程终止、Runner 在线状态、同一 run 与 job 最后更新时间及实际终态。由目标配置回读的 zombie timeout 加上调度观测窗口决定何时结束，最多 15 分钟；仍无可信终态时登记失联 / 结果未知。 |

回读使用 `GET /runs/{run}`、`GET /runs/{run}/attempts/{attempt}` 和 `GET /runs/{run}/attempts/{attempt}/jobs`。以返回的 job ID 通过 `GET /jobs/{job_id}/logs` 轮询标记，取消和失联只在同一 job 仍运行时触发。若在等待窗口内未观察到标记，记录该用例未达触发条件。`GET /runs/{run}/logs` 打包当前最新 attempt 的日志，重跑前先保存原 attempt 的日志与摘要。派发收到 204、网络超时或回执与实际不符时，按工作流、事件、ref、SHA、时间窗与 marker 对账。零匹配、多匹配、日志不可得且关联尚未成立时记录未知，零自动重试。取消和重跑超时时只查既有 run / attempt，观察期内保留原有结果。 [固定版日志实现](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/common/actions.go)

### 补充工作流夹具

另存为隔离仓库的 `.github/workflows/m0-runner-lifecycle.yml`。记录导入后的 YAML 摘要、工作流路径和实际 Git 提交，回读 `m0-toolchain.yml` 的原始摘要。本夹具只定义触发和状态取证。

```yaml
name: M0 base runner lifecycle
'on':
  push:
    branches: [m0-base-push]
    tags: [m0-base-tag]
  workflow_dispatch:
    inputs:
      marker:
        type: string
        required: true
      mode:
        type: string
        required: true
permissions:
  contents: read
jobs:
  observe:
    runs-on: ubuntu-24.04
    steps:
      - name: Report ref and exercise result
        shell: bash
        env:
          EVENT: ${{ github.event_name }}
          SOURCE_REF: ${{ github.ref }}
          SOURCE_SHA: ${{ github.sha }}
          MARKER: ${{ inputs.marker }}
          MODE: ${{ inputs.mode }}
        run: |
          case "$EVENT" in
            push)
              case "$SOURCE_REF" in
                refs/heads/m0-base-push|refs/tags/m0-base-tag) ;;
                *) exit 2 ;;
              esac
              MARKER="m0-base-push-event"
              MODE=pass
              ;;
            workflow_dispatch)
              [[ "$MARKER" =~ ^m0-base-[a-z0-9-]+$ ]] || exit 2
              ;;
            *) exit 2 ;;
          esac
          [[ "$SOURCE_SHA" =~ ^[a-f0-9]{40}$ ]] || exit 2
          printf 'fixture=%s ref=%s source_sha=%s mode=%s\n' "$MARKER" "$SOURCE_REF" "$SOURCE_SHA" "$MODE"
          case "$MODE" in
            pass) ;;
            fail) exit 17 ;;
            hold) sleep 150 ;;
            *) exit 2 ;;
          esac
```

## 证据和清理

保存实际平台 / 镜像 / 版本、配置和夹具摘要、角色与 run / attempt / job ID、时点、脱敏回执与日志字节摘要。对键不存在、响应与副作用不一致、身份越权及停止后仍有 job 资源分别登记失败或未知。正向原样与补充夹具分别记录，镜像、Release 和 GitHub 双端结果待各自批次取证。

先停止新触发并导出证据；回查已派发 run 和任务 job，停止有明确归属的本批进程。Gitea 在线时按仓库和 Runner ID 注销并读回，移除注册输入及会话凭据。再移除明确归属的容器、任务网络、卷及私密文件，回读本批资源归零，核对宿主监听与本批预先登记的镜像 / 缓存去向。若动作超时或资源归属无法确认，保留 ID、结果与交接，不全局清理或盲重试。候选或目标发生变化时，先核对受影响的输入和边界，再决定重测。
