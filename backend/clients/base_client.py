"""音乐客户端抽象基类

定义所有音乐平台客户端必须实现的接口规范，提供公共方法。

参考 musicdl 的 BaseMusicClient 设计模式：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/base.py
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import requests
import logging

logger = logging.getLogger(__name__)


class BaseMusicClient(ABC):
    """音乐客户端抽象基类
    
    所有音乐平台客户端必须继承此类并实现所有抽象方法。
    提供统一的接口规范和公共工具方法。
    """
    
    def __init__(self):
        """初始化客户端"""
        self.session = requests.Session()
        self.platform_name = "base"
        self.platform_id = "base"
    
    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """统一请求封装
        
        Args:
            method: HTTP方法 (get/post/put/delete)
            url: 请求URL
            params: URL参数
            data: 请求体数据
            headers: 请求头
            timeout: 超时时间
            **kwargs: 其他参数
        
        Returns:
            JSON响应数据，失败返回空字典
        """
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                headers=headers,
                timeout=timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.platform_name}] 请求失败: {url}, 错误: {e}")
            return {}
        except ValueError:
            logger.error(f"[{self.platform_name}] 响应不是有效的JSON: {url}")
            return {}
    
    def _get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """GET请求封装"""
        return self._request('GET', url, params=params, **kwargs)
    
    def _post(self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """POST请求封装"""
        return self._request('POST', url, data=data, **kwargs)
    
    def _handle_error(self, error: Exception, context: str = "") -> None:
        """统一错误处理"""
        logger.error(f"[{self.platform_name}] {context} 错误: {error}")
    
    @abstractmethod
    def search(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量
            offset: 偏移量
        
        Returns:
            歌曲列表
        """
        pass
    
    @abstractmethod
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量
        
        Returns:
            歌单列表
        """
        pass
    
    @abstractmethod
    def get_song_url(self, song_id: Any, quality: str = 'high') -> Dict[str, Any]:
        """获取歌曲播放/下载URL
        
        Args:
            song_id: 歌曲ID
            quality: 音质 (standard/high/exhigh/lossless/hires)
        
        Returns:
            包含url的字典
        """
        pass
    
    @abstractmethod
    def get_song_info(self, song_id: Any) -> Dict[str, Any]:
        """获取歌曲信息
        
        Args:
            song_id: 歌曲ID
        
        Returns:
            歌曲信息
        """
        pass
    
    @abstractmethod
    def get_lyric(self, song_id: Any) -> str:
        """获取歌词
        
        Args:
            song_id: 歌曲ID
        
        Returns:
            歌词文本
        """
        pass
    
    @abstractmethod
    def get_playlist(self, playlist_id: Any) -> Dict[str, Any]:
        """获取歌单
        
        Args:
            playlist_id: 歌单ID
        
        Returns:
            歌单详情（包含歌曲列表）
        """
        pass
    
    def get_platform_info(self) -> Dict[str, str]:
        """获取平台信息"""
        return {
            'id': self.platform_id,
            'name': self.platform_name
        }