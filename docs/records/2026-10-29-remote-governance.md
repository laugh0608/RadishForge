# 2026-10-29 远端推送与基础保护

## 授权与范围

用户已创建 `https://github.com/laugh0608/RadishForge.git` 空仓库，并要求推送提交、按项目规则设置 Rulesets，允许使用本机 gh。仓库 public 可见性由用户创建时确定，本次没有改变可见性。执行使用 gh 2.96.0 与现有 laugh0608 登录，不读取或输出 Token，不修改全局 Git 配置。

## 已执行

1. 确认本地位于 dev、初始基线 `c2764aa278cbed9aab3faf6f43a0556e80e623f4`、工作树无改动、无远端；远程为空，无规则，当前账号具有 admin 权限。
2. 添加 origin，以 atomic push 推送 master / dev，分别建立 upstream。远端两分支初始 SHA 与本地共同基线一致。
3. 确认 master 没有旧式 branch protection（明确返回 404 / Branch not protected）和有效 Ruleset，保留变更前快照。
4. 仅修改配套设置中的实际差异：default_branch 从 main 改为 master，allow_squash_merge 从 true 改为 false。merge / rebase 保持允许；auto merge 与自动删源分支保持关闭。
5. 从基础模板构造 active 请求，创建一条规则；没有导入 CI 版，也没有创建重复规则。
6. 重读仓库设置、规则明细及 master / dev 有效规则。随后将本次记录和状态修订提交到 dev，沿该分支推送；不绕过保护直推主线，也不自行创建晋级 PR。

## 远端结果

- 规则：[RadishForge master protection](https://github.com/laugh0608/RadishForge/rules/26129324)，ID `26129324`，enforcement 为 active。
- 仅匹配 `refs/heads/master`，无排除项、无 bypass。
- 生效规则为 deletion、non_fast_forward、pull_request；PR 审批数 0，要求解决 review conversation，不要求 CODEOWNERS 或最后推送审批。
- 允许 merge / rebase，禁用 squash。默认分支为 master；dev 查询有效规则返回空数组。
- 未配置 required_status_checks；没有活动 workflow，不提前要求不存在的 Candidate Quality。
- 本地模板保留 disabled，远端 active 为已记录的预期差异。

配置前后脱敏快照、实际请求、规则响应、有效规则和初始推送 SHA 见[JSON 证据](2026-10-29-remote-governance.json)。该快照记录配置当时的状态，不会随以后的分支推进自动变化。

## 读回差异与验证边界

首次严格读回比较发现 GitHub 自动补充 `required_reviewers: []` 与 `require_extra_approval_for_unattributed_changes: true`。已分别核对这两个默认值，保留在完整响应中；其余声明字段逐项一致，规则数量与目标也一致，没有忽略任意未知差异。[GitHub 官方说明](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)明确额外审批开关在 required approvals 为 0 时无效，因此没有改动该平台默认项。

本轮完成真实推送、设置 / Ruleset 写入及有效规则 API 读回。未尝试删除或 force push master，未创建测试 PR，也未以非管理员账号验证拒绝行为；不宣称完成完整 GOV-02 行为验收。安全报告渠道未在本次范围内启用或验收，G0-02 保持进行中；G0-03 仍待真实 CI。

本地 `python3 scripts/check-repo.py` 通过，覆盖 49 个文本文件、179 个本地文件链接与治理契约；`python3 -B -m unittest discover -s scripts/tests -v` 的 8 项回归通过，`git diff --check` 无错误。没有安装依赖、启动后台服务、创建 tag / Release 或部署。后续若调整规则，先读取同一 ID 与有效规则，再做最小更新；禁止用重复 POST 或常驻 bypass 处理不明状态。
