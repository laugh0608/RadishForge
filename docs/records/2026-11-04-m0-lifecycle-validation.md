# 2026-11-04 M0-S02 生命周期边界与负例验证

状态：本批生命周期切片已交付并完成验证；两项历史差异已定位并形成受控处理，禁用账号仍可刷新继续保留为上游差异。四批流程均完成并退出 2，不关闭整个 M0-02 / IAM 或 M0 阶段出口。脱敏结果与源码 / 配置摘要见[结果 JSON](2026-11-04-m0-lifecycle-results.json)。

## 范围与环境

归属：TOP-IAM，M0-S02 / M0-02，IAM-01 / IAM-02 的上游协议与授权部分。用户明确要求收口两项生命周期差异、补刷新和撤销负例并同步文档；Runner 持续暂停，不进入 M1。未扩大到业务实现、Issue 新功能、依赖安装、Git 提交 / 推送、远端写入或发布。

起点为 `dev` 的 `2d10a65`，工作树 / 暂存区干净，本地缓存的 `origin/dev` 同 SHA；没有 fetch，不推断服务端实时状态。沿用已有 OrbStack context `orbstack`，Engine 29.8.2 / Compose 5.5.0、原生 Linux arm64、Python 3.14.5，以及原 Gitea 28.2.0-rootless / PostgreSQL 18.6-bookworm 的固定 Digest。镜像已在共享缓存中，没有重新拉取、升级宿主或修改全局 context。

先执行旧配置复现与受控生命周期，再以最终源码执行受控组合和旧配置诊断。仍为 PostgreSQL + 资源 Gitea + 独立测试 IdP，仅发布回环 18443 / 19443，合计 2.75 GiB 内存限额；各批串行清理后重建，无 Runner、socket、privileged 或生产数据。长时验证前已说明约 70–90 分钟窗口及 cleanup，真实等待一小时，不修改系统时钟。

| 批次 | 项目 | 命名记录 / gap / 退出码 |
| --- | --- | --- |
| 初始旧配置复现 | `rf-m0-local-d9f32888` | 7 / 2 / 2 |
| 受控生命周期 | `rf-m0-local-21f2d445` | 15 / 1 / 2 |
| 最终源码 `profiles` 回归 | `rf-m0-local-a3fa0d3b` | 20 / 1 / 2 |
| 最终源码 `lifecycle-baseline` 回归 | `rf-m0-local-ba2ee998` | 8 / 2 / 2 |

命名记录包含 fixture、等待和完成标记，不据数量计算产品通过率。受控两批只保留禁用账号仍可刷新的 gap；旧配置两批保留原始两项差异。

## 差异定位与处理

| 边界 | 旧配置新批次复现 | 受控配置结果与处理 |
| --- | --- | --- |
| 禁用账号刷新 | refresh 200；资源 403；introspection 200、正文 `str`，最终路径仍为 `/login/oauth/introspect` | 开启 `[security] DISABLE_QUERY_AUTH_TOKEN=true` 后 introspection 返回对象；refresh 仍 200，在线 `/api/v1/user` 403，凭据复核拒绝。保留上游签发差异，不把 active metadata 或刷新成功当成账号有效 |
| 过期 access token introspection | 正确客户端查询过期 Token 401；同一客户端查询新 Token 200 active；错误 secret 也可能 401 | 受控配置下过期 / 无效 / 其他客户端目标 Token 为 `200 active:false`，错误 secret 401、新 Token 200 active。原因未归属的单独 401 仍拒绝，不自动改写为 inactive 或盲重试 |

固定提交源码显示，通用 OAuth 鉴权会调用 `ParseForm` 并读取 `token`，与 introspection 正文目标参数同名；Web 鉴权在进入目标处理器前处理失效凭据或禁用用户，后者可直接返回 HTTP 200 HTML。新轨迹的最终路径排除了“本批 HTML 是跟随登录重定向得到”的解释。配置对照改变的是本任务新实例的资源 Token 鉴权入口，introspection 本身继续读取协议正文；没有修补 Gitea 核心、关闭 TLS 或放宽返回断言。

