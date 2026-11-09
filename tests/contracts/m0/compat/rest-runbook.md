# M0-S04 仓库、Issue 与 Release 双端 REST 取证

本批执行顺序以 [首批 REST 样例](README.md#rest-与客户端样例)为原始请求基线。先对齐 Git 对象、仓库设置及角色，再做仓库读取、Issue 写入和 Release 写入。GitHub 参考端与 Gitea 原生端独立取证。Runner 和 Actions 在两端保持关闭，仓库内只放 REST 夹具。

## 目标与角色准入

- **GitHub。** 确认获授权的专用私有仓库 `owner/repo`、仓库 ID、普通测试用户和允许的资源写入范围。优先使用获授权的测试组织仓库，让普通成员通过 team 获得读写角色，并将 fine-grained PAT 限于测试仓库。GitHub 文档对外部和仓库协作者使用 fine-grained PAT 有限制，凭据或角色不可用的用例保留待验证。 [GitHub PAT 限制](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#fine-grained-personal-access-tokens-limitations)
- **Gitea。** 采用获授权的新隔离批次、固定镜像和 `https://localhost:18443`，只信任任务 CA。创建空私有测试仓库，回读 Actions 关闭及默认分支。沿用 `resource_read`、`issue_write` 与 `release_write` 三个既定用途。运行环境和停止条件见 [M0 契约入口](../README.md)。
- **两端共通。** 安装前确认仓库为空，绑定仓库 ID、用户 ID、批次与角色，验证 Issues 已启用。配置账户仅准备仓库和权限，实际正负例使用普通用户。保存精确环境、脱敏身份、Token 用途和实际权限回读。未取得目标或授权的端不发起请求。

GitHub 个人私有测试仓库已有所有者凭据和无凭据的参考结果。后续普通用户验收须独立验证表中角色，复用仓库前先核对既有夹具与批次归属。 [GitHub 参考记录](../../../../docs/records/2026-11-09-m0-github-rest-reference.md)

Gitea 侧可用既有探针的 `--mode rest` 复现本机对照。Issue 评论读回使用固定路由的有界 GET，该路由只声明 `since` / `before`，Issue 和 PR 集合仍独立逐页核对。 [执行入口](../README.md#m0-s04-同源-rest-对照) · [Gitea 对照记录](../../../../docs/records/2026-11-09-m0-gitea-rest-comparison.md)

| 角色或对照 | GitHub 最小权限 | Gitea 用途 / 角色 |
| --- | --- | --- |
| 仓库和提交读取 | 目标仓库的 Metadata、Contents 读 | 普通成员持 `resource_read` |
| Issue 正向写入 | 普通写者，目标仓库的 Issues 写 | 普通写者持 `issue_write` |
| Release 正向写入 | 普通写者，目标仓库的 Contents 写 | 普通写者持 `release_write` |
| 凭据范围对照 | 与写入相同的普通写者，分别使用 Issues 读和 Contents 读凭据 | 同一写者使用独立 `resource_read`，区分草稿详情和附件行为 |
| 对象权限对照 | 普通读者、专门用于撤权的普通写者、无目标权限的用户 | 普通读者、专门用于撤权的普通写者、无仓库权限的用户 |

用 `GET /user` 核对实际身份，以有权配置身份读回 `GET R/collaborators/{username}/permission`。保留 GitHub 的 `permission` 和 `role_name`，以及 Gitea 的 `permission`。目标访问负例前后，用独立有权身份确认目标确实存在。401 先确认凭据有效性，403 / 404 结合角色、同端读回及实际副作用解释。私有仓库的 404 单独保留原码。 [GitHub 协作者权限](https://docs.github.com/en/rest/collaborators/collaborators?apiVersion=2026-03-10#get-repository-permissions-for-a-user)

### GitHub 单账号凭据对照

`laugh0608/RadishForge-Test` 是个人私有仓库，协作者可获得写权限。普通写者的仓库授权及移除须使用独立身份，原生读者角色须使用组织仓库。GitHub 的 fine-grained PAT 目前也限制仓库协作者的使用。只读 PAT 体现所有者的凭据权限，角色和凭据结果分别归档。 [个人仓库权限](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository#collaborator-access-for-a-repository-owned-by-a-personal-account) · [Fine-grained PAT 限制](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#fine-grained-personal-access-tokens-limitations)

用当前所有者创建独立短期 fine-grained PAT。Resource owner 选择 `laugh0608`，仓库只选择 `RadishForge-Test`，Contents 和 Issues 为只读，保留默认 Metadata 只读。在 RadishForge 根目录的交互式终端运行：

```bash
python3 -B scripts/m0_github_scope.py
```

凭据只在终端的隐藏提示输入，结果写入忽略的 `.local/m0-scope-*.json`。脚本先以现有 gh 凭据确认仓库、固定提交、已发布 Release、Actions 与匿名对照，再用短期 PAT 读回目标并尝试写入两个带唯一标记的合成对象。权限拒绝需由所有者独立回读确认无副作用。脚本提示后在 GitHub 设置删除本次 PAT，确认列表中该条目已消失，再回终端输入 `REVOKED`。用同一凭据验证返回 401，并确认所有者仍可读取仓库。失败或中断先按结果中的标记对账，测试 PAT 仍由创建者删除。 `--preflight` 只执行现有凭据和匿名读回。 [创建和管理 PAT](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) · [GitHub REST 鉴权](https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api#failed-login-limit)

若只读权限已取证且测试 PAT 仍未删除，使用 `python3 -B scripts/m0_github_scope.py --revocation-only`，按同样的隐藏输入和删除步骤复测。该模式只发 GET，在删除前先验证 PAT 仍可访问，再以进程中的同一凭据验证失效。若列表和安全日志已确认删除，且操作者仍能输入同一 PAT 值，改用 `--check-revoked` 补做一次 GET。该模式记录提交值是否返回 401，操作者需核对输入与之前使用的是同一值。 [实测记录](../../../../docs/records/2026-11-09-m0-github-owner-pat.md)

## 确定性源码夹具

[rest-source.fi](rest-source.fi) 只包含合成文本、两个 SHA-1 提交和一个轻量 Tag。文件 SHA-256 为 `223a5feddbd5791ad883a2a4b30aabdd209aa15193508e929334650b55cb7cef`。

| 引用 | 预期 SHA / 关系 |
| --- | --- |
| `refs/heads/main` | `37aa3d3ca05aa645e8d970a233b95fcebf35452c`，单文件 `fixture.txt` |
| `refs/heads/m0-fixture-pr` | `3527c7d63bebdc0eb5df3405dc23020950df2816`，唯一父提交为 `main` |
| `refs/tags/m0-release-01` | `37aa3d3ca05aa645e8d970a233b95fcebf35452c`，为 Release 正向样例预置 Tag |

从 RadishForge 根目录运行以下本地命令。令 `M0_FIXTURE_PARENT` 指向本批专用临时目录，并记录后续清理归属。

```bash
set -eu
test -d "${M0_FIXTURE_PARENT:?}"
M0_FIXTURE_GIT="$M0_FIXTURE_PARENT/m0-rest-fixture.git"
test ! -e "$M0_FIXTURE_GIT"
test ! -e "$M0_FIXTURE_PARENT/m0-fixture.bin"
git -c init.defaultBranch=main init --bare --object-format=sha1 "$M0_FIXTURE_GIT"
git --git-dir="$M0_FIXTURE_GIT" fast-import --quiet < tests/contracts/m0/compat/rest-source.fi
git --git-dir="$M0_FIXTURE_GIT" fsck --strict --no-reflogs
git --git-dir="$M0_FIXTURE_GIT" show-ref
printf 'M0 fixture\n' > "$M0_FIXTURE_PARENT/m0-fixture.bin"
shasum -a 256 "$M0_FIXTURE_PARENT/m0-fixture.bin"
```

只有安装目标和推送已获授权时，才向各自空仓推送表内的三个 refs。读回默认分支为 `main`。GitHub 使用 `GET R/git/ref/heads/main` 与 `GET R/git/ref/tags/m0-release-01` 的 `object.sha`，Gitea 使用 `GET R/branches/main` 的 `commit.id` 与 `GET R/tags/m0-release-01` 的 `commit.sha`。任一 ref 不符则停止本端测试。 [GitHub Git 引用接口](https://docs.github.com/en/rest/git/refs?apiVersion=2026-03-10#get-a-reference)

## 首个只读请求

以下示例在目标已确认后执行。`M0_GH_REPO` 和 `M0_GITEA_REPO` 是各自记录过的隔离 `owner/repo`。GitHub 通过 `GH_TOKEN` 提供本批普通读者凭据。Gitea 的 `M0_GITEA_READ_TOKEN` 取自本批独立读用途，`M0_TASK_CA` 指向本批 CA。凭据值由当前测试进程的私密输入提供，运行时关闭命令跟踪。

```bash
gh api --hostname github.com --include \
  -H 'Accept: application/vnd.github+json' -H 'X-GitHub-Api-Version: 2026-03-10' \
  "repos/${M0_GH_REPO:?}"

printf 'Authorization: Bearer %s\n' "${M0_GITEA_READ_TOKEN:?}" |
  curl -q --proto '=https' --silent --show-error --include --max-time 15 \
    --cacert "${M0_TASK_CA:?}" --header @- \
    "https://localhost:18443/api/v1/repos/${M0_GITEA_REPO:?}"
```

先核对 200、仓库 ID、可见性和默认分支，再读回固定提交。外部用户对照单独发起并保存拒绝回执。任何目标偏差停止本端。

## 执行顺序与读回

每端以 `R=/repos/{owner}/{repo}` 表示目标。GitHub 使用固定版本头和相应媒体类型。Gitea 从 `/api/v1` 发出请求，使用任务 CA 及本批 Token。每个写入用例在确认有权正向对照后发送一次，按返回 ID 或精确夹具标记读回。使用原始方法、路径和字段名，平台差异逐项记录。

| 顺序 | 操作及停止条件 | 最少证据 |
| --- | --- | --- |
| 1. 仓库读取 | 用普通读身份分别查询 `GET R` 和固定主分支提交，GitHub 为 `GET R/commits/{sha}`，Gitea 为 `GET R/git/commits/{sha}`。用无目标权限的身份重复读取。 | 目标仓库 ID、`private`、默认分支、提交 SHA、正向和拒绝的原码。 |
| 2. Issue 列表夹具 | 两端以 `POST R/issues` 创建标题分别为 `m0-list-open` 和 `m0-list-closed` 的条目。按后者回执的仓库内编号 PATCH `{"state":"closed"}`，回读关闭。使用 `POST R/pulls` 和 `{"title":"m0-list-pr","head":"m0-fixture-pr","base":"main"}` 创建开放 PR，回读其 head 与 base SHA。夹具失败先对账。 | 两个 Issue、一个 PR 的实际编号、状态、分支和提交。 |
| 3. Issue 分页与写入 | GitHub 使用 `state=all&sort=created&direction=asc&per_page=1&page=1` 跟随受信 `Link`。Gitea 使用 `state=all&type=issues&limit=1&page=1` 逐页至空页，再单独取 `type=pulls` 作为对照。验证精确集合和无重复。按基线完成新建、评论、关闭和读回。以同写者的只读凭据尝试创建 `m0-denied-readonly`。另用专门写者验证撤权前可访问、撤权后不能向已知 Issue 写入 `m0-denied-revoked`，保留 Release 正向写者的权限。 | 分页方式、集合、PR 标志、仓库内编号、评论回读和状态。拒绝后按唯一标题或评论标记查询，确认目标没有对应新对象或变化。 |
| 4. Release 草稿与附件 | 以预置 Tag 和固定主分支 SHA 创建草稿。上传合成二进制附件。GitHub 使用回执中的 `upload_url` 及固定上传 origin，Gitea 使用 `POST R/releases/{id}/assets?name=m0-fixture.bin`。先以写者回读元数据并核对真实附件，再用只读凭据、普通读者、无目标权限的身份读取同一对象。Gitea 的草稿详情按 ID 和 Tag 分别读，附件元数据与 UUID / Tag 文件名下载分别记录。 | Release ID、draft、Tag、附件 ID、11 字节实收内容和 SHA-256。记录实际鉴权、重定向与是否返回字节。拒绝后由写者回读对象仍存在。 |
| 5. 字段更新与发布 | 对同一草稿 PATCH `{"body":""}` 后按 ID 读回。记录原样返回和实际字段。发布前分别复核草稿的 Tag 关联和实际 Git Tag SHA，再 PATCH `{"draft":false}`，读回同一 ID、draft、附件、Tag 和 SHA。草稿关联或 Git 引用漂移或无法核实则暂停发布并对账。 | HTTP 回执、字段实际值、发布前后的 Tag 关联与 SHA、附件身份与内容。G20 的空值结果单列。 |

分页最多 20 页，循环、重复编号、丢失应有对象、跨 origin 的 `Link` 或未验证的下载重定向均停在当前用例。GitHub 返回的 `rel="next"` 可以使用同一仓库 ID 的 `/repositories/{id}/issues`，并携带 `after` 游标。确认 origin、仓库 ID 和筛选条件后沿用原链接及游标。附件请求不向跨 origin 重定向转送原 Authorization，确认允许的 HTTPS 下载 origin 后再读取并核对摘要。Release 的 G22 / G23 异常及 G26 / G27 的 OCI 验收留在各自夹具。

## 证据与清理

逐端保留批次、仓库与角色、源 SHA、实际状态码、媒体类型、分页与重定向摘要，以及操作前后的字段或字节读回。脱敏时保留方法、路径模板、语义参数和结果，剔除 Token、Cookie、签名 URL 查询和私有响应原文。对照结果采用已有兼容状态，单端结果和本地夹具验证分别归档。 [项目证据要求](../../../../docs/development/validation.md#证据模板)

写入超时使用本批的标题、评论标记、固定 Tag、Release ID 或附件名及摘要只读对账。零匹配、多匹配或无法确认时保留未知并停止后续写入。结束时按已授权清理范围仅处理本批对象，独立回读确认；超出清理范围的对象登记归属与交接。凭据和原始响应仅在本批私密目录保存。
