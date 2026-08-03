import sys
import os
import re
import json
import base64
import requests

# 复用主插件的 log 模块。兼容两种部署方式：
#   1. 子目录部署：plugins/nise/重设合集封面/重设合集封面.py → log.py 在 plugins/nise/
#   2. 同级部署：  plugins/nise/重设合集封面.py            → log.py 在 plugins/nise/（同级）
_plugin_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_plugin_dir)
for _search_dir in [_plugin_dir, _parent_dir]:
    if os.path.isfile(os.path.join(_search_dir, "log.py")):
        sys.path.insert(0, _search_dir)
        break
import log

# ==================== 配置 ====================
# True = 只预览不实际更新
DRY_MODE = False

# True = 覆盖已有封面的 Movie；False = 跳过已有封面的 Movie
OVERWRITE_EXISTING = True

# 支持的图片扩展名
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


# ==================== 封面搜索（优先级与 nfoParser.py 的 __read_movie_cover_images 一致） ====================
def get_multipart_base_name(file_base):
    """去掉分集后缀（cd1/disc1/part1 等），返回 basename。
    与 nfoParser.py 的 __get_multipart_base_name 逻辑一致。"""
    mp_match = re.search(
        r"(?i)([-._ ])(\d*[a-z\u4e00-\u9fff]+\d*|[a-z\u4e00-\u9fff]+\d+)$", file_base)
    if mp_match:
        return file_base[:mp_match.start()]
    return file_base


def find_image_in_dir(dir_path, file_base):
    """在指定目录精确搜索 {file_base}.{ext}，返回 bytes 或 None。"""
    for ext in IMAGE_EXTENSIONS:
        img_path = os.path.join(dir_path, f"{file_base}{ext}")
        if os.path.isfile(img_path):
            try:
                with open(img_path, "rb") as img:
                    return img.read()
            except OSError:
                continue
    return None


def find_movie_covers_from_scene(scene_path):
    """根据单个 Scene 文件路径搜索 Movie 封面。
    优先级与 nfoParser.py 的 __read_movie_cover_images 一致：
      正面：{basename}-poster > folder
      背面：{basename}-fanart > {basename}-landscape > {basename}-thumb > landscape > backdrop
    basename 候选：完整文件名优先，去掉分集后缀的 basename 回退。
    （get_multipart_base_name 的正则会误匹配结尾的日文/中文人名为分集后缀，
     所以完整文件名优先搜索，避免 basename 被错误截断。）
    返回 (front_bytes, back_bytes)
    """
    if not scene_path:
        return (None, None)

    path_no_ext = os.path.splitext(scene_path)[0]
    file_no_ext = os.path.split(path_no_ext)[1]
    path_dir = os.path.dirname(scene_path)
    base_name = get_multipart_base_name(file_no_ext)

    # basename 候选：完整文件名优先，去掉分集后缀的 basename 回退
    base_candidates = [file_no_ext]
    if base_name != file_no_ext:
        base_candidates.append(base_name)

    # 正面图
    front_image = None
    for base in base_candidates:
        for candidate in [f"{base}-poster", "folder"]:
            front_image = find_image_in_dir(path_dir, candidate)
            if front_image:
                break
        if front_image:
            break

    # 背面图
    back_image = None
    for base in base_candidates:
        for candidate in [
            f"{base}-fanart",
            f"{base}-landscape",
            f"{base}-thumb",
            "landscape",
            "backdrop",
        ]:
            back_image = find_image_in_dir(path_dir, candidate)
            if back_image:
                break
        if back_image:
            break

    return (front_image, back_image)


def find_movie_covers_from_scenes(scene_paths):
    """遍历多个 Scene 路径，按顺序搜索，第一个找到的封面采用。"""
    front_image = None
    back_image = None
    for scene_path in scene_paths:
        f, b = find_movie_covers_from_scene(scene_path)
        if front_image is None:
            front_image = f
        if back_image is None:
            back_image = b
        if front_image and back_image:
            break
    return (front_image, back_image)


