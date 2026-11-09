# ADR 0006：OCI 授权、Digest 保留与未知上传

日期：2026-11-04。状态：已接受，限于 M0 受控验证与后续实现契约。依据[OCI 隔离取证](../records/2026-11-04-m0-oci-validation.md)，原始四项差异继续进入 M0-S04；不批准 M0 出口、完整制品服务或 GitHub 权限等价兼容。

## 原因与证据

Gitea 28.2.0 的 Registry 使用独立 `/v2/token` 和 package Bearer，不能沿用 OAuth introspection / refresh 的结论。本批以普通用户 scoped PAT、私有组织 / team、独立 Registry Token 及真实 regctl 客户端验证基本推拉、撤权和失败回查。

四项原始差异：公开个人名下包关联私有仓库后仍可被其他用户读；请求参数 `scope=repository:...:pull` 未收窄 write:package PAT；覆盖最后一个 Tag 后旧 Manifest Digest 不再可读；删除 PAT 后已签发 Registry Token 仍能读写。它们分别涉及包可见性、请求权限语义、制品保留和凭据撤销，不用一个“镜像推送成功”覆盖。

## 决定

1. **包凭据与 OAuth 分开。** 四种既有 OAuth 组合不变，M0 Registry 配置单一来源为 [gitea-registry-profile.json](../../tests/contracts/m0/gitea-registry-profile.json)。正常包用途仅创建 `read:package` 或 `write:package` PAT，通过固定同源 `/v2/token` 交换 Registry Token；不申请 `all` / admin、不用账户密码直连 Registry 数据接口、不把 Release OAuth Bearer 当作 Registry Token。另有故意错误用途的 PAT 作负例，不进入正常组合。PAT 创建及实际 scope 回读与用户对象权限分别核对。
2. **挑战参数不代替授权。** 严格核对 HTTPS realm、service、origin 与目标 namespace，拒绝未知 challenge / Location，不向任意地址发送秘密。实际读写边界依赖 PAT scope 和当前对象权限，不能把 Registry 的 pull 请求参数宣传为已签发只读 Token；本批 write PAT 即使请求 pull，仍可开启上传。
3. **隐私按 package 所有者建模。** 私有组织对非成员、匿名和仅有仓库协作权的用户拒绝直接拉取；组织成员即使只有代码单元权限，也可能具有包读取基线，不能将 `repo.packages` 缺失解释为禁止读取。公开个人名下的包不因关联私有仓库而私有。受控制品流程必须核实实际所有者 / 组织可见性和直接 Registry 权限，不以 link、UI 隐藏或仓库权限替代；尚不承诺逐仓库隔离包权限。
4. **分别记录权限撤销与凭据撤销。** 团队写权限降级、移出私有组织及禁用账号已阻止旧 Registry Token 的相应操作。删除 PAT 后，原 PAT 交换被拒绝，原 JWT 仍能读取和开启上传，并能换发具备同等已测能力的后继。每枚 JWT 声明 86400 秒，后继的声明到期时间从新签发时刻计算。后续产品本地撤销必须停止依赖操作并丢弃缓存凭据。真实到期和首版单凭据撤销要求仍待收口。 [G27 换发实测](../records/2026-11-09-m0-registry-bearer-reissue.md)
5. **Digest 固定身份，保留另验。** 对服务器确认的原始 Manifest、config、layer 分别核对 size / SHA-256，按 Digest 拉取；不能用 tag 文本、重新编码 JSON 或 Docker image ID 代替具体 descriptor Digest。覆盖最后一个 Tag 后旧 Digest 的 404 是可用性缺口，不能从“按 Digest 命名”推导不可变保留。发布引用应避免覆盖，并在发布 / 部署前重新确认制品存在；强制保留 / 保护方案尚待验证，缺失时阻断，不取 latest、重新构建或重解释冻结版本冒充原制品。
6. **未知上传按已有证据回查。** 在写入前明确预期内容 Digest；能取得 upload Location / UUID 时只查询该同源任务路径及 Range，能取得完整 Digest 时 HEAD / GET 并逐字节校验。启动响应丢失而拿不到 Location、零完整对象、部分前缀、失权或查询失败都保持 unknown，不猜 UUID、不新开上传 / 自动重放 PATCH 或 PUT。Range 只证明已观察到前缀，不表示完整 Blob / Manifest 已提交；半包断开后的零对象不证明无副作用或临时存储已消失。
7. **真实客户端与故障传输分开取证。** Docker 在无网络的 scratch 上构建微型镜像；任务专用 regctl 通过 task CA 推送并按 Digest 导出，Docker load 核对来源与镜像身份。Registry 数据传输由 regctl 完成，不宣称执行了 Docker daemon 的 push / pull；不改系统 / daemon CA。受控故障只作用于有界协议客户端的固定操作、凭据和 bytes，CLI 未接受故障注入，不能外推其内部重试 / 任意中断恢复语义。

regctl v0.11.7 darwin/arm64（Apache-2.0）固定官方资产摘要，仅作为任务临时工具；不进入产品依赖或 lockfile。配置关闭 Docker 凭据 / 证书导入，Buildx 状态留在任务目录，不修改用户配置。清理只移除任务标签、凭据及已确认归属的资源，不全局 prune。

## 2026-11-09 公开机制核查补充

