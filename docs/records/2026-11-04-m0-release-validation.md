# 2026-11-04 M0-S03 Release 隔离取证

状态：本批 Release 上游切片已完整取证，保留五条原始差异；不关闭完整 M0-03 / BASE / REL / COMP 或 M0 出口。原始轨迹、批次、源码摘要及清理回执见[结果 JSON](2026-11-04-m0-release-results.json)，受控边界见[ADR 0005](../adr/0005-release-authorization-and-reconciliation.md)。

## 授权与环境

用户明确要求提交接续文档，再按计划推进 Release 隔离取证，Runner 继续暂停、不进入 M1。先在 dev 精确暂存 / 复核十个接续路径，治理与暂存空白检查通过后提交 `c825fb2`：`docs(m0): 汇总差异基线并准备 Release 与 OCI 契约`。提交后工作区干净；本地缓存 origin/dev 落后三条，没有 fetch / push，不推断服务端实时状态。该批静态 records 保留其导出快照，本记录补充提交事实；本批新探针 / 证据 / 文档尚未提交。

沿用 OrbStack context `orbstack`、Engine 29.8.2 / Compose 5.5.0、Linux arm64、Python 3.14.5 和已缓存的 Gitea 28.2.0-rootless / PostgreSQL 18.6-bookworm 固定 Digest。三个服务合计 2.75 GiB 内存上限，仅回环 18443 / 19443；故障监听短时使用 18543，均验证任务 CA。已在启动前说明命令、约 15–25 分钟窗口、端口 / 内存和 cleanup。没有拉镜像、装依赖、改宿主 / 全局信任 / context，Actions 关闭，无 Runner / socket / privileged。

管理员只准备普通 Alice / Bob / Carol；普通所有者通过公开 API 准备私有仓库的两条提交，普通用户 OAuth 执行 Release / 附件 / Tag 操作。所有 Tag、草稿、发布和删除仅属于隔离 Gitea 合成数据，不在当前 Git 仓库或 GitHub 创建 Tag / Release，不进行外部发行或部署。

原三种授权组合、issuer、客户端和安全 / TTL 配置逐项核对不变；新增第四种独立 `release_write`：`openid read:user write:repository`。五个独立 confidential client 分别验证所有者 Release、所有者只读、错误 Issue 用途、写协作者与外部用户；grant、在线账号和按阶段显式刷新均取得真实回执。新 scope 比 Release 按钮更宽，不是 package 授权，也不能据此宣称逐按钮或 GitHub Token 兼容。

## 批次与工具修正

前三批按真实停止位置保留为中断、退出 1；没有删除开始标记在原环境重跑。每次先只读诊断、保存脱敏结果与已执行源码，再 cleanup，使用新项目 / 空卷继续。最终源码另完成 Release、Issue 与授权组合回归；命名记录含环境 / fixture / 完成标记，不按数量计算产品通过率。

| 批次 | 项目 | 命名记录 / gap / 退出码 |
| --- | --- | --- |
| 首轮 URL 校验中断 | `rf-m0-local-7241af9b` | 8 / 1 / 1 |
| Tag 状态码对照中断 | `rf-m0-local-7035d498` | 12 / 2 / 1 |
| 附件对账 URL 表示中断 | `rf-m0-local-1c43bc36` | 20 / 5 / 1 |
| 最终 Release | `rf-m0-local-0025ecdd` | 27 / 5 / 2 |
| 最终源码 Issue 回归 | `rf-m0-local-a9aa7c6d` | 32 / 12 / 2 |
| 最终源码 profiles 回归 | `rf-m0-local-f8eb22bf` | 20 / 1 / 2 |

首轮探针错误地只接受 UUID 下载路径；真实 Release 内嵌附件还返回仓库 / Tag / 文件名路径，修正为两种均精确绑定同源和对象的校验，并补正反例。第二批中断后 GET 确认 Tag 已创建，再核对同版 `CreateTag` 处理器为 201、OpenAPI 声明 200；精确改为 201 并新增独立 gap，没有放宽为任意成功码。第三批已提交的附件通过 GET 确认唯一对象、1064 bytes 与 SHA-256 均一致，仅列表 / 详情的 `browser_download_url` 不同；对账改为比较稳定 ID / UUID / 名称 / size 与真实内容，两个 URL 仍各自受严格校验。字段变化和错误内容的拒绝断言保留。

