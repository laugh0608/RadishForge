# 2026-11-01 scope 组合收敛与身份生命周期验证

## 范围与基线

归属：TOP-IAM，M0-S02 / M0-02，IAM-01 / IAM-02 的上游与受控客户端部分；协同 M0-S01 的隔离配置。用户明确要求先处理三项 scope 差异，收敛白名单 / Gitea 授权配置，继续身份权限验证，暂不启动 Runner。未扩大到 M1 会话 / 绑定、全量兼容或产品工程。

基线为 `fa3ffe8`，其中已有另一批规划规则统一；开始时 dev 工作区和暂存区干净，未 fetch，未改写或覆盖该批规划规则。沿用 `3be73d3` 的本机工具，保留[首轮原始记录](2026-11-01-m0-local-validation.md)和结果，不回写旧结论。

环境仍为 OrbStack context `orbstack`，Linux arm64 / Engine 29.8.2、Compose 5.5.0；使用原 Gitea 28.2.0-rootless / PostgreSQL 18.6-bookworm 固定 Digest。仅回环 18443 / 19443、三个平台服务和任务专用卷 / CA，不更新宿主工具或启动 Runner。启动前已说明复用范围、2.75 GiB 限额、预计测试窗口与 cleanup。

## 已落地的配置与边界

- [gitea-auth-profile.json](../../tests/contracts/m0/gitea-auth-profile.json)是 M0 单一配置来源：`identity`、`resource_read`、`issue_write` 三种完整组合、各自 issuer 和 confidential client / 精确 callback / 不跳过首次同意设置。
- [m0_scope.py](../../scripts/m0_scope.py)先校验用途、issuer 和完整集合，再允许应用注册 / 授权 / 刷新。默认 OIDC、未知 scope、all、缺 public-only、额外 admin、只读换写入、错误 issuer、空 scope 的八种用例均在联网前拒绝；另有纯本地重复 / 格式和权限组测试。
- 实际登记设置通过公开 API 回读；实际 scope 通过带客户端认证的 introspection 核对，不能仅凭请求字符串宣称已限制。新凭据还须是有效 metadata，并经 `/api/v1/user` 读取有效账号且 ID 与 subject 一致。刷新不接受增加 scope，资源权限始终由真实上游用户决定。
- 本批对新隔离实例显式开启 refresh 单次使用，access token 30 秒 / refresh token 1 小时、关闭默认应用。短 TTL 仅用于等待真实过期；无系统时钟修改，没有将其设为产品默认值。
- API 传输已改为无 cookie，只携带每次指定的 Basic / Bearer；原生登录 / 同意步骤有独立 CookieJar。避免管理员 / 普通用户或浏览器会话干扰 API 权限结果；最终整批已按该方式重跑。

设计取舍、许可 / 版本边界与后续实现契约见[ADR 0003](../adr/0003-gitea-authorization-profiles.md)。这里是 M0 验证实现；自有 Go 服务仍须在 M1 落实同样的白名单、事务和在线复核，不声称产品保护已经上线。

## 三项原始 scope 差异如何处理

| 原始行为 | 处理与本轮证据 | 保留限制 |
| --- | --- | --- |
| `openid public-only email profile` 的 UserInfo 403 | 身份组合显式加入 `read:user`，UserInfo 200；自己的私有仓库和 Issue 写入为 403 | 原组合没有修复；Gitea-specific 配置不推广给所有 IdP |
| 常见 OIDC scope 可读私有资源 | 固定完整身份组合，并与资源客户端分开；省略限制项的请求在联网前拒绝 | 客户端约束不等于 Gitea 为任意应用限制 scope |
| 未知 scope 可能宽授权回落 | 注册 / 授权 / 刷新前拒绝未知或跨用途组合，授权后验证实际 scope | 直接构造的上游请求仍保留原始差异，不宣传原生兼容通过 |

三种组合分别注册为 confidential client，client ID 不同。身份 Token 不可用于另一 issuer 的资源；只读组合能读私有资源但不能写 Issue；Issue 写入组合可以创建 Issue，但不能创建仓库。Scope 是 Gitea 路由组粒度，不是逐按钮权限。

## 授权生命周期真实结果

最终受控组合批次 `rf-m0-local-4763d2fc`，结果及请求轨迹见[脱敏结果](2026-11-01-m0-auth-profile-results.json)。共有 21 条命名记录，含环境 / fixture / 等待 / 完成标记，不按数量推算产品完成率。

已验证：拒绝用户同意时无授权码 / Token；错误 client secret 被拒绝；未登记 callback 被拒绝；refresh token 不能跨客户端使用；本地拒绝刷新扩权；开启 invalidation 后 refresh 轮换且旧值重放被拒绝；刷新后的只读 scope 不扩大；移除协作者后刷新不能恢复仓库权限；删除资源 OAuth 应用使 access / refresh 均失效，独立身份授权仍可用；真实等待 access token 过期后 API 为 401，合法 refresh 恢复原只读能力。

