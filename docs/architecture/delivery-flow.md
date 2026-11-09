# 构建、镜像、Release 与部署

状态：产品链路设计；已有 M0 合成 Release / OCI 上游证据，产品发布器 / 部署链路尚未实现。发布和部署分别建模，每个外部操作有意图、实际结果和恢复路径。

## M0 Release / OCI 契约准备

归属 M0-S03 / M0-03，给 M0-S04 提供原生接口证据；2026-11-04 先完成[静态准备](../records/2026-11-04-m0-gap-and-delivery-preparation.md)，随后取得[Release](../records/2026-11-04-m0-release-validation.md)和[OCI 隔离证据](../records/2026-11-04-m0-oci-validation.md)，分别保留五项 / 四项差异，不是完整 REL / ART / BASE 通过。本节继续规定准入与操作边界，不增加产品工程、Runner、GitHub 发布或部署。

### 认证、角色与资源

- 沿用本机隔离方案的 context、固定镜像、合成账号、回环端口、任务 CA 与串行 cleanup。原三种 OAuth 组合不变；`issue_write` 没有 Release 写入或 package 权限，不把它扩为通用发布凭据。
- 已新增并实测第四种独立 `release_write = openid read:user write:repository`，对应只读与错误用途凭据作负例。它允许宽于 Release 的仓库操作，须如实记录 grant，不能命名成仅 Release 按钮权限。普通角色、grant / 在线账号与刷新分别取证；只读 scope 的草稿元数据与下载可见性不一致，受控草稿读取要求新用途和 Release 单元写权限，原始差异保留，见[ADR 0005](../adr/0005-release-authorization-and-reconciliation.md)。
- OCI 已单独验证 Registry challenge → 固定同源 `/v2/token` → Registry Bearer，使用普通用户 `read:package` / `write:package` PAT；四种 OAuth 组合不变，不透传 Release OAuth Bearer 或用管理员 / 无限制 PAT 兜底。Registry metadata / 源码声明 24 小时，未真实等待；团队 / 组织权限与账号禁用即时拒绝、PAT 删除后旧 JWT 仍可读写分别保留，见[ADR 0006](../adr/0006-oci-authorization-and-digest-retention.md)。
- 普通所有者准备合成仓库 / 私有组织，写者、读者及非成员分别验证。Release 单元读写权限、仓库角色和 Token scope 分开；OCI 按所有者可见性、组织成员 / team package 权限验证，关联私有仓库不等于 package 私有。
- M0 HTTP 客户端已为显式 binary 请求补齐原始 bytes、严格大小限额和响应头白名单，默认 JSON / form 行为保留；沿用固定 origin、任务 CA、禁止带凭据跨域 / 自动跟随重定向及不自动重试。附件上限 64 KiB、通用读取上限 2 MB，不以损失字节的文本解码验证附件或未来镜像 Digest，不表示已有完整 OCI 客户端。

### Release 最小执行切片

令 `R=/api/v1/repos/{owner}/{repo}`，全部指向本批隔离仓库。表中状态码是固定 OpenAPI 声明的正向值，Tag POST 另注明已实测的声明差异；权限拒绝、无效输入和部分失败须保留实际响应及回读，不以宽状态码集合吞掉差异。

| 操作 | 公开入口 / 正向值 | 必须核对的结果 |
| --- | --- | --- |
| 固定源码与 Tag | `GET R/git/commits/{sha}`、`GET R/tags/{tag}`；Tag `POST R/tags` 声明 200，实测 / 同版处理器为 201，保留 gap | 使用完整 commit SHA；Tag 的 `commit.sha` 独立核实，不把 Tag object ID 或 Release 的 `target_commitish` 字符串当最终提交 |
| 创建与定位草稿 | `POST R/releases` / 201；`GET R/releases/{id}`、`GET R/releases/tags/{tag}` / 200 | 唯一 tag、正文关联标记、作者、draft、源 SHA；草稿创建不一定生成 Git Tag，不能在尚未发布时假设已存在 |
| 列表与可见性 | `GET R/releases?draft=...&page=...&limit=...` / 200 | 分页不重不漏；草稿需要 Release 单元写权限且具备仓库写 scope，普通读者 / 只读 scope 看不到草稿不是“创建未执行”证明 |
| 说明 / 发布 | `PATCH R/releases/{id}` / 200 | 说明与 draft / prerelease 分别回读；已有 Tag 必须仍指向预期 SHA。空说明清除、错误 target、Tag 漂移、重复同 tag 创建分别保留结果 |
| 附件上传 / 定位 | `POST R/releases/{id}/assets?name=...` / 201，multipart 字段 `attachment` 或原始 bytes；列表 / 单项 GET 为 200 | 名称、ID / UUID、size、所属仓库 / Release；同名不当作幂等键。Attachment DTO 未提供内容 Digest，必须实际下载计算 SHA-256 |
| 附件改名 / 删除 | `PATCH R/releases/{id}/assets/{attachment_id}` / 201，DELETE / 204 | 跨 Release / 仓库 ID 拒绝；删除后元数据和下载均失效，拒绝 / 超时后回查 |
| 草稿 / Release 删除 | `DELETE R/releases/{id}` / 204 | 回读已删除、关联附件与 Tag 的真实存续；不假设删 Release 等于删 Tag，也不用于自动补偿未知结果 |

