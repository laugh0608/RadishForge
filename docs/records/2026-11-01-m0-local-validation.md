# 2026-11-01 本机 Docker 与身份 / 权限 / Issue API 验证

任务：M0-01 / M0-S01、M0-02 / M0-S02、M0-03 / M0-S03 的平台与 Issue 部分。用户明确要求本机 Docker 优先，调整文档、核查本机环境、准备隔离配置并推进真实验证，暂不启动 Runner。源码基线 `9c1e481`，起始工作区 / 暂存区干净；未 fetch，本轮未提交或推送。

## 环境与范围调整

本机为 macOS / arm64，当前 Docker context 是已运行的 `orbstack`，daemon 为 Linux arm64 / Engine 29.8.2，内核 `7.2.12-orbstack-00394-gbecdd6130068`；Compose 5.5.0，Python 3.14.5，OpenSSL 4.0.3。探测时 daemon 可见 10 CPU、约 15.7 GiB 内存，没有运行容器或 Compose 项目，但有其他项目镜像、20 个卷和构建缓存，全部保留。

已撤销原方案中“当前必须另建专用 Linux VM、先落实外部 HTTPS 主机”的前置。本轮显式 context、本机回环端口、任务 CA、随机 Compose 项目 / 独立卷足以承载受控协议测试；不将 Compose 资源分组宣传为同一 daemon 管理权限的强隔离。正式方案见[本机基线](../planning/m0-s01-baseline.md)，实际入口见[契约说明](../../tests/contracts/m0/README.md)。

发行候选 Engine 29.9.2 / Compose 5.6.1 保留为后续目标，本机实际版本分别记录；没有为匹配文档而升级 OrbStack / Docker / Compose，也不从 arm64 结果推断 amd64 可用。自有 Go / React 业务工程仍未创建。

## 配置与执行

- 新增 `tests/contracts/m0/compose.yaml`、空 PostgreSQL 卷初始化脚本，以及两个 Python 标准库验证工具。配置仅包含 PostgreSQL、资源 Gitea、独立 IdP Gitea 和一次性无网络 seed；不存在 Runner。
- Gitea 固定 `28.2.0-rootless` index Digest，实际 arm64 产物 / 版本已核对；PostgreSQL 固定 `18.6-bookworm`，容器实际输出 18.6。两个镜像解包 Size 合计 885,084,843 字节，未下载工具链、Runner 或 job 镜像。
- 仅发布 `127.0.0.1:18443/19443`；数据库 5432、镜像声明的 SSH 2222 不发布。容器 inspect 确认非 privileged、非 host network、无 Docker socket 挂载。
- 两套 Gitea 分别使用独立库与 DB 用户，不直接操作 Gitea 业务表。服务内存限额合计 2.75 GiB，未测量或承诺峰值性能。
- 每批生成两天有效的 CA 与 localhost SAN 证书，显式信任本批 CA；默认系统信任访问被拒绝，受信任客户端通过。无系统证书 / 钥匙串 / 浏览器修改，无忽略证书错误。
- 管理员只用于建立合成普通用户；其密码由 Gitea CLI 随机生成、输出在工具内存接收，未进入命令参数或工具输出。普通用户 API / OAuth Token 执行私有资源操作；请求结果只保存无参数路径 / 状态，不保留 cookie、密码、授权码或 Token。

最终完整执行批次为 `rf-m0-local-a8d628fc`。容器 ID、固定镜像、版本、平台、端口、脚本 / 配置 SHA-256、请求轨迹与清理结果见[脱敏结果](2026-11-01-m0-local-results.json)。前序开发调试批次均只含本任务合成数据，已逐批清理；没有复用或删除其他项目数据。

## 已取得的真实证据

| 范围 | 实际结果 | 限制 |
| --- | --- | --- |
| TLS / 健康 / 版本 | 默认信任拒绝任务 CA，显式 CA 验证通过；两套 `/api/healthz` 通过并核对容器 CLI 版本 | 不是系统或浏览器信任验收 |
| OAuth / OIDC | 授权码 + PKCE S256，Discovery / JWKS，OpenSSL 验证 RS256，校验 issuer、audience、nonce、sub、有效期及适用 azp；UserInfo sub 与签名 ID Token 一致 | 测试客户端执行校验，不代表 RadishForge 服务已实现 |
| 负向授权码 | 重放授权码和错误 verifier 均拒绝 | 其他完整回调 / 刷新 / 过期矩阵待补 |
| 普通用户私有资源 | Alice 非管理员创建私有仓库并读取，Bob 的同仓库读取 / 写入被拒绝 | 仅本批隔离账号与资源 |
| Issue API | Alice OAuth 创建、评论、关闭并回读一致；只读 OAuth scope 写入被拒绝 | 编辑其他字段、分页 / PR 排除、标签 / 负责人 / 里程碑、超时并发待补 |
| 资源撤权 | Bob 被授予协作者权限后可读；移除后原 OAuth Token 的读 / 写均拒绝 | 后台作业和正在执行任务未实现 |
| OAuth 授权删除 | 删除 Alice 的测试 OAuth 应用后，原 Token 请求为 401 | 未等同其他撤销方式、刷新 Token 或全局登出 |
| 同邮箱不同 issuer | 两套已签名身份 email 相同，issuer 不同；即使 sub 同为 `2`，身份键仍不同 | 未实现产品账号绑定 / 合并逻辑，不能外推已验收不自动合并 |

