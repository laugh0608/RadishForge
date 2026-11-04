# ADR 0003：Gitea 受控授权组合与在线复核

日期：2026-11-01。状态：已接受，范围为 M0 的 Gitea 28.2.0 受控客户端配置与后续实现契约；不表示 M1 会话 / 绑定已实现或 IAM 全项通过。用户已明确要求处理 scope 差异、收敛白名单与授权配置，继续身份 / 权限验证。

## 原因与证据

[首轮真实结果](../records/2026-11-01-m0-local-validation.md)表明：普通 OIDC scope 与未知 scope 可能获得私有资源访问；`openid public-only email profile` 的 ID Token 可验证但 UserInfo 为 403；加入显式 `read:user` 后 UserInfo 200 且私有仓库 403。OIDC 登录与资源授权不能共用一个不受约束的 scope 输入。

这些是原始上游行为，不通过改状态、隐藏接口或扩大管理员授权消除。后续 M0 验证与生命周期证据见[授权组合记录](../records/2026-11-01-m0-auth-profile-validation.md)。

## 决定

1. 以[授权组合 JSON](../../tests/contracts/m0/gitea-auth-profile.json)为 M0 单一配置来源，区分 `identity`、`resource_read`、`issue_write` 三种用途。每种用途固定完整 scope 集合、issuer、独立客户端；拒绝未知用途、未知 / 额外 / 重复 / 空 scope、缺失限制项、跨用途组合和错误 issuer，不从子集或空值回退到默认 OIDC scope。
2. 登录组合保留 `public-only` 并显式加入 `read:user`；资源组合按已验证的用户 / 仓库 / Issue 路由组申请权限。完整字符串从 JSON 读取，不能把两个组合求并集或把资源 Token 当作登录绑定证明。
3. 服务端客户端按 confidential client 注册，使用授权码 + PKCE S256；保留用户首次同意，不跳过 secondary authorization。回读登记的类型、回调和同意设置，核对 Token introspection 的实际 scope 以及当前用户 ID。Client secret 只在后端 / 测试进程内存使用，不进入浏览器、命令参数或正式报告。
4. 配置 `INVALIDATE_REFRESH_TOKENS=true` 并验证轮换 / 重放拒绝。JSON 中的 30 秒 access token、1 小时 refresh token 和关闭默认应用仅用于本轮隔离测试，不能作为生产 TTL 或既有共享实例的升级操作。
5. 新授权和刷新后的凭据都须在线确认账号有效，并保持真实上游用户权限。刷新成功、签名有效、introspection active 或 scope 匹配均不单独证明当前账号 / 私有资源仍可用；拒绝或无法核实的结果不能进入可用会话 / 资源操作。
6. Scope / issuer 校验在创建应用、授权请求或刷新请求前完成；刷新不接受临时增加 scope。改变用途走新的显式授权，不利用刷新扩权。

`write:issue` 是 Gitea 路由组权限，可能包含修改 / 删除等超出本轮三个 Issue 操作的能力；`read:repository` 也不是单个页面权限。它们仍受用户对象权限约束，不能宣传为逐按钮授权。后续产品必须只暴露承诺操作并如实展示上游授权范围，不申请本批不需要的 admin / package / write:repository 权限。

## 三项差异的处理边界

| 原始差异 | 本批处理 | 不能外推的结论 |
| --- | --- | --- |
| public-only 登录组合 UserInfo 403 | 使用已验证的显式 `read:user` 组合并检查私有资源仍拒绝 | 不是所有 IdP 都需要 Gitea scope，也不是原组合已修复 |
| 默认 OIDC scope 有宽资源访问 | 只允许完整身份组合，登录 / 资源注册与凭据分开 | 不证明任意 Gitea OAuth 应用都受限 |
| 未知 scope 宽授权回落 | 受控客户端联网前拒绝；授权后核对实际 scope | 上游仍可能接受直接构造的请求，不能宣传为原生安全等价兼容 |

本批 Python 白名单和在线复核用于 M0 真实验证；M1 Go 服务仍须实现同等边界并重新验收。原始发现模式显式保留，不能用受控组合通过替换其差异结果。

## 替代方案与复核条件

- 继续直接拼接任意 scope：无法阻止缺少限制项或未知值触发宽授权，因此不采用。
- 只限制单个 scope 名称：所有名字合法但组合缺少 `public-only` 仍可能过宽，因此采用完整用途组合校验。
- 用同一应用 / Token 处理登录和 Issue：同意、撤销、生命周期和权限边界混合，因此分开注册与测试。
- 为这三项差异修改 Gitea 核心或更换底座：当前公开接口与受控配置已有可验证切片，暂不扩大为补丁或迁移；不能强制关键账号 / 资源边界时再决定。