执行顺序：先准备两条可区分提交和唯一 Tag 名 → 独立授权与角色负例 → 草稿 / 分页 → 小型合成附件上传 / 字节校验 → 固定 SHA 后发布 / 回读 → 重复、失权、非法关联及故障 → 删除与 cleanup。只在隔离 Gitea 发布合成 Release，不对当前 GitHub 仓库打 Tag 或创建 Release。

至少覆盖：已提交但响应丢失、请求未转发、重复同 tag、同名附件重复 / 部分上传、下载损坏、跨用户 / 撤权、被删除资源、Tag 与 target 不一致。创建未知后先按固定仓库 + tag 查询再回读 ID / 标记；附件未知后列出候选并逐个校验内容。零匹配、多匹配、无权限或查询失败都保持 unknown，不重新 POST、不选 latest、不删除归属未确认的对象。发布前后分别核对 Tag SHA；检查与写入仍存在竞态，不宣称跨系统原子性。

本批已执行上述个人仓库合成切片及真实超时 / 半包断开，失败边界和未覆盖面以验证记录为准。空 name / body 清除被忽略、无效 target 发布 500、已有 Tag 的实际提交与 target 不同等继续为 gap；附件按稳定身份与真实内容对账，列表 / 详情的两种合法下载 URL 均严格验证，不以 URL 字符串相等作为同一对象条件。草稿 scope 差异和空字段能力没有因本地约束而原生修复，不提前关闭完整发布链路。

### OCI 最小执行切片

协议对照固定 OCI Distribution v1.1.1，仅选择本表基础推拉操作；不据此宣称全规范符合。`N={owner}/{image}`，Registry 是同一隔离 Gitea 的根 `/v2`，不是 OpenAPI 的 `/api/v1/packages`。REST Packages 列表 / 版本 / 文件 / link 接口只作关联回读，不能替代直接 Registry 权限负例。

| 操作 | 公开入口 | 验证与未知结果处理 |
| --- | --- | --- |
| 准入 / 凭据 | `GET /v2/`、`GET /v2/token` | challenge 的 realm / service 和 origin 白名单、账号身份、read / write package 区分；不向未知 realm 发送秘密 |
| Blob 上传与状态 | `POST /v2/N/blobs/uploads/`，返回 Location；随后 PATCH / PUT，GET 查询该 upload；HEAD / GET blob Digest | 按返回 Location / UUID 和 Range 回查，限制同源与目标路径；校验完整长度和 SHA-256。POST 回执丢失而 UUID 未知时停止，不新建另一上传冒充恢复 |
| Manifest 与固定拉取 | `PUT /v2/N/manifests/{tag}`，HEAD / GET `{tag}` 与 `{digest}`，GET blobs | 核对 Content-Type、原始 manifest / config / layer 的 size 与 Digest；服务器确认值和实收 bytes 一致，按 Digest 拉取，不从 tag 名猜 Digest |
| 私有包与撤权 | 同一组 Registry URL 由普通成员、仓库协作者但无包权限者、组织非成员及匿名直接访问 | 私有组织 / team package 权限独立验证，包链接私有仓库后仍须直拉核对。当前账号与包权限变更、删除 PAT 后旧 JWT 的行为分别验证 |
| 关联与删除 | `/api/v1/packages/{owner}/...`、Registry manifest / blob / upload 删除 | link 只是关联事实；删除 / 失联 / 摘要不符阻止后续发布。只清理本批已确认归属的上传与镜像 |

本批已用任务 CA 的有界协议客户端取得基础推拉 / 权限 / 故障证据，并由 Docker 无网络 scratch 构建 + regctl v0.11.7 推送 / 固定 Digest 导出 + Docker load 验证微型真实镜像。regctl 独立私密配置禁用 Docker 凭据 / 证书导入，Buildx 状态在任务目录；未改系统 / daemon CA，未使用 Docker daemon push / pull。客户端、网络 / 磁盘和清理条件须在启动前明确，不下载未经说明的大型工具镜像，不把协议样例外推为任意 OCI 客户端 / 构建链路通过。

