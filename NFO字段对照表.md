# nfoSceneParser 项目文档

## 一、架构概览

```
nfoSceneParser.py (主控制器)
    ├── nfoParser.py       (NFO XML 解析器)
    ├── reParser.py        (正则表达式解析器)
    ├── stashInterface.py  (GraphQL API 接口层)
    ├── abstractParser.py  (解析器基类)
    ├── config.py          (配置文件)
    └── log.py             (Stash 插件日志工具)
```

### 数据流

```
Stash Hook 触发
    → NfoSceneParser.process()
        → __process_scene() / __process_reload()
            → __prepare()          # 获取场景数据
            → __parse()            # 解析 NFO/正则
                → NfoParser (folder) → folder_data
                → RegExParser       → re_file_data
                → NfoParser (scene) → nfo_file_data
            → __update()           # 更新 Stash 数据库
                → __find_create_scene_data()
                    → __find_create_performers()
                    → __find_create_studio()
                    → __find_create_movie()
                    → __find_create_tags()
                → gql_updateScene()
```

### 解析优先级

1. **NFO 文件解析** (nfoParser) — 最高优先级
2. **正则表达式解析** (reParser) — 回退方案
3. **文件夹 NFO** (folder.nfo) — 作为默认值传入
4. **现有场景数据** — 最后回退

---

## 二、Stash 数据与 NFO 字段对照表

### 场景字段映射

| Stash 字段 | NFO 字段 | 优先级顺序 | 代码位置 |
|-----------|---------|-----------|---------|
| `title` | `<title>` | `<title>` → `<originaltitle>` → `<sorttitle>` | nfoParser.py |
| `details` | `<plot>` | `<plot>` → `<outline>` → `<tagline>` | nfoParser.py |
| `studio` | `<studio>` | 直接对应（单值） | nfoParser.py |
| `performers` | `<actor><name>` | 所有 `<actor><name>` 子元素（合并去重） | nfoParser.py |
| `movie` | `<set><name>` | `<set/name>` → 有兄弟文件时用文件名前缀 | nfoParser.py |
| `scene_index` | `<set><index>` | `<set/index>` → 仅 CD 式后缀有自动排序（int 类型） | nfoParser.py |
| `rating` (0-100) | `<userrating>` 或 `<ratings>` | `<userrating>` → `<ratings/rating>` | nfoParser.py |
| `tags` | `<tag>` + `<genre>` | 同时读取，去重合并 | nfoParser.py |
| `date` | `<premiered>` | `<premiered>` → `<year>` | nfoParser.py |
| `urls` | `<url>` + `<website>` | 多个标签合并为数组 | nfoParser.py |
| `director` | `<director>` | 用于影片（Movie），非场景字段 | nfoParser.py |
| `cover_image` | `<thumb>` 或本地文件 | 本地文件 → `<thumb>` URL | nfoParser.py |
| `other_image` | 第二个 `<thumb>` 或本地第二张 | 用于影片背面 | nfoParser.py |
| `code` | `<uniqueid>` | `<uniqueid>` → `<num>` → `<sorttitle>` | nfoParser.py |

### 数据合并逻辑

| Stash 字段 | 合并规则 | 说明 |
|-----------|---------|------|
| `title` | NFO 优先，否则保留现有 | 单值覆盖 |
| `details` | NFO 优先，否则保留现有 | 单值覆盖 |
| `date` | NFO 优先，否则保留现有 | 单值覆盖 |
| `rating` | NFO 优先，否则保留现有 | 单值覆盖 |
| `urls` | NFO 优先，否则保留现有 | 数组替换 |
| `studio` | NFO 优先，否则保留现有 | 单值覆盖（不支持合并） |
| `performers` | **合并去重** | 新旧演员合并 |
| `tags` | **合并去重** | 新旧标签合并，reload 时移除标记标签 |
| `movie` | NFO 优先，否则保留现有 | 仅当 NFO 有 `<set/name>` 或有兄弟文件时才创建 Movie |
| `scene_index` | NFO movie 存在时取 NFO 值，否则保留现有 | 仅当 NFO 指定了 movie 时才覆盖；仅 CD 式后缀有自动排序 |
| `cover_image` | NFO 优先 | 单值覆盖 |
| `code` | 直接取 `uniqueid` | 单值覆盖 |

### Rating 计算规则

| NFO 字段 | 计算方式 | 配置项 |
|---------|---------|-------|
| `<userrating>` | 直接取值 × `user_rating_multiplier`，换算到 0-100 | `user_rating_field`、`user_rating_multiplier` |
| `<ratings/rating>` | `value / max × 100`（换算到 0-100） | 无 |

