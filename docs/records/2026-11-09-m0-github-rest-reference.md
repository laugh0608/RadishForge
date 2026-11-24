# 2026-11-09 M0-S04 GitHub REST 参考取证

## 目标与范围

用户授权在其 GitHub 账号创建正式命名的私有测试仓库。本批使用 [laugh0608/RadishForge-Test](https://github.com/laugh0608/RadishForge-Test)，仓库 ID `1451320859`。创建回执为 201，回读为 `private: true`、`visibility: private`、`default_branch: main`、`has_issues: true`。创建时 Actions 默认启用，在该测试仓库以 PUT 关闭，后续 GET 回读 `enabled: false`。正式 RadishForge 的远端和本地 `origin` 保持原状。 [仓库创建接口](https://docs.github.com/en/rest/repos/repos?apiVersion=2026-03-10#create-a-repository-for-the-authenticated-user) · [Actions 设置接口](https://docs.github.com/en/rest/actions/permissions?apiVersion=2026-03-10#set-github-actions-permissions-for-a-repository)

以 GitHub CLI `v2.96.0` 核对本机凭据的账号、建立目标并复核设置，以 Python 标准库执行原始 REST 样例，API 版本固定 `2026-03-10`。`GET /user` 返回 `laugh0608`，仓库权限回读为 `admin: true`。有凭据结果只覆盖个人仓库所有者，匿名请求作为独立对照。请求串行执行，写入间隔至少一秒。凭据留在客户端进程内，记录仅保存必要字段。 [REST 调用建议](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)

## 夹具与回执

用[确定性夹具](../../tests/contracts/m0/compat/rest-runbook.md#确定性源码夹具)验证空远端后一次原子推送，API 独立读回以下三个引用，`object.type` 均为 `commit`。

| 引用 | SHA |
| --- | --- |
| `refs/heads/main` | `37aa3d3ca05aa645e8d970a233b95fcebf35452c` |
| `refs/heads/m0-fixture-pr` | `3527c7d63bebdc0eb5df3405dc23020950df2816` |
| `refs/tags/m0-release-01` | `37aa3d3ca05aa645e8d970a233b95fcebf35452c` |

下表中 `R` 为 `/repos/laugh0608/RadishForge-Test`。除单列的字节下载外，样例使用 `application/vnd.github+json` 接收响应。

| 样例 | 回执及独立读回 |
| --- | --- |
| 仓库与固定提交 | 所有者 `GET R`、`GET R/commits/{sha}` 均为 200，仓库 ID、默认分支、可见性和完整 SHA 符合夹具。匿名请求同两条路径均为 404。 |
| Issue 列表夹具 | `POST R/issues` 两次均为 201，得到开放 Issue #1 和随后 PATCH 200 关闭的 Issue #2。创建 PR #3 为 201，GET 200 确认开放及其 head、base 为固定 SHA。 |
| Issue 分页 | `state=all&sort=created&direction=asc&per_page=1&page=1` 三页均为 200，依次得到 #1、#2、#3。仅 #3 带 `pull_request`。实际 `rel="next"` 指向同源数字仓库路径并带 `after` 游标。首轮探针拒绝额外查询参数后暂停，复核仓库和筛选条件后从第一页重新读取，沿用返回的游标，已创建对象未重放。创建 #4 后用固定版本的 `gh api --paginate` 独立取得四页，编号、类型和状态一致。 |
| Issue 写入 | Issue #4 创建与评论均为 201，评论 ID `6739794630`，关闭为 200。GET Issue 与评论列表均为 200，回读正文、评论及 `closed` 状态。 |
| Release 草稿及附件 | 创建草稿为 201，ID `439093746`，创建回执的 `tag_name` 为 `m0-release-01`。向回执指定的 `uploads.github.com` 上传 `m0-fixture.bin` 为 201，附件 ID `727365986`。按附件 ID 请求二进制得到 302，经允许的签名下载地址省略原 Authorization 后得到 200 和 `application/octet-stream`。实收 11 字节，与夹具及元数据的 SHA-256 一致，值为 `d21cc231a75725ea02671f51c78c42ba501078b9d1b77bc4ca2c2c735c3db285`。 |
| Release 清空正文 | 单独 PATCH `{"body":""}` 为 200，GET 同一草稿为 200，`body` 是空字符串。回读的 Release `tag_name` 为 `untagged-1ff52bdc0c77a69c7829`，实际 Git Tag 仍为预置 SHA。发布步骤暂停，按 Release ID、附件 ID 和 Git Tag 对账。 |
| Release 重新关联及发布 | 对同一草稿单独 PATCH `{"tag_name":"m0-release-01"}` 为 200，GET 200 读到预期 Tag，正文仍为空且附件相同。再确认私有状态和 Git Tag，PATCH `{"draft":false}` 为 200。按 ID 和 Tag 读取均为 200，确认同一 Release、`draft: false`、附件与固定 Tag SHA。发布后仓库仍私有、Actions 仍关闭，匿名读 Release 为 404。 |

Release 的 `tag_name` 与 Git 引用分别读回。正文清除及草稿关联变化是本批一次观测，供 G20 对照，尚无重复样例可将关联变化视为普遍规则。 [GitHub Release 更新](https://docs.github.com/en/rest/releases/releases?apiVersion=2026-03-10#update-a-release) · [附件下载](https://docs.github.com/en/rest/releases/assets?apiVersion=2026-03-10#get-a-release-asset)

## 留存与补证

私有测试仓库、三个引用、三个 Issue、开放 PR 和已发布的合成 Release 保留作参考。临时裸仓、运行脚本和脱敏执行流水在归档后清理。普通读者和写者、凭据 scope、已认证外部用户、撤权负例，以及同源夹具在固定版 Gitea 的运行仍待验证。Runner 和 Actions 继续暂停，COMP-01 的兼容状态保持待验证。 [双端取证手册](../../tests/contracts/m0/compat/rest-runbook.md) · [M0-S04 接续事项](../planning/m0-validation.md#接续事项)