配置单一来源升级为授权 JSON schema 2，加入 `test_security_settings`，三种 scope 组合不变。`m0_oauth.py` 提取既有共享协议 / 凭据复核，API 不跟随重定向，轨迹仅增加 Content-Type、正文类型及无参数最终路径；浏览器同意流程仍使用独立会话。`m0_lifecycle.py` 复用这些实现，没有产品会话或 Token 库。现行决定见[ADR 0003](../adr/0003-gitea-authorization-profiles.md#2026-11-04-生命周期补充决定)。

## 新负例与资源结果

| 用例 | 实际结果 |
| --- | --- |
| 禁用 / 恢复账号 | 禁用后的新凭据资源拒绝且本地复核拒绝；恢复账号后原 grant 又可使用。不能用上游恢复自动恢复已终止的本地授权 |
| 无效 / 其他客户端 Token / 错误客户端 secret | 无效与其他客户端目标 Token 为 inactive；错误 secret 为 401；正确凭据新 Token active，分别保留对照 |
| 两个同时刷新的请求 | 状态分别为 400 / 200；仅成功后继能继续刷新，旧值重放拒绝；后继私有读取 200、Issue 写入 403。只证明本次调度，不外推所有并发 |
| 单用户撤销同意 | 原生设置页中以普通用户 bob 撤销共享应用 grant；刚刷新凭据约 0.931 秒内 access 401、refresh 400、introspection inactive，排除普通 30 秒到期混淆 |
| 撤销范围隔离 | 同一应用的 alice、bob 的其他应用和独立身份发行方仍可刷新并通过账号复核；共享应用仍存在，没有删除应用代替撤销 |
| 撤销后显式重新同意 | 新授权可读原私有资源，已撤销 grant 的旧 refresh token 仍拒绝 |
| refresh token 自身到期 | 保持原凭据未使用，实际等待 3602.849 秒后刷新 400；有效控制凭据可刷新，同一原客户端重新授权有效，旧 refresh token 仍拒绝，旧 access token 401 |

单用户撤销通过真实浏览器登录 → Applications → 目标应用 Revoke → 确认完成。探针在确认前刷新凭据，再由 API 检查失效及其他 grant 的存活；文件标记只协调时点，不能替代真实撤销结果。已检查原生页面成功提示和目标条目消失，不宣称 RadishForge UI、窄屏或完整 UI-01 已验收。

固定 OpenAPI SHA-256 仍为 `c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`，342 个路径中 OAuth 相关只有 `/user/applications/oauth2` 及 `/{id}`，没有单用户 grant 撤销操作。两套实例实际 Discovery 均未公布 `revocation_endpoint`，固定路由源码只见原生设置页 grant 撤销。M0 通过原生 UI 取证，不将私有页面请求作为产品接口，不据此承诺自动远端撤销；自动化方案 / 范围留待 M0-S04 确认。工作台本地解绑、上游撤销和删除共享应用必须分别建模；产品会话、加密存储和后台任务停止仍在 M1。

## 验证与证据限制

- `python3 -B -m unittest discover -s scripts/tests -v` 在最终源码下 25 项通过：8 项治理、6 项 scope、7 项凭据边界和 4 项环境边界。覆盖 HTML / 非对象 metadata、非布尔 active、主体不符、账号拒绝、401 原因未归属、网络未知、解析失败和不重试，以及配置漂移、错误脱敏、协调标记归属和网络残留保留归属标记。不是产品测试或真实故障注入证据。
- 四批真实流程均完成，逐批保留 gap 和退出 2；真实到期、并发 / 后继权限、原生单用户撤销与范围隔离已取得证据，不能把受控拒绝有效改写成上游无差异。
- 已回读两套受控实例的 header-only 设置、30 秒 access token / 1 小时 refresh token、轮换和 Actions 关闭；正式导出只保留白名单配置与摘要，不保留 app.ini 正文。
- 提取共享模块后，以最终源码在新批次回归原 `profiles` 与显式旧配置诊断；身份 / 资源 scope 隔离、拒绝同意、client secret、callback、刷新绑定 / 不扩权 / 轮换 / 重放、仓库撤权、应用删除与真实 access token 到期均保持原边界。受控最终批次直接记录 disabled introspection active，但账号 403 / 本地拒绝；旧配置仍复现 200 HTML 和过期查询 401。
- 长时探针启动后补充了本地输入类型收紧、配置回读、操作协调、证据字段及计时边界保护。长时进程载入版本依据本轮明确的两处输入类型补丁重建快照摘要，后续修改未回写该快照；与最终源码摘要分别保存，结果 JSON 附有从最终源码重建该版本的补丁，不能将最终文件哈希冒充早先已加载进程的源码。最终源码已完成本地及两批真实回归，其摘要与冻结清单一致。
- 后续提交时，暂存区空白检查发现新模块 `m0_oauth.py` 末尾多一行空行，仅删除该空行，Python AST 校验一致并复跑 25 项本地测试。原始联调摘要不回写；JSON 的 `post_validation_format_cleanup` 单独保存格式调整前后摘要与恢复补丁。重建载入版本时先恢复联调格式，再应用快照补丁；没有因纯格式清理重跑一小时取证。

本轮浏览器使用已有 Playwright 工具缓存和本机 Chrome，没有安装第三方依赖。CLI 在沙盒内因缓存目录 EPERM / Chrome SIGABRT 失败；将任务缓存移入 `/private/tmp` 并为任务专用 Chrome 申请最小沙盒外启动后继续。浏览器 profile 位于本批私密目录，仅进程内精确信任本批服务器证书 SPKI，`ignoreHTTPSErrors=false`，不改系统信任。首次仅配置 CA SPKI 未获浏览器接受，改为服务证书 SPKI 后正常；未使用通用忽略证书错误开关。登录密码只由本地脚本在内存读取，没有进入 CLI 参数、截图或正式证据。

已有工具版本为 `@playwright/cli 0.1.22`、`playwright 1.64.0-alpha-1790635538000`（均 Apache-2.0，来源分别为 [playwright-cli](https://github.com/microsoft/playwright-cli)、[playwright](https://github.com/microsoft/playwright)），本机 Chrome 为 `156.0.8078.80`。它们仅用于本次原生页面取证，没有引入仓库依赖、lockfile 或产品工具链承诺；没有复制第三方源码进入交付。

原始 scope 差异、完整浏览器 Cookie / CSRF、其他 IdP、其他版本、产品解绑与后台任务取消、Actions / OCI / Release、amd64 与生产仍不由本批关闭。完整 M0 出口和 IAM 产品验收保持原标准。

## 清理与接续

四批均先导出脱敏结果再 cleanup，最终按各项目标签读回容器 / 网络 / 卷均为 0，`.local/m0` 已移除；本任务浏览器已关闭，私密 profile / 凭据 / 证书随运行目录清理。收尾 `ps` 枚举被沙盒 EPERM 拒绝，改用已知专用进程 PID 的存活检查和显式会话关闭回执，未扩大查询权限或停止其他进程。三处任务专用临时工具 / 来源 / CLI 缓存目录已核对内容后移除，共享镜像和原有 npm 工具缓存保留，不触碰其他项目资源。验证结束及结果导出时尚未提交或推送；后续本地提交见[current](../status/current.md)与 Git 历史，JSON 保留运行时快照。

下一步将受控处理及公开单用户撤销接口缺口纳入 M0-S04 的既有差异基线；身份关键边界已有处理结论，下批可继续 M0-S03 的 Issue 列表 / 分页、编辑 / 重开、关联对象与失败边界。Runner 暂停，M1 不启动；本批没有顺带扩展 Issue 或工作台实现。任务状态只维护于 [tasks](../planning/tasks.md)。

来源定位：[OAuth 中间件](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/auth/oauth2.go)、[Web 鉴权与路由](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/web.go)、[OAuth 处理器](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/auth/oauth2_provider.go)、[配置解析](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/modules/setting/security.go)、[固定 OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json)、[RFC 7662](https://www.rfc-editor.org/rfc/rfc7662.html#section-2.2)。
