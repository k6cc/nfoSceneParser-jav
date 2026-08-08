# nfoSceneParser

> 当前版本 **v1.6.1**（fork 自社区原版，新增 Movie 正反封面搜索、`<series>`/`<set>`/`<rating>` 直文本识别等增强功能）

> ⚠️ **冲突警告**：本插件为社区原版 [nfoSceneParser](https://github.com/stashapp/CommunityScripts/tree/main/plugins/nfoSceneParser) 的 fork 版本，**不可与原版同时安装**。如已安装原版，请先卸载原版后再安装本版本，否则会造成插件冲突。

https://discourse.stashapp.cc/t/nfosceneparser/1385

在扫描时自动、透明地填充场景数据，数据来源支持：
- NFO 文件
- 通过正则表达式配置的文件名模式

非常适合大批量导入新文件（甚至整个库），让你在 Stash 中不必"从零开始"！*……前提是你有 NFO 文件和/或文件名中有一致的命名模式……*

# 安装

## 前置依赖

本插件为 Python 后端插件（非纯前端 JS 插件），运行需要：

| 组件 | 必需 | 说明 |
|------|------|------|
| **Python 3.x** | ✅ | 插件执行器（`exec: python`） |
| **requests 库** | ✅ | 调用 Stash GraphQL API |
| **Stash** | ✅ | 提供 GraphQL 端点 |

**Docker 部署**：Stash 官方镜像已预装 Python 和 requests，无需额外操作。

**Windows / macOS 裸机部署**：需手动安装。在 PowerShell（Windows）或终端（macOS）执行以下命令验证：

```powershell
python --version                  # 应输出 Python 3.x.x
python -c "import requests; print(requests.__version__)"   # 应输出 requests 版本号
```

若任一报错，按以下顺序安装：

```powershell
# Windows（winget）
winget install Python.Python.3.12
pip install requests

# macOS（homebrew）
brew install python@3.12
pip3 install requests
```

> **注意**：`pip` 或 `pip3` 取决于你的 Python 配置。安装后可能需要重新打开终端使 `python` 命令生效。

---

## 方式一：通过 Stash 插件源安装（推荐）

在 **Stash → 设置 → 插件 → 可用插件 → 添加源** 中添加以下 URL：

```
https://k6cc.github.io/stash-plugins/plugins/main/index.yml
```

> 此 URL 是统一插件源，包含 Binge、nfoSceneParser、sceneTranslate、sceneGallerySync、studioMerge、studioSearch 等多个插件，可一并安装。

然后从列表中安装 **nfoSceneParser**。

安装完成后：
- 重新加载插件（`设置 > 插件 > 重新加载`）
- `nfoSceneParser` 出现在插件列表
- 扫描一些新文件即可自动触发

## 方式二：下载 Release 手动安装

1. 前往 [Releases 页面](https://github.com/k6cc/nfoSceneParser-jav/releases)
2. 下载最新版本的 `nfoSceneParser-vX.Y.Z.zip`
3. 解压到 Stash 插件目录（zip 内文件直接放在 `nfoSceneParser` 目录下，不要嵌套子目录）：
   - **Windows**: `%USERPROFILE%\.stash\plugins\nfoSceneParser\`
   - **Linux/macOS**: `~/.stash/plugins/nfoSceneParser/`
4. Stash → 设置 → 插件 → 重新加载插件

## 方式三：从源码构建

```bash
git clone https://github.com/k6cc/nfoSceneParser-jav.git nfoSceneParser
# 将整个目录复制到 Stash 插件目录
# Windows: copy to %USERPROFILE%\.stash\plugins\
# Linux/macOS: cp -r nfoSceneParser ~/.stash/plugins/
# 然后：Stash → 设置 → 插件 → 重新加载插件
```

---

插件会在每次创建新场景时自动触发（通常在扫描期间）。

# 使用方法

从 NFO 文件或正则表达式模式导入场景详情。

每次创建新场景时，插件会：
- 查找匹配的 NFO 文件并解析为场景数据（工作室、演员、日期、名称...）
- 如果未找到 NFO，则使用正则表达式解析文件名中的模式。此回退方案仅在文件名中有一致且可识别的模式时有效。请仔细阅读下方关于如何配置正则表达式的说明。
- 如果以上均未找到：不做任何操作 ;-)

NFO 遵循 KODI 的"影片模板"规范（https://kodi.wiki/view/NFO_files/Movies）。注意：虽然 NFO 结构最初由 KODI 创建，但它已成为视频管理软件的事实标准，如今远超 KODI 本身的用途，被广泛用于存储视频文件的元数据。

正则表达式模式遵循 Python 正则表达式语法。编写/测试正则的好工具：https://regex101.com/

## config.py

nfoSceneParser 无需任何配置修改即可工作。如需更多控制，请查看 `config.py`，你可以在其中更改一些默认行为。

## 重新加载任务

nfoSceneParser 通常在扫描期间处理所有内容。如果你想稍后重新加载 NFO/正则数据，可以执行"重新加载"任务。

分三步操作：配置、选择、运行：
- **配置**：编辑插件 `config.py` 中的 `reload_tag`。设置为 Stash 中已存在的标签名称。该标签用作"标记"，插件通过它识别需要重新加载的场景。
- **选择**：将配置的标签添加到需要重新加载的场景上。
- **运行**：执行"重新加载"任务：Stash 设置 → "任务" → 滚动到"插件任务"/nfoSceneParser → 点击"重新加载已标记场景"按钮

重新加载本质上是将新文件数据与现有场景数据合并，优先使用 NFO/正则内容。具体规则：
- 单值字段：如果找到新内容则覆盖已有值
- 单值字段：如果未找到新内容则保留已有值
- 多值字段：追加到已有值

注意：标记标签会从重新加载的场景中移除（除非 NFO 或正则中包含该标签）=> 无需手动移除...

# NFO 文件组织

## 场景 NFO

插件自动在视频文件同目录下查找同名 .nfo 文件（以及可选的缩略图）。例如对于 `BestSceneEver.mp4`，会查找对应的 `BestSceneEver.nfo` 文件。可通过配置指定 NFO 文件的备用位置。

## 分集文件的 NFO 查找

对于分集文件（如 `IDBD-287-cd1.avi`、`ofje-341-a.mp4`），插件按以下顺序查找 NFO：

| 优先级 | 查找位置 | 示例 |
|--------|---------|------|
| 1 | 视频同名 NFO | `IDBD-287-cd1.nfo` |
| 2 | 去分集后缀的 NFO | `IDBD-287.nfo` |
| 3 | 同系列首集 NFO | `IDBD-287-cd1.nfo`（从 cd2 回退） |
| 4 | 同目录 `movie.nfo` | `movie.nfo` |

## 文件夹 NFO

如果存在 `folder.nfo` 文件，它将作为同文件夹下所有场景文件的默认值加载。场景专用 NFO 会覆盖 folder.nfo 中的默认值。

因此，如果你有一个 folder.nfo 包含工作室或演员信息，它们会自动应用到文件夹中的所有场景，即使没有为每个场景文件提供专用 NFO。

folder.nfo 也用于创建影片（Movie）。详见下方影片支持说明。

## 图片支持

缩略图支持两种来源：NFO 中的 `<thumb>` 标签（图片 URL 链接）或本地磁盘文件（遵循 KODI 的影片封面命名规范）。插件按优先级使用找到的第一张图片：

### 场景级别图片（与视频同名）

| 优先级 | 文件名模式 | 示例 |
|--------|-----------|------|
| 1 | `{文件名}-fanart.{ext}` | `ABP-998-fanart.jpg` |
| 2 | `{文件名}-landscape.{ext}` | `ABP-998-landscape.png` |
| 3 | `{文件名}-thumb.{ext}` | `ABP-998-thumb.jpg` |
| 4 | `{文件名}-poster.{ext}` | `ABP-998-poster.jpg` |
| 5 | `{文件名}-cover.{ext}` | `ABP-998-cover.jpg` |
| 6 | `{文件名}.{ext}` | `ABP-998.jpg` |

### 文件夹级别图片（仅当场景级别无图片时）

| 优先级 | 文件名模式 |
|--------|-----------|
| 1 | `landscape.{ext}` |
| 2 | `backdrop.{ext}` |
| 3 | `thumb.{ext}` |
| 4 | `poster.{ext}` |
| 5 | `cover.{ext}` |
| 6 | `folder.{ext}` |

### NFO `<thumb>` URL 下载

| 优先级 | XPath 查询 | 说明 |
|--------|-----------|------|
| 1 | `thumb[@aspect='landscape']` | 横向图片优先 |
| 2 | `thumb[@aspect='poster']` | 竖向海报 |
| 3 | `thumb` | 任意缩略图 |

**注意**：仅下载 `http://` 或 `https://` 开头的 URL，本地路径会被跳过。

支持的图片格式：`jpg`、`jpeg`、`png`、`webp`

## 影片（Movie）支持

影片会从 NFO 文件中自动查找并在 Stash 中创建。插件支持两种方式：
- **folder.nfo**：如果存在，其包含的数据适用于同目录下所有场景文件。`<title>` 标签指定影片名称，其他相关标签用于创建影片详情（`<date>`、`<studio>`、`<director>`、`<thumb>` 中的正/背面图片）
- **场景 NFO 中的 `<set>` 标签**：指定多个场景所属的组/系列

### 影片创建条件

影片**仅在有兄弟文件时**才会被创建/关联：

| 条件 | 影片名来源 | 示例 |
|------|-----------|------|
| NFO 有 `<set><name>` | 直接取 `<set/name>` 值 | `<set><name>ABP系列</name></set>` → `ABP系列` |
| NFO 有 `<series>` | 取 `<series>` 值（`<set/name>` 缺失时） | `<series>科幻</series>` → `科幻` |
| NFO 有 `<set>` 直文本 | 取 `<set>` 文本（前两者缺失时） | `<set>动作</set>` → `动作` |
| 有兄弟文件 | NFO `<title>` > 文件名前缀 | 先处理的文件决定 Movie 名 |
| 无兄弟文件且无 `<set/name>`/`<series>`/`<set>` | 不创建 Movie | `ABC-123-4k.mp4`（单独） → 无 Movie |

**先到先得**：第一个处理的文件确定 Movie 名，后续文件通过搜索（base_name）找到已有 Movie 并关联。

### 影片关联搜索（先到先得）

插件逐文件处理，采用"先到先得"策略确保同名 Movie 归入同一个影片：

| 步骤 | 搜索方式 | 说明 |
|------|---------|------|
| 1a | `findMovies(movie_name)` | 按影片名搜索已有影片（Stash INCLUDES） |
| 1b | `findMovies(base_name)` | 按文件名前缀搜索已有影片（更短更可靠，作为回退） |
| 2 | `findAllMovies()` 全量规范化匹配 | 兜底：Stash INCLUDES 可能因空格分词失败，全量获取后 Python 端规范化（去空格、小写）精确匹配 |
| 3 | `findScenesByTitle(base_name)` | 按场景标题搜索已关联影片的场景 |
| 4 | `findScenesByPath(base_name)` | 按文件路径搜索已关联影片的场景 |
| 5 | 创建新影片 | 以上均未找到时创建 |

**规范化匹配**：Step 1 和 Step 2 均使用 `__normalize_movie_name()` 进行匹配，依次执行：NFKC 规范化（全角→半角）→ 波浪号统一（U+301C `〜` → `~`）→ 小写 → 去除空格。支持 `"S1GIRLSCOLLECTION"` 匹配 `"S1 GIRLS COLLECTION"`，`"僕と○○の甘〜い性活"` 匹配 `"僕と○○の甘～い性活"`，`"ＩＤＢＤ－２８７"` 匹配 `"IDBD-287"`。

**缓存优化**：reload 模式下全量 Movie 列表缓存在 `self._all_movies_cache`，创建新 Movie 后同步更新缓存，避免同进程后续处理重复创建。

这样无论处理顺序如何，同一组文件始终归入同一个影片。第一个创建的影片名保留，后续文件只关联不新建。

### 分集后缀识别

支持任意后缀格式，只要文件名有统一的前缀，就识别为同一组合集影片：

**后缀识别正则**（支持字母、中文，可含数字）：`(?i)([-._ ])(\d*[a-z\u4e00-\u9fff]+\d*|[a-z\u4e00-\u9fff]+\d+)$`

**注意**：纯数字后缀（如 `SNIS-002` 的 `002`）不会被识别为分集后缀，以避免番号被误判为分集文件。

| 示例 | 前缀 | 后缀 |
|------|------|------|
| `ABC-123-4k` | `ABC-123` | `4k` |
| `ABC-123-uc` | `ABC-123` | `uc` |
| `ABC-123-cd1` | `ABC-123` | `cd1` |
| `ABC-123-破解` | `ABC-123` | `破解` |
| `ABC-123` | `ABC-123` | 无（标准版） |

**合集创建规则**：
- 有兄弟文件（同一前缀的不同后缀版本） → 归入同一合集
- 单独文件（无兄弟） → 不创建合集
- 无后缀文件（标准版）存在时 → 也是兄弟文件之一

**scene_index 编号**：
- 仅 CD 式后缀（`cd1`、`part2`、`disc-a` 等）有自动排序
- 其他后缀（`4k`、`uc`、`U`、`-破解` 等）无 scene_index

**场景标题追加**：
- 有兄弟文件时，标题追加后缀区分版本：`{NFO标题} {后缀}`
- 无兄弟文件时，标题保持不变

| 文件 | NFO标题 | 场景标题 |
|------|---------|---------|
| `ABC-123-4k.mp4` | 一日之计 | 一日之计 4k |
| `ABC-123-cd1.mp4` | 三省吾身 | 三省吾身 CD1 |
| `ABC-123.mp4` | 一日之计 | 一日之计 |

### 场景标题构建

标题构建规则：`{NFO标题} [{后缀}] [CD{序号}]`

| 条件 | 行为 | 示例 |
|------|------|------|
| 有兄弟文件，CD 式后缀（cd1/part2 等） | 仅追加 CD编号 | "三省吾身 CD1" |
| 有兄弟文件，非 CD 后缀（4k/uc/破解等） | 仅追加后缀 | "一日之计 4k" |
| 无兄弟文件 | 不追加 | "一日之计" |

**注意**：CD 式后缀（cd1、part2、disc-a 等）的 `title_suffix` 会被置为 None，仅通过 `scene_index` 追加 `CD{序号}`，避免出现 `cd1 CD1` 这样的冗余标题。

folder.nfo 示例：
```xml
<movie>
  <title>My Movie Title</title>
  <plot>You have to see it to believe it...</plot>
  <thumb aspect="poster">https://front_cover.jpg</thumb>
  <thumb aspect="poster">https://back_cover.jpg</thumb>
  <studio>Best studio ever</studio>
  <director>Georges Lucas</director>
</movie>
```

场景 NFO 示例：
```xml
<movie>
  <title>BestSceneEver</title>
  <plot>Scene of the century</plot>
  <thumb aspect="landscape">https://scene_cover.jpg</thumb>
  <studio>Best studio ever</studio>
  <set>
    <name>My Movie Title</name>
    <index>2</index>
  </set>
</movie>
```

### Movie 正反封面搜索（v1.6.0 新增）

创建 Movie 时，按以下优先级**独立搜索正反封面**（与场景封面 `cover_image`/`other_image` 逻辑完全独立，互不干扰）：

| | 优先级 | 文件名 |
|---|---|---|
| **正面图** | 1（场景级） | `{basename}-poster.{ext}` |
| | 2（文件夹级） | `folder.{ext}` |
| **背面图** | 1（场景级） | `{basename}-fanart.{ext}` |
| | 2（场景级） | `{basename}-landscape.{ext}` |
| | 3（场景级） | `{basename}-thumb.{ext}` |
| | 4（文件夹级） | `landscape.{ext}` |
| | 5（文件夹级） | `backdrop.{ext}` |

- `{basename}` = NFO 文件名去扩展名（与场景封面 `__read_cover_image_file()` 一致）
- 支持扩展名：`.jpg` / `.jpeg` / `.png` / `.webp`
- 受 `config.blacklist` 中的 `"cover_image"` 控制（与场景封面一致）
- 仅在 Movie 创建时设置；已存在的 Movie 不会被更新（需用 `reset-movie-covers` 工具重设）

**向后兼容**：若新字段未找到，回退到旧的 `cover_image`/`other_image` 字段，行为与 v1.5.0 一致。

## URL 支持

NFO 规范未正式支持 `<url>` 标签，但鉴于 URL 对 Stash 的重要性，nfoSceneParser 将其作为 NFO 扩展支持，会正确识别并更新到场景和影片中。同时支持 `<website>` 标签。

## Stash 数据与 NFO 字段对照表

| Stash 场景字段 | NFO 字段 | 说明 |
|---------------|---------|------|
| `title` | `title` 或 `originaltitle` 或 `sorttitle` | 按优先级顺序 |
| `details` | `plot` 或 `outline` 或 `tagline` | 按优先级顺序 |
| `studio` | `studio` | 单值 |
| `performers` | `actor.name` | 合并去重 |
| `movie` | `set.name` / `series` / `set` 直文本 / 文件名前缀 | 按优先级顺序；有兄弟文件时使用文件名前缀创建 Movie |
| `scene_index` | `set.index` | 仅 CD 式后缀有自动排序；其他后缀为 None |
| `rating` | `userrating` / `ratings.rating` / `rating` 直文本 | 按优先级顺序，换算到 0-100；`<rating>` 直文本默认 `max=5` |
| `tags` | `tag` 或 `genre` | 合并去重 |
| `date` | `premiered` 或 `year` | 按优先级顺序 |
| `urls` | `url` + `website` | 多个标签合并为数组 |
| `director`（影片） | `director` | 仅用于影片 |
| `cover_image` | `thumb` 或本地文件 | 本地文件优先于 URL |
| `code` | `uniqueid` 或 `num` 或 `sorttitle` | 按优先级顺序 |

注意：`uniqueid` 支持仅用于之前已导出的 Stash 场景（以便用现有 ID "原地"更新）

## XML 容错处理

插件在解析 NFO 前会自动处理以下常见问题：

| 问题 | 处理方式 |
|------|---------|
| 未转义的 `&` | 自动转义为 `&amp;` |
| `&nbsp;` HTML 实体 | 替换为空格 |
| 反引号包裹 URL | `` `https://...` `` → `https://...` |
| CDATA 嵌套错误 | 捕获异常，记录错误并跳过 |

# 正则表达式模式匹配

正则表达式通过识别文件名中的模式来工作。在未找到 NFO 时作为回退方案。

你需要配置自定义模式（如工作室、演员或影片），以匹配你的命名规则。因此需要一些配置来"告诉插件"如何识别正确的模式。

模式使用"正则表达式"标准来匹配。

## 正则配置 — 不同于常规插件

整个媒体库使用一致且统一的命名规则几乎是不可能的。因此，nfoSceneParser 支持多个 `nfoSceneParser.json` 正则配置文件。它们直接放在媒体库中，与媒体文件放在一起。

一个配置文件适用于其所在目录及所有子目录下的文件。

配置文件可以在库的目录树中嵌套。在这种情况下，始终使用最深、最具体的配置。

`nfoSceneParser.json` 配置在插件执行时搜索和加载。可以在 Stash 运行时添加、修改或删除，无需"重新加载"插件。

## 文件结构 `nfoSceneParser.json`

配置文件由一个正则表达式和一些属性组成。

| 名称 | 必填 | 说明 |
|------|------|------|
| regex | 是 | 正则表达式。可通过 https://regex101.com/ 学习、预览和测试 |
| splitter | 否 | 用于将匹配到的"performers"或"tags"文本进一步拆分为字符串数组（最常见的用例是演员或标签列表）。例如，如果 performers 匹配到 `"Megan Rain, London Keyes"`，使用 `", "` 作为 splitter 会将两个演员从匹配字符串中分离 |
| scope | 否 | 可选值："path" 或 "filename"。正则应用于场景的完整路径还是仅文件名。默认为 "path" |

## 示例 `nfoSceneParser.json`

假设以下目录和文件结构：

`/movies/movie series/Movie Name 17/Studio name - first1 last1, first2 last2 - Scene title - 2017-12-31.mp4`

"movie series" 目录下的所有文件使用相同的命名规则 => 将 `nfoSceneParser.json` 放在 `/movies/movie series` 中。

我们想识别以下模式：
- 最深层的文件夹是 `movie`
- 文件名有不同的部分，都用 `' - '` 分隔。因此可以用它来界定和匹配 `studio`、`performers` 和场景的 `title`
- `date` 会自动匹配，无需配置

`nfoSceneParser.json`（放在你的媒体库中）
```json
{
  "regex": "^.*[/\\\\](?P<movie>.*?)[/\\](?P<studio>.*?) - (?P<performers>.*?) - (?P<title>.*?)[-]+.*\\.mp4$",
  "splitter": ", ",
  "scope": "path"
}
```

正则说明：
- `[/\\]` 匹配斜杠和反斜杠，在 Windows 和 Unix 路径上都能工作
- 捕获组如 `(?P<movie>.*?)` 的名称必须匹配 nfoSceneParser 支持的属性（见下方）

注意：在 JSON 中，每个 `\` 都要转义为 `\\` => JSON 中的 `\\` 实际上是正则中的 `\`。如果不熟悉，可以在线搜索 JSON 正则格式化工具，粘贴你的正则获取正确转义后的字符串。

## 支持的正则捕获组名称

以下名称可用于正则捕获组：
- title
- date
- performers
- tags
- studio
- rating
- movie
- director
- index（映射到 Stash scene_index — 仅与影片相关）

注意：如果未指定 `date`，插件会尝试在文件名中自动检测日期。

# 配置参考

## 基础配置

| 配置项 | 默认值 | 说明 |
|-------|--------|------|
| `dry_mode` | `False` | 试运行模式，不实际修改数据库 |
| `nfo_location` | `"with files"` | NFO 文件位置（目前仅支持 `"with files"`） |
| `custom_nfo_name` | `""` | 自定义 NFO 文件名（如 `"movie.nfo"`） |
| `skip_organized` | `True` | 跳过已标记为 organized 的场景 |
| `set_organized_nfo` | `False` | 从 NFO 更新后标记为 organized |
| `set_organized_only_if` | `["title", "performers", ...]` | 标记 organized 的必要字段 |
| `blacklist` | `[]` | 不导入的字段列表 |
| `blacklisted_tags` | `["HD", "4K", ...]` | 不创建/设置的标签 |
| `reload_tag` | `"_NFO_RELOAD"` | 重新加载模式的标记标签 |

## 创建配置

| 配置项 | 默认值 | 说明 |
|-------|--------|------|
| `create_missing_performers` | `True` | 是否创建缺失的演员 |
| `create_missing_studios` | `True` | 是否创建缺失的工作室 |
| `create_missing_tags` | `True` | 是否创建缺失的标签 |
| `create_missing_movies` | `True` | 是否创建缺失的影片 |

## 别名搜索配置

| 配置项 | 默认值 | 说明 |
|-------|--------|------|
| `search_performer_aliases` | `True` | 搜索演员别名 |
| `search_studio_aliases` | `True` | 搜索工作室别名 |
| `search_tag_aliases` | `True` | 搜索标签别名 |
| `ignore_single_name_performer_aliases` | `True` | 忽略单词名演员的别名匹配 |
| `single_name_whitelist` | `["MJFresh", ...]` | 单词名白名单 |
| `levenshtein_distance_tolerance` | `2` | Levenshtein 距离容差（仅用于标签匹配） |

## Blacklist 可选值

`"performers"`、`"studio"`、`"tags"`、`"movie"`、`"title"`、`"details"`、`"date"`、`"rating"`、`"urls"`、`"cover_image"`、`"director"`

**特殊规则**：
- `"tags"` 黑名单：不创建新标签，但仍会匹配已有标签
- `"cover_image"` 黑名单：同时影响影片的 front_image 和 back_image
- `"urls"` 黑名单：同时影响 `<url>` 和 `<website>` 标签
