# 2026-11-24 M0 Actions 权限配置与手动派发停止条件

Gitea 28.2.0 在新建的私有个人仓库上继承了所有者收紧后的权限上限。单独重启 Gitea 并重新登录后，两个设置页读回一致。另一次对照确认，关闭仓库 Actions 后，普通写者手动派发收到 403，新增 run 为 0。[脱敏设置、运行回执与清理读回](2026-11-24-m0-actions-settings-results.json)

## 哪些权限已核实

上批归档固定了工作流摘要、源码 SHA、run / attempt / job 和独立读者的回查结果，缺少当时的所有者默认模式、分项上限和仓库覆盖开关。该 VM 已清理，其历史有效配置无法回读。固定版本的设计先取 job、工作流或默认请求值，再按生效的上限收窄。因此，新实例的默认模式也不能解释上批失败的根因。[上批实测](2026-11-24-m0-arm64-actions-policy.md) · [固定版本设计](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/actions/token_permission_design.md) · [Gitea 权限说明](https://docs.gitea.com/usage/actions/token-permissions/)

本批由普通所有者通过 Gitea 原生设置页保存一次。每次重新登录后分别读取所有者与仓库两张表，仓库覆盖开关在三次观察中均为关闭。

| 观察点 | 所有者与仓库读回 | 运行 / Runner / Issue 数 |
| --- | --- | --- |
| 新实例启用仓库 Actions 后 | 默认模式 `Permissive`，自定义上限关闭，七个单元的表单显示值均为 `write` | 0 / 0 / 0 |
| 所有者保存后 | 保存 HTTP 200。默认模式 `Restricted`，自定义上限开启。Code 和 Issues 为 `read`，Pull Requests、Wiki、Releases、Projects、Actions 为 `none` | 0 / 0 / 0 |
| 仅重启 Gitea 后 | 同一 Gitea 容器的启动时间更新，PostgreSQL 启动时间保持一致。两张表的模式、上限和逐项值均与重启前相同 | 0 / 0 / 0 |

这些是管理配置的证据。两次实际派发对照都没有运行 job，本批未测 job Token 访问资源时的有效权限。M0-S04 的 job 只读写入拒绝仍待在有明确修正或可强制执行的替代控制下验收。

## 关闭仓库 Actions 后的手动派发

同一普通写者、同一私有仓库和同一 `main` 提交 `1fad7729f7a6f6c4c296c53d079c536a5353fd7e`。合成工作流仅响应 `workflow_dispatch`，唯一的步骤打印固定文本。两次派发均无注册 Runner。

1. 开启 Actions 时，手动派发返回 200。回执对应 run 1 / attempt 1，状态为 `queued`。普通写者取消后，run 和 job 1 均为 `cancelled`，job 的 Runner ID 为 0。
2. 所有者关闭仓库 Actions 后，写者读取私有仓库仍为 200，读回 `has_actions=false`。同一写者对同一工作流派发一次，返回 403。此时查询运行列表也返回 403。
3. 所有者短暂恢复 Actions 供对账，写者读到的 run ID 集合仍为 `[1]`，原 run 和 job 均已取消。新增 run 为 0，Issue 为 0。完成对账后再次关闭本批仓库 Actions。

这为暂停仓库手动派发提供了实测依据。push、PR、schedule 和执行中 job 的停机语义另行验收。允许 job 运行时的最小权限、环境审批及首版承诺继续依据 [M0 出口](../planning/acceptance.md#m0-exit)评审。

## 环境与清理

使用独立 UTM arm64 VM、固定 Debian 镜像及既有 Gitea / PostgreSQL arm64 子 manifest，4 vCPU、6 GiB 内存、12 GiB 根虚盘。管理 SSH 仅转发宿主回环，目录共享关闭。TLS 预检首次因任务 CA 缺少密钥用途扩展而拒绝连接，补签本批证书链后，严格 TLS 校验通过，随后才创建合成账号和仓库。[镜像与隔离条件](../../tests/contracts/m0/compat/runner-runbook.md#arm64-首条私有工作流)

清理时来宾运行容器为 0，Debian 镜像和来宾网卡接收量合计约 0.69 GiB。已核对 UUID 删除本批 VM 及临时虚盘、seed、密钥，UTM 清单恢复原有五台停止的 VM，宿主端口 28422 可重新绑定。
