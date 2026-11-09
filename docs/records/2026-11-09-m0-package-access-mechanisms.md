# 2026-11-09 M0-S04 包可见性与 Registry scope 核查

范围为 M0-04 的 M0-G24 / M0-G25，另登记与签发路径直接相关的 G27 补证。以 `dev` 的 `0add8d3`、Gitea 28.2.0-rootless 的原 Linux arm64 隔离证据和现有四条 OCI 差异为输入。本批为静态核查。 [OCI 实测记录](2026-11-04-m0-oci-validation.md) · [原始结果](2026-11-04-m0-oci-results.json)

官方 v28.2.0 标注 Tag 解引用到 `829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1`。源码按官方树核对 Git blob ID，固定 OpenAPI SHA-256 为 `c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`，与前批一致。官方 Packages 文档用于定位机制，版本行为以固定源码和原批实测为准。 [官方标注 Tag](https://api.github.com/repos/go-gitea/gitea/git/tags/1dc1ecdddcdc60ab14ec14e30e7bb4d84242f21f) · [固定 OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json) · [Packages 访问说明](https://docs.gitea.com/usage/packages/overview/#access-restrictions)

## G24 · 所有者、仓库关联与包权限

- **原批实测。** 公开个人所有者的镜像关联私有仓库后，另一普通用户持包凭据按 Digest 直接读取为 200，并核对 Manifest 原始字节。私有组织的包关联私有仓库后，仅有仓库协作权的非成员仍被拒绝。组织内仅有代码单元读取权的成员可拉取，上传被拒绝。 [原批主路径与权限](2026-11-04-m0-oci-validation.md#主路径与真实客户端)
- **直接 Registry 判定。** `/v2/{owner}/...` 先按路径所有者构造包上下文。个人包由所有者身份与账户可见性决定读写。组织包结合所有者可见性、组织成员和 team 权限。组织成员有读取基线，更高权限来自组织角色或 team 的 package 单元。固定源码还区分 `limited`、受限账号、匿名访问和严格登录设置，并有站点管理员的对象权限特例。原批结论限普通用户和已测可见性。 [包上下文](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/context/package.go#L57-L73) · [包权限判定](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/context/package.go#L112-L165) · [组织可见性](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/models/organization/org.go#L415-L461) · [Registry 权限门槛](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/packages/api.go#L42-L92)
- **公开关联接口。** Packages REST 的 link 在同一所有者下查找包和仓库，服务层再核对同一所有者及调用者对目标仓库 Packages 单元的写权限。成功仅更新包的 `repo_id`，所有者及直接 Registry 权限的计算保持原规则。解除关联有自己的管理权限检查。 [REST link 处理器](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/v1/packages/package.go#L383-L416) · [关联和解除关联](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/packages/package_update.go#L20-L80) · [关联字段](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/models/packages/package.go#L231-L239)

## G25 · 请求 scope 与实际凭据范围

- **原批实测。** `write:package` PAT 请求 `repository:<owner>/<image>:pull` 后，签发的 Registry JWT 仍可开启上传并返回 202。相反，所有者持 `read:package` PAT 所换凭据的上传被拒绝。具备写 scope 的普通组织成员仍须有对象写权限。 [原批差异](2026-11-04-m0-oci-validation.md#保留的四项差异)
- **签发与数据请求。** Basic 交换从 PAT 读取已授予的 scope。固定版 `GET /v2/token` 检查调用者有 package scope 后将该 scope 放入 JWT，处理器未解析 query 中的 `scope` 或 `service` 作为签发约束。JWT 中也没有请求的仓库或镜像坐标。数据路由按请求目标重新判定当前包权限和操作所需的 package scope。`write:package` 包含读取权限。另一个包是否可访问取决于其当前对象权限，跨命名空间的同一 JWT 行为待实测。 [PAT 读取](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/auth/basic.go#L95-L113) · [签发处理器](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/packages/container/container.go#L152-L187) · [JWT 声明](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/packages/auth.go#L21-L49) · [数据路由](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/packages/api.go#L564-L584) · [读写 scope 位图](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/models/auth/access_token_scope.go#L115-L116)
- **协议差异。** CNCF Distribution Token Authentication 对照在签发时取请求动作和允许动作的交集。固定版这里保留原 package scope，差异限于已核查的 Token 语义，原生固定 Digest 推拉证据继续有效。 [Distribution Token Authentication](https://distribution.github.io/distribution/spec/auth/token/#requesting-a-token)

## G27 · 旧 Bearer 换发待证

固定版在整个 Registry 路由组注册 Basic 与 Registry Bearer 鉴权，包含 `GET /v2/token`。Bearer 鉴权可从有效 JWT 回读用户和 scope，签发处理器使用该身份及 scope，并按当前时间计算新 JWT 的 `exp`。因此源码显示旧 JWT 可能在原 PAT 删除后换出后继 JWT。上轮实测只以已删除 PAT 本身尝试换发，并用旧 JWT 读取和开启上传。后继换发、签发期限推进及其实际使用均待实测，原 JWT 的 24 小时声明不足以界定该情况下的远端访问窗口。 [鉴权与签发路由](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/packages/api.go#L538-L562) · [Bearer 身份与 scope](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/packages/auth.go#L26-L58) · [原批 G27](2026-11-04-m0-oci-validation.md#保留的四项差异)

本批未启动隔离环境，G27 保持原编号，差异基线仍为 27 条。边界与补证见 [ADR 0006 核查补充](../adr/0006-oci-authorization-and-digest-retention.md#2026-11-09-包可见性与-registry-scope-核查)和 [M0-S04 OCI 补证条件](../planning/m0-validation.md#oci-补证条件)。