# ==================== Stash 接口 ====================
class StashInterface:
    def __init__(self, fragment):
        self._fragment = fragment
        self._fragment_server = fragment["server_connection"]

    def __gql_call(self, query, variables=None):
        port = str(self._fragment_server["Port"])
        scheme = self._fragment_server["Scheme"]
        cookies = {} if not self._fragment_server.get("SessionCookie") else {
            "session": self._fragment_server["SessionCookie"]["Value"]
        }
        headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Connection": "keep-alive",
            "DNT": "1",
        }
        api_key = self._fragment_server.get("ApiKey")
        if api_key:
            headers["ApiKey"] = api_key
        domain = self._fragment_server["Host"]
        if domain == "0.0.0.0":
            domain = "localhost"
        url = f"{scheme}://{domain}:{port}/graphql"

        payload = {"query": query}
        if variables is not None:
            payload["variables"] = variables

        try:
            resp = requests.post(
                url, json=payload, headers=headers, cookies=cookies, timeout=30)
        except Exception as e:
            log.LogError(f"GraphQL 请求失败: {repr(e)}")
            return None

        if resp.status_code != 200:
            log.LogError(f"GraphQL HTTP {resp.status_code}: {resp.content}")
            return None

        resp.encoding = 'utf-8'
        data = resp.json()
        if data.get("errors"):
            for err in data["errors"]:
                log.LogError(f"GraphQL 错误: {err}")
            return None
        return data.get("data")

    def find_all_movies(self):
        """返回所有 Movie 列表（id, name, front_image_path, back_image_path）"""
        query = """
        query {
            findMovies(filter: {per_page: -1}) {
                movies {
                    id
                    name
                    front_image_path
                    back_image_path
                }
            }
        }
        """
        result = self.__gql_call(query)
        if not result:
            return []
        return result.get("findMovies", {}).get("movies", [])

    def find_scenes_by_movie(self, movie_id):
        """反查关联指定 Movie 的所有 Scene，按 scene_index 升序返回文件路径列表"""
        query = """
        query FindScenes($scene_filter: SceneFilterType, $filter: FindFilterType) {
            findScenes(scene_filter: $scene_filter, filter: $filter) {
                scenes {
                    id
                    files { path }
                    movies {
                        movie { id }
                        scene_index
                    }
                }
            }
        }
        """
        variables = {
            "scene_filter": {
                "movies": {
                    "value": [str(movie_id)],
                    "modifier": "INCLUDES"
                }
            },
            "filter": {
                "per_page": -1
            }
        }
        result = self.__gql_call(query, variables)
        if not result:
            return []
        scenes = result.get("findScenes", {}).get("scenes", [])
        scene_infos = []
        for scene in scenes:
            files = scene.get("files") or []
            if not files:
                continue
            path = files[0].get("path")
            if not path:
                continue
            scene_index = None
            for m in scene.get("movies") or []:
                if m.get("movie", {}).get("id") == str(movie_id):
                    scene_index = m.get("scene_index")
                    break
            scene_infos.append((scene_index, path))
        # scene_index 升序，None 排到最后
        scene_infos.sort(key=lambda x: (x[0] is None, x[0] or 0))
        return [path for _, path in scene_infos]

    def update_movie_images(self, movie_id, front_b64=None, back_b64=None):
        """更新 Movie 封面，只传非 None 的字段（未传入的字段保持不变）"""
        query = """
        mutation movieUpdate($input: MovieUpdateInput!) {
            movieUpdate(input: $input) {
                id
            }
        }
        """
        input_data = {"id": str(movie_id)}
        if front_b64 is not None:
            input_data["front_image"] = front_b64
        if back_b64 is not None:
            input_data["back_image"] = back_b64
        result = self.__gql_call(query, {"input": input_data})
        # 严格检查：movieUpdate 返回 null 也算失败（权限不足/ID 不存在等）
        if not result or not result.get("movieUpdate"):
            log.LogError(
                f"movieUpdate 返回 null，input: id={movie_id}, "
                f"front={'有' if front_b64 else '无'}, back={'有' if back_b64 else '无'}")
            return False
        return True


# ==================== 工具函数 ====================
def encode_b64(image_bytes):
    if not image_bytes:
        return None
    return f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"


