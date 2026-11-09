# 2026-11-09 M0-S04 GitHub 所有者只读 PAT

用私有测试仓库 `laugh0608/RadishForge-Test`（ID `1451320859`）和 GitHub REST `2026-03-10` 执行。本次身份为仓库所有者，独立 fine-grained PAT 的私有仓库选择仅含本测试仓库，`Contents`、`Issues` 和 `Metadata` 设为只读，有效期 7 天。所有者在本机终端的隐藏提示输入凭据。 [执行入口](../../tests/contracts/m0/compat/rest-runbook.md#github-单账号凭据对照)

2026-11-09 21:02:20 CST 开始运行，基线提交为 `d6bd77a`。当时未提交的 `scripts/m0_github_scope.py` SHA-256 为 `434a43f009fb72e24b329ee54f781680d9e7914f27ff076a3ecbca1953f77202`。本地脱敏结果 `m0-scope-b38fbceb6aeb.json` SHA-256 为 `3b3281b4ddf2735084db4f7242e91260f74620917d2b7b53556e0078dc723b35`，文件权限为 0600。

| 用例 | 实际回执与读回 |
| --- | --- |
| 既有凭据对照 | 身份、私有仓库、固定提交、合成 Release 和 Actions 设置均为 200，Actions 为关闭；匿名读私有仓库为 404。 |
| 只读 PAT | `GET /user`、私有仓库、Issue #4 和 Release `439093746` 均为 200，身份与对象匹配。 |
| 拒绝写入 | 以只读 PAT 尝试创建 Issue 和草稿 Release 均为 403。探针确认是 PAT 权限不足，并用既有凭据分别以 GET 回读，未出现带本次标记的对象。 |
| 凭据撤销 | 操作者输入 `REVOKED` 后，同一 PAT 读私有仓库仍为 200，既有凭据对照也是 200。探针退出 1。随后在 GitHub Fine-grained tokens 列表读到 `RadishForge M0 read-only validation` 仍列出，未取得该凭据已从列表移除的回执。 |

21:08:38 CST 启动 `--revocation-only` 复测，21:09:18 操作者确认后，PAT 和既有凭据读取仍各为 200，探针退出 1。该轮只发 GET，探针 SHA-256 为 `78a3f267ee27f91f98936eeb862175296e992a76da0b0f3071043461546c80eb`，脱敏结果 `m0-scope-bd11b6ffa962.json` SHA-256 为 `d4a3facdbdeb8ea8a50c7df9b905adba4ec6c78a051f229a689c8b3f648ec03a`。

用户随后手动删除。GitHub 设置页一度显示删除失败提示，同页列表已为空。刷新后提示消失，仍显示无 Fine-grained PAT。账号安全日志在 21:10 CST 为同名 PAT 记录 `personal_access_token.access_revoked` 和 `personal_access_token.destroy`，晚于上述 200 回执。 [GitHub 安全日志事件](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/security-log-events)

21:13:50 CST 启动 `--check-revoked`。用户确认输入的是同一 PAT 原值，读取测试仓库返回 401，既有所有者凭据读取同一仓库仍为 200，探针记录 `supplied_pat_rejected`。该轮只发 GET，探针 SHA-256 为 `b2afdf3aef4ed0785c5cc6b925bab67e48310ed3d87b9267c01c6306be95b8ed`，脱敏结果 `m0-scope-d1df7d7e763f.json` SHA-256 为 `57a909230d5ce7e761e6105b93e163e25fa20058f95c540e51ad81d22f5a4977`，文件权限为 0600。证据覆盖删除后该次请求的拒绝，精确失效时刻未测。协作者仓库权限撤销另用独立身份验证。 [当前状态](../status/current.md)
