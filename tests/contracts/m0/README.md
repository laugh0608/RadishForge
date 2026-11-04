# M0 本机上游契约验证

这是 Gitea / PostgreSQL 的隔离验证环境，不是 RadishForge 业务应用或发行部署配置。当前平台为 macOS / arm64 + OrbStack 的 Linux arm64 daemon；使用已核对的镜像 Digest，不升级本机 Docker / Compose。方案与边界见[M0-S01](../../../docs/planning/m0-s01-baseline.md)。

## 资源与授权

仅在已授权的本机 Docker 上使用。默认显式 context `orbstack`，随机 Compose 项目名 `rf-m0-local-<8 hex>`；工具不会切换全局 context。运行三个服务：PostgreSQL、资源 Gitea、独立测试 IdP Gitea。无 Runner / Actions、Docker socket、privileged 或 host network。

入口仅绑定 `127.0.0.1:18443/19443`，数据库只接 internal 网络。服务合计内存限额 2.75 GiB；首次网络 / 磁盘影响以实际镜像为准，下载前说明范围。初始六个卷与网络均归本批 Compose 项目，既有容器 / 卷 / 缓存不得清理。

运行目录是仓库忽略的 `.local/m0`：目录 0700、文件 0600，包含两天有效的测试 CA、私钥、随机密码、Token 与任务归属。`.gitignore` 不代替秘密审查。客户端仅显式信任该 CA，不修改系统 / 钥匙串 / 浏览器配置，不关闭 TLS 验证。两个 HTTPS origin 全程固定。

## 执行

依赖：已有 Docker / Compose、Python 3.9+、OpenSSL（支持命令中的证书扩展参数）。本批在 Python 3.14.5 / OpenSSL 4.0.3 验证；其他版本未外推。没有第三方 Python 包安装。

```bash
python3 scripts/m0_local.py prepare --context orbstack --auth-profile
python3 scripts/m0_local.py pull
python3 scripts/m0_local.py up
python3 -u -B scripts/m0_contracts.py --mode profiles
python3 scripts/m0_local.py status
python3 scripts/m0_local.py cleanup
```

`prepare` / `up` 拒绝复用已有运行目录、容器或卷，不覆盖既有数据；配置初始化使用一次性无网络 seed 容器，仅写本批卷，退出即删除。Gitea rootless 配置归 UID 1000，固定 PostgreSQL Debian 镜像的专用秘密归 UID 999；更换镜像须重新核对身份与目录。

协议探针创建本批普通账号、私有仓库、Issue 和 OAuth 客户端，通过公开 API 与原生登录 / 同意表单进行真实调用；不读写 Gitea 业务数据库。API 请求不保存或携带浏览器 cookie，只按本次指定的 Basic / Bearer 凭据鉴权；原生登录 / 同意步骤使用独立 CookieJar，避免测试账号与会话互相影响。回调由协议客户端拦截检查，不启动额外回调服务，也不将授权信息发往外部调试站点。这证明上游协议行为，不能冒充工作台真实浏览器交互。

登录 / 同意的浏览器模拟会话彼此独立；浏览器 cookie 不按端口隔离，因此同一真实浏览器的双实例会话需要后续单独验收，不由协议探针外推。

### 授权配置与验证模式

[gitea-auth-profile.json](gitea-auth-profile.json)是 M0 配置单一来源：固定身份、资源只读、Issue 写入三个完整 scope 组合及 issuer；客户端 confidential / 精确 callback / 不跳过首次同意。`m0_scope.py` 在创建应用、发起授权或刷新前校验完整组合，不接受任意子集、并集、空值或未知 scope。实际授予 scope 用受认证 introspection 核对；凭据还须通过在线账号复核，不能只看签名或 Token 端点 HTTP 200。

`prepare --auth-profile` 另给本任务新实例写入 refresh 单次使用、access token 30 秒 / refresh token 1 小时等测试配置，并要求 `[security] DISABLE_QUERY_AUTH_TOKEN=true`；`up` 回读两套实例的实际设置及 Actions 关闭状态，漂移即停止。后者避免 introspection 正文的 `token` 被通用资源鉴权提前处理，资源 API 只携带 Bearer Header；TTL 不是生产默认值，不改共享 Gitea。默认探针模式为 `profiles`，要求运行目录与当前配置 SHA-256 一致，验证受控组合、拒绝同意、client secret、callback、刷新 / 撤销等。

原始上游差异模式仍保留。需要明确复现时，在一批新环境使用 `prepare`（不带 `--auth-profile`），再执行 `python3 -u -B scripts/m0_contracts.py --mode discovery`；该模式刻意发送不应供产品使用的组合，只对合成账号运行。历史三项差异没有被新模式通过覆盖；改动说明与边界见[ADR 0003](../../../docs/adr/0003-gitea-authorization-profiles.md)。

