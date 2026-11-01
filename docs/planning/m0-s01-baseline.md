# M0-S01 候选组合与隔离验证方案

核查日期：2026-11-01（Asia/Shanghai）。任务 M0-01 进行中；本页已交付官方来源静态核查、候选选择和隔离方案，环境未建立，支持组合未最终冻结。范围沿用[M0 子专题计划](m0-validation.md)；实际取证见[本轮记录](../records/2026-11-01-m0-s01-review.md)和[来源元数据](../records/2026-11-01-m0-s01-sources.json)。

## 候选选择

以下是首个验证候选，不是已支持版本或安装指令。保留精确版本，实际使用时同时固定制品校验值；变更候选先记录原因与受影响契约，不自动追踪 `latest`。

| 组件 | 候选 / 用途 | 选择依据与来源 | 许可边界 |
| --- | --- | --- | --- |
| Gitea | `28.2.0-rootless`；资源底座及独立测试 IdP 实例 | [28.2.0 发行说明](https://blog.gitea.com/release-of-28.2.0/)、[rootless 镜像说明](https://docs.gitea.com/installation/install-with-docker-rootless/)；延续原静态参考，已重新核对发布与镜像元数据 | 自有源码 MIT；不代表镜像内全部组件为 MIT |
| Gitea Runner | `5.2.4` 基础镜像，不含 DinD；只在后续 Actions 验证时启动 | [官方精确 Release API](https://gitea.com/api/v1/repos/gitea/runner/releases/tags/v5.2.4)、[安装说明](https://docs.gitea.com/runner/installation/docker/)；使用已发布 5.x 修订，不继续使用旧 `act_runner` 名称推断版本 | 源码 MIT；基础镜像及任务镜像另核查 |
| PostgreSQL | `18.6-bookworm`；Gitea / 测试 IdP 独立库和身份 | [支持版本](https://www.postgresql.org/support/versioning/)、[18.6 发行说明](https://www.postgresql.org/docs/18/release-18-6.html)、[镜像构建来源](https://github.com/docker-library/postgres/blob/e00e1bd34ec5c8a8e7ad89b273b3d42efaf6d5bc/18/bookworm/Dockerfile)；选正式受支持版本，不选 19 RC | PostgreSQL License；镜像系统包另计 |
| Go | `1.27.3`；后续最小协议样例 / M1 服务工具链 | [官方发行元数据](https://go.dev/dl/?mode=json)、[发行历史](https://go.dev/doc/devel/release)；采用当前稳定修订，未安装 | BSD-3-Clause，依赖另计 |
| Node.js / npm | `24.22.2` / 随附 `11.19.1`；后续 Web 工具链 | [固定版本发行页](https://nodejs.org/en/blog/release/v24.22.2)、[发行索引](https://nodejs.org/dist/index.json)；选择已有维护历史的 24 LTS，26.13.0 LTS 已核对但不纳入首批 | Node.js MIT 及附带声明；npm Artistic-2.0 |
| Docker Engine | `29.9.2`；专用 Linux 环境的容器运行时 | [29.9.2 发行说明](https://docs.docker.com/engine/release-notes/29/#2992)；包含 29.9.1 之后的运行时安全修订 | Engine / CLI 源码 Apache-2.0；不等同 Docker Desktop 许可 |
| Docker Compose plugin | `5.6.1`；通过 `docker compose` 编排验证环境 | [精确发行](https://github.com/docker/compose/releases/tag/v5.6.1)及官方 checksum；候选使用插件命令，不要求沿用旧文档中的 v2 主版本号 | Apache-2.0 |

源码定位：Gitea Tag `v28.2.0` 的标注 Tag 对象为 `1dc1ecdddcdc60ab14ec14e30e7bb4d84242f21f`，解引用到提交 `829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1`；Runner Tag `v5.2.4` 指向 `ffd80101a317d6c3ef922dfb4856b629b3d60064`。Tag 对象 SHA 与源码提交 SHA 不混用。

Node 发行页标注 10 月 28 日，`dist/index.json` 标注 10 月 27 日；保留这一来源日期差异，以精确版本和制品 checksum 确认候选。npm 使用该 Node 发行随附版本，避免额外建立包管理器组合；未创建 package.json / lockfile，也未安装 npm、pnpm 或前端依赖。M1 再落实项目工具链配置。

### 镜像与平台固定

| 镜像 | OCI index Digest |
| --- | --- |
| `docker.gitea.com/gitea:28.2.0-rootless` | `sha256:94807314454f6525994a3b76286ba12bc7e7f8cd14f61d9e67431767f8103306` |
| `docker.io/gitea/runner:5.2.4` | `sha256:e8b3c7a5ed435fec38d1faf730cb784606cdd1c02e8543b6b96525b53281e60a` |
| `docker.io/library/postgres:18.6-bookworm` | `sha256:5c4783a8cc3f0074912164f94dfa1be4e043438f0f707cf968d7af9a0d31a2c8` |

三个 index 的响应字节 SHA-256 与 Registry `Docker-Content-Digest` 一致，均列出 `linux/amd64`、`linux/arm64` 的子 manifest；平台 Digest 保存在来源元数据。这里只读取 index，未下载子镜像 / 层、未运行、未验签来源证明，也未证明二进制由所列源码构建。

首选验证目标为专用 `linux/amd64` 环境，匹配首版发行候选平台；本机 `darwin/arm64` 仅作为控制端。若改用原生 `linux/arm64`，须明确变更验证平台并使用对应子 manifest，结果不外推 amd64；不默认使用跨架构模拟。宿主发行版、内核、虚拟化工具与具体实例尚未指定，实际启动前补齐，不声称整个宿主组合已冻结。

拉取时使用 `镜像仓库@上述 index Digest` 并显式指定目标平台，核对所选子 manifest 与实际镜像。平台不在 index 中、哈希变化、标签漂移或拉取错误即停止，不能自动换架构、版本或关闭 TLS 验证。

### Runner 执行边界

固定 Runner 提交的 [Dockerfile](https://gitea.com/gitea/runner/src/commit/ffd80101a317d6c3ef922dfb4856b629b3d60064/Dockerfile)列出的 DinD 基线为 `docker:29.9.1-dind`，不等于本轮选定的 29.9.2。这里没有执行 DinD 镜像，不据源码声明其实际运行时；首批改选基础镜像，在独立执行 VM 管理 29.9.2 Engine。

Runner 基础镜像通过该执行 VM 的 Docker socket 调度任务；此权限等同控制该 VM，所以该 VM 不放平台数据库、客户数据、日常工作目录或生产凭据，也不挂载本机 Docker socket。平台 Gitea / IdP 不接触 socket。只执行受控隔离样例，fork / 秘密负例使用合成数据；这不构成任意不可信工作流的生产隔离验收。

Runner 5.x 文档要求 Gitea 1.21+、Git 2.34.1+，JavaScript Action 的 Node 运行时取决于 Action 与 job 环境，不能从控制端 Node 版本推导。M0-S03 / S04 启动 Runner 前再固定实际 job 镜像、Git / Node 版本和 Action commit；`builtin:checkout` 可作为独立样例，不能替代原 `actions/checkout` 的兼容取证。

## OpenAPI 与身份静态结论

本轮读取[Gitea 固定提交 OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json)，SHA-256 为 `c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`，与 2026-10-29 静态记录一致。共 342 个路径，Issue / Actions / Release 相关筛选命中 70 个；筛选不代表覆盖所有首版操作。`info.version` 仍为构建占位值，版本以固定来源确认。OCI 的 `/v2/` 属独立协议，不能从此 OpenAPI 推导其可用。

[OAuth2 官方文档](https://docs.gitea.com/development/oauth2-provider/)列出 Discovery、授权码、PKCE、UserInfo、JWKS 与细粒度 scope，并警示常见 OIDC scope 的默认资源权限较宽、未知 scope 可能回落到全权限。此为滚动文档静态结论，精确 28.2.0 的实际授予与拒绝仍须 M0-S02 验证。

验证方案选择第二个独立 Gitea 实例作为标准 OIDC 测试发行方，复用同一镜像但使用独立 issuer、库、账号和密钥；资源 Gitea 另注册用户 OAuth 客户端。另用资源 Gitea 的 OIDC 端点构成第二 issuer，同邮箱样例只用于确认身份键不合并。该方案不增加 Radish 运行依赖，也不证明其他 IdP 实现兼容。

登录客户端先验证 `openid` 与 `public-only` 等限制的实际效果；资源客户端分别验证 `read:repository`、`write:issue` 等最小 scope 与普通用户对象权限，具体请求以接口实测收敛。只用隔离账号进行“仅 OIDC / 未知 scope”负例，观察是否意外扩大权限；不能将未知 scope 回退视为成功。协议测试客户端不能代替工作台绑定 / 会话实现，完整 IAM-01 / IAM-02 仍在 M1 验收。

## 隔离环境方案

以下资源、路径和端口均为拟定值，尚未创建、探测可用性或启动；不是现有实例清单。首次启动前确定实例归属、实际版本、证书与路由，并复核当时空闲端口。

| 项目 | 平台环境 A：M0-S02 优先 | 执行环境 B：M0-S03 / S04 再增加 |
| --- | --- | --- |
| 边界 | 独立 Linux VM：PostgreSQL + 资源 Gitea + 测试 IdP Gitea | 第二个独立 Linux VM：Runner 基础镜像 + 独立 Docker daemon + job 容器 |
| 初始预算 | 2 vCPU、4 GiB RAM、20 GiB 可用磁盘 | 2 vCPU、4 GiB RAM、20 GiB 可用磁盘，Runner capacity=1 |
| 本批拟定运行根 | `/srv/radishforge-m0/2026-11-01/platform` | `/srv/radishforge-m0/2026-11-01/worker` |
| 编排项目名 | `rf-m0-20261101-platform` | `rf-m0-20261101-worker` |
| 对外入口 | 资源 Gitea HTTPS `18443`；IdP HTTPS `19443`，仅控制端与 B 可达 | 无公网服务端口；不开放 Docker TCP API |
| 内部入口 | 数据库 `5432` 仅内部网络；Gitea 容器监听按独立配置映射 | Docker socket 只在 B；注册后移除初始注册 Token 文件的挂载 |
| 数据 | 两个独立 DB / DB 用户、Gitea 数据 / 配置、IdP 数据 / 配置、任务专用秘密文件 | Runner 注册状态、配置、任务缓存与构建层；不存生产秘密 |
| 执行时长 | 首批预留 2—4 小时，按实际记录；不承诺协议验证全部通过 | 仅测试窗口启动；单 job 超时建议 15 分钟，有界注册重试 |

这些是规划预算而非测量值。初期镜像 / 工具下载预留约 1—3 GiB 网络和 5—10 GiB 解包空间，后续 job 镜像 / 构建另估；执行前根据实际 manifest / 平台核对体积。阶段 A 不下载 Runner / job 镜像，不安装 Go / Node 产品依赖；工具链候选仅在样例实际需要时引入。

环境文件计划放在对应运行根：`compose.yaml`、`config/`、`data/`、`secrets/` 和脱敏 `evidence/`。这些文件本轮未生成，不存在可直接执行的 Compose 配置；下一批建立环境时按本方案生成并先做配置校验。运行目录不在正式源码或兄弟项目内，秘密文件限制访问；不得把渲染后的完整 Compose / 环境变量输出入库。

PostgreSQL 18 官方镜像的数据卷挂在 `/var/lib/postgresql`，默认 `PGDATA=/var/lib/postgresql/18/docker`；不能照搬 17 及以前的挂载位置。参见[官方镜像说明](https://github.com/docker-library/docs/blob/master/postgres/README.md)。初始化数据库账户只作用于本任务空数据目录，不清空或复用现有数据库。

### 地址、TLS 与账号

- 由隔离环境提供可供浏览器、协议客户端、Runner 和 job 容器一致访问的两个稳定 HTTPS origin，分别映射上述端口；真实主机名、DNS、证书与回调地址启动前落实，不默认配置候选公网域名。
- Gitea 可直接终止 HTTPS，证书通过该实例专用文件提供；需要任务专用 CA 时只给测试客户端 / 容器配置，浏览器采用隔离测试配置，不修改系统信任、不使用 `insecure` 或忽略证书错误。
- 未落实上述条件时保持环境准备待执行，不将容器 `localhost` 当跨 VM 地址，也不在取证中途换 issuer；确需改 origin 时建立新批次并重测相关身份链路。
- 管理员仅用于初始配置；建立普通用户 A / B、隔离组织 / 仓库和同邮箱不同 issuer 样例。登录 Token、资源 Token、注册 Token 分开保管，均不得传给外部调试网站或进入命令参数 / 报告。
- 只注册测试客户端和测试 Runner，不连接用户真实 GitHub / Gitea 仓库，不使用现有管理员或服务账号 Token 作为权限验收结果。

### 执行、停止与清理顺序

下列命令以平台 VM 的拟定绝对路径为例，尚未执行；实际配置生成、归属和授权确认后才可使用。工作站若远程操作，必须显式指定已确认的专用 Docker context，不切换全局默认 context。

1. 确认 A / B 归属、宿主版本、端口、目录、磁盘、TLS 与路由；复核已选版本和 Digest。不存在专用环境时先准备实例，不复用未知 daemon。
2. 生成 A 的隔离配置和秘密文件，以 `docker compose -p rf-m0-20261101-platform -f /srv/radishforge-m0/2026-11-01/platform/compose.yaml config --quiet` 校验，不打印展开后的秘密。
3. 先用同一命令前缀 `pull postgres forge idp`，核对 Digest / 平台，再 `up -d postgres forge idp`；等待有界健康检查，失败保留脱敏原因，不循环重建或换版本。记录容器 ID、端口和任务标签。
4. 配置两个隔离库及普通账号 / 客户端，执行 M0-S02；B 此时不启动。BASE-01 / IAM 的真实证据仍由对应子专题记录。
5. M0-S03 需要时生成 B 的配置，固定 job 镜像 / Action 与运行时，单独复核 B 的下载 / socket 权限范围后注册并启动 Runner；不使用 daemon 默认无限注册重试。
6. 停止时先终止本批已知 job、停止 B，再停止 A。使用各自精确项目 / 文件的 `stop` / `down`，核对运行实例已停止；不操作其他项目，不使用全局 prune。
7. 证据保留后，仅在确认无需保留合成数据时对该项目的命名卷执行 `down --volumes`；绑定数据目录另按任务归属精确清理。专用 VM 的 Engine 缓存也须核对占用；不以清空共享 Engine 代替清理。需销毁 VM 或回收制品时按实际目标核对授权。

## 尚待真实取证与退出条件

本批静态交付已覆盖候选版本、源码 / 镜像定位、许可入口、OpenAPI 摘要和隔离执行方案。环境创建、镜像拉取 / 来源证明、实际二进制版本、健康、普通用户授权、撤权、Issue / Actions / OCI / Release、客户端 / job 运行时与兼容矩阵均未验证。

M0-01 保持进行中。只有后续 M0-S02—S04 形成证据、关键缺口已处理，才能最终冻结支持组合并考虑 M1；当前不能填写 BASE-01、IAM-01 / IAM-02 或 COMP-01 整项通过。