---

## 三、图片文件优先级

### 场景级别（与 NFO 同名）

| 优先级 | 文件名模式 | 示例 |
|--------|-----------|------|
| 1 | `{basename}-fanart.{ext}` | `ABP-998-fanart.jpg` |
| 2 | `{basename}-landscape.{ext}` | `ABP-998-landscape.png` |
| 3 | `{basename}-thumb.{ext}` | `ABP-998-thumb.jpg` |
| 4 | `{basename}-poster.{ext}` | `ABP-998-poster.jpg` |
| 5 | `{basename}-cover.{ext}` | `ABP-998-cover.jpg` |
| 6 | `{basename}{n}.{ext}` | `ABP-998.jpg`、`ABP-9981.jpg` |

支持的图片格式：`jpg`、`jpeg`、`png`、`webp`

### 文件夹级别（通用，仅当场景级别无图片时）

| 优先级 | 文件名模式 |
|--------|-----------|
| 1 | `landscape.{ext}` |
| 2 | `backdrop.{ext}` |
| 3 | `thumb.{ext}` |
| 4 | `poster.{ext}` |
| 5 | `cover.{ext}` |
| 6 | `folder.{ext}` |

### `<thumb>` URL 下载优先级

| 优先级 | XPath 查询 | 说明 |
|--------|-----------|------|
| 1 | `thumb[@aspect='landscape']` | 横向图片优先 |
| 2 | `thumb[@aspect='poster']` | 竖向海报 |
| 3 | `thumb` | 任意缩略图 |

**注意**：仅下载 `http://` 或 `https://` 开头的 URL，本地路径（如 `/config/data/...`）会被跳过。

---

## 四、NFO 文件查找顺序

### 普通模式（非 folder_mode）

| 优先级 | 文件位置 | 说明 |
|--------|---------|------|
| 1 | `{视频同名}.nfo` | 如 `ABP-998-cd2.mp4` → `ABP-998-cd2.nfo` |
| 2 | `{去分集后缀名}.nfo` | 如 `ABP-998-cd2.mp4` → `ABP-998.nfo` |
| 3 | `{分集系列首集}.nfo` | 如 `ABP-998-cd2.mp4` → `ABP-998-cd1.nfo` |
| 4 | `movie.nfo` | 同目录下的通用 NFO |

### 分集模式（folder_mode）

| 优先级 | 文件位置 | 说明 |
|--------|---------|------|
| 1 | 当前目录的 `folder.nfo` | 向上递归查找父目录 |

### 分集后缀识别模式

后缀识别正则（支持字母、中文，可含数字）：`(?i)([-._ ])(\d*[a-z\u4e00-\u9fff]+\d*|[a-z\u4e00-\u9fff]+\d+)$`

**注意**：纯数字后缀（如 `SNIS-002` 的 `002`）不会被识别为分集后缀，以避免番号被误判为分集文件。

支持任意后缀格式，兄弟文件检测为核心逻辑：

| 示例 | 前缀 | 后缀 |
|------|------|------|
| `ABC-123-4k` | `ABC-123` | `4k` |
| `ABC-123-uc` | `ABC-123` | `uc` |
| `ABC-123-cd1` | `ABC-123` | `cd1` |
| `ABC-123-破解` | `ABC-123` | `破解` |
| `ABC-123` | `ABC-123` | 无（标准版） |

**合集创建规则**：
- 有兄弟文件 → 归入同一合集，用文件名前缀作为 Movie 名
- 无兄弟文件 → 不创建合集
- bare 文件（无后缀）也是兄弟文件之一

**scene_index 编号**：
- 仅 CD 式后缀（`cd1`、`part2`、`disc-a` 等）有自动排序
- 其他后缀（`4k`、`uc`、`U`、`-破解` 等）无 scene_index

**场景标题追加**：有兄弟文件时追加后缀到标题
- `{NFO标题} {后缀}` 或 `{NFO标题} {后缀} CD{序号}`

---

## 五、XML 容错处理

`__clean_nfo_content` 方法在解析前对 NFO 内容进行预处理：

| 问题 | 处理方式 |
|------|---------|
| 未转义的 `&` | 正则 `&(?!(?:[a-zA-Z]+\|#\d+\|#x[0-9a-fA-F]+);)` → `&amp;` |
| `&nbsp;` HTML 实体 | 替换为空格 |
| 反引号包裹 URL | `` `https://...` `` → `https://...` |
| CDATA 嵌套错误 | 由 try/except 捕获，记录错误并跳过 |

