"""ApiSource 数据类：声明式地描述一个第三方 API 端点

每个 ApiSource 封装一个第三方 API 的：
  - 端点信息（URL 模板、method、headers、timeout）
  - 能力声明（能否 search/parse_url/parse_info/parse_lyric）
  - 提取器（从响应中提取 search 结果 / url / info / lyric）

使用示例：
    ApiSource(
        name='xuanluoge',
        platform='netease',
        method='GET',
        can_parse_url=True,
        can_parse_info=True,
        parse_url_url='http://118.24.104.108:3456/api.php?miss=getMusicUrl&id={song_id}&level={quality}',
        parse_info_url='http://118.24.104.108:3456/api.php?miss=getMusicInfo&id={song_id}',
        extract_url=extract_xuanluoge_url,
        extract_info=extract_xuanluoge_song_info,
        timeout=10,
    )
"""
from dataclasses import dataclass, field
from typing import Callable, Optional, Any


@dataclass
class ApiSource:
    """声明一个第三方 API 源

    Attributes:
        name: 源的简短标识（如 'xuanluoge'、'gdstudio'），用于日志和 api_source 字段
        platform: 所属平台（'netease' | 'qq' | 'kugou' | 'kuwo' | 'common'）
        enabled: 是否启用（动态开关）
        priority: 数字越小优先级越高（0 最高）。用于同能力源排序
        description: 备注（如「musicdl 验证可用」「需要 ckey」）

        # 能力开关（每个源可同时具备多种能力）
        can_search: 能否进行搜索
        can_parse_url: 能否获取歌曲下载 URL
        can_parse_info: 能否获取歌曲元信息
        can_parse_lyric: 能否获取歌词

        # URL 模板（支持 {keyword}、{song_id}、{quality}、{limit}、{rid}、{hash} 等占位符）
        search_url: 搜索端点 URL
        parse_url_url: 获取下载 URL 端点
        parse_info_url: 获取歌曲元信息端点
        parse_lyric_url: 获取歌词端点

        # 提取器（从 JSON 响应中提取数据）
        extract_search: 搜索结果提取器 (dict) -> list[dict]
        extract_url: URL 提取器 (dict) -> str
        extract_info: 歌曲信息提取器 (dict) -> dict
        extract_lyric: 歌词提取器 (dict) -> str

        # HTTP 配置
        method: HTTP 方法（'GET' / 'POST'）
        headers: 自定义 headers
        timeout: 超时秒数
        # POST 数据模板（占位符会被填充）
        post_data: dict (for POST)
        # POST 数据是否需要 json 编码（True: json.dumps；False: form-urlencoded）
        is_json: bool

        # Cookie
        needs_cookie: 是否需要 cookie（netease 官方需要）
        cookie_file: cookie 文件路径（netease: netease_cookie.txt）

        # 高级：有状态请求准备器
        # 对于需要动态生成 devid、签名、token 等场景
        # 签名: Callable[(url, method, headers, post_data, kwargs), dict]
        # 返回: {'url', 'method', 'headers', 'post_data', 'is_json'}
        prepare_request: Optional[Callable[..., dict]] = None
    """
    name: str
    platform: str
    enabled: bool = True
    priority: int = 100
    description: str = ''

    # 能力
    can_search: bool = False
    can_parse_url: bool = False
    can_parse_info: bool = False
    can_parse_lyric: bool = False
    can_parse_playlist: bool = False

    # URL 模板（支持 {keyword}、{song_id}、{quality}、{limit}、{rid}、{hash}、{playlist_id}、{page}、{size} 等占位符）
    search_url: str = ''
    parse_url_url: str = ''
    parse_info_url: str = ''
    parse_lyric_url: str = ''
    parse_playlist_url: str = ''

    # 提取器（从 JSON 响应中提取数据）
    extract_search: Optional[Callable[[dict], list]] = None
    extract_url: Optional[Callable[[dict], str]] = None
    extract_info: Optional[Callable[[dict], dict]] = None
    extract_lyric: Optional[Callable[[dict], str]] = None
    extract_playlist: Optional[Callable[[dict], dict]] = None  # 返回 {'name','creator','cover','trackCount','tracks':[...]}


    # HTTP
    method: str = 'GET'
    headers: dict = field(default_factory=dict)
    timeout: int = 10
    post_data: dict = field(default_factory=dict)
    is_json: bool = False

    # Cookie
    needs_cookie: bool = False
    cookie_file: str = ''

    # 高级：有状态请求准备器
    # 签名: (url, method, headers, post_data, kwargs) -> dict
    prepare_request: Optional[Callable[..., dict]] = None

    # 内部统计（运行期填充）
    _stats: dict = field(default_factory=lambda: {'ok': 0, 'fail': 0, 'last_error': '', 'last_used': 0, 'total_ms': 0})

    def supports(self, op: str) -> bool:
        """检查是否支持某操作：'search' | 'parse_url' | 'parse_info' | 'parse_lyric' | 'parse_playlist'"""
        flag = {
            'search': self.can_search,
            'parse_url': self.can_parse_url,
            'parse_info': self.can_parse_info,
            'parse_lyric': self.can_parse_lyric,
            'parse_playlist': self.can_parse_playlist,
        }.get(op, False)
        return self.enabled and flag

    def get_url(self, op: str) -> str:
        """获取某操作对应的 URL 模板"""
        return {
            'search': self.search_url,
            'parse_url': self.parse_url_url,
            'parse_info': self.parse_info_url,
            'parse_lyric': self.parse_lyric_url,
            'parse_playlist': self.parse_playlist_url,
        }.get(op, '')

    def get_extractor(self, op: str):
        """获取某操作对应的提取器"""
        return {
            'search': self.extract_search,
            'parse_url': self.extract_url,
            'parse_info': self.extract_info,
            'parse_lyric': self.extract_lyric,
            'parse_playlist': self.extract_playlist,
        }.get(op)

    def to_dict(self) -> dict:
        """导出为可序列化的 dict（用于保存到配置文件）"""
        return {
            'name': self.name,
            'platform': self.platform,
            'enabled': self.enabled,
            'priority': self.priority,
            'description': self.description,
            'can_search': self.can_search,
            'can_parse_url': self.can_parse_url,
            'can_parse_info': self.can_parse_info,
            'can_parse_lyric': self.can_parse_lyric,
            'search_url': self.search_url,
            'parse_url_url': self.parse_url_url,
            'parse_info_url': self.parse_info_url,
            'parse_lyric_url': self.parse_lyric_url,
            'method': self.method,
            'timeout': self.timeout,
            'post_data': self.post_data,
            'is_json': self.is_json,
            'needs_cookie': self.needs_cookie,
        }
