"""业务服务层

- MusicService: 搜索 / 歌曲（路由层直接调用的 2 个方法）
- BatchDownloadService: 批量下载（任务管理 + 异步下载 + 状态源）

设计原则：
- 公开 API：路由层唯一直接调用的方法
- 私有方法：仅服务内部使用，前缀 `_`
- 客户端调用：直接调 `clients.music_client` 提供的函数，不再额外包装
"""
import logging
import os
import tempfile
import threading
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

import requests

from clients.music_client import music_client, search_music, get_song, get_platforms, parse_playlist
from utils.url_parser import parse_url
from utils.filename import (
    sanitize_filename as _sanitize_filename,
    build_filename as _build_filename,
)
from app_config import QUALITY_LEVELS


def _get_level_display(quality: str, file_ext: str = '') -> Dict[str, str]:
    """把 quality key 转成前端展示所需的字段

    Args:
        quality: quality key ('hires' / 'lossless' / 'exhigh' / 'standard')
        file_ext: 实际下载文件的扩展名（带或不带点，如 '.flac' / 'mp3'）

    Returns:
        {
            'name': '无损',           # 显示名（label）
            'format': 'FLAC',         # 格式描述（description）
            'file_ext': 'flac',       # 文件扩展名（不带点）
        }
    """
    cfg = QUALITY_LEVELS.get(quality) or QUALITY_LEVELS.get('standard', {})
    ext = file_ext.lstrip('.').lower() if file_ext else cfg.get('format', 'mp3').split('/')[0].lower()
    return {
        'name': cfg.get('label', quality),
        'format': cfg.get('description', ''),
        'file_ext': ext,
    }
from utils.audio_utils import (
    get_extension as _get_extension,
    detect_audio_type as _detect_audio_type,
    safe_remove as _safe_remove,
)
from utils.metadata import write_metadata as _write_metadata

logger = logging.getLogger(__name__)

# ==================== 重试错误分类 ====================

# 可重试的 HTTP 状态码（临时性错误）
_RETRYABLE_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504, 507}
# 可重试的网络异常类型
_RETRYABLE_NETWORK_ERRORS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectTimeout,
    requests.exceptions.ReadTimeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
)


def _classify_error(e: Exception, attempt: int, max_attempts: int) -> tuple:
    """分类异常：返回 (是否可重试, 原因)

    确定性错误（不重试）：
      - HTTP 4xx（除 408/425/429）：资源不存在/无权限/请求格式错
      - KeyError/ValueError/TypeError：代码 bug
      - OSError (EEXIST 等)：文件系统错误
      - Exception with 'Forbidden'/'Not Found' message

    不确定错误（可重试）：
      - 网络异常（Timeout/ConnectionError/ChunkedEncodingError）
      - HTTP 5xx/429/408/425：服务器临时过载
    """
    # 网络异常 → 可重试
    if isinstance(e, _RETRYABLE_NETWORK_ERRORS):
        if attempt < max_attempts - 1:
            return True, f'网络异常 {type(e).__name__}'
        return False, f'网络异常已达最大重试次数'
    # HTTP 异常 → 看状态码
    if isinstance(e, requests.exceptions.HTTPError):
        status = e.response.status_code if e.response is not None else 0
        if status in _RETRYABLE_HTTP_STATUSES:
            if attempt < max_attempts - 1:
                return True, f'HTTP {status} 临时错误'
            return False, f'HTTP {status} 已达最大重试次数'
        return False, f'HTTP {status} 确定性错误（如 403/404）'
    # 其他 Exception → 不可重试（代码 bug、文件系统错误等）
    return False, f'{type(e).__name__} 非网络错误'


# ==================== Music Service ====================

