# ADR 0006：OCI 授权、Digest 保留与未知上传

日期：2026-11-04。状态：已接受，限于 M0 受控验证与后续实现契约。依据[OCI 隔离取证](../records/2026-11-04-m0-oci-validation.md)，原始四项差异继续进入 M0-S04；不批准 M0 出口、完整制品服务或 GitHub 权限等价兼容。

## 原因与证据

Gitea 28.2.0 的 Registry 使用独立 `/v2/token` 和 package Bearer，不能沿用 OAuth introspection / refresh 的结论。本批以普通用户 scoped PAT、私有组织 / team、独立 Registry Token 及真实 regctl 客户端验证基本推拉、撤权和失败回查。

四项原始差异：公开个人名下包关联私有仓库后仍可被其他用户读；请求参数 `scope=repository:...:pull` 未收窄 write:package PAT；覆盖最后一个 Tag 后旧 Manifest Digest 不再可读；删除 PAT 后已签发 Registry Token 仍能读写。它们分别涉及包可见性、请求权限语义、制品保留和凭据撤销，不用一个“镜像推送成功”覆盖。

## 决定

1. **包凭据与 OAuth 分开。** 四种既有 OAuth 组合不变，M0 Registry 配置单一来源为 [gitea-registry-profile.json](../../tests/contracts/m0/gitea-registry-profile.json)。正常包用途仅创建 `read:package` 或 `write:package` PAT，通过固定同源 `/v2/token` 交换 Registry Token；不申请 `all` / admin、不用账户密码直连 Registry 数据接口、不把 Release OAuth Bearer 当作 Registry Token。另有故意错误用途的 PAT 作负例，不进入正常组合。PAT 创建及实际 scope 回读与用户对象权限分别核对。
2. **挑战参数不代替授权。** 严格核对 HTTPS realm、service、origin 与目标 namespace，拒绝未知 challenge / Location，不向任意地址发送秘密。实际读写边界依赖 PAT scope 和当前对象权限，不能把 Registry 的 pull 请求参数宣传为已签发只读 Token；本批 write PAT 即使请求 pull，仍可开启上传。
3. **隐私按 package 所有者建模。** 私有组织对非成员、匿名和仅有仓库协作权的用户拒绝直接拉取；组织成员即使只有代码单元权限，也可能具有包读取基线，不能将 `repo.packages` 缺失解释为禁止读取。公开个人名下的包不因关联私有仓库而私有。受控制品流程必须核实实际所有者 / 组织可见性和直接 Registry 权限，不以 link、UI 隐藏或仓库权限替代；尚不承诺逐仓库隔离包权限。
4. **分别记录权限撤销与凭据撤销。** 团队写权限降级、移出私有组织及禁用账号已阻止旧 Registry Token 的相应操作；删除 PAT 只证明新交换拒绝，旧 Registry Token 在本次观察时仍可读写。源码及签发 metadata 声明 86400 秒，本批没有真实等待 24 小时，也未在客户端独立验证 HMAC 签名。后续产品本地撤销必须停止依赖操作并丢弃缓存凭据；这不能保证已经复制的 Token 立即在原生 Registry 失效。不得用禁用整个账号、修改全局签名密钥或服务账号权限补偿代替单凭据撤销；立即远端撤销承诺仍需 M0-S04 决策。
5. **Digest 固定身份，保留另验。** 对服务器确认的原始 Manifest、config、layer 分别核对 size / SHA-256，按 Digest 拉取；不能用 tag 文本、重新编码 JSON 或 Docker image ID 代替具体 descriptor Digest。覆盖最后一个 Tag 后旧 Digest 的 404 是可用性缺口，不能从“按 Digest 命名”推导不可变保留。发布引用应避免覆盖，并在发布 / 部署前重新确认制品存在；强制保留 / 保护方案尚待验证，缺失时阻断，不取 latest、重新构建或重解释冻结版本冒充原制品。
6. **未知上传按已有证据回查。** 在写入前明确预期内容 Digest；能取得 upload Location / UUID 时只查询该同源任务路径及 Range，能取得完整 Digest 时 HEAD / GET 并逐字节校验。启动响应丢失而拿不到 Location、零完整对象、部分前缀、失权或查询失败都保持 unknown，不猜 UUID、不新开上传 / 自动重放 PATCH 或 PUT。Range 只证明已观察到前缀，不表示完整 Blob / Manifest 已提交；半包断开后的零对象不证明无副作用或临时存储已消失。
7. **真实客户端与故障传输分开取证。** Docker 在无网络的 scratch 上构建微型镜像；任务专用 regctl 通过 task CA 推送并按 Digest 导出，Docker load 核对来源与镜像身份。Registry 数据传输由 regctl 完成，不宣称执行了 Docker daemon 的 push / pull；不改系统 / daemon CA。受控故障只作用于有界协议客户端的固定操作、凭据和 bytes，CLI 未接受故障注入，不能外推其内部重试 / 任意中断恢复语义。

regctl v0.11.7 darwin/arm64（Apache-2.0）固定官方资产摘要，仅作为任务临时工具；不进入产品依赖或 lockfile。配置关闭 Docker 凭据 / 证书导入，Buildx 状态留在任务目录，不修改用户配置。清理只移除任务标签、凭据及已确认归属的资源，不全局 prune。

## 停止线

四项差异、早期中断与原始源码摘要全部保留。没有强制制品保留或已复制 Registry Token 的立即撤销证据，不能宣称原生修复 / 完整 ART / BASE 通过。多组件清单、发布冻结、任意组织策略、生产请求持久化 / 崩溃恢复、24 小时真实到期、其他平台 / 客户端、Runner 与 Actions 仍待验收；没有真实 run / attempt，不填占位。Runner 暂停，不进入 M1。

来源：[Registry 路由](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/packages/api.go)、[Token 签发 / 解析](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/packages/auth.go)、[包权限](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/context/package.go)、[OCI Distribution 固定规范](https://github.com/opencontainers/distribution-spec/blob/a139cc423184af6078077b9b7ee336eddbd03f8f/spec.md)、[regctl v0.11.7](https://github.com/regclient/regclient/releases/tag/v0.11.7)。实际行为及摘要以本批记录为准。
