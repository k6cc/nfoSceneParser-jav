import os
import xml.etree.ElementTree as xml
import base64
import glob
import re
import requests
import config
import log
from abstractParser import AbstractParser

class NfoParser(AbstractParser):
    # 兄弟文件检测时排除的非视频扩展名（NFO/图片/字幕/文本等）
    _NON_VIDEO_EXTENSIONS = {".nfo", ".jpg", ".jpeg", ".png", ".webp", ".srt", ".vtt", ".ass", ".sub", ".txt", ".json", ".xml", ".bif", ".edl"}

    def __init__(self, scene_path, defaults=None, folder_mode=False):
        super().__init__()
        if defaults:
            self._defaults = defaults
        self._scene_path = scene_path
        # Finds nfo file
        self._nfo_file = None
        dir_path = os.path.dirname(scene_path)
        if config.nfo_location.lower() == "with files":
            if folder_mode:
                # look in current dir & parents for a folder.nfo file...
                self._nfo_file = self._find_in_parents(dir_path, "folder.nfo")
            else:
                if len(getattr(config, "custom_nfo_name", "")) > 0:
                    self._nfo_file = os.path.join(dir_path, config.custom_nfo_name)
                else:
                    # First try: same name as the scene file (e.g. "Video Title.nfo")
                    nfo_candidate = os.path.splitext(scene_path)[0] + ".nfo"
                    if os.path.exists(nfo_candidate):
                        self._nfo_file = nfo_candidate
                    else:
                        # Fallback: strip multi-part suffix (e.g. "IDBD-287-cd1" → "IDBD-287")
                        base_path = os.path.splitext(scene_path)[0]
                        base_name = os.path.split(base_path)[1]
                        mp_match = re.search(r"(?i)([-._ ])(\d*[a-z]+\d*|[a-z]+\d+)$", base_name)
                        if mp_match:
                            sep = mp_match.group(1)
                            suffix = mp_match.group(2)
                            prefix = base_name[:mp_match.start()]
                            stripped_nfo = os.path.join(dir_path, prefix + ".nfo")
                            if os.path.exists(stripped_nfo):
                                self._nfo_file = stripped_nfo
                            else:
                                # Try first part's nfo for cd-style versions (e.g. cd1.nfo from cd2.nfo)
                                is_cd = bool(re.match(r"(?i)^(cd|part|disc|disk|pt)\d*[a-z]*$", suffix))
                                if is_cd:
                                    first_part_nfo = os.path.join(dir_path, prefix + sep + suffix + ".nfo")
                                    if os.path.exists(first_part_nfo):
                                        self._nfo_file = first_part_nfo
                                    else:
                                        # Try base suffix (e.g. cd1.nfo, uc.nfo)
                                        base_suffix_nfo = os.path.join(dir_path, prefix + sep + suffix + ".nfo")
                                        if os.path.exists(base_suffix_nfo):
                                            self._nfo_file = base_suffix_nfo
                    if not self._nfo_file:
                        # Fallback: look for "movie.nfo" in the same directory
                        movie_nfo = os.path.join(dir_path, "movie.nfo")
                        if os.path.exists(movie_nfo):
                            self._nfo_file = movie_nfo
        # else:
            # TODO: support dedicated dir instead of "with files" (compatibility with nfo exporters)
        self._nfo_root = None

    def __match_image_files(self, files, pattern):
        thumb_images = []
        index = 0
        for file in files:
            if index >= self._image_Max:
                break
            if pattern.match(file):
                with open(file, "rb") as img:
                    img_bytes = img.read()
                thumb_images.append(img_bytes)
                index += 1
        return thumb_images

    def __extract_nfo_uniqueid(self):
        return self._nfo_root.findtext("uniqueid")

    def __read_cover_image_file(self):
        path_no_ext = os.path.splitext(self._nfo_file)[0]
        file_no_ext = os.path.split(path_no_ext)[1]
        path_dir = os.path.dirname(self._nfo_file)

        scene_suffixes = ["fanart", "landscape", "thumb", "poster", "cover"]
        folder_suffixes = ["landscape", "backdrop", "thumb", "poster", "cover", "folder"]

        files = glob.glob(f"{glob.escape(path_no_ext)}*.*")
        scene_images = []
        loaded_files = set()
        for suffix in scene_suffixes:
            pattern = re.compile("^.*" + re.escape(file_no_ext) + \
                f"(-{suffix}\\d{{0,2}})\\.(jpe?g|png|webp)$", re.I)
            for file in files:
                if file in loaded_files:
                    continue
                if pattern.match(file):
                    with open(file, "rb") as img:
                        scene_images.append(img.read())
                    loaded_files.add(file)
                    if len(scene_images) >= self._image_Max:
                        return scene_images
        if len(scene_images) < self._image_Max:
            numeric_pattern = re.compile("^.*" + re.escape(file_no_ext) + \
                "(\\d{0,2})\\.(jpe?g|png|webp)$", re.I)
            for file in files:
                if file in loaded_files:
                    continue
                if numeric_pattern.match(file):
                    with open(file, "rb") as img:
                        scene_images.append(img.read())
                    loaded_files.add(file)
                    if len(scene_images) >= self._image_Max:
                        return scene_images
        if scene_images:
            return scene_images

        folder_files = glob.glob(f"{glob.escape(path_dir)}{os.path.sep}*.*")
        folder_images = []
        loaded_files = set()
        for suffix in folder_suffixes:
            pattern = re.compile(f"^.*({suffix}\\d{{0,2}})\\.(jpe?g|png|webp)$", re.I)
            for file in folder_files:
                if file in loaded_files:
                    continue
                if pattern.match(file):
                    with open(file, "rb") as img:
                        folder_images.append(img.read())
                    loaded_files.add(file)
                    if len(folder_images) >= self._image_Max:
                        return folder_images
        return folder_images

    def ___find_thumb_urls(self, query):
        result = []
        matches = self._nfo_root.findall(query)
        for match in matches:
            if match.text:
                url = match.text.strip()
                if url.startswith(("http://", "https://")):
                    result.append(url)
        return result

    def __download_cover_images(self):
        # Prefer "landscape" images, then "poster", otherwise take any thumbnail image...
        thumb_urls = self.___find_thumb_urls("thumb[@aspect='landscape']") \
            or self.___find_thumb_urls("thumb[@aspect='poster']") \
            or self.___find_thumb_urls("thumb")
        # Ensure there are images and the count does not exceed the max allowed...
        if len(thumb_urls) == 0:
            return []
        del thumb_urls[self._image_Max:]
        # Download images from url
        thumb_images = []
        for thumb_url in thumb_urls:
            img_bytes = None
            try:
                r = requests.get(thumb_url, timeout=10)
                img_bytes = r.content
                thumb_images.append(img_bytes)
            except Exception as e:
                log.LogDebug(
                    f"Failed to download the cover image from {thumb_url}: {repr(e)}")
        return thumb_images

    def __extract_cover_images_b64(self):
        if "cover_image" in config.blacklist:
            return []
        file_images = []
        # Get image from disk (file), otherwise from <thumb> tag (url)
        thumb_images = self.__read_cover_image_file() or self.__download_cover_images()
        for thumb_image in thumb_images:
            thumb_b64img = base64.b64encode(thumb_image)
            if thumb_b64img:
                file_images.append(
                    f"data:image/jpeg;base64,{thumb_b64img.decode('utf-8')}")
        return file_images

    def __read_movie_cover_images(self):
        # Movie 专用正反封面搜索，与场景封面逻辑（__read_cover_image_file）完全独立。
        # basename 与搜索目录均与 __read_cover_image_file 保持一致（基于 NFO 文件路径），
        # 确保两者互不干扰；本方法不使用 glob/数字后缀，仅精确匹配用户指定文件名。
        # 受 config.blacklist 中的 "cover_image" 控制，与场景封面一致。
        if "cover_image" in config.blacklist:
            return (None, None)
        if not self._nfo_file:
            return (None, None)
        # 与 __read_cover_image_file() 使用相同的 basename 和目录来源
        path_no_ext = os.path.splitext(self._nfo_file)[0]
        file_no_ext = os.path.split(path_no_ext)[1]
        path_dir = os.path.dirname(self._nfo_file)
        img_exts = (".jpg", ".jpeg", ".png", ".webp")

        def __find_image(candidates):
            # candidates: [(dir, filename_without_ext), ...] 按优先级排序
            for dir_path, file_base in candidates:
                for ext in img_exts:
                    img_path = os.path.join(dir_path, f"{file_base}{ext}")
                    if os.path.isfile(img_path):
                        try:
                            with open(img_path, "rb") as img:
                                return img.read()
                        except OSError:
                            continue
            return None

        # 正面图：场景级 {basename}-poster > 文件夹级 folder
        front_image = __find_image([
            (path_dir, f"{file_no_ext}-poster"),
            (path_dir, "folder"),
        ])
        # 背面图：场景级 fanart > landscape > thumb > 文件夹级 landscape > backdrop
        back_image = __find_image([
            (path_dir, f"{file_no_ext}-fanart"),
            (path_dir, f"{file_no_ext}-landscape"),
            (path_dir, f"{file_no_ext}-thumb"),
            (path_dir, "landscape"),
            (path_dir, "backdrop"),
        ])
        return (front_image, back_image)

    def __extract_movie_cover_images_b64(self):
        # 编码 Movie 专用封面为 base64 data URL，与场景封面逻辑独立。
        front_bytes, back_bytes = self.__read_movie_cover_images()
        front_b64 = back_b64 = None
        if front_bytes:
            front_b64 = f"data:image/jpeg;base64,{base64.b64encode(front_bytes).decode('utf-8')}"
        if back_bytes:
            back_b64 = f"data:image/jpeg;base64,{base64.b64encode(back_bytes).decode('utf-8')}"
        return (front_b64, back_b64)

    def __extract_nfo_rating(self):
        multiplier = getattr(config, "user_rating_multiplier", 1)
        user_rating = round(float(self._nfo_root.findtext(getattr(config, "user_rating_field", "userrating")) or 0) * multiplier)
        if user_rating > 0:
            return user_rating
        # <rating> is converted to a scale of 5 if needed
        rating = None
        rating_elem = self._nfo_root.find("ratings/rating")
        if rating_elem is not None:
            max_value = float(rating_elem.attrib["max"] or 1)
            value = float(rating_elem.findtext("value") or 0)
            # ratings on scale 100 (since stashapp v24)
            rating = round(value / max_value * 100)
        return rating

    def __extract_nfo_date(self):
        # date either in <premiered> (full) or <year> (only the year)
        year = self._nfo_root.findtext("year")
        if year is not None:
            year = f"{year}-01-01"
        return self._nfo_root.findtext("premiered") or year

    def __extract_nfo_tags(self):
        source = getattr(config, "load_tags_from", "both").lower()
        file_tags = []
        if source in ["tags", "both"]:
            # from nfo <tag>
            tags = self._nfo_root.findall("tag")
            for tag in tags:
                if tag.text:
                    file_tags.append(tag.text)
        if source in ["genres", "both"]:
            # from nfo <genre>
            genres = self._nfo_root.findall("genre")
            for genre in genres:
                if genre.text:
                    file_tags.append(genre.text)
        return list(set(file_tags))

    def __extract_nfo_actors(self):
        file_actors = []
        actors = self._nfo_root.findall("actor/name")
        for actor in actors:
            if actor.text:
                file_actors.append(actor.text)
        return file_actors

    @staticmethod
    def __clean_nfo_content(content):
        content = content.strip()
        content = content.replace("&nbsp;", " ")
        content = re.sub(r"&(?!(?:[a-zA-Z]+|#[0-9]+|#x[0-9a-fA-F]+);)", "&amp;", content)
        content = re.sub(r"`(https?://[^`<]+)`", r"\1", content)
        return content

    def parse(self):
        if not self._nfo_file or not os.path.exists(self._nfo_file):
            if self._nfo_file:
                log.LogDebug(f"The NFO file \"{os.path.split(self._nfo_file)[1]}\" was not found")
            return {}
        log.LogDebug("Parsing '{}'".format(self._nfo_file))
        # Parse NFO xml content
        try:
            with open(self._nfo_file, mode="r", encoding="utf-8") as nfo:
                raw_content = nfo.read()
            clean_nfo_content = self.__clean_nfo_content(raw_content)
            self._nfo_root = xml.fromstring(clean_nfo_content)
        except Exception as e:
            log.LogError(
                f"Could not parse nfo '{self._nfo_file}': {repr(e)}")
            return {}
        # Extract data from XML tree. Spec: https://kodi.wiki/view/NFO_files/Movies
        b64_images = self.__extract_cover_images_b64()
        # Movie 专用封面（独立于场景封面 cover_image/other_image）
        movie_front_b64, movie_back_b64 = self.__extract_movie_cover_images_b64()
        file_data = {
            # TODO: supports stash uniqueid to match to existing scenes (compatibility with nfo exporter)
            "file": self._nfo_file,
            "source": "nfo",
            "title": self._nfo_root.findtext("title") or self._nfo_root.findtext("originaltitle") \
            or self._nfo_root.findtext("sorttitle") or self._get_default("title", "re"),
            "director": self._nfo_root.findtext("director") or self._get_default("director"),
            "details": self._nfo_root.findtext("plot") or self._nfo_root.findtext("outline") \
            or self._nfo_root.findtext("tagline") or self._get_default("details"),
            "studio": self._nfo_root.findtext("studio") or self._get_default("studio"),
            "uniqueid": self.__extract_nfo_uniqueid() or self._nfo_root.findtext("num") or self._nfo_root.findtext("sorttitle"),
            "date": self.__extract_nfo_date() or self._get_default("date"),
            "actors": self.__extract_nfo_actors() or self._get_default("actors"),
            # Tags are merged with defaults
            "tags": list(set(self.__extract_nfo_tags() + self._get_default("tags"))),
            "rating": self.__extract_nfo_rating() or self._get_default("rating"),
            "cover_image": None if len(b64_images) < 1 else b64_images[0],
            "other_image": None if len(b64_images) < 2 else b64_images[1],
            # Movie 专用封面（不影响场景封面）
            "movie_front_image": movie_front_b64,
            "movie_back_image": movie_back_b64,
            # Below are NFO extensions or liberal tag interpretations (not part of the nfo spec)
            "movie": self._nfo_root.findtext("set/name") or self.__get_multipart_movie_name(),
            "base_name": self.__get_multipart_base_name(),
            "title_suffix": self.__get_scene_title_suffix(),
            "scene_index": self.__parse_scene_index(),
            "urls": [url.text for url in self._nfo_root.findall("url") if url.text] +
                    [url.text for url in self._nfo_root.findall("website") if url.text],
        }
        return file_data

    def __has_multipart_siblings(self, prefix):
        """Check if any sibling video files share the same base prefix (including bare file without suffix)"""
        dir_path = os.path.dirname(self._scene_path)
        if not os.path.isdir(dir_path):
            return False
        current_file = os.path.split(self._scene_path)[1]
        sibling_re = re.compile(r"(?i)^" + re.escape(prefix) + r"[-._ ].*$", re.IGNORECASE)
        count = 0
        for f in os.listdir(dir_path):
            # 排除当前文件自身
            if f == current_file:
                continue
            # 排除子目录
            if os.path.isdir(os.path.join(dir_path, f)):
                continue
            # 排除非视频文件（NFO/图片/字幕等）
            ext = os.path.splitext(f)[1].lower()
            if ext in self._NON_VIDEO_EXTENSIONS:
                continue
            if sibling_re.match(f):
                count += 1
        return count > 0

    def __auto_multipart_info(self):
        """Extract base name and suffix from filename.
        Returns (base_name, suffix, is_cd_style, has_siblings)"""
        file_base = os.path.splitext(os.path.split(self._scene_path)[1])[0]
        # Match suffix: separator + letters/Chinese characters (optionally with digits).
        # 纯数字不被识别为分集后缀（避免番号尾部数字如 SNIS-002 的 002 被误判）
        mp_match = re.search(r"(?i)([-._ ])(\d*[a-z\u4e00-\u9fff]+\d*|[a-z\u4e00-\u9fff]+\d+)$", file_base)
        if mp_match:
            sep = mp_match.group(1)
            suffix = mp_match.group(2)
            prefix = file_base[:mp_match.start()]
            is_cd = bool(re.match(r"(?i)^(cd|part|disc|disk|pt)\d*[a-z]*$", suffix))
            index = None
            if is_cd:
                inner_match = re.search(r"(\d+|[a-z])$", suffix, re.I)
                if inner_match:
                    idx_str = inner_match.group(1)
                    index = ord(idx_str.lower()) - ord('a') + 1 if idx_str.isalpha() else int(idx_str)
            has_siblings = self.__has_multipart_siblings(prefix)
            return prefix, suffix, is_cd, index, has_siblings
        else:
            has_siblings = self.__has_multipart_siblings(file_base)
            return file_base, None, False, None, has_siblings

    def __get_multipart_base_name(self):
        base, _, _, _, _ = self.__auto_multipart_info()
        return base

    def __get_scene_title_suffix(self):
        """Get suffix for scene title appending (returns None if not part of a movie set)"""
        _, suffix, is_cd, _, has_siblings = self.__auto_multipart_info()
        if not has_siblings:
            return None
        # CD 式后缀由 scene_index 负责追加 "CD{index}"，避免 "cd1 CD1" 冗余
        if is_cd:
            return None
        return suffix

    def __get_multipart_movie_name(self):
        base, _, _, _, has_siblings = self.__auto_multipart_info()
        if not has_siblings:
            return None
        # Priority: <set/name> > NFO title > base_name
        title = self._nfo_root.findtext("title")
        if title:
            return title
        return base

    def __auto_scene_index(self):
        _, _, _, index, _ = self.__auto_multipart_info()
        return index

    def __parse_scene_index(self):
        index_text = self._nfo_root.findtext("set/index")
        if index_text:
            try:
                return int(index_text)
            except (ValueError, TypeError):
                pass
        return self.__auto_scene_index()
