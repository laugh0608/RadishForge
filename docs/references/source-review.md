# 参考来源与核查范围

核查日期：2026-10-29。兄弟项目按当时本地工作区只读核对；下面的 HEAD 用于定位基线，不保证未提交文档与 HEAD 完全相同。未运行兄弟项目、Gitea、Runner 或数据库，也未据此认定任何线上部署状态。

## 兄弟项目

| 来源 | 本次核对材料 | 吸收的原则 |
| --- | --- | --- |
| RadishInk | AGENTS.md；docs/governance/repository-governance.md、upstream.md、versioning.md；StorageAdapter、运行时配置与 OIDC 相关源码 | 上游来源、模块边界、运行时配置、账号绑定、文档分层 |
| RadishRoot | AGENTS.md、仓库治理与当前状态入口 | 用户授权优先、任务持续推进、真实验证、dev / master、交接记录 |
| Radish | AGENTS.md；Deploy/docker-compose.yaml、docker-compose.local.yaml、deploy-production.sh；Docs/deployment/guide.md；生产迁移和版本治理专题 | 环境分层、预构建固定镜像、TLS、停写、备份、apply / verify、失败停止线 |
| RadishX | src/data/projects.ts 与项目命名 / 家族定位 | RadishForge / 萝卜锻坊命名及与 Nexus 分工；没有写回品牌矩阵 |
| RadishNexus | README.md | 协作定位边界；不形成运行依赖 |

本地源码目录为所有者 `~/Code/` 下对应项目。本轮读取的基线 HEAD：

| 项目 | HEAD |
| --- | --- |
| Radish | `29e7030122bc2462262ebd714964106a00242c65` |
| RadishInk | `c0f0c6c567a0854632202aac9798b7741ab93e6e` |
| RadishRoot | `0aa54c13d109496407534cecc7376fab167e9668` |
| RadishX | `c94ed062bf7654f844445712252eb89458fd0811` |

部署静态核查包括脚本和 Compose，不仅是概念文档。Radish 的生产脚本包含固定镜像检查、提前拉取、停止写入、备份、独立迁移与校验、启动及健康检查；其自测描述为假 Docker / curl 驱动，不能当作真实恢复证据。RadishForge 只吸收其流程原则，不直接搬用六库、Redis、.NET 迁移工具和证书配置。

## 官方资料

| 来源 | 版本 / 用途 | 本次结论边界 |
| --- | --- | --- |
| [Gitea v28.2.0 Release](https://github.com/go-gitea/gitea/releases/tag/v28.2.0) | 2026-10-18 发布 | 静态参考版本；未安装 |
| [v28.2.0 OpenAPI](https://github.com/go-gitea/gitea/blob/v28.2.0/templates/swagger/v1-openapi3.generated.json) | 固定 Tag | 公开接口存在，不等于实际调用成功 |
| [OAuth2 Provider](https://docs.gitea.com/development/oauth2-provider/) | 滚动官方文档，2026-10-29 读取 | 授权码 / PKCE 与 scope 参考；精确部署组合仍需联测 |
| [Actions 对照](https://docs.gitea.com/usage/actions/comparison/) | 滚动官方文档 | 用于建立差异矩阵，不能覆盖所有旧版本与 Action |
| [Packages](https://docs.gitea.com/usage/packages/overview/) | 包归属与权限 | 关联仓库不改变包访问规则；需直接 pull 验收 |
| [官方自定义入口](https://docs.gitea.com/administration/customizing-gitea/) | 模板 / 品牌扩展参考 | 原生导航扩展不等于全站 React 接口 |
| [Gitea v28.2.0 LICENSE](https://github.com/go-gitea/gitea/blob/v28.2.0/LICENSE) | 根许可证 MIT | 不代替依赖与镜像许可核查 |
| [Forgejo 许可说明](https://forgejo.org/faq/#is-forgejo-licensed-under-the-gpl) | 官方说明 v9 起 GPLv3+ | 后续适配必须独立核查具体版本与分发范围 |
| [GitHub REST API 版本](https://docs.github.com/en/rest/about-the-rest-api/api-versions) | 当前列出 2026-03-10、2022-11-28 | 新旧 API profile 应分开验收，不能不带版本头猜测 |
| [GitHub Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) | 兼容矩阵后续对照入口 | 尚未逐项验证 |
| [GitHub REST 文档](https://docs.github.com/en/rest) | API 子集后续对照入口 | 不代表全 API 兼容承诺 |

## OpenAPI 静态检查记录

本轮读取固定 v28.2.0 的 OpenAPI JSON，文件 SHA-256：

`c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`

其中 `info.version` 是构建占位值，不能用它确定产品版本；版本依据下载来源的 Tag。

已见端点范围包括：

- Issue 列表 / 创建、详情 / 修改、评论、标签、负责人。
- Actions workflows、dispatches、runs、jobs、cancel、rerun、logs 与 artifacts。
- Release 与附件相关操作（前一轮架构核对）。

这些支持“优先公开接口集成”的设计。接口存在不能证明 scope、并发、错误码、流式日志、GitHub 字段等价或幂等；M0 必须实测。日志下载接口不能自动推导稳定实时流 API。

## 未完成的核查

尚未冻结或验收 Runner、Action、Go / Node / PostgreSQL / Docker 版本；未下载镜像、运行原型、生成完整 SBOM、执行 OIDC 联测或灾备恢复。规划中的人日是工程估算，不是实测效率或上线承诺。
