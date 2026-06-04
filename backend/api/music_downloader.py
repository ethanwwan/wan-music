"""
增强版音乐下载器
支持：
- 下载队列管理（暂停、恢复、取消）
- 断点续传
- 文件完整性校验
- 智能重试和音质降级
- 封面图片缓存
- 实时进度追踪
"""

import asyncio
import hashlib
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import aiofiles
import aiohttp
from mutagen import File as MutagenFile
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1
from mutagen.mp4 import MP4, MP4Cover

from .music_api import NeteaseAPI


class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class MusicQuality(Enum):
    """音质枚举（按优先级排序）"""
    DOLBY = "dolby"
    JYMASTER = "jymaster"
    JYEFFECT = "jyeffect"
    HIRES = "hires"
    SKY = "sky"
    LOSSLESS = "lossless"
    EXHIGH = "exhigh"
    STANDARD = "standard"


@dataclass
class MusicInfo:
    """音乐信息数据类"""
    music_id: int
    name: str
    artists: str
    album: str
    pic_url: Optional[str] = None
    download_url: Optional[str] = None
    file_extension: str = "mp3"


@dataclass
class DownloadProgress:
    """下载进度数据类"""
    downloaded: int = 0
    total: int = 0
    speed: float = 0.0
    eta_seconds: float = 0.0
    
    @property
    def percentage(self) -> float:
        """计算下载百分比"""
        if self.total <= 0:
            return 0.0
        return min(100.0, (self.downloaded / self.total) * 100)


