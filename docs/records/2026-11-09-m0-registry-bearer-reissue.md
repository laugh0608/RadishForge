# 2026-11-09 M0-S04 G27 Registry Bearer 换发实测

固定版 Gitea 28.2.0 在删除来源 PAT 后仍接受原 Registry JWT 换发。原 JWT 单独调用同源 `GET /v2/token` 得到 200 和不同的 JWT。后继的 `nbf` 和 `exp` 均晚 3 秒，用户和 `write:package` scope 相同。后继按 Digest 读取 Manifest 返回 200，开启上传返回 202。

## 环境与夹具

基线为 `10b58b7327039da3a821de7ecf0ba56808352161`。本机 OrbStack 批次 `rf-m0-local-f9d3820f` 使用 Linux arm64、Engine 29.8.2、Compose 5.5.0、既有回环 18443 / 19443 和 `prepare --auth-profile`。两套 Gitea 回读 Actions 关闭。Python 3.9.6 探针使用任务 CA 和独立无 Cookie 客户端，换发测试只发一个 Bearer 请求。 [M0 本机入口](../../tests/contracts/m0/README.md)

| 镜像 | 固定 Digest |
| --- | --- |
| Gitea 28.2.0-rootless | `sha256:94807314454f6525994a3b76286ba12bc7e7f8cd14f61d9e67431767f8103306` |
| PostgreSQL 18.6-bookworm | `sha256:5c4783a8cc3f0074912164f94dfa1be4e043438f0f707cf968d7af9a0d31a2c8` |

管理员仅用于准备合成账号。Alice 创建私有组织 `m0-private-org`，普通用户 Bob 和 Erin 同属 `repo.packages: write` team。Bob 有待删 PAT（ID 1）及独立对照 PAT（ID 2），Erin 有自己的对照 PAT。三枚 PAT 均为 `write:package`。用 Bob 的对照凭据准备 `m0-private-org/m0-probe`，合成源码 SHA 为 `891ed3a59ad406c244c91f9a64c1f8f369fbd2f6`，Manifest Digest 为 `sha256:d7514dc2145d0b3d527798e0c8bcd1a76a1bbbe6c5a88f337ac01f7f745ff249`。匿名按该 Digest 读取返回 401。

## 请求与回读

删除前以 Bob 的账户凭据读取 PAT 列表，ID 为 `[1, 2]`。单独删除 ID 1 返回 204，列表回读 200，只剩 ID 2。两位写者的 team 成员回读均为 200，package 单元保持写权限。交换使用固定 `service=container_registry` 和 `scope=repository:m0-private-org/m0-probe:pull,push`。

| 阶段 / 凭据 | `GET /v2/token` | 读取 Manifest | 开启 / 取消上传 |
| --- | --- | --- | --- |
| 删除前，待删 PAT 及其原 JWT | Basic 200 | 200 | 202 / 204 |
| 删除后，已删除的 PAT | Basic 401 | 无返回 JWT | 无返回 JWT |
| 删除后，原 JWT | Bearer 200，返回后继 | 200 | 202 / 204 |
| 删除后，后继 JWT | 本轮未再换发 | 200 | 202 / 204 |
| 删除后，Bob 另一枚 PAT 及其 JWT | Basic 200 | 200 | 202 / 204 |
| 删除后，Erin 的 PAT 及其 JWT | Basic 200 | 200 | 202 / 204 |

每次成功读取均核对原始 Manifest 字节、请求 Digest 和响应 Digest。开启上传后按响应 Location 取消独立上传会话。

| JWT | `UserID` | `Scope` | `nbf`（Unix 秒） | `exp`（Unix 秒） | 声明寿命 |
| --- | --- | --- | --- | --- | --- |
| 原 JWT | 3 | `write:package` | 1794231532 | 1794317932 | 86400 秒 |
| 后继 JWT | 3 | `write:package` | 1794231535 | 1794317935 | 86400 秒 |

实测在 21:38:52–21:38:55 CST，完成 15 个记录项。临时探针 SHA-256 为 `8442119470b8994d1efa86948925a636adec7abfde466290e9f1563d7f9848db`，脱敏临时结果 SHA-256 为 `b309fdaf20bba209d666a7407708e85780654f77ff78cc70a80e79083e761a20`。声明在客户端仅解码，JWT 是否被接受由 Gitea 实际接口验证。

## 边界与后续验收

固定源码将 Bearer 鉴权应用于签发路由，以 JWT 还原用户和 package scope，再按当前时间签发 86400 秒。实测证实删除 PAT 后仍可取得声明到期时间更晚的可用后继。原 JWT 的 `exp` 只能描述原凭据，无法作为所有后继的远端失效上限。 [签发路由](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/packages/api.go#L538-L562) · [Bearer 鉴权](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/packages/auth.go#L26-L58) · [签发处理器](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/packages/container/container.go#L152-L187) · [JWT 声明](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/packages/auth.go#L21-L49)

本批限单次换发、一个私有组织及普通写者。真实到期、跨代连续换发、原 JWT 到期后后继的实际可用性和上传续写 / 提交均未测。短测未修改时钟。G27 保留原编号和单凭据远端失效缺口。首版要求和长时取证范围由所有者取舍。 [ADR 0006](../adr/0006-oci-authorization-and-digest-retention.md) · [后续验收](../planning/m0-validation.md#oci-补证条件)

批次已清理。按 Compose 项目标签回读容器、卷和网络各为 0，回环 18443 / 19443 已释放，`.local/m0` 中的任务凭据、证书和临时文件已移除。共享镜像缓存保留。
