# 2026-11-09 M0-S04 G27 单凭据撤销方案核查

基线为 `f0fb928`。固定版 Gitea 已实测原 PAT 交换 401，但原 Registry JWT 可签发到期声明更晚的后继。此次按公开协议和固定源码核查两个可验证方向，供首版取舍。证据限静态核查。 [Gitea 28.2.0 实测](2026-11-09-m0-registry-bearer-reissue.md)

## 可验证的方向

| 路径 | 已核查的机制 | 实施影响和剩余证据 |
| --- | --- | --- |
| Gitea 原生与产品停用 | 停止产品侧操作并删除目标 PAT，可阻止产品继续使用该授权及用原 PAT 交换。固定版原 JWT 可绕过产品直接访问并换发。团队、组织或账号层撤权作用于身份或资源权限 | 保留既有部署和制品坐标。仅承诺已验收的本地停用和原 PAT 交换拒绝。按需指定应急撤权范围及责任，单凭据远端失效缺口保留 |
| 独立 Registry，短期 Bearer | Harbor v2.14.5 为有限窗口候选。项目机器人账号可单独禁用并回读，签发端以分钟配置数据 Bearer 的寿命，Registry Bearer 的鉴权处理限 `/v2` 路径，签发端为 `/service/token`。数据鉴权从 JWT 的授权声明判定访问 | 一枚受管凭据对应一个独立机器人账号。额外部署 Registry 并确定制品坐标、身份映射、权限同步、备份和恢复。短测须验证旧 Bearer 无法换出有权后继、原 JWT 到期拒绝、独立账号隔离及不同入口的有效窗口 |
| 唯一 Registry 入口，逐请求复核 | Gitea 保持内部数据面。对外入口签发或验证可关联到独立授权记录的凭据，在换发和数据操作前检查目标授权状态，并限制目标与操作。内部 Gitea PAT 和 JWT 只由受控服务使用 | 需要新的入口和授权状态，且必须覆盖所有外部访问路径。普通反代或单纯屏蔽换发路径无法从现有 Gitea JWT 可靠还原来源 PAT。先验证身份映射、路径覆盖和故障拒绝，再评估实现 |

