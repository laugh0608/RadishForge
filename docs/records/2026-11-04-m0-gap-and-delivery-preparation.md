# 2026-11-04 M0 差异基线与 Release / OCI 静态准备

状态：已有 Issue 批次已提交；本批接续完成 M0-S04 已有差异汇总与 M0-S03 Release / OCI 公开契约静态核查。未执行新的上游联调，不关闭 M0-03 / M0-04、BASE / COMP / ART / REL 或 M0 阶段出口。

## 授权、起点与提交

用户要求“提交本批工作区更改，继续推进下一步”；沿用 current 的差异基线优先、随后 Release / OCI 准备顺序，Runner 继续暂停，不进入 M1。本轮没有推送、远端仓库写入或发行 / 部署授权。

在 dev 复核上批 19 个路径、暂存差异、未跟踪文件、秘密模式、既有 Git 身份和九项真实联调源码摘要；摘要未变，不重跑已完成的真实取证。治理检查及暂存空白检查通过后，使用当前用户身份提交 `a6eca0d`：`test(issue): 补齐 M0 Issue 契约与失败边界`。提交后工作区干净，本地缓存的 origin/dev 落后两条；没有 fetch，不能推断服务端实时状态。

上批 records 和 JSON 的未提交状态是原始导出快照，保持不变；提交事实由本记录、current 与 Git 历史补充。本批接续仅修改正式文档与静态来源摘要，尚未再次提交或推送。

## 已有差异的核对与归属