共用故障模块从 `m0_issue_faults.py` 提取为 `m0_response_loss.py`，操作类型分别固定 Issue POST、Release POST / 发布 PATCH、附件 POST；新增单次处理锁和附件半包传输。共享 HTTP 只为明确 binary 请求保留原始 bytes / 白名单头并限制大小，默认 JSON / form 与不重试边界保持；新增不完整响应 unknown 轨迹，不输出部分正文。模块迁移后的首次本地检查发现 README 旧链接，已修复，最终 48 项本地测试通过。

## 主路径与权限

| 范围 | 实际证据与限制 |
| --- | --- |
| 空态 / 草稿 / 分页 | 新仓库真实空列表；三条草稿 limit=2 得到 `[2,1,0]`，集合完整，无 Git Tag；只读 scope 的草稿列表为空、详情 404 |
| 编辑 / 发布 | 普通协作者可编辑说明 / 名称和上传附件；所有者编辑说明 / prerelease、发布并回读 draft=false，再改为稳定版本；Tag 的实际 `commit.sha` 等于固定源码 SHA |
| raw / multipart / 改名 | 两种附件上传均为 201，改名 PATCH 为 201，元数据与字节回读一致；1064 bytes 含 NUL / 非 UTF-8，SHA-256 为 `5cf455217db1710351bb5a616296a9fd19f4d9bce832ddc12b43492053974d08` |
| 两种下载 URL | UUID 与 API 展示的仓库 / Tag / 文件名路径，均真实下载核对原始 bytes；分别限制 origin、对象和 query / fragment，未关闭 TLS 或自动跟随跨域 |
| 错误制品 | 刻意上传一字节不同的合成附件，再真实下载；相同长度但不同 SHA-256 被拒绝。这是错误内容夹具，不冒充网络中途篡改证据 |
| 错误用途 / 跨用户 | `resource_read` / `issue_write` 对 Release / 附件 POST 均 403；外部用户列表 / 详情 / 写入与直接下载拒绝，匿名下载 303 登录回执保留，不跟到 200 页面伪装成功 |
| 角色 / 撤权 | 普通仓库写者可编辑草稿 / 上传；降为读者后可读已发布内容，草稿元数据与两种附件路径拒绝，管理操作 403；撤销协作者后列表 / 详情 / 编辑 / 直接下载拒绝，所有者回读未变 |
| 重复 / 非法关联 | 同 tag 重复创建 409，原对象未变；同名附件可创建两个独立对象，对账保持 unknown；跨 Release / 仓库的附件 ID 的 GET / PATCH / DELETE 及错误 Release ID 上传均 404，合法对象仍可下载 |
| Tag 漂移 | 已有 Tag 指向其他提交及删除重建后的移动均由只读前检拒绝，前检写入 0；不能外推为上游或任意并发已被强制阻止 |
| 删除 | 附件、Release、仓库删除后的相应元数据 / 字节不可读；删除 Release 后 Tag 仍存在并保留原 SHA，不把两者当同一动作 |

## 保留的五项差异

| 引用 | 命名记录 | 实际返回 / 回读 |
| --- | --- | --- |
| M0-G19 | `draft_attachment_read_scope_matches_draft_api_gate` | 同一仓库所有者的只读 scope：草稿元数据 404，但 UUID 与 API 展示的下载路径均 200，原始 bytes 可见；不外推为跨用户泄漏 |
| M0-G20 | `release_empty_name_and_body_clear` | PATCH 200，但空 name / body 均未清除原值 |
| M0-G21 | `tag_create_status_differs_from_fixed_openapi` | 固定 OpenAPI 的 Tag POST 声明 200，真实返回和同版处理器均为 201 |
| M0-G22 | `upstream_existing_tag_target_mismatch` | 绕过本地前检的合成原始请求：发布 200，draft=false，但已有 Tag 仍指向另一提交，与请求 target_commitish 不一致 |
| M0-G23 | `upstream_invalid_target_publish_readback` | 不存在 target 的草稿可创建，发布返回 500；本例回读仍为草稿、未生成 Tag，没有重试，不外推所有 500 无副作用 |

