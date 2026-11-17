# 2026-11-17 M0 G22 Release 发布回读回归

以 `3111071` 为基线，沿 M0-03 / M0-04 的 Release 固定引用和未知结果合同推进。现有探针在 PATCH 成功后按回包中的 `tag_name` 查 SHA，同一提交上的其他 Tag 可能通过检查。发布超时的探针也只检查草稿状态和原 Tag SHA，缺少对返回对象的 ID / Tag 名校验。 [原始 Release 差异](2026-11-04-m0-release-validation.md#保留的五项差异) · [ADR 0005](../adr/0005-release-authorization-and-reconciliation.md)

个人仓库 Release、组织权限和同源 REST 探针共用同一发布前后校验。发布前检查原草稿 ID、Tag 名和已存在 Tag 的完整 SHA。明确允许在发布时创建 Tag 的夹具也会检查草稿的完整 `target_commitish`。发布后核对原 Release 的发布状态与原 Tag 的实际完整 SHA。超时场景只读回原 Release 和 Tag，所有检查一致时才确认观察到对应发布。

本机模拟传输新增六项用例，覆盖既有 Tag 与新 Tag 的正向路径，错 ID / 错 Tag / 错状态的写前拒绝，已有 Tag 缺失或指向不同提交，以及写后回读错对象、Tag 漂移或消失和超时错对象。用例检查请求方法及路径，明确写前拒绝发出零次 PATCH，写后不一致发出一次 PATCH，超时对账只发 GET。

`python3 -B -m unittest discover -s scripts/tests -p test_m0_releases.py -v` 的 18 项及完整套件的 69 项通过，`python3 -B scripts/check-repo.py` 和 Git 空白检查通过。本批只使用本地模拟传输，没有服务启停、网络联调、额外账号或 amd64 资源。原固定版 Gitea 的 G21—G23 差异继续适用，更新后的探针待新隔离批次复验。Runner / Actions 暂停，真实 run / attempt、Digest 与 Release 的组合仍待验证。

## 固定版 Gitea 隔离实测

本地回归已提交 `dc36df8`。随后在 OrbStack 新批次 `rf-m0-local-155a31f6` 用 `--mode release-publication` 验证。复用 Linux arm64 缓存的 Gitea 28.2.0-rootless 和 PostgreSQL 18.6-bookworm，Engine 29.8.2、Compose 5.5.0。仅使用任务 CA 和回环网络。普通协作者 Bob 的仓库 `write` 角色和 `release_write` 授权均回读通过。两套实例回读确认 Actions 关闭。 [脱敏请求与源码摘要](2026-11-17-m0-release-publication-results.json)

固定源码 SHA 为 `e93dfa7f77e76ffc094b8a17d6edbc679445d024`。

| 场景 | 实际写入 | 回读结果 |
| --- | --- | --- |
| 已有 Tag `m0-g22-existing`，Release ID `1` | 单次 PATCH 200 | 同一 ID 和 Tag 从草稿变为已发布，Tag 在写前和写后均指向固定 SHA |
| 新 Tag `m0-g22-new`，Release ID `2` | 单次 PATCH 200 | 写前原 Tag GET 404，草稿目标为固定 SHA。写后同一 ID 和 Tag 已发布，Tag GET 200 并指向固定 SHA |
| 上游已提交，调用方超时，Release ID `3` | 单次上游 PATCH 200 | 两次 GET 均为 200，原 ID / Tag 已发布且 SHA 匹配，记为 `observed` |
| 请求未转发，调用方超时，Release ID `4` | 零次上游 PATCH | 两次 GET 为 200 / 404，原 ID / Tag 保持草稿且 Git Tag 缺失，记为 `unknown` |

两次超时均为实测 `TimeoutError`。对账分别只读原 Release 和原 Git Tag，自动重试为 0。探针完成 8 条记录、58 条请求日志，退出 0。原生 G22 差异以及 G21 / G23 的原记录仍适用。发布前后分次回读仍有并发窗口，产品和真实 Runner 组合仍待验证。

结束后按本批项目标签确认容器、卷和网络均为 0，18443、19443 和 18543 均可重新绑定，`.local/m0` 及其中的凭据已删除。固定镜像仍在缓存，Runner 未启动。