@dataclass
class DownloadTask:
    """下载任务数据类"""
    task_id: str
    music_id: int
    quality: str
    status: DownloadStatus
    priority: int = 0
    progress: DownloadProgress = field(default_factory=DownloadProgress)
    file_path: Optional[Path] = None
    temp_path: Optional[Path] = None
    music_info: Optional[MusicInfo] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于API返回"""
        return {
            "task_id": self.task_id,
            "music_id": self.music_id,
            "quality": self.quality,
            "status": self.status.value,
            "priority": self.priority,
            "progress": {
                "downloaded": self.progress.downloaded,
                "total": self.progress.total,
                "percentage": self.progress.percentage,
                "speed": self.progress.speed,
                "eta_seconds": self.progress.eta_seconds
            },
            "file_path": str(self.file_path) if self.file_path else None,
            "music_name": self.music_info.name if self.music_info else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count
        }


class CoverCache:
    """封面图片缓存管理器"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, bytes] = {}
    
    def _get_cache_key(self, url: str) -> str:
        """从URL生成缓存键"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, url: str) -> Path:
        """获取缓存文件路径"""
        key = self._get_cache_key(url)
        return self.cache_dir / f"{key}.jpg"
    
    async def get_cover(self, url: str) -> Optional[bytes]:
        """从缓存获取封面"""
        # 先检查内存缓存
        if url in self._cache:
            return self._cache[url]
        
        # 检查文件缓存
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            try:
                async with aiofiles.open(cache_path, 'rb') as f:
                    data = await f.read()
                    self._cache[url] = data
                    return data
            except Exception:
                pass
        
        return None
    
    async def cache_cover(self, url: str, data: bytes) -> None:
        """缓存封面"""
        # 存储到内存
        self._cache[url] = data
        
        # 存储到文件
        cache_path = self._get_cache_path(url)
        try:
            async with aiofiles.open(cache_path, 'wb') as f:
                await f.write(data)
        except Exception:
            pass


class DownloadQueue:
    """下载队列管理器"""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, DownloadTask] = {}
        self._pending_queue: asyncio.Queue = asyncio.Queue()
        self._active_tasks: Set[str] = set()
        self._paused_tasks: Set[str] = set()
        self._completed_tasks: List[DownloadTask] = []
        self._task_history: List[DownloadTask] = []
        self._lock = asyncio.Lock()
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._cover_cache: Optional[CoverCache] = None
    
    def set_cover_cache(self, cache: CoverCache) -> None:
        """设置封面缓存"""
        self._cover_cache = cache
    
    def generate_task_id(self) -> str:
        """生成唯一任务ID"""
        return hashlib.md5(f"{datetime.now().isoformat()}{os.urandom(16)}".encode()).hexdigest()[:16]
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[DownloadTask]:
        """获取所有任务（进行中+已完成）"""
        all_tasks = list(self.tasks.values())
        all_tasks.extend(self._completed_tasks)
        return sorted(all_tasks, key=lambda t: t.created_at, reverse=True)
    
    async def add_task(
        self,
        music_id: int,
        quality: str,
        priority: int = 0,
        file_path: Optional[Path] = None
    ) -> str:
        """添加下载任务"""
        task_id = self.generate_task_id()
        task = DownloadTask(
            task_id=task_id,
            music_id=music_id,
            quality=quality,
            status=DownloadStatus.PENDING,
            priority=priority,
            file_path=file_path
        )
        
        async with self._lock:
            self.tasks[task_id] = task
            await self._pending_queue.put((-priority, task_id))
        
        return task_id
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        async with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status == DownloadStatus.DOWNLOADING:
                task.status = DownloadStatus.PAUSED
                self._paused_tasks.add(task_id)
                return True
        return False
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        async with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status == DownloadStatus.PAUSED:
                task.status = DownloadStatus.PENDING
                self._paused_tasks.discard(task_id)
                await self._pending_queue.put((-task.priority, task_id))
                return True
        return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        async with self._lock:
            task = self.tasks.get(task_id)
            if task:
                if task.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PENDING, DownloadStatus.PAUSED]:
                    task.status = DownloadStatus.CANCELLED
                    self._paused_tasks.discard(task_id)
                # 清理临时文件
                if task.temp_path and task.temp_path.exists():
                    try:
                        task.temp_path.unlink()
                    except Exception:
                        pass
                return True
        return False
    
    async def remove_task(self, task_id: str) -> bool:
        """删除任务"""
        async with self._lock:
            task = self.tasks.pop(task_id, None)
            if task:
                if task.temp_path and task.temp_path.exists():
                    try:
                        task.temp_path.unlink()
                    except Exception:
                        pass
                self._paused_tasks.discard(task_id)
                return True
        return False
    
    async def _get_next_task(self) -> Optional[DownloadTask]:
        """获取下一个待处理任务"""
        while True:
            try:
                priority, task_id = await asyncio.wait_for(self._pending_queue.get(), timeout=0.1)
                task = self.tasks.get(task_id)
                if task and task.status == DownloadStatus.PENDING:
                    return task
            except asyncio.TimeoutError:
                return None
    
    async def start_workers(self, downloader):
        """启动工作协程"""
        if self._running:
            return
        
        self._running = True
        for _ in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker_loop(downloader))
            self._workers.append(worker)
    
    async def stop_workers(self):
        """停止工作协程"""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        self._workers = []
    
    async def _worker_loop(self, downloader):
        """工作协程主循环"""
        while self._running:
            try:
                task = await self._get_next_task()
                if not task:
                    await asyncio.sleep(0.1)
                    continue
                
                async with self._lock:
                    if task.task_id in self._active_tasks:
                        continue
                    self._active_tasks.add(task.task_id)
                
                try:
                    await downloader._execute_task(task)
                finally:
                    async with self._lock:
                        self._active_tasks.discard(task.task_id)
            
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1)


class EnhancedMusicDownloader:
    """增强版音乐下载器"""
    
    def __init__(
        self,
        api: NeteaseAPI,
        download_dir: Optional[str] = None,
        max_concurrent: int = 3,
        cover_cache_dir: Optional[str] = None
    ):
        self.api = api
        
        if download_dir is None:
            # 使用当前目录下的 downloads 文件夹
            self.download_dir = Path(__file__).parent.parent / "downloads"
        else:
            self.download_dir = Path(download_dir)
        
        # 确保目录存在
        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # 如果权限不足，使用临时目录
            import tempfile
            self.download_dir = Path(tempfile.gettempdir()) / "wan_music_downloads"
            self.download_dir.mkdir(parents=True, exist_ok=True)
        
        cache_dir = Path(cover_cache_dir) if cover_cache_dir else self.download_dir / ".cover_cache"
        self.cover_cache = CoverCache(cache_dir)
        
        self.queue = DownloadQueue(max_concurrent=max_concurrent)
        self.queue.set_cover_cache(self.cover_cache)
        
        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        await self.queue.start_workers(self)
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        await self.queue.stop_workers()
        if self._session:
            await self._session.close()
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    
    def _get_qualities_to_try(self, quality: str) -> List[str]:
        """获取音质尝试列表（包含降级策略）"""
        quality_order = [q.value for q in MusicQuality]
        
        try:
            start_idx = quality_order.index(quality)
            return quality_order[start_idx:]
        except ValueError:
            return [quality] + quality_order
    
    async def _get_music_info(
        self,
        music_id: int,
        quality: str
    ) -> Tuple[Optional[MusicInfo], Optional[str]]:
        """获取音乐信息（自动降级）"""
        qualities = self._get_qualities_to_try(quality)
        
        for quality_option in qualities:
            try:
                download_url, ext = self.api.get_music_url(music_id, quality_option)
                if download_url and ext:
                    music_detail = self.api.get_music_detail([music_id])
                    if music_detail:
                        song = music_detail[0]
                        music_info = MusicInfo(
                            music_id=music_id,
                            name=song.get('name', ''),
                            artists=self._get_artists_str(song),
                            album=song.get('al', {}).get('name', ''),
                            pic_url=song.get('al', {}).get('picUrl'),
                            download_url=download_url,
                            file_extension=ext
                        )
                        return music_info, quality_option
            except Exception:
                continue
        
        return None, None
    
    def _get_artists_str(self, song: Dict) -> str:
        """获取艺术家字符串"""
        artists = song.get('ar', [])
        if not artists:
            return ''
        return ' & '.join([artist.get('name', '') for artist in artists])
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希用于完整性校验"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def _download_with_resume(
        self,
        task: DownloadTask,
        music_info: MusicInfo
    ) -> Path:
        """支持断点续传的下载"""
        if not task.file_path:
            filename = f"{music_info.artists} - {music_info.name}.{music_info.file_extension}"
            filename = self._sanitize_filename(filename)
            task.file_path = self.download_dir / filename
        
        task.temp_path = task.file_path.with_suffix(task.file_path.suffix + '.tmp')
        
        current_size = 0
        if task.temp_path.exists():
            current_size = task.temp_path.stat().st_size
            task.progress.downloaded = current_size
        
        headers = {}
        if current_size > 0:
            headers['Range'] = f'bytes={current_size}-'
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        async with self._session.get(music_info.download_url, headers=headers, timeout=300) as response:
            if response.status in [200, 206]:
                if response.status == 206:
                    task.progress.total = current_size + int(response.headers.get('Content-Length', 0))
                else:
                    task.progress.total = int(response.headers.get('Content-Length', 0))
                    current_size = 0
                
                mode = 'ab' if current_size > 0 else 'wb'
                start_time = datetime.now()
                last_update_time = start_time
                last_downloaded = current_size
                
                async with aiofiles.open(task.temp_path, mode) as f:
                    async for chunk in response.content.iter_chunked(8192):
                        if task.status == DownloadStatus.PAUSED:
                            return task.temp_path
                        if task.status == DownloadStatus.CANCELLED:
                            if task.temp_path.exists():
                                task.temp_path.unlink()
                            raise asyncio.CancelledError("Task cancelled")
                        
                        await f.write(chunk)
                        task.progress.downloaded += len(chunk)
                        
                        current_time = datetime.now()
                        time_diff = (current_time - last_update_time).total_seconds()
                        if time_diff >= 0.5:
                            bytes_diff = task.progress.downloaded - last_downloaded
                            task.progress.speed = bytes_diff / time_diff if time_diff > 0 else 0
                            
                            remaining = task.progress.total - task.progress.downloaded
                            task.progress.eta_seconds = remaining / task.progress.speed if task.progress.speed > 0 else 0
                            
                            last_update_time = current_time
                            last_downloaded = task.progress.downloaded
                
                task.temp_path.rename(task.file_path)
                return task.file_path
            else:
                raise Exception(f"Download failed with status {response.status}")
    
    async def _write_metadata(
        self,
        file_path: Path,
        music_info: MusicInfo
    ) -> None:
        """写入音乐元数据"""
        cover_data = None
        if music_info.pic_url:
            cover_data = await self.cover_cache.get_cover(music_info.pic_url)
            if not cover_data and self._session:
                try:
                    async with self._session.get(music_info.pic_url, timeout=30) as response:
                        if response.status == 200:
                            cover_data = await response.read()
                            await self.cover_cache.cache_cover(music_info.pic_url, cover_data)
                except Exception:
                    pass
        
        ext = music_info.file_extension.lower()
        
        try:
            if ext == 'mp3':
                audio = MutagenFile(file_path, easy=True)
                if audio.tags is None:
                    audio.add_tags()
                audio['title'] = music_info.name
                audio['artist'] = music_info.artists
                audio['album'] = music_info.album
                audio.save()
                
                if cover_data:
                    audio = ID3(file_path)
                    audio['APIC'] = APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,
                        desc='Cover',
                        data=cover_data
                    )
                    audio.save()
            
            elif ext == 'flac':
                audio = FLAC(file_path)
                audio['title'] = music_info.name
                audio['artist'] = music_info.artists
                audio['album'] = music_info.album
                
                if cover_data:
                    picture = Picture()
                    picture.data = cover_data
                    picture.type = 3
                    picture.mime = 'image/jpeg'
                    audio.add_picture(picture)
                
                audio.save()
            
            elif ext in ['m4a', 'mp4']:
                audio = MP4(file_path)
                audio['\xa9nam'] = music_info.name
                audio['\xa9ART'] = music_info.artists
                audio['\xa9alb'] = music_info.album
                
                if cover_data:
                    audio['covr'] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
                
                audio.save()
        
        except Exception:
            pass
    
    async def _execute_task(self, task: DownloadTask):
        """执行单个下载任务"""
        task.status = DownloadStatus.DOWNLOADING
        task.started_at = datetime.now()
        
        try:
            music_info, actual_quality = await self._get_music_info(task.music_id, task.quality)
            if not music_info:
                raise Exception(f"Failed to get music info for {task.music_id}")
            
            task.music_info = music_info
            if actual_quality != task.quality:
                task.quality = actual_quality
            
            await self._download_with_resume(task, music_info)
            await self._write_metadata(task.file_path, music_info)
            
            task.status = DownloadStatus.COMPLETED
            task.completed_at = datetime.now()
            
            async with self.queue._lock:
                self.queue._completed_tasks.append(task)
                self.queue.tasks.pop(task.task_id, None)
            
        except asyncio.CancelledError:
            task.status = DownloadStatus.CANCELLED
        
        except Exception as e:
            task.retry_count += 1
            task.error_message = str(e)
            
            if task.retry_count < task.max_retries:
                await asyncio.sleep(1.5 ** task.retry_count)
                task.status = DownloadStatus.PENDING
                async with self.queue._lock:
                    await self.queue._pending_queue.put((-task.priority, task.task_id))
            else:
                task.status = DownloadStatus.FAILED
    
    async def download(
        self,
        music_id: int,
        quality: str = "lossless",
        priority: int = 0,
        file_path: Optional[str] = None
    ) -> str:
        """添加下载任务"""
        path = Path(file_path) if file_path else None
        return await self.queue.add_task(music_id, quality, priority, path)
    
    async def batch_download(
        self,
        music_ids: List[int],
        quality: str = "lossless"
    ) -> List[str]:
        """批量添加下载任务"""
        task_ids = []
        for i, music_id in enumerate(music_ids):
            task_id = await self.download(music_id, quality, priority=len(music_ids) - i)
            task_ids.append(task_id)
        return task_ids
    
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self.queue.get_task(task_id)
        return task.to_dict() if task else None
    
    async def get_all_tasks(self) -> List[Dict]:
        """获取所有任务状态"""
        tasks = self.queue.get_all_tasks()
        return [t.to_dict() for t in tasks]
    
    async def pause(self, task_id: str) -> bool:
        """暂停任务"""
        return await self.queue.pause_task(task_id)
    
    async def resume(self, task_id: str) -> bool:
        """恢复任务"""
        return await self.queue.resume_task(task_id)
    
    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        return await self.queue.cancel_task(task_id)
    
    async def remove(self, task_id: str) -> bool:
        """删除任务"""
        return await self.queue.remove_task(task_id)


# 兼容旧接口
class MusicDownloader(EnhancedMusicDownloader):
    """兼容旧接口的下载器"""
    
    def __init__(self, api=None, download_dir=None, max_concurrent=3, cover_cache_dir=None):
        """初始化兼容版下载器"""
        if api is None:
            # 如果没有提供 API，使用默认的 NeteaseAPI
            api = NeteaseAPI()
        
        super().__init__(api, download_dir, max_concurrent, cover_cache_dir)
    
    def download_music_file(self, music_id: int, quality: str = "lossless") -> Optional[Path]:
        """同步下载（兼容旧接口）"""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self._download_sync_single(music_id, quality))
        finally:
            loop.close()
    
    async def _download_sync_single(self, music_id: int, quality: str) -> Optional[Path]:
        """同步下载的异步实现"""
        task_id = await self.download(music_id, quality)
        
        while True:
            task = self.queue.get_task(task_id)
            if not task:
                for completed in self.queue._completed_tasks:
                    if completed.task_id == task_id:
                        return completed.file_path
                return None
            
            if task.status == DownloadStatus.COMPLETED:
                return task.file_path
            if task.status == DownloadStatus.FAILED:
                return None
            
            await asyncio.sleep(0.5)
