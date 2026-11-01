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
