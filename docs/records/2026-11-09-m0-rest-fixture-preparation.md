# 2026-11-09 M0-S04 双端 REST 夹具准备

基线为 `dev` 的 `9f2b734`。本批为仓库、Issue 和 Release 首轮双端取证准备同源 Git 夹具、普通用户角色矩阵、只读准入和后续写入及读回顺序。工作流样例继续存放在契约目录。 [REST 取证手册](../../tests/contracts/m0/compat/rest-runbook.md)

将同一 `rest-source.fi` 分别导入两个本任务的本地 SHA-1 裸仓。两仓通过 `git fsck --strict --no-reflogs`，`git show-ref` 结果逐字节相同。主分支和预置 Release Tag 均为 `37aa3d3ca05aa645e8d970a233b95fcebf35452c`，PR 分支为 `3527c7d63bebdc0eb5df3405dc23020950df2816`，其唯一父提交为主分支。主分支只包含合成 `fixture.txt`。本地夹具无远端配置。手册的本地命令在第三个目录复现同一结果，附件摘要一致，重复执行拒绝覆盖。只读请求的 Shell 块通过语法检查。治理检查和 63 项本地测试通过。

固定 Gitea OpenAPI SHA-256 为 `c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`。核对用户、角色、分支、Tag、PR、Issue 和 Release 路由，以及 Gitea 分支 `commit.id`、Tag `commit.sha` 和 Issue 分页 `limit` / `type` 字段。GitHub 对照使用 refs 的 `object.sha`、REST `2026-03-10` 与已选 gh。按官方限制，fine-grained PAT 的组织成员与外部协作者不能混作同一凭据对照。 [Gitea 固定 OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json) · [GitHub refs](https://docs.github.com/en/rest/git/refs?apiVersion=2026-03-10#get-a-reference) · [GitHub PAT 限制](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#fine-grained-personal-access-tokens-limitations)

工作区只有正式项目 GitHub 远端，未指定获授权的专用测试仓库。本机 M0 运行目录在本批开始时不存在。本批只访问公开技术资料并验证本地夹具，没有向候选目标发出样例请求、写入远端、启动隔离服务或运行工作流。双端兼容、权限与发布行为继续待验证。