仍保留两项新生命周期差异，组合探针因此退出 **2**，没有改为全通过：

| 用例 | 实际 | 本地停止边界 |
| --- | --- | --- |
| 禁用账号后刷新 | 上游仍返回 Token；私有资源 403；introspection 最终响应为非对象正文（`str`），不能证明 active / scope | 凭据复核拒绝非对象 metadata，未把该 Token 接纳为有效账号；不能从刷新 200 推断账号可用 |
| 过期 Token introspection | 旧 Token 为 401，同一客户端凭据查询新 Token 为 200 active；API 对过期 Token 也为 401 | 保留与预期 `200 active:false` 的协议差异；不能把所有 401 当作客户端密钥错误、重试或默认通过 |

生命周期差异不表示资源越权已经发生：本轮禁用账号和撤权后的资源访问均拒绝。它们说明上游 Token 签发 / introspection / 实际资源权限需要分别建模。M1 不能仅凭 refresh 成功或缺失元数据维持有效会话。

本工具轨迹保存请求路径及最终响应状态，省略查询参数、请求体、cookie、client secret 和 Token；同源登录重定向可产生最终非 JSON 正文，所以 HTTP 200 还须检查内容结构。API cookie 已排除后上述差异仍复现。过期诊断还在同一凭据下重复对照旧 / 新 Token，排除了客户端凭据失效的解释；未保留不必要的秘密正文。

## 调试与证据限制

拒绝同意用例初次中断源于探针参数与表单变量同名，实际提交仍为同意；核实后改为独立参数 `approve` 并从新隔离批次验证真正的 access_denied，没有把探针错误归咎上游。随后补齐 metadata 类型校验，把禁用账号的非对象响应作为拒绝原因保留，未用默认 active / 空 scope 掩盖问题。

原始上游模式保持为显式 `--mode discovery`，受控模式为默认 `profiles`。前者失败不能被后者通过覆盖；新 profile 元数据或版本改变须新建批次、核对配置哈希。代码 / 配置 SHA-256、容器 ID、版本和实际 trace 在结果文件中保存，不写原始 Token / JWT。

另建未开启 profile provider settings 的批次 `rf-m0-local-6debce31`，以无 cookie 的 API 客户端回归原始发现模式：17 条命名记录、三项原始 scope 差异完整复现，退出 2。结果保存在同一 JSON 的 `upstream_regression` 中，与受控模式分开；因此不是通过修改探针传输或将旧失败改名，来制造上游通过。

未覆盖：完整浏览器交互 / cookie 域、Go 会话 / 绑定 / 加密存储、刷新 Token 自身一小时过期、并发刷新、解绑 / 后台作业取消、其他 IdP / 版本、Actions / Runner、OCI / Release、amd64 与生产。未关闭整个 M0-02、IAM-01 / IAM-02 或 M0 阶段出口。

## 本地检查与交接

| 检查 | 实际结果与范围 |
| --- | --- |
| `python3 -B -m unittest discover -s scripts/tests -v` | 13 项通过：既有 8 项治理回归 + 5 项新增 scope 策略测试；不联网、不启动 Docker |
| `python3 scripts/check-repo.py`、`git diff --check` | 通过；本地格式 / 链接 / JSON / 根入口 / 政策 / 空白，不把业务差异当作已解决 |
| Python AST、`sh -n` | Python 与既有 PostgreSQL 初始化脚本语法通过；不代替真实用例 |
| 受控组合与原始模式 | 受控模式 21 条记录、2 项新生命周期差异；原始模式 17 条记录、3 项旧 scope 差异；两者均退出 2，未关闭 IAM / M0 |
| 证据完整性 / 秘密 | 最终实际执行的脚本、配置 SHA-256 一致；两类 trace 均去除参数 / 请求体 / cookie / Token；凭据和 JWT 未导出，本任务 Python 缓存已清理 |
| 资源清理 | 两个最终批次容器 / 卷 / 网络均读回为 0，`.local/m0` 凭据 / 证书删除；无 Runner、全局设置变更或其他项目资源清理 |
| Git 交付 | 新增 6 个、更新 11 个文件，无删除；暂存区为空，未提交 / 推送；`fa3ffe8` 的规划规则保留 |

下一步在 M0-S02 内收口刷新 / introspection 生命周期适配，补刷新 Token 自身到期、并发、解绑与后台授权；M1 前仍需完成阶段关键范围。当前新增 JSON / Python 约束只用于 M0；没有实现 Go 产品会话或提前建立工程框架。