[GitHub 兼容专题](../architecture/github-compatibility.md#m0-现有差异基线)维护唯一汇总表，本记录不另建兼容状态矩阵。三份原始 JSON 的文件摘要、结果位置 / 命名记录与 `M0-G01`—`M0-G18` 的对应见[来源与核对 JSON](2026-11-04-m0-gap-and-delivery-sources.json)。其中 17 条能定位到原始 gap，另 1 条是公开撤销接口缺口，不伪造为命名失败用例。

| 输入 | 本次去重口径 | 处理依据与未完成项 |
| --- | --- | --- |
| 11 月 1 日原始 scope | 3 条；复现批次不新增编号 | 沿用 ADR 0003 的完整组合、身份 / 资源分离与在线复核；不表示任意 Gitea 应用都安全 |
| 11 月 4 日旧配置生命周期 | 2 条；原始过期 introspection 与禁用账号刷新分别保留 | 受控 header-only 配置与账号拒绝已有证据；上游签发差异不改状态，M1 的本地会话 / 后台停止尚未实现 |
| 单用户撤销公开接口 | 1 条；固定 OpenAPI / 实际 Discovery 缺口 | 原生 UI 撤销已验证，自动远端撤销方案仍待决定；不封装私有请求或删除共享应用 |
| 11 月 4 日最终 Issue | 12 条；首轮 8 条不重复累计 | 沿用 ADR 0004；目录 / 角色 / 正文版本 / 部分写入 / 结果未知分开，不把前检当作上游修复 |

本次只是按既有决定明确受控范围及停止线，没有新增范围豁免或批准关键能力延期。GitHub REST 等价性、首批 Action commit / 运行时、其余原生 API 与完整缺口决策仍未通过；M0-04 从未开始转为进行中，完整阶段冻结仍待后续证据。

## Release / OCI 来源核查

固定 Gitea 28.2.0 源码提交仍为 `829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1`，OpenAPI SHA-256 与既有证据一致：`c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`。web 读取三个 Gitea raw 地址遇到 cache miss，随后直接读取相同官方固定提交，未换版本。公开来源临时落盘约 1.3 MB，不安装包、不下载镜像；正文未复制第三方源码进入仓库。

已提取并核对 16 个 OpenAPI 路径及相关请求 / 响应字段，覆盖 Release、Tag / commit、附件与 REST Packages；Registry 另查 `/v2` 路由、鉴权及 package 权限源码。OCI Distribution 对照为 v1.1.1，官方 annotated tag 解析到 `a139cc423184af6078077b9b7ee336eddbd03f8f`，规范 SHA-256 为 `360b29820869bfaac5f73ebfa30669c9172c069ef619f8c6689acc3bcef6f719`；选择基础推拉子集，不宣称全规范支持。14 个公开来源的 URL、摘要和大小及所选 OpenAPI 元数据保存在 JSON；这些是静态来源证据，全部 `runtime_verified_this_batch=false`。

| 静态发现 | 对下一轮执行的实际影响 |
| --- | --- |
| 草稿访问需 Release 单元写权限和仓库写 scope | 现有 Issue 组合不能直接当发布凭据；新用途单独注册 / 授权，普通读者看不到草稿不能证明未创建 |
| 草稿创建不生成新 Tag；发布会解析已有 Tag | 全 SHA 与 Tag 的 `commit.sha` 独立核对，不能把 target_commitish 当已冻结提交；专门覆盖已有 Tag 指向其他提交 |
| Release 空说明字段在编辑处理器中没有赋值 | 新增空正文清除负例；仅记录源码现象，不提前宣称真实 PATCH 已失败或新增运行 gap |
| 附件支持 multipart / 原始 bytes；DTO 没有 Digest | 补严格有界的字节上传 / 下载和 SHA-256 校验；元数据 GET 不能代替下载，也不能用同名当幂等键 |
| Registry 使用独立 package Bearer 链及 `/v2/token` | 不直接复用 OAuth Bearer；验证 package 只读 / 写入、账号禁用、失权和 Token 生命周期，拒绝未知 realm |
| package 权限取决于所有者可见性和组织 / team | 私有组织、非成员和仅有仓库权限者直接 pull；不能把关联私有仓库推导为包已私有 |
| 现有 HTTP 客户端只处理 JSON / form 和文本 | 二进制与白名单响应头支持需在下一次真实切片补齐，沿用 origin / TLS / 不重试边界，不新建通用 SDK |

下一轮的角色、公开入口、正常状态码、动作顺序及故障验收已写入[交付专题](../architecture/delivery-flow.md#m0-release--oci-契约准备)。先执行 Release 独立切片；OCI 的协议推拉与真实 OCI 客户端构建 / 拉取分开，客户端版本、任务证书信任与可达地址仍须在启动前核实。Runner 暂停时没有真实 run / attempt，不填占位 ID，也不能因此关闭源码 / run / 制品链路。

## 验证、清理与接续

本批只进行静态核查和文档检查，未修改脚本、三种授权组合或检查门槛；上批 35 项本地测试及真实批次结果继续按其原范围成立，没有将其冒充新的 Release / OCI 证据。所有差异引用均核对到原始来源，历史证据文件摘要保持不变。

`python3 -B scripts/check-repo.py` 通过：84 个文本文件、438 条本地链接；`git diff --check` 通过。另核对 9 个计划中的 Release 路径均存在于固定 OpenAPI，18 条差异 / 接口缺口引用和 14 项公开来源摘要一致。只验证静态准确性，不执行服务或把未运行用例标为通过。

没有启动 Docker 服务、临时监听、浏览器或 Runner；没有新增账号 / Token、安装依赖、修改系统信任或写入远端。公开来源临时目录在保存摘要和提取结果后移除，既有 `.local/m0` 仍不存在；共享缓存及其他项目资源保持原状。

下一步执行 Release 的普通用户授权、草稿 / 附件 / 固定 SHA、权限 / 重复 / 超时回查和清理取证，再推进 OCI。Actions 与完整 M0-S04 样例冻结 / 缺口取舍继续待证，不进入 M1。

主要官方来源：[Release 处理器](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/v1/repo/release.go)、[Release / Tag 服务](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/release/release.go)、[附件处理器](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/v1/repo/release_attachment.go)、[Registry 路由](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/packages/api.go)、[package 权限](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/context/package.go)、[OCI Distribution 固定规范](https://github.com/opencontainers/distribution-spec/blob/a139cc423184af6078077b9b7ee336eddbd03f8f/spec.md)。
