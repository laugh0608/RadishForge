# 2026-11-17 M0-S04 G06 原生撤销重启补证

G20 已由 `2a1bf3e` 保存。继续既有 G06 边界，在 OrbStack 空批次 `rf-m0-local-7dc65600` 检查正常自助撤销在服务重启后的持久性。复用 Linux arm64 的固定 Gitea 28.2.0-rootless / PostgreSQL 18.6-bookworm 镜像、任务 CA、回环 18443 / 19443 和 30 秒 access token，Actions 关闭。没有新增镜像下载或外部写入。 [脱敏请求与源码摘要](2026-11-17-m0-oauth-restart-results.json) · [既有 G06 行为证据](2026-11-09-m0-oauth-grant-revocation.md)

同一共享 confidential 应用由普通用户 Alice 与 Bob 分别授权，Bob 另有独立应用。探针通过 Bob 的隔离会话提交原生设置页呈现的自助撤销，随后用独立 API 客户端回读。该步骤是原生页面动作的协议取证，既有真实浏览器 UI 成功回执另见[生命周期记录](2026-11-04-m0-lifecycle-validation.md#新负例与资源结果)。

| 范围 | 观察 |
| --- | --- |
| 重启前 | Bob 撤销共享应用后，目标授权从设置页消失，Bob 的独立授权仍列出。目标 access token introspection 返回 200 / `active:false`，私有仓库 GET 返回 401。 |
| 重启后 | 只重启本批资源 Gitea，容器启动时间发生变化，IdP 与 PostgreSQL 启动时间保持一致。任务 TLS 健康检查恢复，受控配置回读一致。目标 token 在刷新后约 1.143 秒进入回读，introspection 仍为 200 / `active:false`，私有仓库 GET 仍为 401。 |
| 独立对照 | Bob 新登录后目标授权仍不出现，独立授权仍列出。Alice 新登录仍看得到同一共享应用的授权。Alice 的共享应用与 Bob 的独立应用均刷新成功，各自读取私有仓库返回 200。 |

本批于 20:45:35–20:45:39（UTC+08:00）完成，7 条记录、68 次请求，退出 0。服务重启后证据覆盖正常自助撤销、授权列表持久性及已签发 access token 的读取拒绝。未取证撤销时的在途请求，也未实现或验收产品侧停用。固定版本仍缺公开单用户自动撤销接口，继续沿用[ADR 0003](../adr/0003-gitea-authorization-profiles.md#2026-11-09-单用户-grant-撤销边界)，M0 继续进行。

容器、卷、网络按项目标签读回均为 0，回环端口已释放，`.local/m0`、凭据和任务临时副本均已移除。固定镜像保留为缓存。Runner / Actions 未启动。
