# 2026-11-09 M0-S04 首批兼容样例静态准备

以 `dev` 的 `dce1be7` 为基线。交付四份原始工作流、REST 请求与 gh 调用、版本来源、平台准入、正负例和逐端读回条件。样例存放于现有 M0 契约目录。 [首批对照样例](../../tests/contracts/m0/compat/README.md)

GitHub 官方仍列出 REST `2026-03-10` 和 `2022-11-28`，旧版支持到 2028-03-10。选用本机已存在的 gh `v2.96.0`，用官方 Tag 引用核对到完整提交，并本地读取版本和帮助。六个 Action 读取官方正式发行、解析 Tag 至 commit，再从固定 commit 读取 `action.yml`。六个元数据均声明 `node24`。Buildx 同样从官方发行固定到 `v0.38.2`。具体 Tag、SHA 和固定元数据链接随样例保存。 [GitHub REST 版本](https://docs.github.com/en/rest/about-the-rest-api/api-versions#supported-api-versions) · [gh 发行](https://github.com/cli/cli/releases/tag/v2.96.0)

Gitea 固定 OpenAPI SHA-256 为 `c797dc2a94e070c19ea823cb4396829f234a745a7a8c90b4a686b91cbc4d278e`。其单提交查询路径含 `/git/commits/{sha}`，已单独列入对照。GitHub `2026-03-10` 的 dispatch 文档为 200 与运行详情，Gitea 记录 `return_run_details` query 参数和 200 / 204。实际回执及取消、日志语义等待双端取证。 [GitHub dispatch](https://docs.github.com/en/rest/actions/workflows?apiVersion=2026-03-10#create-a-workflow-dispatch-event) · [Gitea 固定 OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/templates/swagger/v1-openapi3.generated.json)

工作流目标为 Linux amd64，参考标签为 `ubuntu-24.04`。Gitea job 镜像、BuildKit 制品、实际运行时在执行前固定，托管 GitHub 镜像版本在执行时记录。首批工具链和镜像路径复用已选 Go、Node 和 OCI 验证条件，安全负例只使用合成数据和凭据。

本批验证 YAML 可解析、Action 输入和输出与固定元数据一致、嵌入 Shell 能通过语法检查，以及选定 Gitea 路径与 OpenAPI 声明相符。未发出任何样例请求、导入工作流、启动 Runner 或开启 Actions。COMP-01、COMP-02 和 COMP-03 的行为验收继续待验证。G26 / G27 的取舍及 27 条差异基线保留。
