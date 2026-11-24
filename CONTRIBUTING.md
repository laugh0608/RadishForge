# 协作入口

先读 [AGENTS.md](AGENTS.md) 和[当前状态](docs/status/current.md)，再按任务阅读最近的专题。默认中文讨论与文档，代码和协议标识保留原文。

## 工作方式

- 清楚区分规划、实现、验证与发布；文档中存在功能不表示它已实现。
- 已明确授权且范围未变的工作直接推进；外部发布、跨项目写入等动作按实际授权执行。
- 当前仅有规划、治理文件与本地检查工具；不要根据未来架构图擅自创建业务工程、下载依赖或运行容器。
- 后续 Git 初始化后，日常开发在 dev，稳定晋级到 master；具体规则见[仓库治理](docs/governance/repository-governance.md)。
- 修复和功能提交说明最终行为、实际验证、未验证项及风险，不用占位测试或默认成功结果冒充验收。
- 不向公开 Issue、日志、示例和提交中写入真实 token、客户数据、私有源码或生产配置。
- 提交贡献前确认自己有权提交。引用上游或第三方材料时记录来源、版本、许可与归属。

## 文档职责

长期规则进入 governance，产品与系统设计进入 product-plan / architecture，待办与验收进入 planning，实际状态只在 status/current，已发生事实进入 records。详见[文档治理](docs/governance/documentation.md)。

## 检查与提交

本地治理检查：`python3 scripts/check-repo.py`；检查器回归：`python3 -B -m unittest discover -s scripts/tests -v`。工具使用 Python 3.9+ 标准库，范围和 Git PR 参数见[检查说明](scripts/README.md)。当前没有 Go / Web 构建或活动 CI，不用治理 PASS 冒充业务通过。

提交使用 Conventional Commits，例如 `docs(governance): 明确主线保护启用顺序`；类型、真实 merge 例外和精确暂存要求见[仓库治理](docs/governance/repository-governance.md)。普通贡献指向 dev，阶段晋级或 hotfix 指向 master；允许 merge / rebase、禁用 squash，合入主线后先回流 dev。

使用仓库内 PR / Issue 模板，明确实际问题、证据和边界。提交的贡献按[根 LICENSE](LICENSE)第 4 节授权，另有书面约定的除外。

遵守[行为约定](CODE_OF_CONDUCT.md)，安全问题按 [SECURITY.md](SECURITY.md) 私下处理。公开贡献入口启用前必须落实本项目自己的安全报告渠道。
