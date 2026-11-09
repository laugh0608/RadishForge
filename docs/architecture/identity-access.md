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

[ADR 0003](../adr/0003-gitea-authorization-profiles.md)记录受控组合与生命周期决定，[JSON](../../tests/contracts/m0/gitea-auth-profile.json)承载 M0 OAuth 单一配置。11 月 1 日的[授权组合验证](../records/2026-11-01-m0-auth-profile-validation.md)覆盖最初三种用途；11 月 4 日的[Release 切片](../records/2026-11-04-m0-release-validation.md)增加第四种独立用途，原三种组合保持不变。四种用途分别注册 confidential client，以授权码 + PKCE S256、精确 callback 和首次用户同意执行；不同用途不共用凭据。

| 用途 | 本批能力与限制 |
| --- | --- |
| `identity` | 显式 public-only / read:user 组合，取得 UserInfo，私有仓库 / Issue 拒绝；不作为 Gitea 资源授权 |
| `resource_read` | 当前用户仓库与 Issue 读取，Issue 写入拒绝 |
| `issue_write` | 当前用户仓库读取与 Issue 路由组写入，不能创建仓库；仍需对象权限 |
| `release_write` | `openid read:user write:repository`，用于已验证的 Release / 附件操作；仓库写 scope 宽于 Release 按钮，仍需 Release 单元与对象权限，不授权 package / OCI |

Release 草稿的只读 scope 元数据与直接下载权限不一致；受控草稿操作要求独立 Release 用途与当前 Release 单元写权限，不能只凭列表可见性或下载 URL 推断授权。原始差异及未实现边界见[ADR 0005](../adr/0005-release-authorization-and-reconciliation.md)。

校验完整组合而非仅校验单个名称：缺少 public-only 的合法名称组合也必须拒绝；创建应用、授权和刷新前均拒绝未知 / 缺失 / 额外 / 重复 scope 或错误 issuer。授权后核对实际 grant scope、签名身份和在线账号；刷新成功或 introspection HTTP 200 不代表凭据可用，缺失 / 非对象 / inactive 元数据、账号不符、拒绝或无法核实均停止。资源访问继续按实际上游对象权限判断，刷新不得恢复已撤销权限。

该边界目前在 M0 验证工具落地，尚未进入 M1 Go 服务；不能据此声称产品已阻止任意客户端构造宽 scope 请求，或把上游差异改成原生兼容成功。30 秒 Token 等参数仅用于隔离生命周期测试，正式会话 / Token 生命周期另定。

2026-11-04 的[生命周期切片](../records/2026-11-04-m0-lifecycle-validation.md)进一步界定 introspection 的表单参数与通用鉴权冲突。受控配置显式关闭表单 / 查询串资源 Token 鉴权，回读实际设置；正确客户端查询过期目标 Token 与错误客户端凭据分别处理。禁用账号仍可能刷新并得到 active metadata，在线账号复核继续作为必要拒绝边界；401 原因不明、网络未知和响应结构错误不进入可用状态。具体决定、并发刷新和历史差异保留见[ADR 0003 生命周期补充](../adr/0003-gitea-authorization-profiles.md#2026-11-04-生命周期补充决定)。

Token 仅在服务端加密保存，密钥独立于数据库、可轮换和备份。处理过期、刷新竞争、撤销、解绑、上游禁用账号与密钥丢失；解绑终止可撤销的后续作业授权，不改变已完成历史。

刷新按同一授权记录串行化，超时或结果未知时暂停使用相关凭据，保留结果并对账。工作台分别报告产品侧停用与上游授权状态。资源授权停用后，拦截依赖它的新操作、刷新和待执行作业，丢弃晚到的旧授权结果，独立身份登录和其他授权保持原有范围。账号恢复也不会重新启用已停用的本地授权。产品侧行为在 M1 实现后验收。

Gitea 28.2.0 的单用户远端撤销由用户在原生授权应用设置页确认。工作台可引导用户前往经核实的入口。固定版公开 API 缺少该操作，PAT 删除、应用删除和 introspection 分别有独立语义。未核实的上游结果保留为未知，单个凭据拒绝只说明该凭据当前不可用。见 [ADR 0003 单用户撤销边界](../adr/0003-gitea-authorization-profiles.md#2026-11-09-单用户-grant-撤销边界)。

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

2026-11-04 的[OCI 切片](../records/2026-11-04-m0-oci-validation.md)使用独立的[Registry 契约](../../tests/contracts/m0/gitea-registry-profile.json)：普通用户 `read:package` / `write:package` PAT 经固定同源 `/v2/token` 交换 Registry Bearer，不复用 OAuth 凭据。私有组织非成员及只有仓库协作权的用户直接拉取被拒绝；组织成员的读取基线与 team package 写权限分别判断，缺少 package 单元不等于没有读取权。公开个人包关联私有仓库仍可读，Registry 的 pull 请求参数也不能收窄 write PAT，不能承诺逐仓库包隔离或仅凭 query 得到只读凭据。

团队降权、移出私有组织和禁用账号已对旧 Registry Token 的相应操作生效。删除 PAT 后新交换被拒绝，旧 Registry JWT 在观察时仍可读写。Gitea 28.2.0 的 Registry JWT 校验不回查签发 PAT，公开路径未提供单凭据即时撤销。其固定 24 小时有效期为签发声明，真实到期仍待补证。后续产品分别报告本地停用、PAT 删除及上游状态，远端失效窗口与首版要求待所有者确认，见 [ADR 0006 核查补充](../adr/0006-oci-authorization-and-digest-retention.md#2026-11-09-公开机制核查补充)。

排队到实际执行之间重新检查授权。生产 Runner 只消费已授权、固定清单和固定工作流的部署意图，不能接受普通 PR 任意指定目标、命令或秘密。用户失权时新操作拒绝，正在运行的外部任务记录已发生副作用与可取消范围。

## 会话和失败行为

Cookie 采用 Secure、HttpOnly、适当 SameSite；登录后轮换会话 ID，写请求防 CSRF，配置合理空闲与绝对过期时间。工作台登出和 IdP / Gitea 全局登出是不同动作，界面准确说明。

发行方不可用、Token 无效、权限不可核实分别显示；私有数据默认拒绝。测试跨用户资源猜测、同邮箱不同 issuer、重放回调、错误 audience、权限撤销和后台机器人越权。
