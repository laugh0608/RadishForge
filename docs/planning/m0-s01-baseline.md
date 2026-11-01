# M0-S01 候选组合与隔离验证方案

核查日期：2026-11-01（Asia/Shanghai）。任务 M0-01 进行中；本页维护官方来源、候选和隔离方案；已按用户要求调整为本机 Docker 优先，支持组合仍需按实际证据最终冻结。范围沿用[M0 子专题计划](m0-validation.md)；初始静态取证见[来源记录](../records/2026-11-01-m0-s01-review.md)和[元数据](../records/2026-11-01-m0-s01-sources.json)，本机准备与协议结果见[本机验证记录](../records/2026-11-01-m0-local-validation.md)。

## 候选选择

以下是首个验证候选，不是已支持版本或安装指令。保留精确版本，实际使用时同时固定制品校验值；变更候选先记录原因与受影响契约，不自动追踪 `latest`。

| 组件 | 候选 / 用途 | 选择依据与来源 | 许可边界 |
| --- | --- | --- | --- |
| Gitea | `28.2.0-rootless`；资源底座及独立测试 IdP 实例 | [28.2.0 发行说明](https://blog.gitea.com/release-of-28.2.0/)、[rootless 镜像说明](https://docs.gitea.com/installation/install-with-docker-rootless/)；延续原静态参考，已重新核对发布与镜像元数据 | 自有源码 MIT；不代表镜像内全部组件为 MIT |
| Gitea Runner | `5.2.4` 基础镜像，不含 DinD；只在后续 Actions 验证时启动 | [官方精确 Release API](https://gitea.com/api/v1/repos/gitea/runner/releases/tags/v5.2.4)、[安装说明](https://docs.gitea.com/runner/installation/docker/)；使用已发布 5.x 修订，不继续使用旧 `act_runner` 名称推断版本 | 源码 MIT；基础镜像及任务镜像另核查 |
| PostgreSQL | `18.6-bookworm`；Gitea / 测试 IdP 独立库和身份 | [支持版本](https://www.postgresql.org/support/versioning/)、[18.6 发行说明](https://www.postgresql.org/docs/18/release-18-6.html)、[镜像构建来源](https://github.com/docker-library/postgres/blob/e00e1bd34ec5c8a8e7ad89b273b3d42efaf6d5bc/18/bookworm/Dockerfile)；选正式受支持版本，不选 19 RC | PostgreSQL License；镜像系统包另计 |
| Go | `1.27.3`；后续最小协议样例 / M1 服务工具链 | [官方发行元数据](https://go.dev/dl/?mode=json)、[发行历史](https://go.dev/doc/devel/release)；采用当前稳定修订，未安装 | BSD-3-Clause，依赖另计 |
| Node.js / npm | `24.22.2` / 随附 `11.19.1`；后续 Web 工具链 | [固定版本发行页](https://nodejs.org/en/blog/release/v24.22.2)、[发行索引](https://nodejs.org/dist/index.json)；选择已有维护历史的 24 LTS，26.13.0 LTS 已核对但不纳入首批 | Node.js MIT 及附带声明；npm Artistic-2.0 |
| Docker Engine | 发行候选 `29.9.2`；本机实际 `29.8.2` | [29.9.2 发行说明](https://docs.docker.com/engine/release-notes/29/#2992)；包含 29.9.1 之后的运行时安全修订 | Engine / CLI 源码 Apache-2.0；不等同 Docker Desktop 许可 |
| Docker Compose plugin | 发行候选 `5.6.1`；本机实际 `5.5.0`，使用 `docker compose` | [精确发行](https://github.com/docker/compose/releases/tag/v5.6.1)及官方 checksum；候选使用插件命令，不要求沿用旧文档中的 v2 主版本号 | Apache-2.0 |

源码定位：Gitea Tag `v28.2.0` 的标注 Tag 对象为 `1dc1ecdddcdc60ab14ec14e30e7bb4d84242f21f`，解引用到提交 `829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1`；Runner Tag `v5.2.4` 指向 `ffd80101a317d6c3ef922dfb4856b629b3d60064`。Tag 对象 SHA 与源码提交 SHA 不混用。

Node 发行页标注 10 月 28 日，`dist/index.json` 标注 10 月 27 日；保留这一来源日期差异，以精确版本和制品 checksum 确认候选。npm 使用该 Node 发行随附版本，避免额外建立包管理器组合；未创建 package.json / lockfile，也未安装 npm、pnpm 或前端依赖。M1 再落实项目工具链配置。

### 镜像与平台固定

| 镜像 | OCI index Digest |
| --- | --- |
| `docker.gitea.com/gitea:28.2.0-rootless` | `sha256:94807314454f6525994a3b76286ba12bc7e7f8cd14f61d9e67431767f8103306` |
| `docker.io/gitea/runner:5.2.4` | `sha256:e8b3c7a5ed435fec38d1faf730cb784606cdd1c02e8543b6b96525b53281e60a` |
| `docker.io/library/postgres:18.6-bookworm` | `sha256:5c4783a8cc3f0074912164f94dfa1be4e043438f0f707cf968d7af9a0d31a2c8` |

三个 index 的响应字节 SHA-256 与 Registry `Docker-Content-Digest` 一致，均列出 `linux/amd64`、`linux/arm64` 的子 manifest；平台 Digest 保存在来源元数据。初始来源核查只读取 index；随后本机验证按固定 index 拉取 arm64 镜像，实际产物见本机记录。平台清单、运行版本不等于源码构建来源证明，仍未验签供应链 provenance。

用户已确认本机 Docker 优先。当前使用 macOS / arm64 上已运行的 OrbStack，显式 context 为 `orbstack`，daemon 为 `linux/arm64`、Engine 29.8.2、Compose 5.5.0；不修改本机工具或全局 context。这里是本地协议验证组合，不声称发行候选 Engine 29.9.2 / Compose 5.6.1 或 Linux amd64 已通过。发行目标的 amd64 安装、恢复与兼容另行验证，不以模拟或 arm64 结果外推。

拉取时使用 `镜像仓库@上述 index Digest` 并显式指定目标平台，核对所选子 manifest 与实际镜像。平台不在 index 中、哈希变化、标签漂移或拉取错误即停止，不能自动换架构、版本或关闭 TLS 验证。

### Runner 执行边界

固定 Runner 提交的 [Dockerfile](https://gitea.com/gitea/runner/src/commit/ffd80101a317d6c3ef922dfb4856b629b3d60064/Dockerfile)列出的 DinD 基线为 `docker:29.9.1-dind`，不等于本轮选定的 29.9.2。这里没有执行 DinD 镜像，不据源码声明其实际运行时；Runner 基础镜像保留为后续候选；本批 Compose 不包含 Runner，不下载、注册或启动它。

平台 Gitea / IdP 不挂 Docker socket、不使用 privileged 或 host network。独立 Compose 项目、网络、卷用于资源归属与避免串数据，不宣称隔离同一 daemon 的管理权限。后续 M0-S03 / S04 如需执行工作流，先明确受控样例与 daemon 权限；不可信工作流、平台数据和生产凭据的信任隔离单独设计，不把专用 VM 作为当前身份 / API 验证的前置。

Runner 5.x 文档要求 Gitea 1.21+、Git 2.34.1+，JavaScript Action 的 Node 运行时取决于 Action 与 job 环境，不能从控制端 Node 版本推导。M0-S03 / S04 启动 Runner 前再固定实际 job 镜像、Git / Node 版本和 Action commit；`builtin:checkout` 可作为独立样例，不能替代原 `actions/checkout` 的兼容取证。

## OpenAPI 与身份静态结论

本轮读取[Gitea 固定提交 OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json)，SHA-256 为 `c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`，与 2026-10-29 静态记录一致。共 342 个路径，Issue / Actions / Release 相关筛选命中 70 个；筛选不代表覆盖所有首版操作。`info.version` 仍为构建占位值，版本以固定来源确认。OCI 的 `/v2/` 属独立协议，不能从此 OpenAPI 推导其可用。

[OAuth2 官方文档](https://docs.gitea.com/development/oauth2-provider/)列出 Discovery、授权码、PKCE、UserInfo、JWKS 与细粒度 scope，并警示常见 OIDC scope 的默认资源权限较宽、未知 scope 可能回落到全权限。初始静态核查后，精确 28.2.0 的[本机证据](../records/2026-11-01-m0-auth-profile-validation.md)已复现三项原始 scope 差异，并验证受控组合；完整生命周期和其他发行方仍待取证。

验证方案选择第二个独立 Gitea 实例作为标准 OIDC 测试发行方，复用同一镜像但使用独立 issuer、库、账号和密钥；资源 Gitea 另注册用户 OAuth 客户端。另用资源 Gitea 的 OIDC 端点构成第二 issuer，同邮箱样例只用于确认身份键不合并。该方案不增加 Radish 运行依赖，也不证明其他 IdP 实现兼容。

已验证的登录 / 资源三种完整组合以[授权 JSON](../../tests/contracts/m0/gitea-auth-profile.json)为单一来源，决定见[ADR 0003](../adr/0003-gitea-authorization-profiles.md)；不能仅凭单个 scope 名称推定权限。只用隔离账号进行“仅 OIDC / 未知 scope”负例，保留意外扩大权限的原始结果；不能将未知 scope 回退视为成功。协议测试客户端不能代替工作台绑定 / 会话实现，完整 IAM-01 / IAM-02 仍在 M1 验收。

## 本机隔离配置

正式配置在 [compose.yaml](../../tests/contracts/m0/compose.yaml)，操作入口为 [m0_local.py](../../scripts/m0_local.py)，真实上游协议探针为 [m0_contracts.py](../../scripts/m0_contracts.py)。它们是 M0 验证工具，不是自有业务服务；不引入第三方 Python 依赖、产品工程或密码库。使用说明见[契约验证入口](../../tests/contracts/m0/README.md)。

| 项目 | 本批设置 |
| --- | --- |
| Docker | 显式使用用户已运行的 `orbstack` context；不启动 / 停止 OrbStack，不操作其他 context |
| 平台 | 原生 `linux/arm64`；固定来源快照中的 Gitea / PostgreSQL index Digest |
| 服务 | PostgreSQL + 资源 Gitea + 独立 IdP Gitea；应用分别使用独立 DB / DB 身份 |
| 资源归属 | 每批随机 `rf-m0-local-<8 hex>` Compose 项目，独立网络、六个命名卷及仓库 `.local/m0/owner.json` 标记 |
| 网络 | 数据库仅 internal 网络；两套 Gitea 另接任务 frontend 网络用于本机发布端口 |
| 端口 | 仅 `127.0.0.1:18443` 和 `127.0.0.1:19443`；数据库 / SSH 不发布 |
| 地址 | `https://localhost:18443`、`https://localhost:19443`；取证期间 issuer 保持不变 |
| TLS | 本批生成两天有效的测试 CA / localhost 证书，含 SAN / SKI / AKI；客户端显式加载本批 CA，不改系统 / 浏览器信任、不跳过校验 |
| 私密数据 | 仅 `.local/m0` 的 0700 目录与 0600 文件、任务专用配置 / secret 卷；密码、Token、私钥不写源码、命令参数或报告 |
| 权限 | 两套 Gitea 以 rootless 镜像默认用户运行；一次性 seed 容器仅在专用卷写配置并授予必要 CHOWN，完成即退出 |
| 预算 | 两套 Gitea 各限 1 GiB / 1 CPU，PostgreSQL 限 768 MiB / 1 CPU；本批首次下载 / 解包按实际记录，不升级宿主工具 |
| Runner | Compose 中不存在 Runner，Gitea Actions 明确关闭；无 Docker socket、privileged 或 host network |

PostgreSQL 18 镜像卷挂在 `/var/lib/postgresql`，使用上游空卷初始化机制创建两套应用库和非超级用户；不接触 Gitea 业务表。上游自身 schema 初始化由 Gitea 负责，不建立自有迁移。

本机所有测试对象使用合成账号、邮箱、私有仓库和 Issue。管理员仅用于普通账号准备及禁用账号负例；资源创建、读取、写入、用户 OAuth 授权和仓库撤权使用真实普通用户身份。初始化命令让 Gitea 自行生成随机管理员密码，工具仅在内存接收并写入本批私密目录，不将密码传为 CLI 参数。

### 执行与清理

先只读确认 daemon 归属、实际版本 / 架构、任务名称与端口。用户本轮授权覆盖本机隔离配置及身份、权限、API 真实验证，下载 / 启动前已说明用途与资源影响；这一授权不扩大到 Runner、工具升级、全局设置、提交 / 推送、发布或部署。

```bash
python3 scripts/m0_local.py prepare --context orbstack --auth-profile
python3 scripts/m0_local.py pull
python3 scripts/m0_local.py up
python3 -u -B scripts/m0_contracts.py --mode profiles
python3 scripts/m0_local.py status
python3 scripts/m0_local.py cleanup
```

`prepare` 先拒绝既有运行目录或非 arm64 daemon，探测端口后生成归属、CA 和私密配置，执行 `compose config --quiet`。`pull` 只拉三个平台服务所需的两个固定镜像；`up` 拒绝复用已有任务容器 / 卷，先初始化专用卷，再启动并用受信任 TLS 的 `/api/healthz` 和容器 CLI 精确版本检查就绪。

scope 收敛已使用[单一授权配置](../../tests/contracts/m0/gitea-auth-profile.json)与默认 `profiles` 模式，`--auth-profile` 仅为本批新实例开启短 Token / refresh rotation 验证参数。原始差异通过显式 `--mode discovery` 保留；具体命令、已验证与未通过范围见[授权组合记录](../records/2026-11-01-m0-auth-profile-validation.md)，不能以受控组合结果替代原始上游兼容结论。

协议探针只访问登记的两个本机 origin，拦截 loopback OAuth 回调，无需额外回调服务器；通过公开 API 和原生登录 / 同意页表单验证协议，不依赖底座数据库或内部 Go 包。授权码、cookie、密码、Token 均不打印；写操作失败 / 未知时保留进度并拒绝直接整批重跑，先对账或确认本批合成数据后建立新批次。

默认结束执行 `cleanup`：按归属标记仅移除本批容器、网络、命名卷及 `.local/m0` 证书 / 凭据，保留脱敏证据。既有容器、卷、其他项目缓存及系统信任均不改；固定镜像留在共享下载缓存，不执行全局 prune。

### 验收范围

本批优先验证两套实例健康 / 版本、TLS 信任边界、OIDC Discovery / JWKS / 签名 / 声明、授权码 PKCE、重放拒绝、普通用户私有资源、Issue 写入 / 回读、只读 scope、跨用户越权、资源撤权和 OAuth 授权删除行为。常见 OIDC scope、未知 scope 的广泛授权属于差异取证，不能把资源可读作为“仅登录”权限正确。

浏览器真实交互、完整绑定 / Cookie / CSRF / Token 存储及后台撤权仍待 M1；Actions / Runner、OCI、Release、多组件交付、amd64 与生产均不由本批结果关闭。`M0-01` 最终冻结及阶段晋级依然依赖 M0-S02—S04 的证据与关键缺口决定。
