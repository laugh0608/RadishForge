# 2026-11-04 M0-S03 OCI 隔离取证

状态：本批 OCI 原生协议与真实客户端切片已取证，四条差异保留；不关闭完整 ART / BASE / COMP 或 M0 出口。原始批次、脱敏轨迹、源码及清理回执见[结果 JSON](2026-11-04-m0-oci-results.json)，受控边界见[ADR 0006](../adr/0006-oci-authorization-and-digest-retention.md)。

## 授权、提交与环境

用户要求先提交 Release 批次，再推进 OCI 隔离取证，覆盖私有组织包权限、固定 Digest 推拉、撤权与超时先回查，做好验证 / 文档同步。先在 dev 复核 28 个路径、暂存差异、十项真实联调源码摘要、治理 / 空白及敏感信息，再以现有身份提交 `c77b29e`：`test(release): 验证隔离发布契约与真实超时回查`。提交后工作区干净；本地缓存 origin/dev 落后四条，未 fetch / push，不推断服务端实时状态。历史 records 的未提交快照不回写，本记录补充提交事实；本批 OCI 新改动尚未提交。

沿用 OrbStack context `orbstack`、Engine 29.8.2 / Compose 5.5.0、Linux arm64、Python 3.14.5，以及已缓存的 Gitea 28.2.0-rootless / PostgreSQL 18.6-bookworm 固定 Digest。三个平台服务内存限额合计 2.75 GiB，回环端口 18443 / 19443；故障监听短时使用 18543。启动前已说明资源、命令、约 15–25 分钟取证 / 回归窗口及 cleanup。无新 VM、平台镜像下载、宿主升级、系统 / daemon CA 修改、Runner / socket / privileged；Actions 关闭。

独立客户端仅为任务临时 regctl v0.11.7 darwin/arm64，官方资产 12,129,570 bytes，SHA-256 `8ac077a1eeb834d3053714e86ccbd838d0da46567df8cd7c2695d1a19135bf60`，与官方 Release metadata 一致；版本自报 commit `36abda84830dae07db00bf9e5cec95d97b78222a`、Go 1.27.3，许可 Apache-2.0。用途、约 12 MB 网络 / 磁盘影响、临时目录和清理方式在下载前说明；未安装至全局路径、修改 PATH、引入产品依赖 / lockfile 或声称完成资产签名验真。

regctl 配置显式关闭 Docker 凭据 / 证书导入，仅信任本批 Registry CA；真实负例确认没有 task CA 时出现 x509 拒绝。PAT 只写私密配置文件，未进入命令参数 / 正式证据。Buildx v0.37.2、既有 BuildKit v0.33.1 使用同一 context 的 Docker driver，状态改至任务目录；Dockerfile 仅 `FROM scratch` + COPY 合成文本，无 RUN、无网络、不拉基础镜像。构建与拉回镜像按本批标签清理，共享镜像 / BuildKit 缓存不全局 prune。

## 凭据与权限夹具

普通 Alice 创建 `m0-private-org`，回读 visibility=private；Bob 的 team 仅 `repo.packages:write`，Carol 的 team 仅 `repo.code:read`，均通过 team / membership API 回读。Dave 是私有组织仓库的外部只读协作者，Basic 读仓库 200、组织成员查询 404。管理员只准备账号和改变合成账号禁用状态，不用于访问包。

原四种 OAuth 组合的文件内容逐字未变；新增独立 [Registry 契约配置](../../tests/contracts/m0/gitea-registry-profile.json)，PAT 仅 `read:package` / `write:package`。普通账号 Basic 仅用于创建 PAT / 管理夹具，Registry 数据请求使用该 PAT 换得的 Bearer。挑战固定 realm / service / namespace；有效 Release OAuth Bearer 与非 package PAT 交换均拒绝。Token metadata 声明 86400 秒，与固定源码一致，但没有本地独立验 HMAC 或真实等待 24 小时。

## 批次与修正

前两批按真实停止点保留退出 1，没有删除开始标记重放。每批先保存脱敏结果 / 只读诊断，再清理并使用新项目 / 空卷继续；两批完整 OCI 不是新增差异计数。

