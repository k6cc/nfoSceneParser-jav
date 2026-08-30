# AGENTS.md

本项目是 Stash 插件 **nfoSceneParser-jav**（Python 后端插件），GitHub 仓库：https://github.com/k6cc/nfoSceneParser-jav

## 发布机制（无需手动操作）

推送 `vX.Y.Z` 格式的 git tag 即触发 `.github/workflows/release.yml` 自动发布：
打包 zip → 计算 sha256/时间戳 → 更新 `k6cc/stash-plugins` 仓库的 `plugins/main/index.yml` → 创建 GitHub Release。
**tag 名是发布版本号的唯一来源**（zip 文件名、插件源 index.yml、Release 名均取自 tag），因此修改插件后发布时，必须先在仓库内把版本号改好，再以同名 tag 发布。

## 每次发布必须同步更新的版本号位置

| 位置 | 内容 | 说明 |
|------|------|------|
| `nfoSceneParser.yml` 第 3 行 | `version: 1.6.2` | 主插件元数据版本号（不含 `v`），Stash 插件源据此识别更新，必须与 tag 一致 |
| `README.md` 第 3 行 | `> 当前版本 **v1.6.2**（...）` | 文档顶部版本号（带 `v`）+ 本次版本说明，必须与 tag 一致 |
| git tag | `v1.6.2` | 发布触发点，格式 `vX.Y.Z`，是自动化流程实际读取的版本号 |

三处版本号必须保持完全一致（差一个字符都会导致插件源显示的版本与代码/文档不符）。

## 版本说明位置

- `README.md` 第 3 行：当前版本说明，用括号写明本次新增/增强的功能（如“新增 Movie 正反封面搜索、`<series>`/`<set>`/`<rating>` 直文本识别等增强功能”）。
- `README.md` 对应功能章节：新功能按需加“（vX.Y.Z 新增）”标注（如“Movie 正反封面搜索（v1.6.0 新增）”），仅记录该功能的引入版本，非每次必改。
- GitHub Release Notes：由 workflow 的 `generate_release_notes: true` 自动生成，无需手工维护。

## 子工具（独立维护，不打包进主插件 release）

`reset-movie-covers/reset-movie-covers.yml` 第 3 行 `version: 1.0.0`：临时维护工具，其 README 明确“不包含在 nfoSceneParser-jav 的 release zip 中”，仅随源码提供。主插件发布 zip 只打包 8 个文件（nfoSceneParser.yml + 7 个 .py），不含该子目录；若单独改动并发布该工具，需同步更新它自己的 yml 版本号。

## 发布前 Checklist

- [ ] 修改插件代码，确认功能完成
- [ ] `nfoSceneParser.yml` 的 `version` 改为新版本号（不含 `v`）
- [ ] `README.md` 第 3 行更新版本号（带 `v`）+ 版本说明（写明本次新增/修复内容）
- [ ] （可选）README 中新功能章节补充“（vX.Y.Z 新增）”标注
- [ ] 提交改动并推送
- [ ] 打 tag `vX.Y.Z` 并推送（tag 名即版本号，触发 release.yml）
- [ ] 在 GitHub Actions 确认发布成功：zip 已上传、`stash-plugins` 仓库 index.yml 已更新（若未设 `STASH_PLUGINS_TOKEN` 需手动更新 index.yml）、Release 已创建
