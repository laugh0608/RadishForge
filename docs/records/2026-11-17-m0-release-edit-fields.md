# 2026-11-17 M0-S04 G20 Release PATCH 字段实测

G19 已提交为 `041cd88`。随后在 OrbStack 空批次 `rf-m0-local-ae770684` 按 M0-S04 计划验证 G20，沿用固定 Gitea 28.2.0-rootless / PostgreSQL 18.6-bookworm 镜像、Linux arm64、Engine 29.8.2 / Compose 5.5.0 和任务 CA。Runner / Actions 暂停，未下载新镜像或对外写入。 [脱敏请求与源码摘要](2026-11-17-m0-release-edit-results.json)

普通写者用 `release_write` 编辑私有仓库内的同一合成草稿，普通所有者以独立凭据按原 ID 回读。每例只发送一次 PATCH，记录 HTTP 状态及实际字段。成功响应和独立回读结果一致。

| PATCH 输入 | HTTP | 实际副作用 |
| --- | --- | --- |
| 只传非空 `name` | 200 | 标题更新，省略的说明保留 |
| 只传非空 `body` | 200 | 说明更新，省略的标题保留 |
| 非空 `name` 与空 `body` | 200 | 标题更新，说明保留旧值 |
| 空 `name` 与非空 `body` | 200 | 标题保留旧值，说明更新 |
| `name: null` 与 `body: null` | 200 | 两个字段均保留旧值。该输入位于公开字符串契约之外 |

Release ID `1` 保持草稿，附件 ID `1` 的原始 1064 字节及 SHA-256 `5cf455217db1710351bb5a616296a9fd19f4d9bce832ddc12b43492053974d08` 一致。Tag `m0-g20-edit` 仍指向 `57f0188694aabaacd61984c73244212deb974bf0`。本批完成 11 条记录、56 次请求，两个混合用例复现同一 G20 差异，退出 2。

G20 继续采用 ADR 0005 的边界。合法非空字段可以更新，显式清空须在产品向上游发送 PATCH 前拒绝整个请求，`null` 由字符串契约校验拒绝。原生页面手动清空草稿说明沿用既有实测。产品侧零上游写入仍待实现和验收。 [ADR 0005](../adr/0005-release-authorization-and-reconciliation.md) · [固定版 PATCH 实现](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/v1/repo/release.go#L348-L394)

按项目标签确认容器、卷和网络均为 0，18443 / 19443 已释放，`.local/m0` 与任务临时文件已移除，固定镜像保留为缓存。M0 继续进行。
