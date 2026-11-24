# M0 OCI 权限、留存与恢复操作单

按[首版留存与撤销决定](../../../../docs/adr/0006-oci-authorization-and-digest-retention.md#first-release-oci-decisions)验证 G24—G26，复用 G27 的原 PAT 拒绝证据。先取得一批普通角色、固定 Digest、真实包清理与恢复的证据。这批使用本机 Linux arm64 上游协议环境，工作流和 Release 组合另按原计划取证。

2026-11-17 已由[定向探针](../../../../scripts/m0_oci_retention.py)完成一批隔离实测。见[结果与未覆盖范围](../../../../docs/records/2026-11-17-m0-oci-retention-validation.md)。

## 资源与准入

- 复用[本机契约环境](../README.md#资源与授权)的 OrbStack、Gitea 28.2.0-rootless / PostgreSQL 18.6-bookworm 固定 Digest、任务 CA 和 2.75 GiB 容器内存上限，回环端口 18443 / 19443。Actions 关闭。复用 [Registry 原始字节检查](../../../../scripts/m0_registry.py)和同源、无 cookie 的 [API 客户端](../../../../scripts/m0_oauth.py)。本批用合成 OCI 字节，不需要 regctl、Buildx、额外监听或新 VM。
- 缓存缺失时，按固定的 arm64 manifest 校验，Gitea 压缩层 65,196,193 字节，PostgreSQL 155,251,271 字节，合计约 210 MiB；Gitea 两个容器共用同一镜像。预计含解包和验证数据预留 2 GiB；Docker 数据写入本机 OrbStack，合成夹具、凭据和原字节副本留在本批 `.local/m0`。镜像作为共享缓存保留，临时卷和目录随本批清理。
- 拟占用约 45 分钟，含读取固定镜像、实际清理与隔离恢复。获得本批拉取与运行授权后，回读上下文、端口、磁盘、项目标签和镜像平台，再用下列入口。固定镜像拉取失败、资源归属不明或预算超出时停止。单个写请求超时先对账，保留失败或未知结果。

```bash
python3 scripts/m0_local.py prepare --context orbstack --auth-profile
python3 scripts/m0_local.py pull
python3 scripts/m0_local.py up
python3 -u -B scripts/m0_oci_retention.py
# 从 .local/m0/oci-retention-results.json 复核、导出脱敏证据。
python3 scripts/m0_local.py status
python3 scripts/m0_local.py cleanup
```

退出 2 表示流程完成且保留原生 G25 差异。退出 1 时保留中断证据，先按所有权清理，再开新批次。先导出脱敏结果，再执行清理。

## G24 / G25 权限矩阵

在空批次用普通账号建立三个私有组织 `m0-private-org`、`m0-build-alt`、`m0-release-org` 及同名合成包 `m0-probe`。首个组织与现有签发夹具的目标一致。发布管理员仅管理发布组织、独立保存副本并执行例外恢复；部署读取者只有发布组织读取角色；构建写者在前两个组织都有包写权限，在发布组织只有私有源码仓库的外部协作权。站点管理员只准备合成账号并触发清理。逐项从公开 API 回读私有可见性、team 单元权限、成员 / 协作者状态及包关联，然后用对应组织的独立读凭据证明各目标 Digest 存在。

| 凭据与目标 | 期望和必留证据 |
| --- | --- |
| 构建写者用独立 `write:package` PAT 对第一个构建组织请求 `pull`，用同一 Bearer 访问两个构建组织 | 分别读取已知 Manifest / Blob 并按原字节核对 Digest；仅启动空上传并删除已知上传。记录 JWT 声明仍为 `write:package` 与两处行为，保留 G25 原生差异。 |
| 同一 Bearer 访问发布组织中的现存 Digest，以及在该组织启动上传 | Manifest / Blob 直连均拒绝，响应无夹具内容与匹配 Digest，上传返回拒绝且无有效 Location。包链接到构建写者能读的私有源码仓库后再复核。 |
| 同一构建写者的独立 `read:package` PAT 对第一个构建组织请求 `pull,push` | 在其有真实写角色的目标读取 Digest 成功，启动上传仍拒绝且无有效 Location。 |
| 部署读取者持发布组织的只读 PAT | 按原 Digest 拉取发布制品，启动上传和删除均拒绝。再用匿名请求直接读取同一私有包，核对拒绝且无夹具内容。 |

HTTP 拒绝须与对象存在、实际权限和同期正例对账，禁止用缺失对象的 404 证明权限拒绝。意外返回制品字节、确认上传或越权写入时登记差异并停止后续制品验证；只清理可确认归属的上传或本批资源。记录目标坐标、角色、声明 scope、原始状态、摘要及副作用，不保存 PAT / JWT 或上传 URL。

## G26 真实清理与按原 Digest 恢复

1. 发布管理员准备同一发布包下内容不同的 A、B 及独立的可删除对照 C。A 模拟上一可回退版本，B 模拟现行版本；保存两个环境假定引用、各自原坐标和全部描述符。发布 A / B 前保存可独立取得的原始 Manifest、config 和层字节，校验原始大小、Digest 与副本归属。C 使用不同 Digest 且无保留引用。为 A / B 建立独立的 `m0-retain-a` / `m0-retain-b` 引用，由只读凭据分别按 Tag 和 Digest 核对，随后把一个普通活动 Tag 从 A 移到 B。
2. 用发布管理员在该合成组织的原生包设置保存 Container 清理规则。定向短测使用版本名保留匹配 `m0-retain-(a|b)`、删除匹配 `m0-retain-(a|b)|m0-prune-control`，保留数量和年龄过滤均为 0；C 的 Tag 是 `m0-prune-control`。先回读保存值，预览确认为候选删除 C，保留 A / B 的发布引用。规则若表现不同，保留设置和预览结果，停止触发清理。年龄为 0 仅用于本批合成正反例，使 C 当场满足删除条件。
3. 用站点管理员只调用一次 `POST /api/v1/admin/cron/cleanup_packages`，先后回读 `GET /api/v1/admin/cron` 运行记录及对象。204 是触发回执。以 C 的 Tag 被清理、A / B 的独立发布引用及原 Digest、config 和所有层仍匹配作为规则通过条件。C 的原 Digest 与 Blob 存续单独回读。普通构建写者对发布命名空间的 OCI 同名覆盖、Manifest / Blob 删除和 Packages REST 版本 / 整包删除均须被拒绝。写负例用发布组织内另备的可牺牲包，要求现存对象、拒绝回执与独立回读一致；原生页面的删除角色验证须检查服务端拒绝。 [固定清理机制](../../../../docs/records/2026-11-09-m0-oci-public-mechanisms.md)
4. 只对合成 A 记录一次发布管理员例外删除，保留 B 作为健康对照。独立读者先确认 A 缺失并记录回退前检查应阻断；以隔离副本的原始字节恢复 A 到原命名空间 / 包坐标，复核 Manifest / config / layers 摘要、大小与字节，再记录回退前检查可继续。恢复失败或重新上传改变 Digest 时停止。恢复过程只操作 OCI 夹具，环境切换和产品阻断仍按产品阶段验收。

产品侧时间口径以实际切换时点、引用与保留记录为准。固定版清理规则的年龄比较使用包版本创建时间，所以候选方案通过独立发布引用保护仍生效的环境引用和窗口，达到期满且无引用后才允许释放保护。取证样例中，A 在测试环境于 2026-11-17 08:00 UTC 被替换，在生产环境于 2026-11-21 08:00 UTC 被替换；两次切换均成功且没有其他引用时，最早到 2026-12-21 08:00 UTC 才能释放保护。后续成功切换其他版本仍保留 A 已生效的窗口。短测验证真实清理中的保护、拒绝与原字节恢复，30 天窗口的时间边界和持久化由产品验证覆盖。 [固定清理实现](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/packages/cleanup/cleanup.go)

按路径归档脱敏响应、原始内容摘要、清理读回及异常；包括中断在内，最后按本机入口清理并逐项目读回容器、卷、网络及端口，移除本批私密文件。G27 沿用[删除 PAT 后交换拒绝与旧 Bearer 换发实测](../../../../docs/records/2026-11-09-m0-registry-bearer-reissue.md)，后续在产品中验证本地停用。单批用例通过后仍需原生 Runner 与组合链路证据。