# ==================== 主流程 ====================
def main():
    fragment = None
    if len(sys.argv) > 1:
        fragment = json.loads(sys.argv[1])
    else:
        fragment = json.loads(sys.stdin.read())

    stash = StashInterface(fragment)

    log.LogInfo("=== 重设合集封面任务开始 ===")
    log.LogInfo(f"配置: DRY_MODE={DRY_MODE}, OVERWRITE_EXISTING={OVERWRITE_EXISTING}")

    movies = stash.find_all_movies()
    log.LogInfo(f"共 {len(movies)} 个合集")

    if not movies:
        log.LogInfo("没有合集，任务结束")
        print(json.dumps({"output": "No movies found"}))
        return

    total = len(movies)
    updated = 0
    skipped_has_cover = 0
    skipped_no_scene = 0
    skipped_no_cover = 0
    failed = 0

    progress_step = 1 / total
    progress = 0

    for movie in movies:
        movie_id = movie["id"]
        movie_name = movie["name"]

        progress += progress_step
        log.LogProgress(progress)

        has_front = bool(movie.get("front_image_path"))
        has_back = bool(movie.get("back_image_path"))

        if (has_front or has_back) and not OVERWRITE_EXISTING:
            log.LogDebug(f"[{movie_id}] '{movie_name}' 已有封面，跳过")
            skipped_has_cover += 1
            continue

        scene_paths = stash.find_scenes_by_movie(movie_id)
        if not scene_paths:
            log.LogWarning(f"[{movie_id}] '{movie_name}' 没有关联 Scene，跳过")
            skipped_no_scene += 1
            continue

        # 诊断：输出首个 Scene 路径帮助定位 Docker 路径问题
        log.LogDebug(f"[{movie_id}] '{movie_name}' 关联 {len(scene_paths)} 个 Scene，首个路径: {scene_paths[0]}")

        front_bytes, back_bytes = find_movie_covers_from_scenes(scene_paths)
        front_b64 = encode_b64(front_bytes)
        back_b64 = encode_b64(back_bytes)

        if not front_b64 and not back_b64:
            # 诊断：输出路径存在性，帮助定位 Docker 路径映射问题
            first_path = scene_paths[0]
            first_exists = os.path.exists(first_path)
            first_dir = os.path.dirname(first_path)
            dir_exists = os.path.isdir(first_dir)
            log.LogWarning(
                f"[{movie_id}] '{movie_name}' 未找到封面"
                f"（搜索 {len(scene_paths)} 个 Scene，"
                f"首个路径是否存在={first_exists}，目录是否存在={dir_exists}）")
            if first_exists:
                # 路径存在但没找到封面，输出目录下文件数量帮助诊断
                try:
                    dir_files = os.listdir(first_dir)
                    log.LogDebug(
                        f"  目录下共 {len(dir_files)} 个文件，"
                        f"其中图片: {[f for f in dir_files if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS][:5]}")
                except OSError:
                    pass
            else:
                log.LogWarning(f"  路径不可访问: {first_path}")
            skipped_no_cover += 1
            continue

        if DRY_MODE:
            log.LogInfo(
                f"[DRY] [{movie_id}] '{movie_name}' 将更新: front={'是' if front_b64 else '否'}, back={'是' if back_b64 else '否'}")
            updated += 1
            continue

        ok = stash.update_movie_images(movie_id, front_b64, back_b64)
        if ok:
            log.LogInfo(
                f"[{movie_id}] '{movie_name}' 已更新: front={'是' if front_b64 else '否'}, back={'是' if back_b64 else '否'}")
            updated += 1
        else:
            log.LogError(f"[{movie_id}] '{movie_name}' 更新失败")
            failed += 1

    log.LogInfo("=== 任务完成 ===")
    log.LogInfo(f"总数: {total}")
    log.LogInfo(f"已更新: {updated}")
    log.LogInfo(f"跳过（已有封面）: {skipped_has_cover}")
    log.LogInfo(f"跳过（无 Scene）: {skipped_no_scene}")
    log.LogInfo(f"跳过（无封面文件）: {skipped_no_cover}")
    log.LogInfo(f"失败: {failed}")

    print(json.dumps({"output": f"Updated {updated}/{total}"}))


if __name__ == "__main__":
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stdin and hasattr(sys.stdin, 'reconfigure'):
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    main()
