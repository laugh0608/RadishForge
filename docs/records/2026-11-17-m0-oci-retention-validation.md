# 2026-11-17 M0 OCI 权限、清理与恢复实测

按 Asia/Shanghai 记录。所有者明确授权在 OrbStack 拉取固定镜像、运行本机隔离服务、实测 G24—G26 并清理。沿用[操作单](../../tests/contracts/m0/compat/oci-retention-runbook.md)，运行[定向探针](../../scripts/m0_oci_retention.py)。各批脱敏请求、摘要、退出码与清理读回见[结果 JSON](2026-11-17-m0-oci-retention-results.json)。

## 环境与批次

OrbStack Engine 29.8.2、Compose 5.5.0。按固定 index 拉取 Gitea 28.2.0-rootless 和 PostgreSQL 18.6，两枚镜像实际读取为 Linux arm64。PostgreSQL 18.6 由运行容器回读；两套 Gitea 通过任务 CA 的 TLS 就绪检查，Actions 关闭。使用 18443 / 19443 回环端口、独立项目与空卷。无 Runner、regctl、Buildx、外部写入、系统信任改动或宿主升级。镜像传输约 210 MiB，缓存保留。

| 项目 | 结果 |
| --- | --- |
| `rf-m0-local-83145728` | 退出 1。匿名请求 API 版本返回 403，尚未创建账号或数据。改用公开健康检查，再由合成站点管理员回读版本。 |
| `rf-m0-local-860b4175` | 退出 1。G24 / G25 已取得预期数据面证据，探针误要求旧版 CSRF Token，尚未提交清理规则。读回原生表单及固定源码，改用同源请求的 `Origin`。 [Gitea 28.2.0 Web 鉴权实现](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/web.go#L177-L220) |
| `rf-m0-local-09fe1c40` | 最终源码完成，26 条记录、224 次请求，退出 2。同一 G25 原生差异记录了两个允许命名空间的结果。 |

两次中止均先保存结果、清理，再新建空批次。已开始标记未被移除后重放，未重发已知或结果未知的写请求。

## 实际结果

| 项目 | 观察与回读 |
| --- | --- |
| G24 发布组织 | 构建写者可读取私有源码仓库，组织成员回查为 404。同一写 Bearer 访问现存发布 Manifest / Blob，关联仓库前后均为 401，启动上传为 401，未返回制品字节或上传位置。部署读取者按原 Digest 读取 200，上传和删除 401。匿名直读 Manifest / Blob 均为 401。 |
| G25 签发与独立读凭据 | 请求 `pull` 后 JWT 声明仍为 `write:package`，同一 Bearer 在两个获授权构建组织均读取 200、启动空上传 202。两次上传删后读回 404。相同用户使用独立 `read:package` PAT 请求 `pull,push`，读 200、启动上传 401。原生请求粒度差异保留。 |
| G26 清理 | 发布管理员在原生包设置保存规则并读回，预览只列删除对照。一次真实清理触发返回 204，执行计数 1 → 2。对照 Tag、Manifest Digest 和独有 config 均为 404，共用层仍为 200。移动活动 Tag 后，A / B 的独立 Tag、原 Digest、config 和层均按字节、大小和摘要回读。 |
| G26 写权限 | 构建写者的 OCI 覆盖、Manifest 删除和 Blob 删除均为 401，Packages REST 删版本和整包均为 403。发布组织读取者以原生页面表单提交删除返回 404。每个负例后独立读回夹具仍为 200。 |
| G26 例外恢复 | 发布管理员删除合成 A，返回 202。独立读者按原 Digest 观察到 404，B 仍健康。由预先保存的副本恢复到原包坐标，独立读者按 Tag 和 Digest 读回 A，Manifest、config 和 layer 的字节、大小及摘要与删除前一致。A 的原 Manifest 为 `sha256:6703fc0dffe93d284222713ec423e20037b5ffba4429e275668a5c02c925a469`。 |

本轮覆盖实际清理与原字节恢复，规则短测的年龄过滤为 0。30 天实际运行、产品侧保留计时与回退操作未执行。G27 沿用原 PAT 交换拒绝与旧 Bearer 换发证据。原四条 OCI 差异总数保持，M0 仍待原生 Runner、真实 run / attempt 与镜像 / Release 组合取证。

三批项目在 OrbStack 逐项读回容器、卷、网络均为 0。18443 / 19443 可重新绑定，`.local/m0` 与本批凭据、证书、备份均已移除。脱敏结果转存后删除任务临时副本。

最终源码摘要与第 3 批结果匹配，本地治理和 63 项 unittest 通过。工作区改动未暂存、提交或推送。