上游版本、scope 语义、客户端类型、支持操作或配置改变时重跑相应契约；权限 / 刷新 / 过期的新差异须保留证据并单独处置，不以本 ADR 提前关闭阶段出口。官方参考：[Gitea OAuth2](https://docs.gitea.com/development/oauth2-provider/)、[OAuth2 配置](https://docs.gitea.com/administration/config-cheat-sheet/#oauth2-oauth2)、[RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html)。

## 2026-11-04 生命周期补充决定

本节延续同一精确版本、公开协议和零核心补丁边界；[本批证据](../records/2026-11-04-m0-lifecycle-validation.md)分别保留旧配置复现和受控配置结果，不改写 11 月 1 日的差异。

1. 受控组合要求 `[security] DISABLE_QUERY_AUTH_TOKEN=true`，由授权 JSON 的 `test_security_settings` 单一维护；`up` 回读两套实例的相关配置、短 TTL、轮换及 Actions 关闭状态。通用 OAuth 中间件会从表单读取 `token`，与 introspection 的目标 Token 参数重名；原配置下目标凭据的账号 / 过期状态可在 introspection 处理器之前被处理。禁用表单 / 查询串资源鉴权后，introspection 仍按协议从正文读取待查询 Token，并以独立客户端凭据认证调用者；资源 API 使用 Bearer Header。
2. 旧配置的禁用账号 introspection 为 HTTP 200 HTML，最终路径没有变化；不再把“发生了登录重定向”作为其原因。受控配置下可取得对象 metadata，但禁用账号仍可能刷新成功、introspection active；必须再用该凭据在线读取 `/api/v1/user`，账号被拒绝即停止。恢复上游账号会重新启用原 grant，不能据此恢复已终止的本地授权或会话。
3. 受控配置下，过期 / 无效 / 不属于调用客户端的 Token 返回 `200 active:false`；错误 client secret 返回 401。历史过期 Token 的 401 保留为原配置差异。运行时孤立的 401 不足以推断具体原因，记录为原因未归属的拒绝；不能重试密钥或默认判为 inactive 成功。网络 / 超时为结果未知，非对象、非布尔 active、缺失或不匹配的主体 / scope 为无效响应；这些结果均不建立可用授权。
4. 同一授权的并发刷新须在 M1 按授权记录串行化；不能依赖一次并发样例证明所有调度均正确。刷新写入超时或响应丢失时不重放旧 Token，不因失败再并发请求；先停止该授权的依赖操作并走明确的恢复 / 重新授权流程。M0 保留实际竞争、后继凭据资源权限及旧值重放结果，真实等待刷新 Token 到期，不改系统时钟。
5. 单用户撤销同意、删除整个 OAuth 应用、撤销仓库权限和工作台解绑是不同操作。本版本固定 OpenAPI 未提供单用户 grant 撤销 REST 接口，实际 Discovery 未公布 `revocation_endpoint`；M0 通过原生设置页的真实用户操作取证，不把其私有页面请求封装成产品 API。M1 解绑的本地后续授权停止与凭据处理沿用现有设计；目前上游单用户撤销只有原生 UI 路径证据，不能承诺自动远端撤销。若要将其列为自动功能，须在 M0-S04 另行确认公开接口方案 / 范围；未收到真实结果不能宣称远端撤销成功，也不删除共享客户端来代替。

旧配置诊断必须显式使用 `prepare --auth-profile --legacy-query-auth` 和 `--mode lifecycle-baseline`，不能作为受控组合默认值。该开关仅用于本任务隔离实例的历史行为复现，不授权变更共享或生产配置。原始三项 scope 差异与禁用账号仍可刷新继续保留为上游差异；上述决定不等于 Gitea 原生行为已修复，也不代表 M1 或完整 IAM 验收通过。

原因定位依据固定提交的 [OAuth 中间件](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/auth/oauth2.go)、[Web 鉴权与路由](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/web.go)、[OAuth 处理器](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/auth/oauth2_provider.go)，以及 [RFC 7662](https://www.rfc-editor.org/rfc/rfc7662.html#section-2.2)；实际行为和来源摘要以本批记录为准。

## 2026-11-04 Release 用途补充

按用户授权的 Release 隔离取证，新增第四种 `release_write` 组合：`openid read:user write:repository`；原三种组合、issuer、客户端约束及安全 / TTL 设置逐项核对未变。新用途在独立 confidential client 下完成同意、grant scope / 在线账号复核及按阶段显式刷新，再验证实际 Release 单元角色、资源撤权与错误用途拒绝。它是仓库写 scope，不是仅 Release 按钮权限，也不授权 package / OCI 或任意第三方应用；具体边界与五项差异见[ADR 0005](0005-release-authorization-and-reconciliation.md)和[Release 记录](../records/2026-11-04-m0-release-validation.md)。前三种用途的历史结论保留，不能将新增用途回写成过去已验证。
