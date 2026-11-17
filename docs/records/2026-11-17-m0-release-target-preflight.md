# 2026-11-17 M0 G23 发布目标前检回归

以 G22 隔离实测提交 `dc33663` 为基线。G23 的历史实测中，不存在的目标可保存为草稿，原生发布返回 500。该批回读仍为草稿且无 Git Tag，保留原回执和适用范围。 [原始 Release 证据](2026-11-04-m0-release-validation.md#保留的五项差异)

当发布明确允许新建 Tag、原 Tag 查询为 404 时，M0 探针先核对草稿的 `target_commitish`，再以同一写者凭据请求目标仓库的 `GET /git/commits/{sha}`。提交响应须为 200 且返回同一完整 SHA 才能发送发布 PATCH。已有 Tag 的路径继续按实际 Tag SHA 核对。共享 `release-publication` 入口的正向证据检查已纳入新增 GET 的路径与顺序。 [Release 授权与对账](../adr/0005-release-authorization-and-reconciliation.md)

本地模拟覆盖正向新 Tag 和已有 Tag，以及提交查询 404 / 403 / 500、超时、返回不同 SHA 或缺少 SHA 的情形。正向新 Tag 在确认提交后只发一次 PATCH，所有失败情形只有三次 GET。19 项 Release 定向测试、70 项本地测试和仓库治理检查通过。

新增前检待固定版 Gitea 隔离复测。本批沿用历史 500 证据，验证层级为本地模拟。Runner / Actions 继续暂停，未启动 OrbStack 服务或使用额外账号。