| 批次 | 项目 | 命名记录 / gap / 退出码 |
| --- | --- | --- |
| 初轮 Buildx 状态目录中断 | `rf-m0-local-88e9ad48` | 13 / 2 / 1 |
| 原 Digest 保留检查中断 | `rf-m0-local-69cc7806` | 15 / 2 / 1 |
| 首次完整 OCI | `rf-m0-local-7a9c99f9` | 30 / 4 / 2 |
| 最终源码 OCI | `rf-m0-local-720e0749` | 30 / 4 / 2 |
| Release 共享回归 | `rf-m0-local-b1ea9d8e` | 27 / 5 / 2 |
| Issue 共享回归 | `rf-m0-local-26fcdca6` | 32 / 12 / 2 |
| profiles 共享回归 | `rf-m0-local-8b8fd5d5` | 20 / 1 / 2 |

首轮 Docker 失败后，检查命令复现 Buildx 尝试写 `~/.docker/buildx/activity` 被沙盒拒绝；两个任务镜像标签不存在。使用官方支持的 `BUILDX_CONFIG` 把状态放入任务运行目录，并保留原 context / TLS；没有改用户配置或关闭安全机制。

第二批已完成真实客户端推拉，随后覆盖 Tag 后原 Digest 404；只读诊断确认新 Tag 为 200、原 layer 仍为 200。改为独立 Tag 保留性夹具，404 记录为 gap，并在撤权前另外读取稳定主权限夹具，避免把资源不存在误当权限拒绝。该批字段 `built_config_digest` / `loaded_config_digest` 实际记录的是 Docker image ID；后续明确为 image_id，并独立记录 Registry config descriptor Digest，原导出不改名。最终源码另把上传启动的预期内容 Digest 在写入前确定，完整重跑 OCI；没有回写早先执行摘要。

## 主路径与真实客户端

| 范围 | 实际结果与限制 |
| --- | --- |
| 协议推拉 | scoped PAT 交换，Blob POST / PATCH / PUT、GET upload Range、HEAD / GET Digest，Manifest PUT 与按 Digest GET；原始 bytes、media type、descriptor size / SHA-256 一致 |
| 包权限 | owner / package 写者可推拉；read PAT 即使属于 owner / writer 仍不能上传；私有组织对非成员、仅仓库协作者及匿名直接拉取拒绝 |
| 组织读取基线 | Carol 没有 package 单元但仍是组织成员，可读包而不可写；不能将 team 中缺失 package 单元当作禁止读取 |
| 关联 | 私有组织包 link 私有仓库后，仓库外部协作者仍不能拉取包；公开个人名下包 link 私有仓库后，另一用户可拉取，见原始差异 |
| 真实客户端 | Docker 无网络构建，regctl import 推送、查询服务器 Digest、按该 Digest export，再 Docker load；构建 / 加载 image ID 一致，独立读取 config / layer 字节，导出内容寻址成员摘要逐项一致 |
| 具体制品 | 最终 source SHA `f83a95f33f0ab38f44e9aeb4a0fd9a606f8f9a28`；CLI Manifest `sha256:8f8d442a296dbc7080ad999100995991e46f89df8f3b235e828e510ad5e296a7`，config `sha256:98d87996fa331892c6ff79ea3e2fc032453e02e4e5e984a1872a7f4593e5c28e`；archive / pull 各 8704 bytes |
| 撤权 | 缓存 JWT 在 team 写降为读后写拒绝、读仍可；移出私有组织后缓存 / 新换 JWT 均不可读；禁用账号后旧 JWT 资源 401；删除 PAT 的差异另列 |
| 非法 / 删除 | 错误 Blob Digest 为 400，未生成该 Digest；Manifest 引用缺失 Blob 为 404；Manifest DELETE 202 后 tag / Digest 404；upload DELETE 204 后查询 404 |

真实推拉由 regctl 执行，Docker 用于 build / save / load，未执行 daemon 的 push / pull。CLI 仅执行健康正向传输，故障用例由标准库协议客户端完成；不宣称 regctl 内部重试或任意网络故障恢复已验收。Docker image ID 在当前 containerd 存储下可能是 Manifest Digest，不能当成 config descriptor Digest。

## 保留的四项差异

