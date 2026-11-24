# 2026-11-24 M0 Actions 只读入口与上游修正核查

## 候选版本

以已测 Gitea 28.2.0 / Runner 5.2.4 为基线，核对截至 11 月 24 日发布的后续稳定版说明。28.3.0 的 Issue 权限条目涉及子资源读取，其 Actions 修正涉及停用仓库后领取排队 job。28.4.0 的 Actions 权限条目涉及仓库管理员调用管理 API。两版发行说明均未明确列出本项目所需的运行时只读写入拒绝修正。停用仓库时，新派发、已有排队 job 和运行中 job 须分别对账。此前 28.2.0 的 403 仅覆盖新手动派发。[28.3.0 发行](https://github.com/go-gitea/gitea/releases/tag/v28.3.0) · [排队任务修正](https://github.com/go-gitea/gitea/pull/40122) · [28.4.0 发行](https://github.com/go-gitea/gitea/releases/tag/v28.4.0) · [手动派发实测](2026-11-24-m0-actions-settings.md)

Runner 5.3.0、5.4.0、5.4.1、6.0.0、6.0.1 的发行说明同样未标出对应修正。Gitea 28.2.0、28.3.0、28.4.0 的 job Token 设计文件 SHA-256 相同，均为 `8f39065e5373a1c752d15ebb5919e12ef7f4d89fdbd6be3fcf8252830d78d5c9`。三个版本的公开 OpenAPI 均未列出环境配置或待审批部署路径。以上为公开契约与发行说明核查，新版本的实际运行时行为仍待有针对性的证据。[Runner 发行目录](https://gitea.com/gitea/runner/releases) · [28.4.0 固定设计](https://github.com/go-gitea/gitea/blob/0b5dfdeeeaadf6350314246c5936b53cce38170c/services/actions/token_permission_design.md) · [28.4.0 固定 OpenAPI](https://raw.githubusercontent.com/go-gitea/gitea/0b5dfdeeeaadf6350314246c5936b53cce38170c/templates/swagger/v1-openapi3.generated.json)

## 固定模板的只读入口

本批用独立工作流检验一个较小的承诺：指定 job 能读取一个合成私有仓库的 Issue 列表，其写请求停在入口。模板访问 `https://read.m0.test:3000/m0/issue-list`，入口仅允许这个精确地址的 GET，固定 Gitea 上游、方法、仓库和资源路径。读取沿用请求者的 job Token，入口校验上游 TLS，仅转交授权头，忽略客户端请求体。写者从独立网络使用自己的仓库权限做正向对照。[工作流](../../tests/contracts/m0/compat/m0-readgate-arm64.yml) · [入口配置](../../tests/contracts/m0/compat/arm64-readgate.conf)

Runner 控制连接与 job 分网，Gitea 和 PostgreSQL 另有数据库网。三张网均为 VM 内部网络。job 网到来宾的入站规则只接受入口地址的 TCP 3000，来自该网的转发被丢弃。入口日志只保存时刻、方法、本地与上游状态码。

实验从 Debian trixie-security 的 arm64 包中解包 nginx `1.26.3-3+deb13u11`，572,848 字节，SHA-256 为 `4a2153ccbc440727f31743d4a2e0e59578641e7984625ef19a938291d995133f`。包内版权清单标明 nginx 主体为 BSD-2-Clause，其余文件按清单归属。二进制仅用于本次来宾实验。[Debian 软件包](https://security.debian.org/debian-security/pool/updates/main/n/nginx/nginx_1.26.3-3+deb13u11_arm64.deb) · [nginx 上游代理文档](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)

## 独立读回

普通写者派发一次。普通读者核对 `refs/heads/main` 的源码 SHA 为 `b2d5425d5192612c3b39d7c94825e6f8d436172e`，并按 SHA 回读模板。run / attempt / job 均为 1，三个终态均为 `success`。北京时间 21:50:33 出现预期日志标记。独立读取的两份日志均为 3,822 字节，SHA-256 均为 `76748770d30fb9581da7b7d1f817f8c601c48f484f6926b15282bfaa2e128a4b`。仓库外账号读取该 run、attempt 和日志均为 404。[脱敏结果与逐请求记录](2026-11-24-m0-arm64-readgate-results.json)

| 对照 | 实际观察 |
| --- | --- |
| 私有读取 | 匿名 GET 的入口及上游均为 403。真实 job 带自己的 Token 读取同一入口，两端均为 200，返回唯一的种子 Issue 1。 |
| job 写入 | 同一 job 向该入口提交合成 Issue，收到本地 403 和固定拒绝标记。入口日志的上游状态为 `-`。job 完成后，普通读者从 Gitea 查到的集合仍只有 Issue 1。 |
| 执行网络 | 现场检查实际容器仅加入 job 网、非 privileged、丢弃全部 capabilities、启用 no-new-privileges，唯一 bind mount 为只读 CA。容器与 Gitea 后端建立 TCP 连接得到 `ENETUNREACH`，同时控制网的普通读者读取该仓库为 200。 |
| 普通写者 | 在独立读者完成零新增核对后，写者通过 Gitea 原生接口提交相同标题，返回 201。读者再查到 Issue 1 和新增的 Issue 2。 |

**M0 判定。** 固定模板的单一 Issue 列表入口已取得读取成功、写入本地拒绝、零新增和授权写者对照。该路径属于需适配的候选，原始工作流的原生权限验收仍为失败。下一项决定是首版是否接受这一受控模板范围。若选用，还须证明模板与 Runner 配置在调度前受独立约束，并单独验收环境审批。当前尚无任意 YAML、fork、环境秘密或原生 amd64 的新证据。

本批基线为 `f4ea207`。仓库级 Runner 注销为 204，原 ID 回读 404、列表为 0；入口已停止，来宾运行容器为 0。UTM VM 和本批虚盘、seed、密钥均已清理，UTM 清单恢复原有五台停止的 VM，回环端口 28422 已释放。Debian 镜像和来宾网卡接收量合计约 1.25 GiB。
