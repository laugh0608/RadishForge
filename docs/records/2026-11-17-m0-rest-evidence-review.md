# 2026-11-17 M0-S04 首批 REST 证据复核

以 `596d1b7` 为基线，对照 GitHub REST `2026-03-10`、本机 gh `2.96.0` 和 Gitea 28.2.0 的历史取证。复核本地 `rest-source.fi` 的 SHA-256 为 `223a5feddbd5791ad883a2a4b30aabdd209aa15193508e929334650b55cb7cef`，11 字节附件的 SHA-256 与原记录一致。 [GitHub 原始参考](2026-11-09-m0-github-rest-reference.md) · [Gitea 同源对照](2026-11-09-m0-gitea-rest-comparison.md)

## GitHub 测试仓库只读预检

`scripts/m0_github_scope.py --preflight` 的所有者身份、仓库、固定提交、已发布 Release 和 Actions 设置读取均为 200，匿名仓库读取为 404。仓库 ID 仍为 `1451320859`，私有、默认分支为 `main`、Issues 可用、Actions 关闭。

用现有 gh 登录逐一回读三个实际引用。主分支与 `m0-release-01` 指向 `37aa3d3ca05aa645e8d970a233b95fcebf35452c`，PR 夹具分支指向 `3527c7d63bebdc0eb5df3405dc23020950df2816`。已发布 Release ID 为 `439093746`，附件 ID 为 `727365986`，服务器仍报告 11 字节和 SHA-256 `d21cc231a75725ea02671f51c78c42ba501078b9d1b77bc4ca2c2c735c3db285`。本次读取附件元数据，字节证据沿用原批。协作者分页结果只含仓库所有者，普通协作者为 0。以上操作均为 GET。

## 已有行为与仍需验证的项目

| 首批用例 | 已有对照 | 仍缺的证据 |
| --- | --- | --- |
| 私有仓库、提交 | 两端的有权凭据均读到固定提交。匿名读取在 GitHub 为 404，在本机受控 Gitea 为 403。 | GitHub 普通读取者和已认证无权用户的对照。 |
| Issue 集合、写入 | 相同夹具中，GitHub 列表含带 `pull_request` 的 PR，分页实际出现带 `after` 的 `Link`；Gitea 用 `type` 和 `limit` 分别查询。两端创建、评论、关闭后读回一致；关闭回执为 GitHub 200、Gitea 201。 | GitHub 普通写者、权限降低或移除后的实际写入拒绝及无副作用读回；分页转换和指定客户端效果在兼容入口实现后验收。 |
| Release 与附件 | 两端录得真实相同附件字节；GitHub 下载经 302 后取得 200，Gitea 返回同源 200。GitHub 所有者曾通过 PATCH 清空说明，固定 Gitea 保留原值，G20 后续又证实混合 PATCH 部分写入。 | GitHub 普通团队角色对草稿、附件和已发布对照的行为；G19 / G20 的原生差异及产品处理继续沿 ADR 0005。 [G19](2026-11-17-m0-release-org-role-transitions.md) · [G20](2026-11-17-m0-release-edit-fields.md) |
| 凭据与角色撤销 | GitHub 所有者只读 PAT 写入拒绝、删除后读取被拒绝。Gitea 普通角色移除后资源被拒且同一凭据仍能识别用户。 | 独立 GitHub 账号的仓库角色授予及撤销。 [GitHub 所有者 PAT](2026-11-09-m0-github-owner-pat.md) |

下一轮优先取得 GitHub 普通角色参考。若用同一批验收仓库 `Read` / `Write`，选获准的私有组织仓库与独立普通成员，核对两个角色和凭据各自的范围。现有个人私有仓库可作为普通写者 / 移除协作者的备选；它只能授予协作者写权限，fine-grained PAT 对仓库协作者的贡献也有限制。已确认可读的历史夹具作为参考保留，后续写入用新标记、Tag 及独立读回。 [执行手册](../../tests/contracts/m0/compat/rest-runbook.md) · [GitHub 个人仓库权限](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository#collaborator-access-for-a-personal-account-repository) · [GitHub 凭据限制](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#fine-grained-personal-access-tokens-limitations)

原 COMP-01 状态和 27 条差异保持，GitHub 普通角色继续待验证。Runner / Actions 暂停，M0 阶段出口继续适用。本轮无远端写入、服务启停或新运行资源。
