# 领域模型与权威数据

状态：逻辑设计，尚无数据库表或迁移。

## 权威来源

| 事实 | 权威来源 | 自有存储 |
| --- | --- | --- |
| Gitea 用户、组织、仓库、提交、Issue、PR | Gitea | 稳定 ID、必要缓存与关联 |
| 工作流文件、运行、任务、日志 | Gitea / Runner | 运行引用、关联、查询水位 |
| 镜像内容、包版本、Digest、Release 正文与附件 | Gitea / Registry | 内容引用和发布快照 |
| OIDC 外部身份 | 发行方 | issuer + sub 绑定；不以邮箱为主键 |
| 工作台会话、上游授权绑定 | RadishForge | 会话、加密凭据和撤销状态 |
| 项目组件、版本清单、部署目标与执行记录 | RadishForge | 自有权威事实 |

自有表不外键引用 Gitea 数据库。上游重命名后用稳定 ID 维持关联；删除或转移后显示失联 / 权限变化，不自动绑定同名新仓库。

## 核心对象

| 对象 | 关键字段 / 约束 |
| --- | --- |
| ForgeConnection | 实例 ID、类型、公开地址、精确版本、能力与凭据引用 |
| IdentityBinding | 工作台用户、issuer、sub、底座实例与用户 ID；显式双向确认 |
| Project / Component | 项目 ID、组件名、仓库 ID、镜像坐标、必需 / 可选定义 |
| BuildReference | 底座、仓库、run ID、attempt、workflow ref、source SHA、状态 |
| ArtifactReference | Registry、owner、image、Digest、平台、构建引用、校验结果 |
| ReleaseManifest | schema version、项目、版本、各仓库 SHA、组件 Digest、构建引用、附件校验和 |
| ReleaseOperation | 请求 ID、目标仓库及版本唯一键、步骤、上游 Release ID、结果 |
| Environment | 项目、环境名、目标引用、受控 workflow ref、部署权限、当前已验证清单 |
| Deployment | 清单 ID、环境、发起人、执行身份、workflow run / attempt、锁租约、健康结果 |
| EventInbox / Job | 来源、去重键、原始载荷受控保留、租约、重试、失败原因 |
| AuditEvent | 谁以何种授权对何资源执行何操作、关联 ID、结果；不保存 Token |

发布清单冻结后只追加修订，不能原地修改已经部署的清单。版本是托管项目的业务字符串，不强制 SemVer。多仓库项目逐仓库固定 SHA，不用一个模糊的项目 SHA 代表全部源码。

## 状态与一致性

- ReleaseOperation：draft → validating → preparing → publishing → published；任一步可进入 failed 或 outcome_unknown，恢复先查询实际副作用。
- Deployment：requested → authorized → queued → running → verifying → succeeded；可进入 rejected、failed、cancelled 或 outcome_unknown。
- succeeded 表示预先约定的健康检查通过，不能代表业务永远健康；后续漂移另记录。
- 上游附件被删、Tag 被移动、镜像缺失或 Release 被编辑时标记 drifted / unavailable，不伪装成不可变存储。
- 每个环境仅一个有效部署操作；租约过期不能立即启动第二个部署，先确认旧执行器已停止或被可靠隔离。
- 跨底座请求必须携带实例 ID；上游 ID、Issue number、run ID 不假定全局唯一。

缓存可重建；身份密钥、冻结清单、部署与审计记录不可通过删库重建。备份必须覆盖它们及关联的上游数据，见[部署策略](../deployment/strategy.md)。
