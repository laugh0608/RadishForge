# 2026-11-09 M0-S04 固定版 Gitea REST 对照

本批以 `10d451144f650f15916915ff8f6661cff15b5454` 为基线。用同一 Git 对象、Issue / PR 标记和 11 字节附件，对照已保存的 GitHub REST `2026-03-10` 参考结果。GitHub 侧证据覆盖仓库所有者和匿名请求。Gitea 侧由实例管理员建合成账号，普通所有者安装夹具、配置角色和创建 PR，仓库读取及 Issue / Release 用例使用实际普通角色。 [GitHub 参考](2026-11-09-m0-github-rest-reference.md) · [执行手册](../../tests/contracts/m0/compat/rest-runbook.md)

## 批次与复现

使用 OrbStack `orbstack`、Engine 29.8.2、Compose 5.5.0、Linux arm64、Python 3.9.6 和 Git 2.54.0。固定 Gitea 28.2.0-rootless 镜像 Digest 为 `sha256:94807314454f6525994a3b76286ba12bc7e7f8cd14f61d9e67431767f8103306`，PostgreSQL 18.6-bookworm 为 `sha256:5c4783a8cc3f0074912164f94dfa1be4e043438f0f707cf968d7af9a0d31a2c8`。用已缓存镜像建立三个服务，总内存限额 2.75 GiB，仅回环 18443 / 19443，HTTP 和 Git 都显式信任本批 CA。资源和 IdP 实例均回读 Actions 关闭。

按[契约入口](../../tests/contracts/m0/README.md#m0-s04-同源-rest-对照)运行 `prepare --auth-profile`、`up` 和 `m0_contracts.py --mode rest`。最终批次 `rf-m0-local-8d4e4f9a`，取证时间 20:27:39–20:27:43 CST，记录 175 条 HTTP 轨迹和 14 个命名结果。探针流程完成，G19 / G20 保留两条差异，退出 2。源码和夹具摘要为：

| 文件 | SHA-256 |
| --- | --- |
| `scripts/m0_contracts.py` | `97531b338ead526dff455793b039215b7ba5cdf1de4ccd4c1c47a82e0659b3aa` |
| `scripts/m0_rest.py` | `c07f0c3eb0911881b1bb7415b9eb8ccff674549148f68d2c5b70a49e42289d15` |
| `tests/contracts/m0/compat/rest-source.fi` | `223a5feddbd5791ad883a2a4b30aabdd209aa15193508e929334650b55cb7cef` |

第一批 `rf-m0-local-8307a1cd` 退出 1。探针将 Issue 评论接口作为分页列表读取，两页均返回同一评论 ID `3` 后触发重复保护。只读核实 Issue #4 已关闭，固定评论只写入一次。固定 OpenAPI 的该路由只声明 `since` / `before` 查询参数，最终探针对合成评论使用有上限的单次读取。清理首批后启用新项目和空卷，未在原环境重放写入。 [固定 Gitea OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json)

## 实际回执

| 切片 | Gitea 28.2.0 实际 | GitHub 参考或后续边界 |
| --- | --- | --- |
| 仓库与固定提交 | `alice/private-fixture` 为私有空仓，ID `1`、默认分支 `main`，Issues 已启用。经本机 HTTPS 原子推送三条 refs，Git 和 REST 读回一致。普通读者读取仓库和固定提交均为 200，外部用户均为 404，匿名均为 403。 | 同一 main / Tag SHA `37aa3d3ca05aa645e8d970a233b95fcebf35452c`，PR head `3527c7d63bebdc0eb5df3405dc23020950df2816`。GitHub 所有者两次 GET 为 200，匿名均为 404。 |
| Issue / PR 分页 | `type=issues&limit=1` 的页长为 `[1,1,0]`，返回 #1 开放、#2 关闭。独立 `type=pulls` 页长为 `[1,0]`，开放 PR #3 的 head / base 与夹具一致。 | GitHub 同一集合通过带 `after` 的 `Link` 一起返回，PR 项带 `pull_request`。 |
| Issue 写入与权限 | 普通写者创建 #4、评论 ID `3`、关闭分别为 201 / 201 / 201，正文、评论和状态读回一致。该写者的只读凭据创建 Issue 得到 403。另一写者移除仓库角色后凭据的 `GET /user` 仍为 200，读取 Issue 和评论写入均为 404。独立读回确认无新增对象和评论。 | GitHub 所有者关闭为 200。GitHub 普通角色、受限凭据、越权及撤权用例仍待证。 |
| Release 草稿及附件 | 普通写者用 `release_write` 创建草稿及上传均为 201，Release / 附件 ID 均为 `1`。固定 Tag 实际 SHA 正确。原生下载实收 11 字节，媒体类型为 `text/plain`，与同源夹具逐字节一致。 | GitHub 参考下载为 302 后 200 `application/octet-stream`。两端实收 SHA-256 均为 `d21cc231a75725ea02671f51c78c42ba501078b9d1b77bc4ca2c2c735c3db285`。 |
| G19 草稿读取 | 同一普通写者改用 `resource_read` 后，按 ID 及 REST 附件单项为 404，按 Tag 为 200 且返回同一 Release ID，UUID 和 Tag / 文件名下载均为 200 且字节正确。普通读者和外部用户五条路径均为 404。 | 追加到既有 G19，产品草稿入口仍须同时校验 Release 写用途及当前单元写权限。GitHub 相应普通角色待证。 |
| G20 空正文及发布 | 单独 PATCH `{"body":""}` 为 200，草稿仍保留原正文 `m0 notes`，草稿关联和实际 Git Tag 不变。PATCH `{"draft":false}` 为 200，按 ID 和 Tag 回读同一 Release，正文保持观察值，普通读者下载字节一致，外部用户详情为 404。 | GitHub 同请求清空正文，草稿关联一度返回 `untagged-*`，独立恢复预置 Tag 后发布。Gitea 原生页面手动清空仍待实测。 |

## 清理与接续

两批均按标签核实容器、卷和网络各为 0，运行目录 `.local/m0` 已移除，两个回环端口已释放，共享镜像缓存保留。Gitea 写入限于本机合成数据。GitHub 测试仓库的协作者列表仅做只读确认，只有所有者。普通账号及角色授权、完整兼容验收、Runner / Actions 和 M1 继续按当前停止线处理。G19 / G20 是既有差异的补证，M0 差异基线仍为 27 条。 [当前状态](../status/current.md)
