# 本地治理检查

本目录包含仓库维护及 M0 上游验证工具，不是业务服务。Python 工具使用标准库，无第三方包依赖；产品技术栈仍为 Go + TypeScript + React。下列治理检查不安装包、不联网、不启动服务、不写 Git；M0 工具的 Docker / 网络副作用单列说明。

```bash
python3 scripts/check-repo.py
python3 -B -m unittest discover -s scripts/tests -v
```

Windows 可用 `py -3` 替代 `python3`，不额外维护仅转发命令的 shell / PowerShell wrapper。

## 检查范围

- 必需治理文件、UTF-8 无 BOM、LF、末尾换行与尾随空白（Markdown 两空格换行允许）。
- JSON 解析、Markdown 行内链接的本地文件目标、AGENTS / CLAUDE 除标题一致、根入口 250 行上限。
- 仓库设置、基础 / CI Ruleset 的目标分支、合并、审批、bypass、disabled 模板状态及阶段差异。
- 已初始化 Git 时，检查工作树 / 暂存区的 diff 空白；文件清单含已跟踪与未忽略的未跟踪文件。
- 无 Git 时遍历源码目录并排除明确的本地产物目录，显式输出 Git 检查未运行，不声称工作树干净。

已有 Git 后可使用 `python3 scripts/check-repo.py --base-ref <ancestor-sha>` 检查指定祖先到 HEAD 的 diff 空白与提交标题。PR 使用实际 merge base；分叉的原始 base tip、缺失历史、无 Git、无提交或非法 ref 必须失败，不自动换成空范围。真实多父 merge 允许 Git 生成标题，不放行伪造 Merge 标题的单父提交。

非零退出表示失败；失败后修复原因，不自动重写文件。脚本不检查远程 URL 可用性、Markdown 标题锚点 / 引用式链接、完整 YAML schema、真实 GitHub API schema、秘密泄漏或业务功能；这些按需人工 / 专门工具复核，不从本地 PASS 推断远端保护、CI 或安全验收成功。

## 维护方式

新增真实约束时同步治理专题与检查器，补充能揭露错误放行的负例。后续建立 CI 时复用这个入口，先运行成功和故障传播验收，再将真实 job 纳入 Candidate Quality；当前没有活动 workflow。

## M0 本机验证工具

[m0_local.py](m0_local.py)管理明确归属的本机 Docker 验证批次，[m0_contracts.py](m0_contracts.py)验证真实 Gitea OIDC / OAuth、普通用户权限及 Issue API；两者不是默认治理检查的一部分。配置、命令、资源、退出码、秘密和清理边界见[M0 契约说明](../tests/contracts/m0/README.md)。

`prepare` 生成本批私密文件，`pull` 下载固定镜像，`up` 初始化新卷并启动三个平台服务，协议探针写入合成账号 / 仓库 / Issue / OAuth 授权，`cleanup` 删除本批测试资源。仅在对应授权下执行，不因本地治理通过自动启动；当前配置没有 Runner，也不挂 Docker socket。

授权组合配置位于 [gitea-auth-profile.json](../tests/contracts/m0/gitea-auth-profile.json)，[m0_scope.py](m0_scope.py)校验完整用途组合与 issuer；对应纯本地负例测试包含在现有 unittest 入口内。真实组合验证使用 `prepare --auth-profile` 和探针 `--mode profiles`；原始上游差异只能通过显式 `--mode discovery` 复现，不能以组合验证取代原始兼容结论。

[m0_oauth.py](m0_oauth.py)由既有探针提取，统一 HTTP / 浏览器会话分离、授权码 / PKCE、凭据 metadata 与在线账号复核；[m0_lifecycle.py](m0_lifecycle.py)使用同一实现验证生命周期，没有新增产品会话或第二套 scope 规则。纯本地凭据拒绝测试也在 unittest 入口内，覆盖 HTML / 非对象 metadata、401 原因未归属、主体不符、账号拒绝、网络未知及不重试；不替代真实上游证据。

`--mode lifecycle` 使用受控配置，含真实一小时 refresh token 到期和一次原生页面单用户撤销，需要单独预算长时窗口。`consent-ready` / `consent-revoked` 仅协调页面点击前后的取证时点，真实失效仍由 API 断言验证。历史两项差异使用新隔离批次 `prepare --auth-profile --legacy-query-auth` 与 `--mode lifecycle-baseline` 复现。步骤、浏览器秘密边界和清理要求见[M0 契约说明](../tests/contracts/m0/README.md)。

`--mode issues` 调用 [m0_issues.py](m0_issues.py) 验证 Issue 列表 / 筛选 / 分页、正文版本与状态、元数据 / 分配、真实权限、非法输入和删除。[m0_issue_faults.py](m0_issue_faults.py)仅在超时用例中临时监听回环 18543，固定一个合成 Issue POST 的路径 / 凭据 / 请求体，不是通用代理或产品服务。共享 HTTP 默认超时仍为 15 秒，故障用例单次显式 1 秒；网络错误记录 unknown，不自动重试。新增纯本地前检、分页、对账和传输负例同样从 unittest 入口运行；不启动 Docker 或监听端口。
