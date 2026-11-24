# 2026-11-17 M0-S04 G19 组织仓库草稿权限实测

所有者明确授权在本机 OrbStack 复用固定镜像、启动空隔离环境验证组织仓库 Release 草稿权限，结束清理。基线为 `4c8b714`。OrbStack Engine 29.8.2、Compose 5.5.0，镜像实际为 Linux arm64，复用 Gitea 28.2.0-rootless / PostgreSQL 18.6-bookworm 的固定 Digest。两套 Gitea 通过任务 CA 就绪检查，回读 Actions 关闭。没有拉取新镜像、启动 Runner、改系统信任或向外部仓库写入。 [脱敏请求与源文件摘要](2026-11-17-m0-release-org-role-transitions-results.json)

合成普通用户 Alice 作为组织所有者，在私有组织 `m0-release-team-org` 的私有仓库 `private-fixture` 建立草稿及独立已发布对照。站点管理员仅准备合成账号。Bob 所在 team 仅绑定该仓库，`repo.code` 为 `read`，`repo.releases` 从 `write` 降到 `read`，再移出 Bob。Carol 的独立 team 始终为代码和 Release 的读取者。team 单元、仓库归属和成员状态均经公开 API 回读。

两条 Tag 均指向 `66f62be6c15c6e405fce59eea0b9ee3ae0410876`。草稿 ID 1、附件 ID 1，附件 1064 字节，SHA-256 为 `5cf455217db1710351bb5a616296a9fd19f4d9bce832ddc12b43492053974d08`。已发布 Release ID 2、附件 ID 2，附件 41 字节，SHA-256 为 `2ebe883717f9ada4ec81a687ba455f3bc83ba5e6228fe27750d5cfa73b494d5f`。

| 阶段与身份 | 草稿列表 | 草稿按 ID / Tag、附件列表 / 单项、UUID / Tag 下载 | 已发布列表、详情、附件及两路下载 |
| --- | --- | --- | --- |
| Bob，Release 写 team | 200，包含同一草稿 | 全部 200 | 全部 200 |
| Bob，Release 单元降为读 | 200，无草稿 | 全部 404 | 全部 200 |
| Bob，移出 team | 404 | 全部 404 | 全部 404 |
| Carol，独立读 team，全程 | 200，无草稿 | 全部 404 | 全部 200 |

Bob 的 `release_write` 与 Carol 的 `resource_read` 均在矩阵开始前刷新一次，三阶段沿用各自同一枚凭据。每阶段前后一并检查 introspection active、授予 scope 和在线账号，移出 team 后 Bob 的仓库请求与 team 成员回读均为 404。拒绝响应未含夹具正文、附件名或附件原始字节。全部下载正例逐字节比对，最后通过所有者凭据核对两条 Tag、Release 状态和附件仍与夹具一致。

首批 `rf-m0-local-671d06cf` 退出 1，探针遗漏已发布对照的显式发布参数，将它创建成第二份草稿，在读者正向对照处中断。经只读对账后归档并清理，修正调用后开新空批，未删除已开始标记重放。最终批 `rf-m0-local-c2b9f11c` 于 20:31:15–20:31:18（UTC+08:00）完成，退出 0，11 条结果、219 次请求。

本批确认固定版私有组织仓库按当前 Release 单元权限处理草稿与附件。原有写者持只读 scope 的 G19 差异继续保留，产品入口仍须核验写用途及当前 Release 单元写权限。对象存储直链和产品权限验收仍按启用配置另验，阶段保持 M0。 [ADR 0005](../adr/0005-release-authorization-and-reconciliation.md)

两批容器、卷、网络按项目标签读回均为 0。18443 / 19443 已释放，`.local/m0`、合成凭据和任务文件已移除。固定镜像保持缓存。

仓库治理与 63 项本地测试通过，最终探针源码摘要与实测记录匹配。改动留在工作区。