以 Gitea 28.2.0 的固定 OpenAPI、配置、Registry 和 Packages 请求链为准。原始实测与本批静态结论分列，见[公开机制核查记录](../records/2026-11-09-m0-oci-public-mechanisms.md)。

- **M0-G26 可承诺边界。** 固定发布清单的镜像坐标与 Digest，发布、部署和回退前复核同一制品及所需描述符，缺失或不符即阻断并保留原因。独立发布 Tag、包写权限隔离和所有者清理保留规则可作为受控保留候选。清理规则只在清理流程生效，Git Tag 保护只管 Git 引用，已审阅的公开 Registry / Packages 路径仍允许有权用户覆盖或删除。制品留存依赖所选机制及其验收，底座强制保留缺口保留。
- **M0-G27 可承诺边界。** 删除 PAT 已实测阻止该 PAT 的新交换。后续产品按授权记录停止新操作、让待执行作业在复核时拒绝、丢弃本地缓存，并分别报告 PAT 删除、产品侧停用与上游状态。旧 JWT 校验按当前账号和包权限执行，固定版本未发现专用 TTL 配置或绑定来源 PAT 的单凭据撤销机制。账号、权限和签名密钥保持不变时，已复制的原 JWT 能继续访问并换出可用后继。单枚 JWT 声明的 24 小时无法界定删除 PAT 后的总体远端失效窗口。 [G27 换发实测](../records/2026-11-09-m0-registry-bearer-reissue.md)

**待所有者取舍**

| 缺口 | 接受受控边界需要决定的范围 | 坚持强保证的影响 |
| --- | --- | --- |
| M0-G26 | 是否接受 Gitea 私有发布命名空间内的受控保留，明确须保留的版本 / 回退窗口、可删除角色和恢复目标。需承担额外引用、存储和恢复演练，具备写权限的角色仍可能移除制品。 | 若要求服务端在保留期内拒绝常规写者覆盖和显式删除，继续评估有可验证保留机制的 Registry 或独立受保护制品副本。需明确保护的坐标、例外角色、存储成本、部署与恢复路径。 |
| M0-G27 | 是否接受产品侧停用、拒绝原 PAT 交换，同时承担已复制 JWT 仍可访问及换发后继的风险。明确最小读写范围、事件处置责任及对失效窗口的要求。真实到期另按所需证据安排。 | 若首版要求单凭据在确定窗口内远端失效，现有原生路径继续作为阻塞缺口。可另评估具备逐凭据鉴权的 Registry 或不可绕过的统一入口，需验证原生客户端、身份映射、旁路和故障拒绝，增加部署与运维成本。 |

两项分别决策。现阶段只确认公开机制的核查范围和受控边界，保留首版要求；产品承诺、底座变更及新增部署组件待确认。补证按[定向验收条件](../planning/m0-validation.md#oci-补证条件)执行。

## 2026-11-09 包可见性与 Registry scope 核查

- **G24 包可见性。** 受控私有制品须核实实际私有组织所有者，并按普通成员、写者、仓库外部协作者及非成员验证直连 Registry。包的 link 是仓库关联，关联操作本身须有对应权限。仓库私有状态及关联结果均不能作为包私有的判定依据。组织成员仍有读取基线，同组织内按仓库隔离继续保留为缺口。
- **G25 凭据范围。** 读写用途分别使用明确的 `read:package` 和 `write:package` PAT，按实际 grant scope 和当前目标对象权限执行。固定版签发器保留原 package scope，JWT 未绑定请求中的镜像坐标。受控客户端核实目标命名空间、服务和操作，限制自身凭据使用。原生端的请求级收窄或单镜像绑定需要可验证的底座机制。
- **G27 补证。** 删除来源 PAT 并回读后，原 JWT 单独请求 `GET /v2/token` 返回 200，后继的 `nbf` / `exp` 均晚 3 秒。后继按 Digest 读取 Manifest 和开启上传分别为 200 / 202。真实到期及连续换发仍待验，两个 OCI 取舍保留。 [G27 换发实测](../records/2026-11-09-m0-registry-bearer-reissue.md)

静态路径、原始实测及协议对照见 [G24 / G25 核查记录](../records/2026-11-09-m0-package-access-mechanisms.md)。测试条件见 [M0-S04 OCI 补证](../planning/m0-validation.md#oci-补证条件)。

## 停止线

四项差异、早期中断与原始源码摘要全部保留。没有强制制品保留或已复制 Registry Token 的立即撤销证据，不能宣称原生修复 / 完整 ART / BASE 通过。多组件清单、发布冻结、任意组织策略、生产请求持久化 / 崩溃恢复、24 小时真实到期、其他平台 / 客户端、Runner 与 Actions 仍待验收；没有真实 run / attempt，不填占位。Runner 暂停，不进入 M1。

来源：[Registry 路由](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/packages/api.go)、[Token 签发 / 解析](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/packages/auth.go)、[包权限](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/context/package.go)、[OCI Distribution 固定规范](https://github.com/opencontainers/distribution-spec/blob/a139cc423184af6078077b9b7ee336eddbd03f8f/spec.md)、[regctl v0.11.7](https://github.com/regclient/regclient/releases/tag/v0.11.7)。实际行为及摘要以本批记录为准。
