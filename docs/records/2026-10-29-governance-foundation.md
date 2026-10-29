# 2026-10-29 治理基础建立记录

## 范围与来源

在前期规划基础上，按用户要求只读参考 Radish、RadishMind、RadishCatalyst、RadishFlow、RadishAxiom，建立适合 RadishForge 的通用协作、仓库文件、分支、PR 与 Rulesets 策略。来源 HEAD 与差异见[治理核查](../references/governance-review.md)。

任务：P0-04、P0-05；验收：DOC-01、GOV-01。未启动 G0 或 M0，不含业务代码和远端动作。

## 已落地

- 三个基础点文件，按 Go / TypeScript 与本地治理工具处理文本与产物。
- SECURITY、CODE_OF_CONDUCT、更新后的 CONTRIBUTING 与同步根协作入口。
- PR 与两类 Issue 模板、仓库设置 JSON、基础 / CI 两阶段 Ruleset JSON。
- 分支与回流、规则启用 / 读回 / 验收 / 恢复、平台迁移边界与 ADR 0002。
- Python 标准库治理检查器及故障回归，更新任务、验收、路线图、索引与 current。

## 验证

环境：macOS / arm64，Python 3.14.5；无额外依赖。兼容目标为 Python 3.9+，未逐版本执行。

| 操作 | 结果与范围 |
| --- | --- |
| `python3 scripts/check-repo.py` | 通过：46 个文本文件、159 个本地文件链接、JSON 与治理契约；明确输出 Git 检查未运行 |
| `python3 -B -m unittest discover -s scripts/tests -v` | 8 项通过；包含有效目录、缺失文件、入口漂移、BOM / CR 与坏链接、无效 JSON、错误 CI context、误启用模板、无 Git 却要求范围检查 |
| 修改前快照与最终清单对照 | 新增 19、更新 11、删除 0；保留前期业务架构与历史记录 |
| 根协作入口核对 | 除首行标题一致，均 88 行；手写检查器 210 行 |
| 定向秘密特征复核 | 未发现私钥块、常见 GitHub Token / AWS access key 特征；不是完整秘密检测或安全审计 |

首次检查器回归发现 macOS 临时目录存在逻辑路径与实际路径差异，导致有效相对链接被误判越界；已统一解析根路径，修复后有效目录和全部拒绝样例通过。未通过删除断言或放宽文件边界消除失败。

PR / Issue 模板人工核对字段与提示语，GitHub Rulesets 字段与官方资料静态对照；尚未在平台 UI / API 实际导入。所有测试副本使用自动清理的临时目录；没有后台进程或端口资源。

## 实际边界

本项目无 .git，因此没有分支、提交、暂存区、未跟踪状态、跟踪关系或可用 Git diff；通过本轮修改前文件快照与最终文件清单复核增改。没有初始化 Git、提交、创建远端、push、PR、修改 Ruleset、发布或部署；没有安装依赖、下载镜像或启动后台服务。

规则字段与平台文档仅做静态核对，JSON 解析和本地政策检查不能证明 GitHub 接受、GitHub UI 模板展示、Gitea 等效保护或 CI 故障传播。Git 范围检查路径尚未在本项目真实提交上运行。产品功能、安全、安装、迁移与恢复均未验收。

未选择许可证、未借用兄弟项目安全邮箱或角色 ID。GOV-02 / GOV-03 留待对应授权与真实证据。
