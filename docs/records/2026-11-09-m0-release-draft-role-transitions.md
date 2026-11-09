# 2026-11-09 M0-S04 G19 草稿降权与撤权实测

基线为 `5e6e39c34a3e46ddc75d2cc1ae6c3df0199bdd9e`。本机 OrbStack `orbstack` 批次 `rf-m0-local-45c704e8` 使用已缓存的 Gitea 28.2.0-rootless / PostgreSQL 18.6-bookworm、Linux arm64、Engine 29.8.2 / Compose 5.5.0。沿用固定镜像 Digest 和 `prepare --auth-profile`，回环 18443 / 19443，两套实例回读 Actions 关闭。API 使用 Python 3.9.6 与任务 CA，资源请求只携带对应 Bearer，无浏览器 Cookie。 [M0 本机入口](../../tests/contracts/m0/README.md) · [G19 源码核查](2026-11-09-m0-release-public-mechanisms.md#m0-g19--草稿权限)

管理员仅准备三个合成普通账号。Alice 创建个人私有仓库 `alice/private-fixture`（ID `1`），Bob 为普通协作者，Carol 为外部对照。Alice 持独立 `resource_read` 与 `release_write` 凭据。Bob 用同样两个用途分别授权，在基线前刷新一次后，按 `write → read → none` 切换角色并逐次回读。角色切换期间两枚 access token 均沿用原值，三个阶段的 introspection 均为 active，在线账号始终为 Bob，scope 保持原值。

草稿 ID `1`、Tag `m0-g19-draft`、附件 ID `1`。已发布对照 ID `2`、Tag `m0-g19-published`、附件 ID `2`。两条预置 Tag 均指向 `9242cd509f8292e5e44e45a9767836ea97d12583`。草稿附件实收 1064 字节，SHA-256 为 `5cf455217db1710351bb5a616296a9fd19f4d9bce832ddc12b43492053974d08`。已发布附件实收 31 字节，SHA-256 为 `48d156f139d3999060e77c9617fe7d4913dce1525e5e9501a834e8711c9e61a1`。

| 角色与凭据 | 草稿列表 | 草稿按 ID / 按 Tag | REST 附件列表 / 单项 | UUID / Tag 与文件名下载 | 已发布按 Tag / 两路下载 |
| --- | --- | --- | --- | --- | --- |
| Alice 所有者，`release_write` | 200，含草稿 | 200 / 200 | 200 / 200 | 200 / 200 | 撤权后复核均为 200 |
| Alice 所有者，`resource_read` | 200，空列表 | 404 / 200 | 404 / 404 | 200 / 200 | 本组未测 |
| Bob 普通写者，`release_write` | 200，含草稿 | 200 / 200 | 200 / 200 | 200 / 200 | 均为 200 |
| Bob 普通写者，`resource_read` | 200，空列表 | 404 / 200 | 404 / 404 | 200 / 200 | 均为 200 |
| Bob 降为读者，原两枚凭据 | 200，空列表 | 404 / 404 | 404 / 404 | 404 / 404 | 均为 200 |
| Bob 移除权限，原两枚凭据 | 404 | 404 / 404 | 404 / 404 | 404 / 404 | 均为 404 |
| Carol 外部用户，`release_write` | 404 | 404 / 404 | 404 / 404 | 404 / 404 | 均为 404 |
| 匿名 | 403 | 403 / 403 | 403 / 403 | 303 / 303，同源登录页 | 403 / 303 / 303 |

只读凭据按 Tag 得到同一草稿 ID、完整说明和附件元数据，两路下载字节与摘要一致。读者、撤权用户、外部用户和匿名拒绝响应均未包含对应夹具字节或草稿说明。普通写者持只读凭据交叉使用草稿与已发布 Tag、附件名，两路均为 404，未返回草稿字节。所有者在 Bob 被移除后仍可读两个对象和附件，两条 Tag 的实际提交回读一致。

实测在 21:29:31–21:29:34 CST，临时探针完成 30 个记录项、106 次矩阵 GET。探针 SHA-256 为 `16336d12399a603e1bd9af678500e0576520504d1311776287d04c5ffd30b861`，脱敏临时结果 SHA-256 为 `db3bfbb2d5984791a15b93bcfd9f9efc98c3651eb5e299ec59062c919e1b26a4`。

Gitea 按当前仓库角色执行草稿降权和撤权，同时保留写者持只读凭据按 Tag 查草稿、下载附件的原生差异。产品草稿入口仍需同时核验 `release_write` 和当前单元写权限。证据限定于该个人私有仓库、任务配置和本地附件存储。组织单元、对象存储直链和产品实现按启用配置另验。 [ADR 0005](../adr/0005-release-authorization-and-reconciliation.md)

批次已清理。按标签回读容器、卷和网络各为 0，回环端口 18443 / 19443 已释放，`.local/m0` 中的任务凭据和临时文件已移除。
