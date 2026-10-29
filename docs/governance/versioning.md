# 产品版本与发行标识

本页约束 RadishForge 自身发行，不约束平台上托管项目的版本习惯。托管项目可以使用 SemVer、日历版本或其他合法 Git Tag。

## 自身发行规则

参考 Radish 与 RadishInk：

- 产品版本：YY.M.RELEASE，月份不补零，RELEASE 为当月发行序号。
- Git Tag：vYY.M.RELEASE-(dev|test|release)，需要细分时可用 vYY.M.RELEASE.DDXX-(dev|test|release)。
- 同一产品发行的自有镜像使用相同完整 Tag，OCI 元数据记录源码提交与版本。
- 固定 Tag 发布后不得换内容；重试先比对产物，内容不同必须新版本。
- dev / test / release 为发行轨道，不能替代 API 或数据库兼容性说明。
- test 创建预发布；正式版使用新的 release Tag，不移动测试 Tag。
- 浮动别名仅用于发现版本，生产使用确定的 Digest，或经验证不可变的完整 Tag。
- Gitea、Runner、数据库和反代镜像保留各自上游版本与 Digest，不能伪装成自有版本。

未来通过一个正式版本源和机器可读发行清单统一展示、镜像和 Release 信息。当前不创建 version.json、不分配首个发行版本，也不预设镜像已经存在。

## 发行流程

候选代码与说明 → 检查及验收 → 主线晋级与回流 → 获授权创建 Tag → 构建并扫描自有镜像 → 保存镜像 Digest 和随包声明 → Release → 部署预检与维护窗口 → 实际部署记录。

镜像构建成功、镜像推送、Release 发布、服务部署分别记录。RadishForge 自身不能依赖“已经运行的自身实例”才能第一次部署或恢复；首次发行可用 GitHub/GHCR 或其他获授权渠道。
