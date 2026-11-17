# 2026-11-17 M0 G23 发布目标前检回归

以 G22 隔离实测提交 `dc33663` 为基线。G23 的历史实测中，不存在的目标可保存为草稿，原生发布返回 500。该批回读仍为草稿且无 Git Tag，保留原回执和适用范围。 [原始 Release 证据](2026-11-04-m0-release-validation.md#保留的五项差异)

当发布明确允许新建 Tag、原 Tag 查询为 404 时，M0 探针先核对草稿的 `target_commitish`，再以同一写者凭据请求目标仓库的 `GET /git/commits/{sha}`。提交响应须为 200 且返回同一完整 SHA 才能发送发布 PATCH。已有 Tag 的路径继续按实际 Tag SHA 核对。共享 `release-publication` 入口的正向证据检查已纳入新增 GET 的路径与顺序。 [Release 授权与对账](../adr/0005-release-authorization-and-reconciliation.md)

本地模拟覆盖正向新 Tag 和已有 Tag，以及提交查询 404 / 403 / 500、超时、返回不同 SHA 或缺少 SHA 的情形。正向新 Tag 在确认提交后只发一次 PATCH，所有失败情形只有三次 GET。19 项 Release 定向测试、70 项本地测试和仓库治理检查通过。

新增前检待固定版 Gitea 隔离复测。本批沿用历史 500 证据，验证层级为本地模拟。Runner / Actions 继续暂停，未启动 OrbStack 服务或使用额外账号。

## 固定版 Gitea 隔离复测

本地前检已提交 `a37c21d`。随后在 OrbStack 独立批次 `rf-m0-local-44ecbfb4` 用 `--mode release-publication` 复测。复用 Linux arm64 的 Gitea 28.2.0-rootless 和 PostgreSQL 18.6-bookworm 固定镜像，Engine 29.8.2、Compose 5.5.0。普通协作者以 `write` 角色和 `release_write` 凭据操作私有仓库，两套实例的 Actions 设置均回读为关闭。 [脱敏请求与源码摘要](2026-11-17-m0-release-target-preflight-results.json)

新 Tag 用例固定目标提交 `c0a12f5d254abf47d74b0df212d610fd7535f782`。实际顺序如下。

| 顺序 | 请求 | 结果 |
| --- | --- | --- |
| 1 | GET 原 Release ID `2` | 200，仍为草稿 |
| 2 | GET 原 Tag `m0-g22-new` | 404 |
| 3 | GET 目标仓库的完整 SHA | 200，响应 SHA 与预期逐字符一致 |
| 4 | PATCH 原 Release ID `2` | 200，仅发一次 |
| 5 | GET 原 Release 和原 Tag | 均为 200。原 ID 和 Tag 已发布，Tag 指向同一完整 SHA |

已有 Tag 的对照和两种超时只读回查同时通过。共 8 条通过记录、59 条脱敏请求，探针退出 0。本轮真实证据覆盖新建 Tag 的成功前检；提交查询失败后的零 PATCH 仍使用本地模拟证据。原生 G23 的历史 500 记录继续适用。

容器、卷及网络按本批标签回查均为 0，18443、19443、18543 已释放，`.local/m0` 与其中的凭据已移除。固定镜像仍在缓存，Runner 未启动。