Gitea 固定源码以用户、scope 和时间构造 JWT，声明中没有来源 PAT ID 或独立 JWT ID。按原 JWT 文本列黑名单也无法从声明关联后继与来源 PAT。保留 Gitea 数据面时，应使用受控入口能独立标识的凭据，向 Gitea 访问时保持当前用户及目标权限检查。用共享高权限账号代替用户会越过这条边界。 [Gitea 固定签发与声明](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/packages/auth.go#L21-L49)

Harbor v2.14.5 对应 `c83198c6a10c040370df997660eda989965d5a25`。项目机器人 Basic 鉴权检查 secret、禁用和到期状态。`/service/token` 使用请求安全上下文签发，Registry JWT 鉴权处理只匹配 `/v2` 前缀。带 scope 的未认证请求仍可能拿到无目标权限的 Token，须用真实私有制品验证原 secret 和旧 Bearer 无法获得有权后继。签发器按实际角色生成权限，读用途应单独配置只读机器人。 [版本](https://github.com/goharbor/harbor/releases/tag/v2.14.5) · [项目机器人](https://goharbor.io/docs/2.14.0/working-with-projects/project-configuration/create-robot-accounts/) · [机器人鉴权](https://github.com/goharbor/harbor/blob/c83198c6a10c040370df997660eda989965d5a25/src/server/middleware/security/robot.go#L33-L72) · [公开机器人接口](https://github.com/goharbor/harbor/blob/c83198c6a10c040370df997660eda989965d5a25/api/v2.0/swagger.yaml#L3327) · [签发权限过滤](https://github.com/goharbor/harbor/blob/c83198c6a10c040370df997660eda989965d5a25/src/core/service/token/creator.go#L142-L220)

Harbor Core 验证数据 Bearer 时使用 60 秒时钟宽限。已签发 Bearer 的数据权限基于 JWT 声明及当前目标项目检查，无逐机器人禁用回查。撤销后已签发 JWT 的窗口须计入寿命和宽限，项目机器人的账户到期设置和数据 Bearer 寿命需分别回读。 [签发寿命](https://github.com/goharbor/harbor/blob/c83198c6a10c040370df997660eda989965d5a25/src/core/service/token/authutils.go#L112-L155) · [Bearer 路径与验证](https://github.com/goharbor/harbor/blob/c83198c6a10c040370df997660eda989965d5a25/src/server/middleware/security/v2_token.go#L44-L78) · [时钟宽限](https://github.com/goharbor/harbor/blob/c83198c6a10c040370df997660eda989965d5a25/src/common/const.go#L253-L254) · [数据权限](https://github.com/goharbor/harbor/blob/c83198c6a10c040370df997660eda989965d5a25/src/common/security/v2token/context.go#L70-L94)

CNCF Distribution 的公开 token 配置支持独立签发服务。v3.1.2（`3220848f15d9279c66a41aa0a257469e6aede1e9`）的数据鉴权验证签名、发行方、服务、时间及请求所需权限，同样给 `exp` 留出 60 秒宽限。它可作为独立签发的协议对照。逐凭据签发状态需由签发服务提供，已经签发的 Bearer 不会因该状态改变而由默认验证器主动失效。若实现逐请求拒绝，需将检查放在所有受保护数据路径上。 [独立签发配置](https://distribution.github.io/distribution/about/configuration/#token) · [请求鉴权](https://github.com/distribution/distribution/blob/3220848f15d9279c66a41aa0a257469e6aede1e9/registry/auth/token/accesscontroller.go#L388-L435) · [时间验证](https://github.com/distribution/distribution/blob/3220848f15d9279c66a41aa0a257469e6aede1e9/registry/auth/token/token.go#L118-L160)

## 选型前的最小验收

1. **固定撤销语义。** 从撤销写入成功且目标状态读回时开始计时，分别记录各实例停止签发和停止数据操作的时间。允许有限窗口时，预算须覆盖撤销传播和签发竞态、最长已签 Bearer 寿命、验证器宽限和实例时钟偏差。选择逐请求复核时，验收每个新请求在约定传播窗口后都拒绝，授权状态未知时拒绝，重启、故障恢复和重复撤销后仍保持。
2. **验证身份与在途操作。** 用同一归属下两枚可分别撤销的凭据及另一位普通主体的凭据作对照。禁用目标并读回后，检查原 secret、原 Bearer、已取得后继、可用刷新入口以及与撤销并发的签发。使用原 Bearer 和可取得的后继测试 Manifest / Blob 读取、上传 POST / PATCH / PUT、Manifest 写入，回读 Digest 和上传进度确认拒绝未产生额外副作用。独立凭据继续有效。对已开始传输的请求和已交付字节明确承诺边界。
3. **检查所有可达入口。** 以 Docker 和 regctl 实测挑战、同源 Location、续写和拒绝。检查 Registry 内部端口、替代域名、直连及重定向。如果同一私有制品还可经 Packages REST、网页下载、镜像代理或对象存储签名 URL 访问，对这些路径应用同一撤销规则，或将其隔离并限定其有效窗口。入口不可达和授权依赖故障须分别验证，确认没有以内部高权限凭据放行。

若首版只要求产品侧停用，保留 Gitea 受控边界。若允许短期 Bearer 的剩余窗口，先对 Harbor 做一个固定镜像的隔离短测，配置与回读寿命后，以真实时钟覆盖到期和宽限两侧。若要求已签发 Bearer 在更短窗口内失效，先验证逐请求入口能封住所有外部路径。G26 的强制 Digest 保留另行决策；此次没有批准新增组件、部署或长时取证。 [ADR 0006](../adr/0006-oci-authorization-and-digest-retention.md) · [OCI 补证条件](../planning/m0-validation.md#oci-补证条件)
