# 2026-10-29 规划建立记录

## 请求与范围

建立 RadishForge（萝卜锻坊）项目目录与规划文档；以 Gitea 为底座，Go + TypeScript + React，参考兄弟项目协作和部署方式，纳入 OIDC、Issue、GitHub 工作流 / Actions / API 兼容目标。仅文档，不写业务代码。

## 产物

根入口 README、AGENTS、CLAUDE、CONTRIBUTING；docs 下产品规划、架构、身份、Issue、GitHub 兼容、交付链路、部署、开发与验证、治理、阶段任务、验收、ADR、当前状态和来源记录。

来源核查见[参考资料](../references/source-review.md)。任务见[阶段清单](../planning/tasks.md)。

## 验证状态

- 指定目录：`/Users/luobo/Code/RadishForge`，共 27 份 Markdown，未附带业务工程或依赖缓存。
- 检查 105 个本地相对链接，目标均存在；代码围栏配对、UTF-8 无 BOM、LF、文件末尾换行通过。
- AGENTS.md 与 CLAUDE.md 除首行标题外逐字一致，根协作入口各 86 行。
- 26 项阶段任务引用的 24 项验收编号均有定义；P0 完成，M0—M6 功能任务全部待开始。
- 落盘前检查目标不存在，以不覆盖既有文件的方式创建；复制后逐文件 SHA-256 比对并在目标目录重新检查。
- 项目中无 `.git`，无 Go / TypeScript 源文件、依赖清单、Dockerfile、Compose 或活动 workflow。

本次使用一次性 Python 标准库检查文档，不将该检查脚本当作产品测试或生成空成功 CI。DOC-01 通过；其余功能验收未执行。

## 尚未执行

无业务实现、依赖安装、镜像下载、服务启动、功能测试或性能测量。未初始化 Git、创建远端、提交、推送、Tag、Release、DNS 或部署。未修改兄弟项目。本记录不证明 OIDC、GitHub 兼容或产品恢复能力已经完成。
