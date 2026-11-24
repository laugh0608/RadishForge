# 2026-11-09 M0-S04 单用户 OAuth grant 撤销核查

范围为 M0-04 的 M0-G06，关联 IAM-02。以 `dev` 的 `4d3468d` 和 [11 月 4 日生命周期结果](2026-11-04-m0-lifecycle-results.json)为输入。本批静态核查固定接口与源码。真实证据来自此前 Linux arm64 隔离批次的 Gitea 28.2.0-rootless、合成普通用户、独立资源与身份实例、任务 CA、header-only 资源鉴权及 30 秒 access token。 [原批环境与验证边界](2026-11-04-m0-lifecycle-validation.md)

官方 [v28.2.0 标注 Tag](https://api.github.com/repos/go-gitea/gitea/git/tags/1dc1ecdddcdc60ab14ec14e30e7bb4d84242f21f)解引用到 `829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1`。读取该提交官方树与 23 个相关文件，逐项核对 Git blob ID。[固定 OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json)有 342 个路径，SHA-256 为 `c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`，与原批一致。

## 原生设置页与失效范围

- **已有实测。** 普通用户 bob 在 Settings → Applications → Authorized OAuth2 Applications 对共享应用执行 Revoke。探针在确认前刚刷新凭据；整个取证窗口约 0.931 秒，观察到旧 access token 访问 401、Issue 写入拒绝、refresh 400、introspection `active:false`。同应用的 alice、bob 的另一应用和独立身份发行方的对照授权仍有效，共享应用仍可读回。bob 显式重新同意后取得新授权，旧 refresh token 仍拒绝。该时间是单批取证数据。 [原批记录](2026-11-04-m0-lifecycle-validation.md#新负例与资源结果)
- **固定源码。** 页面列出当前登录用户的 grants；Revoke 按 grant ID 载入记录，检查记录归属当前用户，再按 grant ID 与用户 ID 删除，并记录审计事件。应用登记保留。固定提交的上游集成测试还断言其他登录用户请求撤销目标 grant 得到 404，目标记录仍在。本批只读该测试源码。 [页面模板](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/user/settings/grants_oauth2.tmpl#L9-L25) · [撤销处理器](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/user/setting/oauth2_common.go#L195-L224) · [按用户删除 grant](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/models/auth/oauth2.go#L622-L626) · [上游跨用户测试](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/tests/integration/user_settings_oauth2_grant_test.go#L17-L27)
- **凭据链。** API access token 鉴权、refresh、introspection 和授权码兑换各自查询关联 grant。源码预期撤销后发起的新请求无法使用旧 grant，仍须实测尚未兑换的授权码及已进入处理器的并发请求。独立 IdP 登录会话、已经建立的产品会话和已经提交的外部操作各有生命周期。 [API 认证](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/auth/oauth2.go#L28-L58) · [refresh](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/auth/oauth2_provider.go#L563-L628) · [授权码查询](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/models/auth/oauth2.go#L485-L500)

## 公开接口排查

| 公开面 | 固定版核查结论 |
| --- | --- |
| Discovery 与 OAuth 路由 | 此前资源 / IdP 两套实例均公布 introspection，均缺少 `revocation_endpoint`。固定 Discovery 生成器及 OAuth 路由也无对应撤销入口。Introspection 查询当前目标 Token；`active:false` 可能来自过期、无效、grant 缺失或客户端不匹配。 [Discovery](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/auth/oauth2_wellknown.go#L25-L67) · [OAuth 路由](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/web.go#L609-L623) · [introspection 处理器](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/auth/oauth2_provider.go#L144-L197) |
| `DELETE /api/v1/token` 和 `DELETE /api/v1/users/{username}/tokens/{token}` | 前者按当前请求的 Bearer 值查询 PAT 并删除对应记录，后者按用户和 PAT 标识删除。两个处理器均不撤销 OAuth grant。 [当前 PAT 处理器](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/v1/token/token.go#L54-L88) · [指定 PAT 删除](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/v1/user/app.go#L166-L232) |
| `/api/v1/user/applications/oauth2` 与 `/{id}` | 管理 OAuth 应用登记，删除入口会删除整个共享应用及其 grants。未发现按单用户 grant 撤销的 REST 操作。原生设置页有独立的已登录用户操作，属于页面契约。 [应用删除 API](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/v1/user/app.go#L321-L362) · [原生设置路由](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/web.go#L671-L687) |

固定版公开接口自动撤销缺口保留。未来的 RFC 7009 端点仍须验证其撤销粒度和关联凭据行为，该协议允许对已无效的 Token 返回 HTTP 200。产品侧设计与定向验收分别见 [ADR 0003 撤销边界](../adr/0003-gitea-authorization-profiles.md#2026-11-09-单用户-grant-撤销边界)和 [M0-S04 补证条件](../planning/m0-validation.md#单用户-grant-撤销补证条件)。 [RFC 7009](https://www.rfc-editor.org/rfc/rfc7009.html#section-2.2)

本批只做静态核查与文档同步，未启动隔离实例或运行上游测试，原始证据与 27 条差异基线保留。