探针退出码：0 表示本批所执行用例未发现差异，1 表示执行中断，2 表示流程完成但存在权限 / 协议缺口。三者都不代表整个 IAM / BASE / COMP 产品验收通过；缺口不得改为默认成功。结果包含命名用例、状态、无参数请求 / 最终路径、HTTP 状态、Content-Type / 正文类型和源码摘要，不导出响应正文、查询参数或秘密；私密结果目录仍按秘密处理，导出前复核。禁用账号仍可刷新即使被本地复核拒绝，也继续保留 gap 和退出 2。

写操作不自动重试；出现失败 / 超时，先查 `results.json` 和实际对象状态，再决定恢复步骤。`contract-started.json` 存在时拒绝整批重跑，不能删除该标记后重复创建账号 / 仓库。确认可清理的合成测试批次可以先保存脱敏证据、执行 cleanup，再新建一批。

### 生命周期与原生单用户撤销

使用新批次 `prepare --auth-profile` / `up`，执行：

```bash
python3 -u -B scripts/m0_contracts.py --mode lifecycle
```

该模式先创建一个保持未使用的 refresh token，按配置真实等待一小时；期间验证禁用 / 恢复账号、过期 introspection 与客户端凭据对照、两个并发刷新 / 后继权限 / 重放，再验证原生单用户撤销。总窗口约 70–90 分钟，不能改系统时钟或将短 TTL 当成生产建议。UI 协调超时、中断或未知结果均停止，不能自动重放写操作。

收到 `awaiting_native_consent_revocation` 后，在另一个本任务浏览器 / 终端完成：

1. 读取 `.local/m0/consent-target.json` 核对项目、用户和应用；在仅信任本批证书的隔离浏览器中，以合成普通用户 bob 登录资源 Gitea，进入 Settings → Applications → Authorized OAuth2 Applications。密码仅从私密运行目录在内存提供，不进入 CLI 参数、日志、截图或报告；不安装浏览器依赖、不改系统信任。
2. 找到目标 `m0-shared-consent`，点击其 **Revoke** 并停在确认框；不是 Remove 应用。在另一个终端执行 `python3 -B scripts/m0_local.py consent-ready`。
3. 等待 `.local/m0/consent-click-ready.json` 出现。这表示探针刚刷新并核实待撤销的凭据；在 25 秒内确认页面的 Yes，观察成功提示 / 目标授权消失，再执行 `python3 -B scripts/m0_local.py consent-revoked`。准备页面的窗口为 20 分钟；超时须保留结果并对账。
4. 探针检查尚未正常过期的 access token、refresh token 和 introspection 均失效，同应用另一用户、同用户其他应用和独立身份授权仍有效，并验证显式重新同意及旧值仍拒绝。标记文件仅协调时点，不能替代这些真实断言。

固定公开 REST 描述没有单用户 grant 撤销接口，因此使用真实原生 UI 操作；探针和产品都不封装私有前端撤销请求，不删除整个共享应用代替撤销。不将该路径的通过外推为产品解绑 / 后台任务停止或 UI-01 通过。

仅需重新定位两项旧配置差异时，使用另一新批次：

```bash
python3 -B scripts/m0_local.py prepare --context orbstack --auth-profile --legacy-query-auth
python3 -B scripts/m0_local.py up
python3 -u -B scripts/m0_contracts.py --mode lifecycle-baseline
```

这是显式历史诊断，保留表单 / 查询串资源 Token 鉴权；受控 `profiles` / `lifecycle` 模式拒绝该设置，不能作为默认运行方案。新结果不覆盖旧差异，见[生命周期记录](../../../docs/records/2026-11-04-m0-lifecycle-validation.md)和[ADR 0003](../../../docs/adr/0003-gitea-authorization-profiles.md)。

## 清理与未覆盖

无论探针成功、发现缺口或中断，交接前执行 `cleanup`。它按归属删除本批容器 / 网络 / 六个卷和 `.local/m0` 凭据，不触碰其他项目资源；下载镜像保留在共享缓存，不全局 prune。需要保留运行环境时先有用户明确要求，再交接项目名、容器 ID、端口和停止命令。

完整产品会话 / 账号绑定 / 加密存储、浏览器 Cookie / CSRF、产品解绑与后台任务停止、其他 IdP / 版本、Actions / Runner、OCI、Release、多组件清单、amd64 安装 / 恢复和生产仍未覆盖。刷新到期 / 并发与原生撤销按实际批次记录，不从本地测试或模式存在推导通过。首轮结果见[本机记录](../../../docs/records/2026-11-01-m0-local-validation.md)，历史组合与生命周期见[授权组合记录](../../../docs/records/2026-11-01-m0-auth-profile-validation.md)，本批结果见[生命周期记录](../../../docs/records/2026-11-04-m0-lifecycle-validation.md)。
