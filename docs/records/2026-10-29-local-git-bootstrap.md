# 2026-10-29 本地 Git 初始化与协作复核

## 授权与范围

用户明确要求使用现有 Git 身份初始化本地仓库、完成首个提交、建立 master / dev 并切到 dev，先不创建远端或推送；同时专项复核五个兄弟项目的 AGENTS / CLAUDE，补充通用协作细节。任务为 P0-06、G0-01，验收为 DOC-01、GOV-01、GOV-04；不包含业务实现或远端治理。

## 协作约束复核

完整读取 Radish、RadishMind、RadishCatalyst、RadishFlow、RadishAxiom 的十份根协作文件，核对版本与双文件差异；来源 HEAD、采用与排除项见[治理提炼](../references/governance-review.md)。兄弟项目仅只读访问。

本项目两份根入口从 88 行扩展至 133 行，补充最小阅读链、工作区差异处理、推进与澄清、依赖 / 服务副作用、最小权限、路径清理、秘密保护、类型与错误边界、验证分层、Git 约束和根入口准入。通用原则与本项目长期边界分开，详细动作矩阵与交接流程进入 collaboration。

保留本项目持续授权规则，没有照搬每轮重新审批、默认提交许可、专用工具命令、技术栈或业务门禁。两份文件仍只允许首行标题不同。

## 本地 Git 基线

- 初始化使用 `git init --initial-branch=master`；首次执行受沙盒 .git 写权限限制，按已授权目标取得最小权限后成功，未调整全局配置。
- 作者与提交者沿用现有 `laugh0608` 身份；以实际 Git commit 对象记录的姓名与邮箱为准，没有覆盖身份或添加 AI 协作者署名。
- 首个提交题为 `chore: initialize RadishForge planning and governance`，包含本项目规划、治理基础、通用协作补充与本记录。
- 从该提交建立 dev 并切换，master / dev 共用一个无父基线提交；没有另起孤立历史、额外主题分支或 worktree。
- 不创建 remote / upstream，不 fetch / push、不创建 PR / tag / Release，不安装依赖或启动后台服务。

本记录随首次基线提交保存，不将自身提交哈希嵌入自身内容。精确基线可以通过 `git rev-list --max-parents=0 HEAD` 查询，再用 `git show --no-patch --format=fuller <sha>` 核对身份和提交说明；后来分支前进不改变此基线的定位方式。

## 验证与实际边界

提交前在 macOS / arm64、Python 3.14.5 执行：

- `python3 scripts/check-repo.py`：47 个文本文件、172 个本地文件链接与政策契约通过，Git 工作树 / 暂存区空白检查已启用。
- `python3 -B -m unittest discover -s scripts/tests -v`：8 项回归全部通过；包含无 Git 临时副本和各类错误拒绝，不冒充业务测试。
- 任务与验收编号、根入口 133 行及逐字同步、待提交文件清单、格式与常见秘密特征另行复核；没有新增业务依赖或生成缓存。

检查器实现未改动，不扩大为业务验证；本次只有初始提交，不以空提交范围声称已经验证过真实多提交 PR 的 Conventional Commits 路径。

最终核对：HEAD 位于 dev，master / dev 的提交 SHA 相同，提交总数为 1 且基线无父提交，Git 作者与提交者匹配既有身份，`git status --porcelain=v1` 无输出，remote / upstream 均为空。该结果证明本地初始化，不代表远端保护、CI 或产品功能已验收。

GOV-02 / GOV-03 仍待后续授权与真实远端证据；本地 GOV-04 独立记录，不因完成首个提交关闭远端任务。此前“未初始化 Git”的记录保留为当时事实。
