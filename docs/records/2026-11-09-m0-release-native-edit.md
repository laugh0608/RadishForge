# 2026-11-09 M0-S04 G20 原生草稿编辑实测

基线为 `aa8556facedfb6bee7e16ecea5c24df0e99b8a6d`。在本机 OrbStack 批次 `rf-m0-local-aa4c3b65` 使用已缓存的 Gitea 28.2.0-rootless 和 PostgreSQL 18.6-bookworm。镜像 Digest、Compose 资源限制及回环端口沿用既有 M0 配置，两个 Gitea 实例均回读 Actions 关闭。API 使用 Python 3.9.6 与任务 CA。原生页面使用缓存的 Playwright CLI 0.1.22、Playwright 1.64.0-alpha-1790635538000 和 Chrome 156.0.8078.80，浏览器信任只配置本批服务证书的 SPKI，`ignoreHTTPSErrors=false`。 [本机验证入口](../../tests/contracts/m0/README.md)

管理员仅准备合成账号。Alice 建立私有仓库 `alice/private-fixture`，赋予普通用户 Bob 仓库 `write` 权限，并通过协作者权限接口回读。Bob 持独立 `release_write` 授权创建 Tag、草稿和合成附件。网页用 Bob 的隔离会话，API 回读使用同一普通用户的独立 OAuth Bearer。浏览器登录由本地脚本读取临时密码，CLI 只载入本批会话。CLI 的代码执行环境无法从文件动态导入密码读取模块，因此改用同一缓存的 Playwright 登录浏览器生成会话，后续表单动作使用 CLI。

## 操作与回读

初始夹具为 Release ID `1`、标题 `M0 G20 original title`、非空说明 `M0 G20 notes to clear`、`draft: true`。附件 ID 为 `1`，名为 `m0-g20-attachment.bin`，实收 1064 字节，SHA-256 为 `5cf455217db1710351bb5a616296a9fd19f4d9bce832ddc12b43492053974d08`。预置 Tag `m0-g20-draft` 的实际提交为 `07d918471274a8e4a7582aef69d5816ac55c450a`。

| 原生页面操作 | 页面回执 | 独立 API 回读 |
| --- | --- | --- |
| 清空说明，保留标题，点击 Save Draft | 表单 POST 返回 200，回到 Release 列表，原条目仍显示 Draft。 | 21:22:12 CST 按原 ID 读取，`body` 为精确空字符串。标题、作者、草稿状态、预发行标记、附件 ID / UUID / 名称 / 实收字节及 SHA-256、Tag 和实际提交均与初始夹具一致。 |
| 清空标题，同时填入另一段说明，再点击 Save Draft | 表单 POST 返回 400，仍在编辑页并显示 `Title cannot be empty.`。 | 21:22:46 CST 按原 ID 回读，原标题与空正文均保留，拒绝的说明未写入。草稿状态、附件和 Tag / SHA 与上一步一致。 |

两次提交各发出一次。固定版普通写者可通过原生页面手动清空草稿说明，标题为空时保存会被拒绝。公开 REST PATCH 的空字段差异继续保留。产品可将用户引导到原生页面，公开 API 调用边界沿用 ADR 0005。 [固定 Gitea 页面处理器](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/repo/release.go#L576-L629) · [REST 对照](2026-11-09-m0-gitea-rest-comparison.md) · [ADR 0005](../adr/0005-release-authorization-and-reconciliation.md)

## 清理

专用 Playwright 浏览器已关闭，任务缓存回读无浏览器会话。按批次标签回读容器、卷和网络各为 0，回环端口 18443 / 19443 已释放，`.local/m0` 的凭据、会话、临时脚本和快照已清理。共享镜像缓存保留。
