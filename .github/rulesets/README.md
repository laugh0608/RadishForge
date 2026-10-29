# GitHub Rulesets 模板

正式政策见 [Rulesets 专题](../../docs/governance/rulesets.md)，分支与回流见[仓库治理](../../docs/governance/repository-governance.md)。本目录无部署副作用，当前未创建远端规则。

- [基础模板](master-protection.json)：无 required check，适用于真实 CI 尚未建立的初始保护。
- [CI 模板](master-protection-ci.json)：在同一规则上增加 strict `Candidate Quality`；启用前须真实运行并绑定查得的 check App ID。
- 两份模板名称相同、互为阶段替代；不要同时 POST。均为 disabled、仅保护 master、默认无 bypass。
- [仓库设置](../repository-settings.json)：独立于 Ruleset 的默认分支与合并选项。

## 操作参考

以下是获授权并明确实际 host / owner / repo 后使用的路径，占位符不是已存在的远端。需要分页的只读请求必须读完全部页，并包含父级规则：

```text
GET /repos/{owner}/{repo}
GET /repos/{owner}/{repo}/rulesets?includes_parents=true
GET /repos/{owner}/{repo}/rulesets/{ruleset_id}
GET /repos/{owner}/{repo}/rules/branches/master
GET /repos/{owner}/{repo}/branches/master/protection
```

先保存脱敏快照及最小差异。创建使用 `POST /repos/{owner}/{repo}/rulesets`，更新使用 `PUT /repos/{owner}/{repo}/rulesets/{ruleset_id}`；仓库设置使用 `PATCH /repos/{owner}/{repo}`。写前选择一个模板，把审阅的请求副本设为 active；不要上传 disabled 模板并声称保护开启，也不要把 GET 的只读元数据原样写回。

请求只放实际 API 接受的字段，CI 阶段补入查明的 integration_id。GitHub host、REST API 版本与权限按启用时核查结果固定，不复用兄弟项目地址、角色 ID、Token 或平台假设。

写后重读设置、规则与有效分支规则，完成专题列出的行为验收；记录 ID、SHA、check run、预期差异、限制与恢复方式。JSON 解析成功只证明本地格式，不能证明远端 API 接受或策略实际阻断。