输入前检、写后核对和独立用途尚不在产品实现中，不能修复任意原生客户端。空字段清除路径与草稿 scope 不一致等限制进入 M0-S04，不能静默缩小功能或通过空格 / 删除重建模拟成功。

## 真实故障与只读回查

故障监听使用任务服务器证书，客户端继续验证 CA；精确路径 / Bearer / body、单次处理，只操作本任务固定端点。每个场景一次 caller 请求，1 秒真实 TimeoutError，自动重试均为 0。默认共享超时仍为 15 秒。

| 场景 | 上游传输 / 回执 | 回查结果 |
| --- | --- | --- |
| 创建、发布、附件已提交后扣留响应 | 分别一次写入，201 / 200 / 201；caller 超时 | 按精确 tag / ID、状态 / Tag SHA、附件字节等 GET 回查观察到唯一目标结果 |
| 三类请求完全不转发 | 上游写入 0，caller 仍超时 | 创建 / 附件零匹配，发布仍草稿且无 Tag；均 unknown，不自动写入 |
| 附件 Content-Length=1064，仅发送 532 bytes 后关闭 TLS 连接 | 一次部分传输，没有上游响应回执，caller 超时 | 零可见完整对象，unknown；没有证明所有临时存储已消失，不假定整个请求未执行 |
| 两个同名 / 同内容附件 | 两个明确创建的独立夹具 | 匹配 2、内容校验 2，仍 unknown，不选最新、不再 POST |

所有监听在场景退出时停止。查询失败 / 失权会停止而非返回空成功，半包 / 零匹配不触发补偿删除；合成标记不是生产幂等键或持久化请求关联。

## 来源、验证与交接

固定 Gitea 源码仍为 `829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1`，OpenAPI SHA-256 仍为 `c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`；Release / Tag 处理器、下载 scope 检查、转换和附件模型的来源摘要进入 JSON。web raw cache miss 后直接读取相同官方固定提交，没有换版本或引入第三方实现依赖。

`python3 -B -m unittest discover -s scripts/tests -q`：48 项通过，含原 35 项、新用途边界 1 项及 Release / 二进制决策 12 项；本地 Mock 不替代上述真实调用。最终 Release、Issue 和 profiles 回归的十项源码 / 配置摘要与交付文件一致；前三轮源码分别保存并提供从最终源码恢复的可验证补丁，不改写已执行摘要。Issue 原 12 条差异与 profiles 原禁用账号刷新差异均回归复现；新作用域没有把旧客户端计为已验证第四用途。历史生命周期 / Issue / 静态准备 records 保持原样。

`python3 -B scripts/check-repo.py` 通过：89 个文本文件 / 459 条本地链接；`git diff --check` 通过。交接复核含未跟踪文件的 UTF-8 / LF / 末尾换行、敏感信息模式、十项最终源码摘要、三份中断源码恢复补丁与空暂存区；只作为本地静态证据。

本批只验证普通个人仓库的合成 Release 与失败切片。尚未覆盖组织自定义 Release 单元权限、任意并发 / 崩溃恢复、生产请求持久化、真实工作台 / 发布器、GitHub 双端客户端、完整五组件清单与签名 / 冻结、对象存储重定向、OCI、Actions / Runner、amd64 与生产；不以缺失的 run / attempt 填占位值。下一步按 current 推进 OCI 和 M0-S04 完整取舍，Runner 暂停，M1 不启动。

六批均保存脱敏证据后 cleanup，逐标签读回容器 / 网络 / 卷均为 0；`.local/m0` 凭据 / 证书已移除，18443 / 19443 / 18543 端口已释放，当前无本任务服务。公开来源与源码快照临时目录在核对正式 JSON 已保留全部导出 / 摘要 / 恢复补丁后移除；共享镜像保留，不停止其他任务资源。没有提交新探针 / 证据、推送或对外发布。
