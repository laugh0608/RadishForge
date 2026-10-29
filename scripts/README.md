# 本地治理检查

本目录是仓库维护工具，不是业务服务。使用 Python 3.9+ 标准库，无第三方依赖，不安装包、不联网、不启动服务、不写 Git。产品技术栈仍为 Go + TypeScript + React。

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
