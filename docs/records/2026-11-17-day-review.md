# 2026-11-17 提交回顾与收工交接

按 Asia/Shanghai 日界核对本地 `dev`。收工文档提交前，`339281c` 至 `6d0465a` 共有 12 个提交，涉及 42 个不同路径。此次回顾另以文档提交保存。

## 当日提交

| 提交 | 交付与证据边界 |
| --- | --- |
| `22094d4` | 固定基础 Runner 操作单、首轮 job 镜像的 amd64 Digest、身份与清理边界。完成静态核查，工作流执行待验证。 [Runner 准备](2026-11-17-m0-runner-preparation.md) |
| `4c8b714` | 确认 G26 / G27 的首版取舍，隔离实测 G24—G26 的发布权限、真实清理和原 Digest 恢复。最终批退出 2，保留 G25 原生差异。30 天产品窗口及组合仍待验。 [OCI 实测](2026-11-17-m0-oci-retention-validation.md) |
| `041cd88` | 实测 G19 组织仓库 team 降权和移除，原有效凭据被拒，独立读者持续可读已发布对照。最终批退出 0。 [G19 实测](2026-11-17-m0-release-org-role-transitions.md) |
| `2a1bf3e` | 实测 G20 省略、混合 PATCH 和 `null`。两个混合用例只写入非空字段，退出 2。 [G20 实测](2026-11-17-m0-release-edit-fields.md) |
| `d3cd475` | 仅重启资源 Gitea 后，正常自助撤销仍有效，独立授权继续可用，退出 0。 [G06 重启](2026-11-17-m0-oauth-restart-validation.md) |
| `596d1b7` | 复核 G06 证据，将晚到回调、在途刷新结果防护写入 M1 验收；两项上游时序结果待验。 [撤销时序复核](2026-11-17-m0-oauth-revocation-timing-review.md) |
| `b40b3fb` | 对照 COMP-01 双端 REST 证据，确认现有 GitHub 测试仓库的固定引用、已发布 Release 和附件元数据。 [REST 复核](2026-11-17-m0-rest-evidence-review.md) |
| `3111071` | 只读回查现有测试仓库仅有 `admin` 所有者，普通写者与移除协作者继续待验。 [协作者复查](2026-11-17-m0-rest-evidence-review.md#个人仓库普通写者复查) |
| `dc36df8` | 在共享 Release 发布与超时回查绑定原 ID、Tag 名和完整 SHA，补回归。 [G22 本地回归](2026-11-17-m0-release-publication-readback.md) |
| `dc33663` | 在隔离 Gitea 实测已有 / 新建 Tag，以及已提交 / 未转发超时的只读回查，退出 0。 [G22 实测](2026-11-17-m0-release-publication-readback.md#固定版-gitea-隔离实测) |
| `a37c21d` | 增加 G23 新建 Tag 发布前按完整 SHA 回读目标仓库提交，读取失败时以本地回归验证零 PATCH。 [G23 本地前检](2026-11-17-m0-release-target-preflight.md) |
| `6d0465a` | 隔离复测 G23，完整 SHA 响应 200 且匹配后仅发一次 PATCH，发布后原引用一致，退出 0。 [G23 复测](2026-11-17-m0-release-target-preflight.md#固定版-gitea-隔离复测) |

## 代码与文档复核

- 核对 `m0_contracts.py` 的四个新增模式，以及 OCI 定向脚本的独立执行入口。工具索引补齐 `release-publication`，契约手册补上超时按原 Tag 名回读的要求。 [工具索引](../../scripts/README.md) · [发布与超时入口](../../tests/contracts/m0/README.md#g22-release-发布与超时回读)
- `m0_release_org.py` 和 `m0_rest.py` 共用 `m0_releases.py` 的发布校验。后续实测使用个人仓库的定向入口，组织 team 与双端 REST 的结果仍对应各自归档批次。交付专题更新 G19 / G20 的既有证据及 G22 / G23 的前检和对账边界。 [交付链路](../architecture/delivery-flow.md#release-最小执行切片)
- `m0_oci_retention.py` 的真实清理及原字节恢复按短测记录，产品保留窗口仍按 ADR 0006 验收。`m0_consent_restart.py` 的重启核验限本批资源 Gitea；晚到授权结果的防护仍归 M1。 [OCI 首版决定](../adr/0006-oci-authorization-and-digest-retention.md#first-release-oci-decisions) · [M1 防护验收](2026-11-17-m0-oauth-revocation-timing-review.md#m1-防护验收)

## 验证与交接

- 70 项本地测试、治理检查、当日提交范围的空白检查和九份改动 Python 文件的语法解析通过。六份最终实测记录的源码摘要均与各自入档提交一致。首次中断与后续批次按原记录保留。
- 收尾只读核对 OrbStack，今日九个批次的容器、卷和网络均为 0。`.local/m0` 已移除，18443、19443、18543 可以重新绑定。固定镜像保留在缓存，Runner / Actions 暂停，收尾未启动环境或推送。
- 单人、单台 Mac 的下一次工作建议是一批 G23 拒绝用例。按完整 SHA 查询 404 时记录零发布 PATCH，回读原草稿与 Tag 后清理。之后集中决定现有设备下的 Runner 执行平台，GitHub 普通角色继续待验证。 [接续事项](../planning/m0-validation.md#接续事项) · [当前停止线](../status/current.md#下一步)