class MusicService:
    """音乐业务服务 - 2 个公开方法供路由调用：search / get_song"""

    # ==================== 公开 API（路由直接调用） ====================

    def search(self, keyword: str, platform: str = None,
               limit: int = 50) -> Dict[str, Any]:
        """统一搜索

        1. keyword 是 URL → 解析后拿歌曲详情
        2. 否则按关键词搜歌曲

        返回：{'data': [...], 'warnings': [...]}
        """
        parsed = parse_url(keyword)
        if parsed:
            return self._resolve_from_url(parsed)
        return self._search_by_keyword(keyword, platform, limit)

    def get_song_info(self, song_id, quality: str = 'lossless',
                      platform: str = None,
                      quality_map: dict = None,
                      with_lyric: bool = True) -> Optional[Dict[str, Any]]:
        """获取歌曲完整信息（基本信息 + 播放 URL + 可选歌词）

        song_id 可以是 str 或 dict（含 id + mp3_hash 等）
        quality_map（可选）：该歌曲的可用品质字典，让降级更精准
        with_lyric（可选，默认 True）：是否获取歌词（重试时可设 False 节省请求）
        """
        return get_song(song_id, quality, platform, quality_map=quality_map, with_lyric=with_lyric)

    def get_platforms(self) -> List[Dict[str, str]]:
        """获取可用平台列表（前端从 /platforms 接口读取，避免硬编码）"""
        try:
            return music_client.get_platforms()
        except Exception as e:
            logger.error(f"获取平台列表失败: {e}")
            return []

    # ==================== 私有方法（仅服务内部使用） ====================

    def _resolve_from_url(self, parsed: Dict[str, str]) -> Dict[str, Any]:
        """URL 解析后获取详情（支持歌曲链接和歌单链接）

        返回带 type 字段，前端根据 type 决定是否展示 toolbar：
        - type='song': 单曲列表（无 toolbar）
        - type='playlist': 歌单（detail 含 name/cover/creator/trackCount）
        """
        resource_type = parsed.get('type')
        resource_id = parsed['id']
        source_platform = parsed['platform']

        if resource_type == 'music':
            song_info = self.get_song_info(resource_id, 'lossless', source_platform)
            if song_info and song_info.get('id') and song_info.get('url'):
                return {
                    'data': [song_info],
                    'type': 'song',
                    'warnings': [],
                }
            return {
                'data': [],
                'type': 'song',
                'error': '未找到歌曲信息（可能 URL 已失效）',
                'warnings': [],
            }

        if resource_type == 'playlist':
            playlist = parse_playlist(resource_id, platform=source_platform)
            if playlist and playlist.get('tracks'):
                return {
                    'data': playlist['tracks'],
                    'type': 'playlist',
                    'detail': {
                        'name': playlist.get('name') or '歌单',
                        'creator': playlist.get('creator') or '',
                        'cover': playlist.get('cover') or '',
                        'trackCount': playlist.get('trackCount') or len(playlist['tracks']),
                    },
                    'warnings': [],
                }
            return {
                'data': [],
                'type': 'playlist',
                'error': f'{source_platform} 平台暂不支持歌单解析',
                'warnings': [],
            }

        return {
            'data': [],
            'type': 'unknown',
            'error': f'暂不支持解析 {resource_type} 类型的链接',
            'warnings': [],
        }

    def _search_by_keyword(self, keyword: str, platform: str, limit: int) -> Dict[str, Any]:
        """关键字搜索歌曲"""
        try:
            result = search_music(keyword, platform, limit)
            # music_client.search() 返回 {'data': [...], 'search_source': 'xxx'}
            songs = result.get('data', []) if isinstance(result, dict) else result
            search_source = result.get('search_source', '') if isinstance(result, dict) else ''
            return {'data': songs, 'type': 'song', 'search_source': search_source, 'warnings': []}
        except Exception as e:
            logger.error(f"[{platform}] 搜索失败: {e}")
            return {
                'data': [],
                'type': 'song',
                'search_source': '',
                'error': f'搜索失败: {e}',
                'warnings': [],
            }

    def _resolve_from_url(self, parsed: Dict[str, str]) -> Dict[str, Any]:
        """URL 解析后获取详情（支持歌曲链接和歌单链接）

        返回带 type 字段，前端根据 type 决定是否展示 toolbar：
        - type='song': 单曲列表（无 toolbar）
        - type='playlist': 歌单（detail 含 name/cover/creator/trackCount）

        ★ 修复：URL 解析出的单曲也会被标记 _search_source，让 /song 接口的
        url/info/lyric 链能用同源优先（之前只有 keyword 搜索走这条路径，
        URL 解析的歌曲 preferred_source 永远是空，会被 random 源顶替）。
        """
        resource_type = parsed.get('type')
        resource_id = parsed['id']
        source_platform = parsed['platform']

        if resource_type == 'music':
            song_info = self.get_song_info(resource_id, 'lossless', source_platform)
            if song_info and song_info.get('id') and song_info.get('url'):
                # 标记 _search_source（让 /song 后续链可以同源优先）
                song_info['_search_source'] = 'url_resolved'
                return {
                    'data': [song_info],
                    'type': 'song',
                    'warnings': [],
                }
            return {
                'data': [],
                'type': 'song',
                'error': '未找到歌曲信息（可能 URL 已失效）',
                'warnings': [],
            }

        if resource_type == 'playlist':
            playlist = parse_playlist(resource_id, platform=source_platform)
            if playlist and playlist.get('tracks'):
                # 给每首歌标记 _search_source（让 /song 后续链可以同源优先）
                for t in playlist.get('tracks', []) or []:
                    t.setdefault('_search_source', 'playlist_resolved')
                return {
                    'data': playlist['tracks'],
                    'type': 'playlist',
                    'detail': {
                        'name': playlist.get('name') or '歌单',
                        'creator': playlist.get('creator') or '',
                        'cover': playlist.get('cover') or '',
                        'trackCount': playlist.get('trackCount') or len(playlist['tracks']),
                    },
                    'warnings': [],
                }
            return {
                'data': [],
                'type': 'playlist',
                'error': f'{source_platform} 平台暂不支持歌单解析',
                'warnings': [],
            }

        return {
            'data': [],
            'type': 'unknown',
            'error': f'暂不支持解析 {resource_type} 类型的链接',
            'warnings': [],
        }


