"""业务服务层

- MusicService: 搜索 / 歌曲 / 歌单（路由层直接调用的 3 个方法）
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
from typing import Dict, List, Any

import requests

from clients.music_client import music_client, search_music, get_song_url, get_song_detail, get_lyric, get_playlist_detail
from clients.quality_config import QualityLevel
from utils.url_parser import parse_url
from utils.filename import (
    sanitize_filename as _sanitize_filename,
    build_filename as _build_filename,
)
from utils.audio_utils import (
    get_extension as _get_extension,
    detect_audio_type as _detect_audio_type,
    safe_remove as _safe_remove,
)
from utils.metadata import write_metadata as _write_metadata

logger = logging.getLogger(__name__)


# ==================== Music Service ====================

class MusicService:
    """音乐业务服务 - 3 个公开方法供路由调用"""

    # ==================== 公开 API（路由直接调用） ====================

    def search(self, keyword: str, search_type: int = 0, platform: str = None,
               limit: int = 50, quality: str = 'lossless') -> Dict[str, Any]:
        """
        统一搜索方法
        1. keyword 是 URL → 解析详情
        2. 否则按 search_type 搜索

        返回：{'type': 0/1/2, 'data': [...], 'warnings': [...]}
        """
        parsed = parse_url(keyword)
        if parsed:
            return self._search_by_url(parsed)
        return self._search_by_keyword(keyword, search_type, platform, limit, quality)

    def get_song_info(self, song_id: str, quality: str = 'lossless', platform: str = None) -> Dict[str, Any]:
        """
        获取完整歌曲信息（基本信息 + 播放 URL + 歌词）

        播放和下载都走这个接口。返回空 dict 表示歌曲不可用。
        """
        try:
            song_info = get_song_detail(song_id, platform)
            if not song_info or not song_info.get('id'):
                return {}

            # 校验音质（无效时回退到 lossless）
            valid_qualities = [q.value for q in QualityLevel]
            if quality not in valid_qualities:
                quality = 'lossless'

            url_info = get_song_url(song_id, quality, platform)
            url_data = url_info.get('data', [{}])[0] if isinstance(url_info, dict) else {}

            lyric_raw = get_lyric(song_id, platform)
            lyric = lyric_raw.get('lyric', '') if isinstance(lyric_raw, dict) else lyric_raw

            return {
                'id': str(song_info.get('id', song_id)),
                'name': song_info.get('name', ''),
                'artists': song_info.get('artists', ''),
                'album': song_info.get('album', ''),
                'picUrl': song_info.get('picUrl', ''),
                'duration': song_info.get('duration', 0),
                'url': url_data.get('url', ''),
                'quality': quality,
                'lyric': lyric,
                'source': url_data.get('source', 'netease')
                # 不返回 fileType：后端用 magic bytes 检测真实类型
            }
        except Exception as e:
            logger.error(f"获取歌曲信息失败: {e}")
            return {}

    def get_playlist_detail(self, playlist_id: str, platform: str = None) -> Dict[str, Any]:
        """获取歌单详情"""
        try:
            return get_playlist_detail(playlist_id, platform)
        except Exception as e:
            logger.error(f"获取歌单详情失败: {e}")
            return {}

    def get_platforms(self) -> List[Dict[str, str]]:
        """获取可用平台列表（前端从 /platforms 接口读取，避免硬编码）"""
        try:
            return music_client.get_platforms()
        except Exception as e:
            logger.error(f"获取平台列表失败: {e}")
            return []

    # ==================== 私有方法（仅服务内部使用） ====================

    def _search_by_url(self, parsed: Dict[str, str]) -> Dict[str, Any]:
        """URL 解析后获取详情"""
        resource_type = parsed['type']
        resource_id = parsed['id']
        source_platform = parsed['platform']

        if resource_type == 'music':
            song_info = self.get_song_info(resource_id, 'lossless', source_platform)
            if song_info and song_info.get('id'):
                song_info['_type'] = 'song'
                return {'type': 1, 'data': [song_info], 'warnings': []}
            return {'type': 1, 'data': [], 'error': '未找到歌曲信息', 'warnings': []}

        if resource_type == 'playlist':
            playlist_info = self.get_playlist_detail(resource_id, source_platform)
            if playlist_info and playlist_info.get('id'):
                playlist_info['_type'] = 'playlist'
                return {'type': 2, 'data': [playlist_info], 'warnings': []}
            return {'type': 2, 'data': [], 'error': '未找到歌单信息', 'warnings': []}

        return {'type': 0, 'data': [], 'error': f'暂不支持解析{resource_type}类型', 'warnings': []}

    def _search_by_keyword(self, keyword: str, search_type: int, platform: str, limit: int, quality: str = 'lossless') -> Dict[str, Any]:
        """关键字搜索

        错误处理策略：
        - 单平台失败：放进 warnings['platform_errors']，不阻断（多平台降级）
        - 全部平台都失败且无数据：返回 error 字段
        """
        items = []
        warnings = []
        platform_errors = []  # 各平台错误详情

        if search_type in (0, 1):
            try:
                songs = search_music(keyword, platform, limit, quality=quality)
                for s in songs:
                    s['_type'] = 'song'
                items.extend(songs)
            except Exception as e:
                msg = f"歌曲搜索失败: {e}"
                logger.error(f"[{platform}] {msg}")
                platform_errors.append({'platform': platform, 'type': 'song', 'message': str(e)})

        if search_type in (0, 2):
            try:
                playlists = music_client.search_playlist(keyword, platform, limit)
                for p in playlists:
                    p['_type'] = 'playlist'
                items.extend(playlists)
            except Exception as e:
                msg = f"歌单搜索失败: {e}"
                logger.error(f"[{platform}] {msg}")
                platform_errors.append({'platform': platform, 'type': 'playlist', 'message': str(e)})

            # 标记歌单搜索不支持的平台（用于前端 UI 提示）
            if platform in ('kugou', 'bodian'):
                warnings.append('playlist_search_unsupported')

        # 把平台错误透传给前端
        if platform_errors:
            warnings.append({'code': 'platform_errors', 'details': platform_errors})

        # 判断是否"全部平台都失败"（有错误但一条结果都没拿到）
        if platform_errors and not items:
            error_msg = '; '.join(
                f"{e['platform']}: {e['message']}" for e in platform_errors
            )
            return {
                'type': search_type,
                'data': [],
                'warnings': warnings,
                'error': f'所有平台搜索均失败 ({error_msg})'
            }

        return {'type': search_type, 'data': items, 'warnings': warnings}


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
        # 任务存储（task_id -> 任务状态）
        # 单进程 Flask 足够用，多进程部署需改为 Redis/DB
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

        estimated_file_size = self._estimate_size(items)
        task_id = f"task_{uuid.uuid4().hex[:16]}"

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
                'file_size': estimated_file_size,
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
            'file_size': estimated_file_size,
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
    def _estimate_size(items: list) -> int:
        """从 qualityMap 估算总文件大小"""
        total = 0
        for item in items:
            qm = item.get('qualityMap') or {}
            quality = item.get('quality', 'lossless')
            if quality in qm:
                total += qm[quality].get('size', 0)
        return total

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
        }

    def _process_song(self, item: dict, settings: dict):
        """处理单首歌曲：下载音频 + 写 metadata + 返回结果

        settings: {writeMetadata, filenameFormat}
        返回：{'tmp_path', 'arcname', 'lrc_content', 'name'} 或 None
        """
        song_id = item.get('id')
        if not song_id:
            return None

        quality = item.get('quality', 'lossless')
        source = item.get('source', '').strip() or None
        name = item.get('name', 'song')
        artist = item.get('artist', '')
        album = item.get('album', '')

        last_error = None
        for attempt in range(3):
            try:
                song_info = music_service.get_song_info(song_id, quality, source)
                url = song_info.get('url')
                if not url:
                    return None

                extension = _get_extension(url, fallback=song_info.get('fileType', 'mp3'))
                if not extension.startswith('.'):
                    extension = '.' + extension

                fd, tmp_path = tempfile.mkstemp(suffix=extension, prefix='wan-music-batch-')
                os.close(fd)

                try:
                    resp = requests.get(url, stream=True, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
                    resp.raise_for_status()
                    with open(tmp_path, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                except Exception as e:
                    _safe_remove(tmp_path)
                    raise e

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

                return {
                    'tmp_path': tmp_path,
                    'arcname': arcname,
                    'lrc_content': None,
                    'name': name
                }
            except Exception as e:
                last_error = e
                if attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))

        logger.warning(f"批量下载: 重试 3 次仍失败 [{song_id}]: {last_error}")
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
            future_to_item = {executor.submit(self._process_song, item, settings): item for item in items}
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
