# 2026-11-24 M0 arm64 单镜像与私有 Release

普通写者向隔离 Gitea 的私有仓库 `owner/private-source` 推送一次轻量 Tag。唯一的工作流检出触发提交，并把其 SHA 写入真实 scratch 镜像。独立读者从两个私有命名空间按 Digest 拉回镜像，再从同一提交的已发布 Release 下载来源附件，逐字节核对成功。 [脱敏结果与附件内容](2026-11-24-m0-arm64-image-release-results.json) · [arm64 工作流](../../tests/contracts/m0/compat/m0-image-arm64.yml) · [操作单](../../tests/contracts/m0/compat/runner-runbook.md#arm64-单镜像与私有-release)

| 对象 | 独立回读 |
| --- | --- |
| 源码 | `refs/tags/m0-oci-arm64-01` 指向 `eb7b90db4f93fb9e1820856847052d466f23aa3d`。读者按 SHA 取得工作流，YAML SHA-256 为 `277e480f3a819e3dcc58279711fa97c1adcc2010ebdcf88870f171f7e4e77ed6` |
| Actions | 推送前 0 个 run，推送后 1 个。run / attempt / job 均为 `1`，两步及三个终态均为 `success`。北京时间 20:52:26 至 20:52:31。读者日志记录真实检出 SHA、run / attempt 和构建 Digest，8,148 字节，SHA-256 为 `48dfafedf22f5d961a37462617f1cbc5ad1abd0893265f5c6665383077e08ea5`。顶层 `repository_id=0` 的既有差异仍在，按仓库路径和嵌套 ID `1` 对账 |
| 镜像 | 构建端输出、两个 Registry 位置的 Manifest 原字节和响应头均为 `sha256:88ca004767ce4e2202d5be275fa5abc9eb165d95afde806c789ee1d7ee8e3e20`。发布位置为 `forge.m0.test:3000/m0-release-org/m0-probe`，保留引用 `m0-retain-arm64-01` |
| 内容 | 独立读者分别按 Digest 下载构建和发布两份副本。两份 config、压缩层与未压缩层摘要逐项一致；平台均为 `linux/arm64`，唯一普通文件 `/source-sha` 内容均为触发提交的完整 SHA 加换行。 [校验器](../../scripts/m0_image_source.py) |
| Release | 普通写者创建草稿、上传附件，前检确认原 Tag、SHA 和附件后发布。独立读者按 ID 与 Tag 读回 Release `1`，`draft=false`，作者 `writer`。附件 `1` 为 `m0-provenance.json`，463 字节，SHA-256 为 `144de19d575914dd4596ba856cd11aaea888065b1f2b636441bd9dcb13dba7b1`。下载内容包含完整 ref、SHA、run / attempt / job、日志摘要、固定发布镜像坐标及 Release ID |

## 权限与运行边界

- job 只持构建账号的 `write:package` 测试 PAT。晋级使用独立普通账号 `publisher`，通过 Skopeo 1.18.0 的 `copy --preserve-digests` 将构建组织的原始制品复制到发布组织。读者以自己的 `read:package` 拉取、以 `read:repository` 下载附件。Release 写者使用仓库级用途的 `write:repository` PAT；这个 scope 约束操作类别，实际仓库范围仍由账号权限决定。
- 已确认发布制品存在时，匿名与构建账号按 Digest 读取发布制品均为 401。构建账号与仅有读取权限的读者向发布包启动上传均为 401，两次均无 Location。仓库外普通账号读取 run、attempt、日志、Release 详情均为 404。
- 本地基线 `6b15b67`，UTM 来宾 `RadishForge-M0-image-79SYNS`，UUID `B73EFDDC-777E-4469-8260-EDF7A753346D`。4 vCPU、6 GiB、12 GiB 虚盘，目录共享关闭。沿用 Gitea 28.2.0、PostgreSQL 18.6、Runner 5.2.4、来宾 Engine 26.1.5+dfsg1。BuildKit v0.35.1 的真实 worker 仅列出 `linux/arm64`，使用 rootless OCI、native snapshotter 和进程沙盒。构建用户无 Docker 组权限，systemd 读回地址白名单、内存与 CPU 限额。真实 job 非 privileged，internal 网络，只读挂载 CA、buildctl、专用 BuildKit socket，工作流断言 Docker socket 缺失。
- 源码检出使用 Git 和临时 askpass，构建使用固定 `buildctl`。原始 amd64 样例中的 checkout / login / setup-buildx / build-push Action 组合作为原生 COMP-01 独立验收。本批覆盖私有 arm64 功能链路。 [原样工作流](../../tests/contracts/m0/compat/m0-image.yml)
- 仓库 secret 已删除并读回 0 条。五份 PAT 删除均为 204，原 ID 均缺失，原凭据再次请求均为 401。历史 G27 对已签发 Registry Bearer 的结论继续适用。Runner 注销 204，列表 0、详情 404；构建服务已停、运行容器为 0。按 UUID 核对停机后删除 VM 和本批临时盘、seed、密钥。宿主端口 28422 释放，UTM 清单恢复原有五台停止 VM。Debian 镜像和清理前来宾网络接收合计约 1.40 GiB。

## 对 M0 出口的影响

[出口第 2 项](../planning/acceptance.md#m0-exit)要求的普通用户跨制品来源关联已有实测，失败、取消和失联沿用[生命周期记录](2026-11-24-m0-runner-lifecycle.md)。G26 的独立发布引用、清理和恢复证据现在能与一条真实运行相连；30 天产品窗口与 G27 产品侧停用仍沿[原决定](../adr/0006-oci-authorization-and-digest-retention.md#first-release-oci-decisions)验收。本次仅发布来宾内的合成 Release。

下一步按 M0-S04 对首批权限与兼容承诺逐项评审，先列出本机可验证的 Gitea 行为和仍需原生 amd64、GitHub 普通身份的双端项。根据所选范围取得行为证据或形成明确的范围决定，再冻结支持组合并评审 M1 交接。五组件和生产部署沿原阶段安排。
