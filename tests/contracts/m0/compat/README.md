# M0-S04 首批 GitHub 对照样例

2026-11-09 固定首批输入，REST、客户端和工作流均为待验证。样例保存在契约目录。未来取证时只把原始 YAML 装入获授权的隔离仓库，保留原文件摘要、实际安装路径及任何改动 diff。来源与阶段归属见 [GitHub 兼容策略](../../../../docs/architecture/github-compatibility.md)。

## 版本与准入

GitHub REST 主样例显式使用 `X-GitHub-Api-Version: 2026-03-10`。官方在核查日仍列出 `2022-11-28`，支持到 2028-03-10。旧版按独立 profile 重做取证。客户端选用本机已存在的 GitHub CLI `v2.96.0`，Tag 指向 `b300f2ec7ec9dc9addc39b2ad88c54097ded7ca0`。只核对了本机版本和命令帮助。 [GitHub REST 版本](https://docs.github.com/en/rest/about-the-rest-api/api-versions#supported-api-versions) · [CLI 固定发行](https://github.com/cli/cli/releases/tag/v2.96.0) · [gh api 手册](https://cli.github.com/manual/gh_api)

| Action | 发行版 / 完整源码提交 | 官方来源 |
| --- | --- | --- |
| `actions/checkout` | `v7.0.1` / `3d3c42e5aac5ba805825da76410c181273ba90b1` | [发行](https://github.com/actions/checkout/releases/tag/v7.0.1) · [固定元数据](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/action.yml) |
| `actions/setup-go` | `v7.0.0` / `b7ad1dad31e06c5925ef5d2fc7ad053ef454303e` | [发行](https://github.com/actions/setup-go/releases/tag/v7.0.0) · [固定元数据](https://github.com/actions/setup-go/blob/b7ad1dad31e06c5925ef5d2fc7ad053ef454303e/action.yml) |
| `actions/setup-node` | `v7.1.0` / `949feb2413d6458794dcd2491c4babbbce0c15c1` | [发行](https://github.com/actions/setup-node/releases/tag/v7.1.0) · [固定元数据](https://github.com/actions/setup-node/blob/949feb2413d6458794dcd2491c4babbbce0c15c1/action.yml) |
| `docker/login-action` | `v4.8.0` / `8aa5831fb8d48d8f76594c7ddde61ae58019f550` | [发行](https://github.com/docker/login-action/releases/tag/v4.8.0) · [固定元数据](https://github.com/docker/login-action/blob/8aa5831fb8d48d8f76594c7ddde61ae58019f550/action.yml) |
| `docker/setup-buildx-action` | `v4.4.1` / `f87e5991a6d7451dcb8d9637bfbc97413f497069` | [发行](https://github.com/docker/setup-buildx-action/releases/tag/v4.4.1) · [固定元数据](https://github.com/docker/setup-buildx-action/blob/f87e5991a6d7451dcb8d9637bfbc97413f497069/action.yml) |
| `docker/build-push-action` | `v7.4.0` / `c3c9e263c25d99ce0380d002d59b67737d91b0dc` | [发行](https://github.com/docker/build-push-action/releases/tag/v7.4.0) · [固定元数据](https://github.com/docker/build-push-action/blob/c3c9e263c25d99ce0380d002d59b67737d91b0dc/action.yml) |

以上六个 Action 的固定元数据均声明 `node24`。目标平台为 Linux amd64，GitHub 参考标签为 `ubuntu-24.04`。Gitea 对照沿用 28.2.0-rootless / Runner 5.2.4 候选。启动前固定并记录 Gitea job 镜像与 BuildKit 的 amd64 Digest、Docker Engine、实际 Git 和 Action 所用 Node 24 运行时，GitHub 侧记录实际托管镜像和运行时。工作流安装的 Go `1.27.3`、Node `24.22.2` 和随附 npm `11.19.1` 用于应用工具链对照。Buildx 固定 `v0.38.2`。 [候选组合与隔离约束](../../../../docs/planning/m0-s01-baseline.md) · [Buildx 固定发行](https://github.com/docker/buildx/releases/tag/v0.38.2)

## 工作流样例

两端分别准备合成私有仓库，导入相同源码提交，默认分支 `main`。先以 `.github/workflows` 的原始布局验证发现与触发。验证 Gitea 的另一发现目录或文件优先级时，使用独立夹具，记录真实触发数量和 diff。分支、Tag、制品和凭据均限定在各自隔离环境。

| 文件 | 输入与预期 |
| --- | --- |
| [m0-toolchain.yml](m0-toolchain.yml) | 手动派发 `ref=main`、`marker=m0-toolchain-01`。回执对应恰好一次运行。记录 ref、提交、run ID 和 attempt，验证私有 checkout、实际 HEAD、三个工具版本及 marker。 |
| [m0-image.yml](m0-image.yml) | 推送一个指向固定提交的轻量 Tag `m0-oci-01`，仅触发一次构建。可信仓库变量提供 `M0_REGISTRY_HOST`、完整 `M0_IMAGE` 和 `M0_BUILDKIT_IMAGE=docker.io/moby/buildkit@sha256:<digest>`，专用 Secrets 提供 Registry 用户和写凭据。逐端核对输出 Digest、Registry 实收 Manifest 和镜像内的 `/source-sha`。拉取验证使用独立读凭据。 |
| [m0-policy.yml](m0-policy.yml) | 分别派发 `probe=permissions`、`environment`、`concurrency`。权限用例先验证读成功，再验证 job Token 写入拒绝并用独立身份回查无 Issue 新增。`M0_API_URL` 固定原生 API origin 和前缀。环境用例设置 `m0-protected` 人工审批与只属于环境的合成 `M0_ENV_CANARY`，确认审批前没有执行，批准后才能取得该值。并发用例在首个 job 输出 `concurrency-start` 后派发第二次，同组首个 job 应取消，第二个完成，并核对执行窗口。 |
| [m0-fork.yml](m0-fork.yml) | 分别用同仓库分支和受控外部 fork 提交只改合成数据的 PR。确认前者取得合成 `M0_FORK_CANARY`，后者运行时取不到。记录两端允许 fork 运行、审批和秘密转发的实际设置。 |

权限用例需要可用的写入正向对照，以排除接口缺失或错误仓库。环境用例需先确认参考环境支持所选保护规则。出现未调度、不可执行、事件缺少字段、对照失败时保留该条证据。静默忽略权限、环境或并发设置判失败。日志仅输出标记和结果，环境与 fork 用例只使用无实际权限的合成秘密。Checkout 的 submodule / LFS、缓存、通用 artifacts、复用工作流、生产晋级和工作负载 OIDC 留待后续用例。

## REST 与客户端样例

仓库、Issue 和 Release 的双端执行顺序、角色及确定性 Git 夹具见 [REST 取证手册](rest-runbook.md)。

以 `R=/repos/{owner}/{repo}` 表示隔离仓库路径。除特别注明外，GitHub 请求走 `https://api.github.com`，使用 `Accept: application/vnd.github+json`、固定版本头和单用途测试凭据，JSON 写入另带 `Content-Type: application/json`。样例中的 ID 由本次回执取得，Tag 与 SHA 由夹具预先固定。Gitea 原生请求从已固定的 `/api/v1` 入口发出，使用各用途独立授权。对同一动作保留原始请求、必要转换、响应和副作用读回。

| 切片 | GitHub 原始请求与验收 | Gitea 原生对照点 |
| --- | --- | --- |
| 仓库与提交 | `GET R`、`GET R/commits/{sha}` 均预期 200。核对仓库 ID、完整名称、私有状态、默认分支及完整 SHA。第二用户的私有访问按真实拒绝记录。 | `GET R` 和 `GET R/git/commits/{sha}`，比较响应字段与用户权限。 |
| Issue 与分页 | 准备至少两个 Issue 和一个 PR。`GET R/issues?state=all&sort=created&direction=asc&per_page=1&page=1` 预期 200，跟随实际 `Link` 并核对完整集合，按 `pull_request` 字段识别 PR。`POST R/issues` 传 `{"title":"m0-compat-issue","body":"m0 fixture"}` 预期 201。用回执 `number` 执行 `POST R/issues/{number}/comments` 传 `{"body":"m0 compat comment"}` 预期 201，再 `PATCH R/issues/{number}` 传 `{"state":"closed"}` 预期 200，GET 回读正文、评论和状态。 | 记录 `limit` / `page`、`type`、分页头与 PR 默认集合的差异，区分路径 index 与全局 ID。固定 OpenAPI 的 Issue PATCH 声明 201，实际值单独记录。只读、越权和撤权写入须拒绝并保持目标不变。 |
| Release 与附件 | `POST R/releases` 传 `{"tag_name":"m0-release-01","target_commitish":"<fixture-sha>","name":"M0 fixture","body":"m0 notes","draft":true}` 预期 201。创建后用返回的 `upload_url` 展开 `?name=m0-fixture.bin`，向已核实的 `uploads.github.com` 以 `application/octet-stream` 上传固定字节 `M0 fixture\n`，预期 201。通过 `GET R/releases/assets/{asset_id}` 和 `Accept: application/octet-stream` 核对 200 或 302 指向的实际字节。用 `PATCH R/releases/{release_id}` 传 `{"body":""}`，记录 200 后的字段回读。最后用 `{"draft":false}` 发布，回读 ID、草稿状态与 Tag 的实际提交。 | 上传位于 `POST R/releases/{id}/assets?name=...`，附件元数据与实际下载 URL 分开。保留只读 scope 草稿差异 G19 和清空差异 G20。发布前后独立核对实际 Tag SHA，异常回读保留副作用。 |
| 派发与运行 | `POST R/actions/workflows/m0-toolchain.yml/dispatches` 传 `{"ref":"main","inputs":{"marker":"m0-toolchain-01"}}`，`2026-03-10` 文档预期 200 和 `workflow_run_id`、`run_url`、`html_url`。按返回 ID 查询 `GET R/actions/runs/{run_id}` 与 `GET R/actions/runs/{run_id}/attempts/{attempt}/jobs`，核对事件、ref、SHA、attempt 和最终结果。 | 固定 OpenAPI 列出 200 / 204，`return_run_details` 位于 query。原始请求与追加 `?return_run_details=true` 的对照使用独立 marker 和派发。204 缺少 ID 时须以能唯一关联的真实证据确认派发，最新一条 run 不能单独用于归因。 |
| 取消、重跑与日志 | 对进行中的 `m0-policy.yml` 并发用例单独调用 `POST R/actions/runs/{run_id}/cancel`，预期 202 后读到终态。对已完成的受控运行调用 `POST R/actions/runs/{run_id}/rerun`，预期 201，回读增加的 attempt。用 `GET R/actions/runs/{run_id}/logs` 核对 302 和允许目标的日志字节。 | 固定 OpenAPI 的 cancel 为 200，rerun 为 201，logs 为 200。回执与真实终态分别取证。跳转目标按固定版本和环境校验，跨 origin 下载请求省略原 Authorization。 |

附件夹具为 11 字节，末尾为 LF，SHA-256 为 `d21cc231a75725ea02671f51c78c42ba501078b9d1b77bc4ca2c2c735c3db285`。

客户端取证时，用 `GH_TOKEN` 提供该次隔离凭据，`M0_GH_REPO` 固定为获授权仓库的 `owner/repo`。以下调用分别取证分页客户端和原始 JSON 派发，后者只发送一次。

```bash
gh api --hostname github.com --include --paginate \
  -H 'Accept: application/vnd.github+json' -H 'X-GitHub-Api-Version: 2026-03-10' \
  "repos/${M0_GH_REPO:?}/issues?state=all&sort=created&direction=asc&per_page=1"

gh api --hostname github.com --include --method POST --input - \
  -H 'Accept: application/vnd.github+json' -H 'X-GitHub-Api-Version: 2026-03-10' \
  "repos/${M0_GH_REPO:?}/actions/workflows/m0-toolchain.yml/dispatches" <<'JSON'
{"ref":"main","inputs":{"marker":"m0-toolchain-01"}}
JSON
```

记录原始状态码、关键字段、`Link` / `Location` 语义、权限拒绝和读回。签名下载链接只保存脱敏目标。写入超时先对账，零条、多条或无权核实均保留未知。将 GitHub 与 Gitea 原生结果分列。产品兼容入口、Octokit 和 Webhook 属于后续 COMP-03 取证。

[GitHub 仓库与提交](https://docs.github.com/en/rest/commits/commits?apiVersion=2026-03-10#get-a-commit) · [Issues](https://docs.github.com/en/rest/issues/issues?apiVersion=2026-03-10#list-repository-issues) · [Release](https://docs.github.com/en/rest/releases/releases?apiVersion=2026-03-10) · [Release 附件](https://docs.github.com/en/rest/releases/assets?apiVersion=2026-03-10) · [Workflow dispatch](https://docs.github.com/en/rest/actions/workflows?apiVersion=2026-03-10#create-a-workflow-dispatch-event) · [运行与日志](https://docs.github.com/en/rest/actions/workflow-runs?apiVersion=2026-03-10) · [固定 Gitea OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json)
