# ADR 0005：Release 授权、固定引用与附件对账

日期：2026-11-04。状态：已接受，限于 M0 受控探针与后续实现契约；原始差异进入 M0-S04，不批准整个 M0、产品发布器或 GitHub 等价兼容。

## 原因与证据

[Release 隔离取证](../records/2026-11-04-m0-release-validation.md)覆盖普通用户草稿 / 编辑 / 发布、附件、Tag / SHA、权限 / 撤权 / 删除以及真实响应丢失。最终批次保留五项差异：只读 scope 的草稿元数据与附件可见性不一致、空字段清除被忽略、Tag 创建状态码与 OpenAPI 不同、已有 Tag 可覆盖 target 的实际提交含义、无效 target 发布返回 500。

不能把正确 scope、HTTP 2xx、`target_commitish` 或下载 URL 之一单独视为已按请求完成。用户身份、资源单元权限、实际 Tag 提交与附件内容必须分别核实；不修补 Gitea 核心、不读写其业务数据库或使用服务账号补足权限。

## 决定

1. **Release 使用独立用途。** 在原三种组合不变的基础上增加 `release_write = openid read:user write:repository`，独立 confidential client、精确 callback、显式同意、实际 grant 与在线账号复核，沿用 [ADR 0003](0003-gitea-authorization-profiles.md)。`write:repository` 是宽于 Release 按钮的仓库权限，不能改名宣称仅发布权限；它不包含 package 用途，不自动推广为 OCI 凭据。既有 `resource_read` / `issue_write` 对 Release 写入拒绝继续验收。
2. **草稿读取明确校验用途与角色。** 元数据 API 在只读 scope 下返回 404，但仓库所有者持相同凭据能从 UUID 和 API 展示的下载路径读取草稿附件。受控草稿操作要求 Release 写用途及当前 Release 单元写权限，并在下载前回查对象状态 / 归属；无权或无法确认则停止。这个约束尚未进入产品，也不能限制用户直接调用原生接口；原始差异不改成成功。普通仓库读者与外部用户的直接下载拒绝已分别取证，不宣称存在跨用户泄漏。
3. **固定源码用 Tag 的实际 commit。** 保存完整 SHA，发布前独立读取精确 Tag 的 `commit.sha`，已有 Tag 指向其他提交时拒绝写入；新 Tag 发布后再次核对。`target_commitish` 不等于已有 Tag 已被移动，草稿创建也不保证已生成 Git Tag。前后两次检查不能消除并发移动竞态；写后不符须保留实际副作用并停止后续发布链路，不自动删除 / 重建 Release 或强移 Tag 模拟回滚。
4. **请求字段逐项回读。** 当前 PATCH 的空 `name` / `body` 返回 200 而原值保留，不能报告“已清空”。尚无通过验证的公开清空路径，不用空格替代、删除重建或隐藏错误；如需承诺该能力，M0-S04 另行确认公开方案和范围。无效 target 的 500 仍保留原码，回读草稿和 Tag 后再判断本次副作用，不因这一例草稿未发布外推所有 500 都无写入。
5. **按精确版本处理状态码差异。** 固定 OpenAPI 声明 Tag POST 为 200，同版处理器和真实返回均为 201；M0 精确接受 201 并单独记录 gap，不用宽状态码集合吞掉差异、不改写上游生成文档。后续客户端 / 适配器仍须明确版本与失败边界。
6. **附件以身份和内容对账。** 原始 bytes 有大小上限，核对 ID / UUID、名称、size、下载实收长度与 SHA-256；同名不是幂等键，元数据没有内容 Digest。列表中的仓库 / Tag / 名称路径与详情中的 UUID 路径均须精确绑定任务 origin 与对象；两种有效 URL 表示不作为身份变化。比较稳定字段和真实内容，不按字符串 URL 相等或 `download_count` 判断同一上传。
7. **未知写入只回查。** 创建按固定仓库 + 唯一 tag / 合成标记 / 作者查询，再回读详情；发布按保存的 ID、draft 与 Tag SHA 回查；附件按保存的 Release、名称候选及字节摘要查询。零条、多条、失权、查询失败或字段 / 内容不符均不自动再次写入，不选择 latest 或删除归属未确认的对象。半包传输后零可见对象仍为 unknown，不能据此断言请求没有执行或不存在临时存储。

本批标记仅属于合成夹具，不是上游原生幂等键或任意生产请求关联方案。`m0_oauth.py` 的有界字节传输与 `m0_response_loss.py` 的固定端点注入仅用于 M0；产品授权、草稿 / 部分完成交互、请求持久化、崩溃恢复、五组件清单与发布冻结仍需后续实现和真实验收。

## 2026-11-09 草稿权限与字段清除核查

固定版按 ID、列表和 REST 附件元数据共用草稿鉴权。原生下载和按 Tag 的 REST 详情要求用户拥有 Release 单元写权限，Token 只需仓库读 scope。同源对照已实测普通写者持 `resource_read` 时按 Tag 返回同一草稿，两种下载地址返回夹具字节，按 ID 和 REST 附件单项均为 404。普通读者和外部用户五条路径均为 404。该批也复现单独 PATCH 空 `body` 为 200 且保留原值。 [源码核查](../records/2026-11-09-m0-release-public-mechanisms.md) · [Gitea 同源对照](../records/2026-11-09-m0-gitea-rest-comparison.md)

- **G19 产品边界。** 草稿列表、按 ID / Tag 详情、附件元数据和字节交付统一校验实际 `release_write` grant 及当前用户的 Release 单元写权限。绑定仓库、Release 和附件后再返回内容。只读用途、失权、归属不符或无法核实时拒绝。先核验授权再读取上游内容，草稿下载由服务端执行同一检查，返回受控字节。原生地址直接访问仍由 Gitea 的策略决定，原始差异保留。
- **G20 产品边界。** 固定版 REST PATCH 支持非空更新，省略字段保留原值。收到显式清空现有标题或说明的请求，提交前报告公开 API 不支持该意图。含清空与其他字段的混合请求整体停止，避免只修改部分字段。原生页面要求标题非空，手动清空说明是待实测候选。公开自动清除缺口保留，产品调用范围限公开契约。成功以原 Release 的字段回读为准。

若首版要求原生下载也强制仓库写 scope，或必须通过公开 API 清空说明或标题，需先确认公开上游方案和支持范围。保留 [定向补证条件](../planning/m0-validation.md#release-草稿权限与字段清除补证条件)。

## 停止线

保留五项原始差异、早期中断批次及非零退出码，进入[既有差异基线](../architecture/github-compatibility.md#m0-现有差异基线)；不以本 ADR 关闭 REL / BASE / COMP、降低权限或原子性标准。本 Release 批次未包含 OCI；同日后续的 OCI 协议 / 客户端证据及限制见[ADR 0006](0006-oci-authorization-and-digest-retention.md)，不回写本批原始结果。Actions / Runner、真实 workflow run / attempt、完整客户端兼容及生产仍未验证，Runner 继续暂停，不进入 M1。

来源：固定提交的[Release API](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/v1/repo/release.go)、[Release / Tag 服务](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/services/release/release.go)、[Tag API](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/api/v1/repo/tag.go)、[附件下载与 scope 检查](https://github.com/go-gitea/gitea/blob/829b49c1ae96015e345f9d2a0eb1ea7acd5f31e1/routers/web/repo/attachment.go)；来源摘要与实际证据见验证记录。
