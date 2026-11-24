# 2026-11-24 GitHub PR CI 与主线必需检查

本批按 Asia/Shanghai 记录，覆盖 G0-03 / GOV-03。所有者授权把仓库 CI 加入 [PR #1](https://github.com/laugh0608/RadishForge/pull/1)，验证结果传播后更新现有主线 Ruleset。远端操作使用宿主机 `/opt/homebrew/bin/gh`。

## 工作流与验证结果

[PR Checks](../../.github/workflows/pr-checks.yml) 使用 GitHub 托管 Ubuntu 24.04。治理检查在源提交上使用 PR 共同祖先，Python 测试运行在 GitHub 生成的 PR 合并候选树上。本地治理检查、工作流 YAML 和 Bash 语法检查、70 项现有测试均通过。

各次 PR 运行的目标分支均为 `master`，当时基线是 `c2764aa278cbed9aab3faf6f43a0556e80e623f4`。下面的 SHA 为对应 PR 的源提交。

| 场景 | 源提交 | Repository Governance | Python Tests | Candidate Quality | 运行 |
| --- | --- | --- | --- | --- | --- |
| 主 PR 正常候选 | `399755a` | success | success | success | [45383895868](https://github.com/laugh0608/RadishForge/actions/runs/45383895868) |
| 草稿中加入失效的文档链接及故意失败的 unittest | `5fbf953` | failure | failure | failure | [45384020491](https://github.com/laugh0608/RadishForge/actions/runs/45384020491) |
| 草稿让治理组件意外跳过 | `cd7e750` | skipped | success | failure | [45384166885](https://github.com/laugh0608/RadishForge/actions/runs/45384166885) |
| 草稿在测试组件运行期间取消 | `eccca40` | success | cancelled | failure | [45384302406](https://github.com/laugh0608/RadishForge/actions/runs/45384302406) |

负例只写入[草稿 PR #2](https://github.com/laugh0608/RadishForge/pull/2) 的临时分支。验收后已关闭草稿、删除远端临时分支并移除本机临时工作树，GitHub 运行和 PR 记录仍可查阅。PR 事件及合并候选规则见 [GitHub Actions 事件文档](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request)。

## 远端绑定与读回

- 读回成功 [check run 138409828857](https://github.com/laugh0608/RadishForge/actions/runs/45383895868/job/138409828857)，确认名称 `Candidate Quality`、源提交 `399755a7cc383c4c8101b412b5813dc33a1c8880` 和 GitHub Actions App `15368`。三个拒绝样例也由同一 App 上报。
- 验证完成后以 PUT 更新 [Ruleset 26129324](https://github.com/laugh0608/RadishForge/rules/26129324)。读回确认状态 active，仅作用于 `master`，新增且只新增 strict `Candidate Quality`，来源限定 App `15368`。原 PR、删除与非快进保护、合并方式及空 bypass 均保留，`dev` 继续没有生效的 Ruleset。 [GitHub Rulesets API](https://docs.github.com/en/rest/repos/rules#update-a-repository-ruleset)
- 绑定后用 `gh pr checks --required` 核对，主 PR 的 `Candidate Quality` 为必需且成功，草稿最后一条 `Candidate Quality` 为必需且失败。PR #1 合入前最后一次必需检查在源提交 `3a8e7d7` 上通过。 [合并前 CI](https://github.com/laugh0608/RadishForge/actions/runs/45385365112)

需要恢复基础保护时，经相应授权读回同一规则，精确移除本批新增的 `required_status_checks`，保留其他现行规则，并重新验证有效分支规则。M0 的 Gitea Runner 和上游契约运行仍按原计划管理。

## 主线合入、回流与手动验证

- 2026-11-24 19:38:03（Asia/Shanghai），使用宿主机 `gh` 将 [PR #1](https://github.com/laugh0608/RadishForge/pull/1) 以 merge commit `dd88e4b80ace0715e36e918b2f084f4af20531db` 合入 `master`。双亲分别是合入前的 `master`（`c2764aa`）和已通过必需检查的 `dev`（`3a8e7d7`）。
- 在 `dev` 执行 `git merge --ff-only origin/master` 并推送。回流时文件树与已审查的 PR 源提交一致。GitHub 读回 `master` 和 `dev` 均指向 `dd88e4b`，本机也验证了 `origin/master` 是 `origin/dev` 的祖先。
- 通过宿主机 `gh workflow run` 在 `dev` 上触发 `PR Checks`。读回事件为 `workflow_dispatch`，运行 SHA 为 `dd88e4b80ace0715e36e918b2f084f4af20531db`。治理检查、70 项 Python 测试和 `Candidate Quality` 均通过。聚合 check run `138417321544` 由 GitHub Actions App `15368` 上报。 [手动 CI](https://github.com/laugh0608/RadishForge/actions/runs/45386088275)

G0-03 已完成，GOV-03 验收通过。