---

## 六、配置项完整参考

### 基础配置

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
| `reload_tag` | `"_NFO_RELOAD"` | Reload 模式的标记标签 |

### 创建配置

| 配置项 | 默认值 | 说明 |
|-------|--------|------|
| `create_missing_performers` | `True` | 是否创建缺失的演员 |
| `create_missing_studios` | `True` | 是否创建缺失的工作室 |
| `create_missing_tags` | `True` | 是否创建缺失的标签 |
| `create_missing_movies` | `True` | 是否创建缺失的影片 |

### 评分配置

| 配置项 | 默认值 | 说明 |
|-------|--------|------|
| `user_rating_field` | `"userrating"` | 评分来源字段 |
| `user_rating_multiplier` | `1` | 评分倍率 |

### 标签配置

| 配置项 | 默认值 | 说明 |
|-------|--------|------|
| `load_tags_from` | `"both"` | Tag 来源：`"tags"` / `"genres"` / `"both"` |

### 别名搜索配置

| 配置项 | 默认值 | 说明 |
|-------|--------|------|
| `search_performer_aliases` | `True` | 搜索演员别名 |
| `search_studio_aliases` | `True` | 搜索工作室别名 |
| `search_tag_aliases` | `True` | 搜索标签别名 |
| `ignore_single_name_performer_aliases` | `True` | 忽略单词名演员的别名匹配 |
| `single_name_whitelist` | `["MJFresh", ...]` | 单词名白名单 |
| `levenshtein_distance_tolerance` | `2` | Levenshtein 距离容差（仅用于标签匹配） |

### Blacklist 可选值

`"performers"`, `"studio"`, `"tags"`, `"movie"`, `"title"`, `"details"`, `"date"`, `"rating"`, `"urls"`, `"cover_image"`, `"director"`

**特殊规则**：
- `"tags"` 黑名单：不创建新标签，但仍会匹配已有标签
- `"cover_image"` 黑名单：同时影响 Movie 的 front_image 和 back_image
- `"urls"` 黑名单：同时影响 `<url>` 和 `<website>` 标签

---

## 七、实体匹配逻辑

### 匹配流程（以 Performer 为例）

```
1. GraphQL INCLUDES 搜索名称
2. 第一轮：精确名称匹配（大小写不敏感，Unicode NFC 标准化）
3. 第二轮：别名匹配（受配置控制）
4. 无匹配：创建新实体（受配置控制）
5. 多匹配：使用第一个匹配，输出警告
```

### 标签匹配的特殊性

标签匹配使用 **Levenshtein 距离** 容差，允许模糊匹配：
- 容差阈值 = `max(levenshtein_distance_tolerance × log10(max(len(text), 2)), 1)`
- 短字符串（2字符）最小容差为 1
- 其他实体（演员、工作室、影片）使用精确匹配

---

## 八、Movie 创建逻辑

### Movie 创建条件

| 条件 | movie 名来源 | 示例 |
|------|------------|------|
| NFO 有 `<set><name>` | 直接取 `<set/name>` 值 | `<set><name>S1 GIRLS COLLECTION</name></set>` → `S1 GIRLS COLLECTION` |
| 有兄弟文件 | NFO `<title>` > 文件名前缀 | 先处理的文件决定 Movie 名 |
| 无兄弟文件且无 `<set/name>` | 不创建 Movie | `ABC-123-4k.mp4`（单独） → 无 Movie |

### Movie 关联搜索（先到先得）

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

### Movie 字段来源

| Movie 字段 | 优先级 | 说明 |
|-----------|--------|------|
| `name` | file_data | 必须来自场景 NFO |
| `studio_id` | file_data → blacklist | |
| `date` | folder_data → file_data | 文件夹 NFO 优先 |
| `director` | file_data | |
| `synopsis` | folder_data → file_data | 文件夹 NFO 优先 |
| `rating100` | folder_data → file_data | 文件夹 NFO 优先 |
| `url` | folder_data → file_data | 取 urls 数组第一个 |
| `front_image` | folder_data → file_data | |
| `back_image` | folder_data → file_data | |

### Stash Movie 模型限制

以下字段 Stash Movie 不支持：`tags`、`performers`、`aliases`、`duration`

---

## 九、场景标题构建

标题构建规则：`{NFO标题} [{后缀}] [CD{序号}]`

| 条件 | 行为 | 示例 |
|------|------|------|
| 有兄弟文件，CD 式后缀（cd1/part2 等） | 仅追加 CD编号 | "三省吾身 CD1" |
| 有兄弟文件，非 CD 后缀（4k/uc/破解等） | 仅追加后缀 | "一日之计 4k" |
| 无兄弟文件 | 不追加 | "一日之计" |

