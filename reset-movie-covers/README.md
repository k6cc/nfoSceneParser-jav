# 重设合集封面（reset-movie-covers）

> 临时维护工具：遍历 Stash 库中所有合集（Movie），按文件名规则从关联 Scene 目录重新搜索并设置正反封面。

## 适用场景

- 已有大量 Movie 但封面缺失或错误
- 升级 nfoSceneParser-jav 到 v1.6.0 后，想为旧 Movie 补齐按新规则搜索的封面
- 批量重设封面，无需逐个手动操作

## 封面搜索优先级

与 nfoSceneParser-jav 主插件 `__read_movie_cover_images()` 完全一致：

### 正面图（front_image）
1. 场景级：`{basename}-poster.{ext}`
2. 文件夹级：`folder.{ext}`

### 背面图（back_image）
1. 场景级：`{basename}-fanart.{ext}`
2. 场景级：`{basename}-landscape.{ext}`
3. 场景级：`{basename}-thumb.{ext}`
4. 文件夹级：`landscape.{ext}`
5. 文件夹级：`backdrop.{ext}`

支持的扩展名：`.jpg` / `.jpeg` / `.png` / `.webp`

### basename 推导

- 优先用完整文件名（去扩展名）
- 回退到去掉分集后缀的 basename（如 `movie-cd1` → `movie`）
- 兼容日文/中文文件名结尾的人名（不被误判为分集后缀）

## 工作流程

1. 查询所有 Movie（id + name + 现有封面路径）
2. 对每个 Movie，反查关联 Scene（按 `scene_index` 升序）
3. 遍历 Scene 文件路径，按优先级搜索封面
4. 调用 `movieUpdate` 更新（未传入的字段保持不变）

## 配置

在 [reset-movie-covers.py](./reset-movie-covers.py) 顶部：

```python
DRY_MODE = False              # True = 只预览不写入
OVERWRITE_EXISTING = True      # False = 跳过已有封面的合集
```

## 部署方式

### 与主插件同目录部署（推荐）

把 `reset-movie-covers.py` 和 `reset-movie-covers.yml` 直接放在主插件目录（与 `nfoSceneParser.py` 同级），复用主插件的 `log.py`。

```
plugins/nfoSceneParser-jav/
├── nfoSceneParser.py
├── nfoSceneParser.yml
├── log.py
├── ...
├── reset-movie-covers.py    ← 放这里
└── reset-movie-covers.yml   ← 放这里
```

### 子目录部署

也可放在 `nfoSceneParser-jav/reset-movie-covers/` 子目录，脚本会自动查找上级目录的 `log.py`。

## 使用方法

1. Stash → 设置 → 插件 → 重新加载插件
2. 在插件列表找到「重设合集封面」
3. 点击任务「重设所有合集封面」→ 运行
4. 在 Stash 日志窗口查看进度和统计

## 已知限制

- 仅对关联了 Scene 的 Movie 生效（无关联 Scene 的 Movie 会跳过）
- 仅对新建 Movie 时的封面规则生效；已存在的 Movie 需用本工具重设
- Docker 部署下，Stash 数据库中的 Scene path 必须与容器内可访问路径一致

## 不打包到主插件 zip

本工具是临时维护脚本，**不包含在 nfoSceneParser-jav 的 release zip 中**，仅随仓库源码提供。如需使用，请单独下载 `reset-movie-covers.py` 和 `reset-movie-covers.yml`。