music_service = MusicService()


# ==================== Batch Download Service ====================

class BatchDownloadService:
    """批量下载服务
    职责：
    - 管理任务状态（task_id → {status, progress, file_path, ...}）
    - 后台并发下载 + 写 metadata + 打包 ZIP
    - 提供 SSE 状态查询接口
    - 提供文件下载信息接口
    """

    # 任务完成后自动清理的秒数
    TASK_TTL = 600

    # 并发下载线程数
    MAX_WORKERS = 6

    # 音频扩展名 → MIME 类型
    EXT_MIME_TYPES = {
        '.mp3': 'audio/mpeg',
        '.flac': 'audio/flac',
        '.m4a': 'audio/mp4',
        '.ogg': 'audio/ogg',
        '.wav': 'audio/wav',
    }

    def __init__(self):
        self._tasks: dict[str, dict] = {}
        self._lock = threading.Lock()

    # ==================== 公开 API（路由直接调用） ====================

    def start(self, items: list, zip_name: str, settings: dict) -> dict:
        """启动批量下载任务，立即返回 task_id 等信息

        Raises:
            ValueError: items 为空
        """
        if not items:
            raise ValueError("缺少 items 参数")

        task_id = f"task_{uuid.uuid4().hex[:16]}"

        # 初始化每首歌曲的状态：pending
        # 前端 DownloadDrawer 用 songs 数组渲染 per-song 进度
        # 立即填充 level_name / file_ext / file_format（基于用户请求的 quality 推测），
        # 这样前端一开始就能看到显示名（"无损"等），不用等拿到 url
        initial_songs = []
        for item in items:
            item_quality = item.get('quality', 'lossless')
            display = _get_level_display(item_quality, '')
            initial_songs.append({
                'id': item.get('id', ''),
                'name': item.get('name', '未知歌曲'),
                'artist': item.get('artist', item.get('artists', '')),
                'platform': item.get('platform') or item.get('source', ''),
                'level': item_quality,
                'level_name': display['name'],     # 立即显示（无需等拿到 url）
                'file_ext': '',                    # 拿到 url 后填充
                'file_format': display['format'],  # 立即显示音质描述
                'status': 'pending',     # pending/processing/done/failed
                'file_size': 0,
                'error': '',
                'started_at': 0,
                'completed_at': 0,
            })

        with self._lock:
            self._tasks[task_id] = {
                'status': 'running',
                'total': len(items),
                'completed': 0,
                'failed': 0,
                'current': '',
                'zip_path': None,
                'zip_name': zip_name,
                'errors': [],
                'cancelled': False,
                'created_at': time.time(),
                'completed_at': 0,
                'file_size': 0,                # 前端实时累加 done 歌曲的 file_size
                'songs': initial_songs,        # per-song 状态数组
            }

        thread = threading.Thread(
            target=self._run_batch_task,
            args=(task_id, items, zip_name, settings)
        )
        thread.daemon = True
        thread.start()

        return {
            'task_id': task_id,
            'total': len(items),
            'file_size': 0,    # 前端实时累加 done 歌曲的 file_size
        }

    def get_list(self) -> list:
        """列出所有任务（按创建时间倒序），对外暴露的字典"""
        with self._lock:
            items = [self._task_to_dict(tid, t) for tid, t in self._tasks.items()]
        items.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        return items

    def cancel(self, task_id: str):
        """取消/删除任务

        - 任务进行中：标记 cancelled，清理 zip 文件，等待后台线程退出
        - 任务已完成：清理 zip 文件
        - 任务不存在：返回 None
        """
        with self._lock:
            task = self._tasks.get(task_id)
        if not task:
            return None

        with self._lock:
            task['cancelled'] = True
            status = task['status']
            zip_path = task.get('zip_path')

        if zip_path and os.path.exists(zip_path):
            _safe_remove(zip_path)

        # 等待短暂时间让后台线程检测到取消（最多等 0.3s）
        if status == 'running':
            time.sleep(0.3)

        with self._lock:
            self._tasks.pop(task_id, None)

        return {'task_id': task_id, 'previous_status': status}

    def get_state(self, task_id: str):
        """获取当前任务状态（SSE 轮询用），返回 None 表示任务不存在"""
        with self._lock:
            task = self._tasks.get(task_id)
        if not task:
            return None
        return {
            'status': task['status'],
            'total': task['total'],
            'completed': task['completed'],
            'failed': task['failed'],
            'current': task['current'],
            'file_size': task.get('file_size', 0),
            'errors': task.get('errors', []),
            'error': task.get('error', ''),
            'songs': task.get('songs', []),     # per-song 状态（SSE 推送用）
        }

    def get_file_info(self, task_id: str):
        """获取下载文件信息（供 send_file 使用）

        返回：{status, path, name, is_single, mime_type} 或 None
        """
        with self._lock:
            task = self._tasks.get(task_id)
        if not task:
            return None
        is_single = task.get('single_file', False)
        path = task.get('zip_path')
        name = task.get('zip_name', 'playlist')
        if is_single and path:
            ext = os.path.splitext(path)[1]
            mime_type = self.EXT_MIME_TYPES.get(ext, 'audio/mpeg')
        else:
            mime_type = 'application/zip'
        return {
            'status': task['status'],
            'path': path,
            'name': name,
            'is_single': is_single,
            'mime_type': mime_type,
        }

    def cleanup(self, task_id: str):
        """下载完成后清理：移除任务 + 删除文件"""
        with self._lock:
            t = self._tasks.pop(task_id, None)
        if t:
            _safe_remove(t.get('zip_path', ''))

    # ==================== 私有方法（仅服务内部使用） ====================

    @staticmethod
    def _task_to_dict(task_id: str, task: dict) -> dict:
        """对外暴露的任务状态（不包含 zip_path 等敏感字段）"""
        return {
            'task_id': task_id,
            'status': task['status'],
            'name': task.get('zip_name', ''),
            'total': task['total'],
            'completed': task['completed'],
            'failed': task['failed'],
            'current': task.get('current', ''),
            'errors': task.get('errors', []),
            'error': task.get('error', ''),
            'created_at': task.get('created_at', 0),
            'completed_at': task.get('completed_at', 0),
            'single_file': task.get('single_file', False),
            'file_size': task.get('file_size', 0),
            'songs': task.get('songs', []),   # per-song 状态数组
        }

    def _update_song_status(self, task_id: str, song_id: str, **updates):
        """更新 task.songs 数组中某首歌的状态字段（线程安全）"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            for s in task.get('songs', []):
                if s.get('id') == song_id:
                    s.update(updates)
                    break

    def _process_song(self, item: dict, settings: dict, task_id: str = None):
        """处理单首歌曲：下载音频 + 写 metadata + 返回结果

        settings: {writeMetadata, filenameFormat}
        task_id: 批量任务 ID，传入后会更新 per-song 状态
        返回：{'tmp_path', 'arcname', 'lrc_content', 'name'} 或 None
        """
        song_id = item.get('id')
        if not song_id:
            return None

        quality = item.get('quality', 'lossless')
        # item.source = 4 大 platform（netease/qq/kugou/kuwo）
        source = item.get('source', '').strip() or None
        name = item.get('name', 'song')
        artist = item.get('artist', '')
        album = item.get('album', '')

        # ★ 关键：从 search 透传 qualityMap，让 music_client.get_song 做智能降级
        # 场景：用户请求 lossless，但该歌曲 qualityMap 只有 exhigh/standard
        #   → 跳过 lossless，直接从 exhigh 开始，节省 5-10 秒
        item_quality_map = item.get('qualityMap') or {}

        # 酷狗特殊：mp3_hash 单独携带（用于 exhigh/standard 备用）
        # kugou 的 normalize 已将 SQFileHash 设为 id（FLAC hash），
        # 这里把 mp3_hash 一并传入供 music_client.get_song 在降级时使用
        mp3_hash = item.get('mp3_hash', '')
        if source == 'kugou' and mp3_hash:
            song_id_arg = {'id': song_id, 'mp3_hash': mp3_hash, 'qualityMap': item_quality_map}
        else:
            song_id_arg = song_id

        # 注意：不要重置失败名单 — mark_source_failed 应该跨歌曲生效
        # 让 vkeys_url 失败后 5 分钟内其他歌曲都自动跳过它（除非过期）
        # 重置会在 mark_source_failed 5 分钟后自动清理（_is_source_failed 懒清理）

        # ===== 字段约定（用户定义）=====
        # item['source']  =  platform：4 大平台名（netease/qq/kugou/kuwo）
        # song_info['api_source'] = source：底层 API 域名（vkeys_url/xunhuisi_lyric 等）
        # source = platform 是 4 平台层，api_source 是 3 方 API 层
        # 前端 buildDownloadItem 用 'source' 字段名传 platform

        # 标记 per-song 状态：开始处理
        if task_id:
            self._update_song_status(task_id, song_id,
                status='processing',
                started_at=time.time(),
            )

        last_error = None
        tmp_path = None  # 重试时复用，初始化一次
        # 重试策略：mark_source_failed 让 chain 内部自动换源（vkeys 403 后跳过 vkeys 试下个），
        # 外部再做多次重试没意义（同样换源，同样失败）。
        # 只在网络/瞬时错误时重试 1 次（5xx/Timeout）。
        max_attempts = 1   # 取消外层重试，依赖 mark_failed 机制
        for attempt in range(max_attempts):
            try:
                # 重试时跳过 lyric（如果第 1 次已经拿到，第 2 次没必要重做）
                with_lyric = (attempt == 0)
                song_info = music_service.get_song_info(
                    song_id_arg, quality, source,
                    quality_map=item_quality_map,
                    with_lyric=with_lyric,
                )
                url = song_info.get('url') if song_info else None
                if not url:
                    # 拿不到 URL：mark 当前 api_source 为坏源，让下次重试自动换源
                    api_source = song_info.get('api_source', {}) if song_info else {}
                    if isinstance(api_source, dict):
                        url_source = api_source.get('url')
                        if url_source and source:
                            music_client.mark_source_failed(
                                source, url_source,
                                reason='返回数据无效（URL 为空）',
                                expire_seconds=300,
                            )
                    if attempt < max_attempts - 1:
                        logger.debug(f'[{song_id}] 拿不到 URL（attempt {attempt+1}/{max_attempts}），重试')
                        continue   # 重试让 chain 换源
                    # 最后一次仍失败，标记 failed
                    if task_id:
                        self._update_song_status(task_id, song_id,
                            status='failed',
                            error='无法获取下载链接（可能因版权问题）',
                            completed_at=time.time(),
                        )
                    return None

                # 拿到 url 后立刻推音质/格式/扩展名信息（与 file_size 独立，
                # 这样用户能立即看到当前歌曲的目标音质，不需要等下载完成）
                extension = _get_extension(url, fallback=song_info.get('fileType', 'mp3'))
                if not extension.startswith('.'):
                    extension = '.' + extension
                actual_level = song_info.get('level') or quality
                display = _get_level_display(actual_level, extension)
                if task_id:
                    self._update_song_status(task_id, song_id,
                        level=actual_level,
                        level_name=display['name'],
                        file_ext=display['file_ext'],
                        file_format=display['format'],
                    )

                # 准备临时文件（重试时复用同一路径，避免泄漏旧文件）
                if not tmp_path:
                    fd, tmp_path = tempfile.mkstemp(suffix=extension, prefix='wan-music-batch-')
                    os.close(fd)

                try:
                    resp = requests.get(url, stream=True, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
                    resp.raise_for_status()
                    with open(tmp_path, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                except Exception:
                    # 不在这里清理：让外层 except（_classify_error）统一处理
                    # 重试时 tmp_path 复用（不被删除），确定性错误下外层会清理
                    raise

                # 用 magic bytes 检测真实类型，覆盖错误扩展名
                detected = _detect_audio_type(tmp_path)
                if detected and '.' + detected != extension:
                    new_path = os.path.splitext(tmp_path)[0] + '.' + detected
                    try:
                        os.rename(tmp_path, new_path)
                        tmp_path = new_path
                        extension = '.' + detected
                    except Exception:
                        pass

                # 写 metadata
                lyric = song_info.get('lyric', '') or ''
                if settings.get('writeMetadata', True):
                    _write_metadata(
                        tmp_path, extension,
                        name or song_info.get('name', ''),
                        artist or song_info.get('artists', ''),
                        album or song_info.get('album', ''),
                        lyric,
                        song_info.get('picUrl', ''),
                        platform=song_info.get('source', source or ''),
                        song_id=song_info.get('id', song_id)
                    )

                arcname = _sanitize_filename(
                    _build_filename(artist or song_info.get('artists', ''),
                                    name or song_info.get('name', 'song'),
                                    extension,
                                    settings.get('filenameFormat', 'song-artist'))
                )

                # 标记 per-song 状态：完成 + 实际文件大小
                # （level / level_name / file_ext / file_format 已在拿到 url 时推送，
                #  这里只追加 file_size + completed_at）
                actual_size = os.path.getsize(tmp_path)
                if task_id:
                    self._update_song_status(task_id, song_id,
                        status='done',
                        file_size=actual_size,
                        completed_at=time.time(),
                    )

                # ★ 标记成功的源：让后续 10 分钟内同平台歌曲优先用这个源
                api_source = song_info.get('api_source', {}) if song_info else {}
                if isinstance(api_source, dict):
                    url_source = api_source.get('url')
                    if url_source and source:
                        music_client.mark_source_success(source, url_source)

                return {
                    'tmp_path': tmp_path,
                    'arcname': arcname,
                    'lrc_content': None,
                    'name': name,
                }
            except Exception as e:
                last_error = e
                # ★ 4xx 永久错误：标记 api_source 为坏源，让重试自动换源
                # 场景：vkeys_url 返的 URL → 403 → mark vkeys_url → 下次重试跳过
                # 配合 chain 框架的 per-rid 失败：传 song_id 让该失败只影响当前 song
                if isinstance(e, requests.exceptions.HTTPError):
                    status_code = e.response.status_code if e.response is not None else 0
                    if 400 <= status_code < 500 and status_code not in (408, 425, 429):
                        api_source = song_info.get('api_source', {}) if song_info else {}
                        if isinstance(api_source, dict):
                            url_source = api_source.get('url')
                            if url_source and source:
                                # 4xx → per-rid permanent（30min）只影响该 song 的同源
                                # 但 QQ 403 风控是全局性的（短 TTL）→ 改用 transient 5min
                                # 区分：403/451 版权风控 → 短 transient；404 资源不存在 → per-rid permanent
                                if status_code in (403, 451):
                                    music_client.mark_source_failed(
                                        source, url_source,
                                        reason=f'HTTP {status_code}: 风控/版权',
                                        expire_seconds=300,  # 5min TTL，QQ 风控通常临时
                                        scope='transient',  # 强制全局（QQ 风控对所有 song 都生效）
                                    )
                                else:
                                    # 404 等资源错误 → per-rid permanent（不影响其他 song）
                                    music_client.mark_source_failed(
                                        source, url_source,
                                        reason=f'HTTP {status_code}: {str(e)[:100]}',
                                        expire_seconds=1800,  # 30min
                                        song_id=song_id,
                                        scope='permanent',
                                    )
                # 异常分类：只重试可重试错误（网络/临时），确定性错误立即放弃
                retryable, reason = _classify_error(e, attempt, max_attempts)
                if retryable:
                    logger.info(
                        f'[{song_id}] 可重试错误 (attempt {attempt+1}/{max_attempts}): '
                        f'{type(e).__name__}: {str(e)[:100]} — {reason}'
                    )
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                # 确定性错误：清理临时文件 + 跳出循环
                logger.warning(
                    f'[{song_id}] 确定性错误（不重试）: '
                    f'{type(e).__name__}: {str(e)[:100]} — {reason}'
                )
                _safe_remove(tmp_path)
                break

        # 失败原因（最后一次错误）
        err_str = str(last_error)[:200] if last_error else 'unknown'
        logger.warning(f'批量下载: [{song_id}] 失败: {err_str}')
        # 标记 per-song 状态：失败
        if task_id:
            self._update_song_status(task_id, song_id,
                status='failed',
                error=str(last_error)[:200],
                completed_at=time.time(),
            )
        return None

    def _run_batch_task(self, task_id: str, items: list, zip_name: str, settings: dict):
        """后台批量下载任务（Phase 1 并发下载 → Phase 2 单线程打包）

        支持取消：通过 task['cancelled'] = True 触发
        """
        with self._lock:
            task = self._tasks.get(task_id)
        if not task:
            return

        # Phase 1: 并发下载
        completed_results: list[dict] = []
        failed_items: list[dict] = []

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            future_to_item = {executor.submit(self._process_song, item, settings, task_id): item for item in items}
            for future in as_completed(future_to_item):
                # 检查是否被取消
                with self._lock:
                    if task.get('cancelled'):
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                item = future_to_item[future]
                try:
                    result = future.result()
                    if result:
                        completed_results.append(result)
                    else:
                        failed_items.append({
                            'id': item.get('id'),
                            'name': item.get('name', ''),
                            'reason': '无法获取下载链接（可能因版权问题）'
                        })
                except Exception as e:
                    failed_items.append({
                        'id': item.get('id'),
                        'name': item.get('name', ''),
                        'reason': str(e)
                    })

                with self._lock:
                    if task.get('cancelled'):
                        break
                    task['completed'] = len(completed_results)
                    task['failed'] = len(failed_items)
                    task['current'] = item.get('name', '')

        # 检查是否被取消
        with self._lock:
            if task.get('cancelled'):
                task['status'] = 'cancelled'
                for r in completed_results:
                    _safe_remove(r.get('tmp_path', ''))
                return

        # Phase 2: 单曲直接保留，多首打包 zip
        try:
            if len(completed_results) == 1:
                result = completed_results[0]
                final_path = result['tmp_path']
                final_name = result['arcname']
                with self._lock:
                    task['status'] = 'done'
                    task['zip_path'] = final_path
                    task['zip_name'] = final_name
                    task['single_file'] = True
                    task['errors'] = failed_items
                    task['completed_at'] = time.time()
            else:
                fd, zip_path = tempfile.mkstemp(suffix='.zip', prefix='wan-music-batch-')
                os.close(fd)

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                    for result in completed_results:
                        zf.write(result['tmp_path'], result['arcname'])

                with self._lock:
                    task['status'] = 'done'
                    task['zip_path'] = zip_path
                    task['errors'] = failed_items
                    task['completed_at'] = time.time()

            # 启动延迟清理（TASK_TTL 秒未下载则清理）
            def _cleanup_task():
                with self._lock:
                    t = self._tasks.pop(task_id, None)
                if t:
                    _safe_remove(t.get('zip_path', ''))

            timer = threading.Timer(self.TASK_TTL, _cleanup_task)
            timer.daemon = True
            timer.start()
        except Exception as e:
            _safe_remove(zip_path)
            for r in completed_results:
                _safe_remove(r['tmp_path'])
            with self._lock:
                task['status'] = 'error'
                task['error'] = str(e)


batch_download_service = BatchDownloadService()