**注意**：CD 式后缀的 `title_suffix` 会被置为 None，仅通过 `scene_index` 追加 `CD{序号}`，避免 `cd1 CD1` 冗余。

---

## 十、Bug 修复记录

### 历史修复

| 问题 | 修复 | 文件 |
|------|------|------|
| `gql_findMovies` 变量名错误 | `studio_filter` → `movie_filter` | stashInterface.py |
| `NoneType` subscriptable 错误 | 所有 GraphQL 返回添加空值保护 | nfoSceneParser.py |
| `folder_data.get("urls")` 空值 | 添加默认值 `[None]` | stashInterface.py |
| 图片优先级按字母排序 | 改为按优先级列表顺序查找 | nfoParser.py |
| `<thumb>` 本地路径超时 | 仅下载 http/https URL | nfoParser.py |
| 分集文件找不到 NFO | 增加回退查找逻辑 | nfoParser.py |
| NFO 未转义 `&` 导致解析失败 | 新增 `__clean_nfo_content` | nfoParser.py |
| 反引号包裹 URL | 正则去除反引号 | nfoParser.py |

### 本次修复

| 问题 | 严重性 | 修复 | 文件 |
|------|--------|------|------|
| `cover_image` 黑名单键名错误：代码检查 `"image"` 而非 `"cover_image"` | 🔴 致命 | `"image" not in bl` → `"cover_image" not in bl` | nfoSceneParser.py |
| `movies` 字段类型错误：传 dict 而非 list，GraphQL 期望 `[SceneMovieInput!]` | 🔴 致命 | `{...}` → `[{...}]` | stashInterface.py |
| `scene_index` 类型错误：返回 str 但 GraphQL 期望 Int | 🔴 致命 | 统一返回 int，新增 `__parse_scene_index` 方法 | nfoParser.py, reParser.py |
| `gql_findScenes` 返回 None 时崩溃 | 🔴 致命 | 添加 None 检查前置返回 | nfoSceneParser.py |
| NFO 无 movie 时 scene_index 覆盖现有值 | 🟡 逻辑冲突 | 仅当 file_movie_id 存在时使用 NFO 的 scene_index | nfoSceneParser.py |
| Tag 别名搜索错误使用 `search_studio_aliases` | 🟡 逻辑冲突 | 新增 `search_tag_aliases` 配置项 | nfoSceneParser.py, config.py |
| `self._scene["performers"]`/`["tags"]` 无 None 保护 | 🟠 健壮性 | 改为 `.get("performers") or []` | nfoSceneParser.py |
| `self._scene["title"]` 等字段无 None 保护 | 🟠 健壮性 | 改为 `.get("title")` 等 | nfoSceneParser.py |
| `gql_findScene` 路径重写未检查 None | 🟠 健壮性 | 添加 None 检查前置返回 | stashInterface.py |
| GraphQL 错误时 `raise Exception` 后有死代码 | 🟠 健壮性 | 改为 `log.LogError` + `return None` | stashInterface.py |
| 所有 `gql_*` 方法未处理 `__gql_call` 返回 None | 🟠 健壮性 | 统一使用 `(result or {}).get(...)` | stashInterface.py |
| `__gql_call` 无 data 无 errors 时隐式返回 None | 🟠 健壮性 | 显式 `return None` | stashInterface.py |
| `scene.get("tags")` 在 reload 模式无 None 保护 | 🟠 健壮性 | 改为 `.get("tags") or []` | nfoSceneParser.py |
| Windows 中文系统 UTF-8 编码乱码 | 🔴 致命 | `sys.stderr/stdin/stdout.reconfigure(encoding='utf-8')` + `response.encoding='utf-8'` | log.py, nfoSceneParser.py, stashInterface.py |
| 非分集文件也创建 Movie（`__strip_multipart_suffix` 无后缀时返回原标题） | 🔴 致命 | 改为 `re.search` 先检查后缀是否存在，不存在返回 None；新增 `__get_multipart_movie_name` 仅分集文件才派生 movie | nfoParser.py |
| **`__find_create_movie` 使用 `self._file_data["movie"]` 导致 KeyError** | 🔴 致命 | 改为 `self._file_data.get("movie")` 并检查 None | nfoSceneParser.py |
| **`gql_movieCreate` 使用 `file_data["movie"]` 导致 KeyError** | 🔴 致命 | 改为 `file_data.get("movie")` 并检查 None | stashInterface.py |
| **`gql_updateScene` 多处使用 `scene_data["key"]` 导致 KeyError** | 🔴 致命 | 全部改为 `.get()` 方法 | stashInterface.py |
| **`__find_create_scene_data` 多处使用 `self._file_data["key"]` 导致 KeyError** | 🔴 致命 | 全部改为 `.get()` 方法 | nfoSceneParser.py |
| **`__update` 方法使用 `self._file_data["file"]` 和 `updated_scene["id"]` 导致 KeyError** | 🔴 致命 | 全部改为 `.get()` 方法 | nfoSceneParser.py |
| 新增中文字符后缀支持（`-无码`、`-破解`等） | 🟢 新功能 | 正则 `[a-z\u4e00-\u9fff]` 支持中文；场景标题追加后缀 | nfoParser.py, README.md, NFO字段对照表.md |
| 优化 Movie 关联搜索逻辑：先搜 Movie 名，再搜场景标题，再搜场景路径 | 🟢 新功能 | 三个步骤的搜索策略，提高匹配成功率 | nfoSceneParser.py, README.md, NFO字段对照表.md |
| 新增 `title_suffix` 字段，场景标题区分不同版本 | 🟢 新功能 | 有兄弟文件时标题追加后缀 | nfoParser.py, nfoSceneParser.py, README.md, NFO字段对照表.md |
| **单个场景也创建合集**：后缀正则 `\d+` 分支把番号尾部数字（如 `SNIS-002` 的 `002`）误识别为分集后缀 | 🔴 致命 | 移除 `\d+` 分支，纯数字不再识别为分集后缀 | nfoParser.py |
| **`__has_multipart_siblings` 把当前文件自身和 .nfo/.jpg 等非视频文件计入兄弟数量**，导致单文件也报告 `has_siblings=True` | 🔴 致命 | 排除当前文件、子目录、非视频扩展名 | nfoParser.py |
| **CD 式后缀标题冗余**：`title_suffix`（cd1）和 `scene_index`（CD1）同时追加，产生 `标题 cd1 CD1` | 🟡 逻辑冲突 | CD 式后缀时 `title_suffix` 置 None，仅追加 `CD{序号}` | nfoParser.py |
| **分集文件各自创建独立 Movie**：`__find_create_movie` Step 1 仅用 movie_name（NFO title）搜索，长搜索词+特殊字符导致 Stash INCLUDES 搜索失败 | 🔴 致命 | Step 1 增加 base_name 回退搜索；Step 2/3 的 `per_page` 从 5 增至 50 | nfoSceneParser.py, stashInterface.py |
| **同名 Movie 未关联**：Stash INCLUDES 搜索对含空格的 movie_name（如 "S1 GIRLS COLLECTION"）匹配失败，导致相同 `<set/name>` 的场景各自创建同名 Movie | 🔴 致命 | 新增 Step 2 全量获取 Movie + 规范化（去空格、小写）精确匹配作为兜底；reload 模式下缓存全量 Movie 列表 | nfoSceneParser.py, stashInterface.py |
| **空格不敏感匹配**：`"S1GIRLSCOLLECTION"` 和 `"S1 GIRLS COLLECTION"` 无法关联 | 🟢 新功能 | `__normalize_movie_name()` 规范化（NFKC + 波浪号统一 + 小写 + 去空格）后比较，Step 1 包含匹配 + Step 2 精确匹配 | nfoSceneParser.py |

---

## 十一、已知限制

1. **Movie 不支持别名搜索**：`__find_create_movie` 使用子串匹配搜索 Movie 名
2. **Movie 不支持更新**：匹配到已有 Movie 时不会用 NFO 数据更新
3. **仅支持一个 Movie 关联**：场景只关联第一个 Movie
4. **`scene_index` 不支持小数**：`int()` 转换会截断
5. **HTML 实体仅处理 `&nbsp;`**：其他 HTML 实体可能导致 XML 解析失败
6. **标签搜索每次全量查询**：reload 模式下每个场景都调用 `gql_findTags()`
7. **图片下载串行**：多个 `<thumb>` URL 逐个下载
8. **不支持自定义 NFO 目录**：`nfo_location` 仅支持 `"with files"`
9. **Windows 编码依赖 Python 3.7+**：`sys.stdout.reconfigure()` 需要 Python 3.7+
10. **乱码数据需手动修复**：编码修复前已写入数据库的乱码需重新扫描
11. **`<set/name>` 与无 `<set>` 混合时可能创建多个 Movie**：建议同一组文件的 NFO 保持 `<set>` 一致性