两个实例当前使用 localhost 不同端口，协议客户端按 origin 使用独立 CookieJar；尚未验证同一真实浏览器中的并行会话 / cookie 域行为。后续浏览器验收须独立设计地址与 cookie 范围，不能用本批客户端模拟结果代替。

最终探针包含 17 条命名记录，其中包括环境、fixture 与流程完成标记，并非 17 项产品验收。流程完整运行，发现下列三个 scope 差异，退出码为 2；未将缺口改为成功、跳过或丢弃。

## scope 差异与可用变体

| 请求 scope | 实际行为 | 结论 |
| --- | --- | --- |
| `openid public-only email profile` | 可取得并验证含 email 的 ID Token，但 UserInfo 为 403 | 不能仅凭滚动文档将此组合声明为完整 UserInfo 路径可用 |
| `openid public-only email profile read:user` | UserInfo 200；同一用户私有仓库访问为 403 | 已验证的显式配置变体，仅限当前组合 / 用例，保留原组合差异 |
| `openid email profile` | 能读取同一普通用户私有仓库，HTTP 200 | 这些 scope 不能被当成“只有登录身份权限” |
| `openid m0-unknown-scope` | 授权成功，能读取私有仓库，HTTP 200 | 未知 scope 没有按期望拒绝，存在宽授权回落；不能声明 scope 安全等价兼容 |

后续处理方向：自有客户端固定并校验已验证的 scope 白名单，身份与资源客户端分离；禁止将未知输入直传上游，也不能把默认 OIDC scope 视为资源权限隔离。M0-S04 需根据这些事实形成明确的 Gitea profile / 差异决定，再冻结支持范围。这里没有擅自实现账号绑定、对外 Token 方案或全量兼容入口，也没有用管理员权限补足缺口。

## 调试问题与修正

开发阶段曾出现工具形参命名冲突、种子卷先 chown 后 chmod 导致权限拒绝、只连接 internal 网络时端口未发布、本地证书缺 AKI，以及受保护 `/api/v1/version` 不能作匿名就绪检查。分别修正参数、权限顺序、添加任务 frontend 网络、补齐 SKI / AKI、改用公开健康端点并独立核对 CLI 版本；未增加 privileged、开放数据库端口、修改系统信任或关闭 TLS 校验。修正期间的一个局部变量作用域错误也已消除，最终从空隔离卷完成 prepare / up / 协议流程。

探针初版预期 Issue PATCH 返回 200，实测为 201；先回读确认已关闭，再核对固定提交 OpenAPI 的 `issueEditIssue` 明确声明 201 后修正客户端预期。不是为通过而随意放宽状态码。原 UserInfo 403 作为真实差异保留，另加显式 `read:user` 变体验证，没有冒充原组合成功。

## 验证与清理

| 检查 | 实际结果与边界 |
| --- | --- |
| `python3 scripts/check-repo.py`、`git diff --check` | 通过；仅本地治理、格式 / 链接 / JSON 与空白，不代表三项 scope 差异已解决 |
| `python3 -B -m unittest discover -s scripts/tests -v` | 既有 8 项治理回归通过，未修改检查器或断言制造通过 |
| Compose schema 与配置边界核对 | `config` 通过；服务集合仅 postgres / forge / idp / seed，原生 arm64、回环端口、数据库 internal、无 socket / privileged / host network |
| Python AST、`sh -n` | 两个 Python 工具语法与 PostgreSQL 初始化脚本语法通过；不冒充单元 / 产品验收 |
| 从空任务卷执行 prepare / up / 协议流程 | 就绪成功；流程完整运行，17 条命名记录，三项 scope 差异，退出码 2；差异仍是未通过结果 |
| 证据完整性与秘密复核 | 工具 / 配置 SHA-256 与实际执行结果一致；轨迹仅 origin / method / 无参数 path / status，凭据和 JWT 未导出；本任务 Python 缓存已清理 |
| Git 与交付清单 | 新增 7 个文件、更新 13 个文件，无删除；暂存区为空，所有改动属于本批，未提交 / 推送 |

已执行任务专属 cleanup，并读回确认最终项目容器、网络、卷均为 0，`.local/m0` 凭据 / CA 私钥已删除。没有停止 OrbStack，没有清理既有 20 个卷或其他项目缓存；本轮固定镜像保留在共享下载缓存，没有全局 prune。当前无本任务后台资源或端口待交接。

M0-01 保持进行中，M0-02 / M0-03 的部分真实证据已建立；BASE-01、IAM-01 / IAM-02、COMP-01 均未整项关闭。Actions / Runner、OCI、Release、完整产品 UI / 会话 / 绑定、刷新与后台授权、安装恢复和生产仍未验证。