包隐私按所有者和当前包权限判定。组织成员仍有读取基线。删除 PAT 后，旧 Registry JWT 的远端失效与后续产品侧停用分别报告，见[身份与访问](identity-access.md#权限模型)。

Manifest / config / layer Digest 固定内容身份。上轮实测覆盖最后一个 Tag 后旧 Manifest Digest 返回 404。Gitea 28.2.0 的包清理保留规则只作用于清理任务，Registry 覆盖和显式删除按包权限处理。独立发布引用和清理保留规则是待验收的受控保留候选。发布、部署及回退均复核清单所需的原制品，缺失、摘要不符或不可复核时阻断并保留原因。强制保留范围和恢复目标待所有者确认，见 [ADR 0006 核查补充](../adr/0006-oci-authorization-and-digest-retention.md#2026-11-09-公开机制核查补充)。

Runner 暂停时没有真实 workflow run / attempt，证据须明确为缺失，不能填 0、占位 ID 或借最新 run 补齐；源码 SHA、制品 Digest 的原生协议证据可独立取得，完整源码 / run / 制品链路仍未通过。M0 的最小镜像样例不关闭五组件 ART / REL、部署或恢复验收。

## 完整链路

1. Push / Tag 由底座触发构建；Webhook 只同步已发生事件，不重复触发同一次 CI。
2. 独立 CI Runner 构建各组件，推送 Registry，获取 Registry 确认的 Digest。
3. 构建清单记录仓库 ID、源码 SHA、workflow ref、run / attempt、各组件 Digest 和附件校验和。
4. Go 对账运行结果、制品存在与权限，验证必需组件全部就绪；不能只信任上传 JSON 声称成功。
5. 用户发起发布；先持久化操作和唯一键，再创建或关联 Gitea 草稿 Release，上传说明、清单和附件。
6. 校验草稿内容、Tag 对应 SHA、清单与附件一致后发布；冻结自有清单并保存上游引用。
7. 用户选择 Release 与环境，服务端重新授权、取环境锁，触发受控部署工作流。
8. CD Runner 预检、备份、迁移、启动、健康验证；结果对账后更新环境当前已验证版本。
9. 测试晋级生产使用同一组 Digest，不重新构建；失败和回退创建新的部署记录。

以下只是清单概念示例，并非可执行配置：

```yaml
schema_version: 1
project: sample
version: v1.2.0
sources:
  - repository_id: 42
    commit: <full-commit-sha>
build:
  run_id: 1086
  attempt: 1
components:
  api:
    image: git.example.com/team/api@sha256:<digest>
  web:
    image: git.example.com/team/web@sha256:<digest>
```

## 幂等与失败恢复

| 情况 | 预期处理 |
| --- | --- |
| 重复 webhook / 用户双击发布 | 去重并返回同一操作，不新增同版本 Release |
| 上游创建成功但响应超时 | 标记结果未知，按引用 / 唯一关联回查；不能盲重试 |
| 五个必需镜像只成功四个 | 保持未就绪，指出缺失组件；不发布半套版本 |
| 部分附件上传失败 | 保存草稿与步骤，支持校验后继续；不自动删除无归属确认的附件 |
| Tag 被移动或镜像被删除 | 阻止部署并标记漂移，不能重新解释已有冻结清单 |
| Runner 失联 | 状态未知；确认旧执行已终止后才能解锁环境 / 重试 |
| 迁移后健康失败 | 不自动切回旧镜像，依据 schema 兼容决定前滚或批次恢复 |

状态机与唯一键必须覆盖崩溃恢复。跨 Gitea / Registry / 自有库不宣称原子事务或恰好一次执行。写操作执行身份、用户授权依据和每步副作用进入审计。

## CD 信任边界

部署工作流保存在受保护仓库 / ref，部署凭据只给予独立受控 Runner。普通开发者提交的 YAML、PR 代码或构建输出不能替换部署步骤、镜像坐标、目标主机或秘密引用。构建产物清单须与服务端允许的组件坐标和运行记录匹配。

工作流触发回执与实际 run 可能分离，使用部署请求关联标识、固定 ref 与对账关联，不能取“最新一次 run”当作本次部署。回调如需接收，采用短时、单次且绑定操作的凭据，并回查上游运行结果。

回滚是对上一已验证清单发起新部署，不抹去失败历史。数据库恢复独立授权、独立验证；镜像回退不能恢复数据。平台自身安装与升级见[部署策略](../deployment/strategy.md)，不能依赖已经运行的自身实例才能完成首次安装或灾备恢复。
