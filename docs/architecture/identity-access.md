# OIDC、账号绑定与访问控制

状态：产品设计；OIDC 是首版要求。已取得[本机 Gitea 上游协议与权限部分证据](../records/2026-11-01-m0-local-validation.md)，自有会话 / 绑定尚未实现。外部身份认证与 Gitea API 授权分别建模。

## 登录流程

工作台 → Go 创建登录事务 → 标准 OIDC 发行方授权码流程 → Go 校验并换取 Token → 创建服务端会话 → 浏览器获得 HttpOnly 会话 Cookie。

使用 Authorization Code + PKCE S256，校验 state、nonce、签名、issuer、audience、过期时间和必要 azp，回调严格匹配登记地址。Discovery 和 JWKS 只面向管理员登记的 HTTPS issuer，处理密钥轮换并限制外部取址，开发环回地址单独约定。

Radish OIDC 是首个家族联测对象，但不成为部署硬依赖。没有外部 IdP 的独立安装可评估以 Gitea 的 OIDC 能力提供登录；M0 验证精确版本，不把普通 OAuth 身份响应当作已完成标准 OIDC 验收。默认不再建立一套工作台密码库。

## 上游资源授权

OIDC 登录成功只建立工作台身份。访问私有仓库之前，用户还须完成 Gitea OAuth 授权；首次绑定要求当前工作台会话和目标 Gitea 账号共同确认。键使用底座实例 + 上游用户 ID，禁止按用户名或同邮箱静默合并。

默认使用用户 Token 调用 Issue、仓库与 Release API。具体 Scope 必须根据精确版本验证；不能假定 `openid email profile` 天然只有身份权限。若部署版本只能提供较宽授权，必须明确展示范围并记录取舍，不能使用管理员 Token 隐藏缺口。

2026-11-01 的 Gitea 28.2.0 本机验证确认：`openid email profile` 及带未知 scope 的样例均可读私有仓库；`openid public-only email profile` 的签名 ID Token 有效但 UserInfo 为 403，增加显式 `read:user` 后 UserInfo 200 且私有仓库仍为 403。此为当前组合的配置差异，不是所有 OIDC 发行方规则。M0-S02 已形成下述受控组合与白名单；M0-S04 仍须汇总兼容范围和缺口决定，不能把宽授权回落宣传为兼容通过。

### Gitea 受控授权组合

[ADR 0003](../adr/0003-gitea-authorization-profiles.md)记录本批决定，[JSON](../../tests/contracts/m0/gitea-auth-profile.json)承载 M0 单一配置；实际结果见[授权组合验证](../records/2026-11-01-m0-auth-profile-validation.md)。三种用途分别注册 confidential client，以授权码 + PKCE S256、精确 callback 和首次用户同意执行；不同用途不共用凭据。

| 用途 | 本批能力与限制 |
| --- | --- |
| `identity` | 显式 public-only / read:user 组合，取得 UserInfo，私有仓库 / Issue 拒绝；不作为 Gitea 资源授权 |
| `resource_read` | 当前用户仓库与 Issue 读取，Issue 写入拒绝 |
| `issue_write` | 当前用户仓库读取与 Issue 路由组写入，不能创建仓库；仍需对象权限 |

校验完整组合而非仅校验单个名称：缺少 public-only 的合法名称组合也必须拒绝；创建应用、授权和刷新前均拒绝未知 / 缺失 / 额外 / 重复 scope 或错误 issuer。授权后核对实际 grant scope、签名身份和在线账号；刷新成功或 introspection HTTP 200 不代表凭据可用，缺失 / 非对象 / inactive 元数据、账号不符、拒绝或无法核实均停止。资源访问继续按实际上游对象权限判断，刷新不得恢复已撤销权限。

该边界目前在 M0 验证工具落地，尚未进入 M1 Go 服务；不能据此声称产品已阻止任意客户端构造宽 scope 请求，或把上游差异改成原生兼容成功。30 秒 Token 等参数仅用于隔离生命周期测试，正式会话 / Token 生命周期另定。

Token 仅在服务端加密保存，密钥独立于数据库、可轮换和备份。处理过期、刷新竞争、撤销、解绑、上游禁用账号与密钥丢失；解绑终止可撤销的后续作业授权，不改变已完成历史。

## 权限模型

| 领域 | 判定方式 |
| --- | --- |
| 仓库 / Issue / PR | 用户在 Gitea 的实际资源权限；工作台角色不能扩大 |
| 镜像 | 用户 / 组织包权限单独检查，不从关联仓库权限推导 |
| 发布 | 仓库发布权限 + 工作台项目发布权限 |
| 部署 | 当前用户项目 / 环境部署权限 + 受限执行身份 |
| 平台配置 | 管理员角色；不能自动获得所有客户仓库内容 |
| 后台同步 | 明确范围的机器人授权，审计其来源及撤销 |

包与仓库关联不改变包权限。首版以组织作为制品隔离边界，需要项目间严格隔离时分组织或使用后续独立 Registry；验收直接 pull 的权限，不能只看网页隐藏。

排队到实际执行之间重新检查授权。生产 Runner 只消费已授权、固定清单和固定工作流的部署意图，不能接受普通 PR 任意指定目标、命令或秘密。用户失权时新操作拒绝，正在运行的外部任务记录已发生副作用与可取消范围。

## 会话和失败行为

Cookie 采用 Secure、HttpOnly、适当 SameSite；登录后轮换会话 ID，写请求防 CSRF，配置合理空闲与绝对过期时间。工作台登出和 IdP / Gitea 全局登出是不同动作，界面准确说明。

发行方不可用、Token 无效、权限不可核实分别显示；私有数据默认拒绝。测试跨用户资源猜测、同邮箱不同 issuer、重放回调、错误 audience、权限撤销和后台机器人越权。