| 引用 | 命名记录 | 实际结果 / 边界 |
| --- | --- | --- |
| M0-G24 | `public_personal_owner_linked_private_repo_does_not_define_package_privacy` | owner visibility=public，关联私有仓库后另一用户 pull 200；是所有者模型差异，不是已验证私有组织边界被绕过 |
| M0-G25 | `registry_requested_pull_action_is_not_a_pat_scope_reduction` | 请求 pull，PAT 实际为 write:package，仍可 POST 上传 202；不能把 query scope 当作已收窄凭据 |
| M0-G26 | `overwriting_last_tag_original_digest_retention` | 覆盖最后一个 Tag 后旧 Manifest Digest 404；不以 latest 或新 Tag 代替原 Digest，也不宣称已证明制品长期保留 |
| M0-G27 | `deleted_pat_does_not_imply_cached_registry_token_revoked` | 删除 PAT 后新交换 401，但已缓存 Registry JWT 的读 200、上传 202；仅证明当时仍有效，未等待声明的 24 小时到期 |

受控限制不修复任意原生调用；包所有者范围、请求权限粒度、强制保留与远端立即撤销继续进入 M0-S04，不能静默弱化权限 / 恢复承诺。

## 真实超时与回查

短时监听仅固定 `m0-private-org/m0-probe` 的上传启动、分块、完成和 Manifest 写入，精确核对 method / path / Bearer / body，一次处理，使用任务 CA。九个场景 caller 均真实 TimeoutError，自动重试 0；默认请求超时仍 15 秒，注入调用显式 1 秒。

| 场景 | 回查事实与决策 |
| --- | --- |
| 上传启动响应丢失 / 未转发 | caller 拿不到 Location；只读 HEAD 未见预期完整 Blob，保持 unknown，不猜 UUID / 再开上传 |
| 已追加 chunk 但响应丢失 | GET 已知 upload 的 Range 为 `0-80`；仅观察到 81 bytes 前缀，不宣称完整 Blob 已提交 |
| Blob 完成 / Manifest 提交后响应丢失 | HEAD / GET exact Digest 与原始内容一致；分别观察到完整 Blob / Manifest，不重新 PUT |
| chunk / 完成 / Manifest 未转发 | Range / 完整对象不满足目标，仍 unknown，不根据空结果自动写入 |
| Blob 半包断开 | 声明 535 bytes、仅发送 267 bytes 后关闭 TLS；完整 Digest 不存在、upload 仍可查询 204 / 无 Range，保持 unknown |

回查期间只用 GET / HEAD。随后对已知且归属明确的测试 upload 执行清理，属于夹具回收，不是自动恢复或对未知结果做删除补偿；未知 Location 的临时上传由本批隔离卷 cleanup 回收。零完整对象不证明未执行或不存在临时存储。

## 来源、验证与交接

固定 Gitea commit `829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1`，OpenAPI 摘要仍为 `c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`；OCI Distribution v1.1.1 对照 commit `a139cc423184af6078077b9b7ee336eddbd03f8f`，不宣称完整规范符合。官方来源、regctl 资产 / 许可与失败查找记录进入结果 JSON；raw web cache miss 后读取同一官方固定提交，没有换版本。

63 项本地测试通过，含原 48 项与新增 OCI 决策 / 客户端隔离 15 项；不启动网络、监听或 Docker。最终 OCI 与共享回归均保存 14 项源码 / 配置摘要；早期执行版本保留恢复补丁和逐项核对，不改写原摘要。历史 Release / Issue / IAM 与静态 records 保持原样。没有自有业务工程、生产数据或外部 Registry / GitHub 写入。

`python3 -B scripts/check-repo.py`：97 个文本文件 / 484 条本地链接，治理检查通过；`git diff --check` 通过。最终复核包括未跟踪文件的 UTF-8 / LF / 末尾换行、敏感信息、14 项执行摘要、三份早期源码恢复补丁和空暂存区，不把静态检查当作真实推拉或产品验收。

最终源码的 Release / Issue / profiles 均完成，原 5 / 12 / 1 条差异继续复现并退出 2，没有计为新的 OCI 差异。七批保存脱敏结果后 cleanup，逐项目标签读回容器 / 网络 / 卷 / 任务镜像均为 0；`.local/m0` 凭据、证书、regctl / Buildx 配置与 archive 已移除，18443 / 19443 / 18543 已释放。公开来源、源码快照和 regctl 二进制的任务临时目录在核对正式证据后移除；共享镜像 / BuildKit 缓存保持，不停止其他资源。

未覆盖 24 小时真实到期、独立 HMAC 验签、原生即时 JWT 撤销、强制 Tag / Digest 保留、任意组织策略 / 并发 / 崩溃恢复、regctl 故障内部重试、daemon 原生 push / pull、其他客户端 / 平台、生产及完整多组件发行链路。Runner / Actions 仍暂停，无真实 run / attempt，不填占位，不进入 M1。
