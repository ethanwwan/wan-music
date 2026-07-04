"""JBSou (jbsou.cn) 跨平台 API 共享模块

JBSou 是一个统一的第三方音乐 API，支持 netease/qq/kugou/kuwo 四个平台。
一次 POST 请求即可返回歌曲名称/歌手/封面/URL/歌词。

平台代号映射：
  netease → 'wy'
  qq      → 'qq'
  kugou   → 'kg'
  kuwo    → 'kw'

API 端点：
  - 搜索：POST https://www.jbsou.cn/ → form {input, filter, type, page}
          返回: {"data": [{name, artist, album, songid, url, lrc, cover}]}
  - URL：search result 的 url 字段（相对路径）→ GET 后 302 跳转到真实音频 URL
  - 歌词：search result 的 lrc 字段（相对路径）→ GET 返回含 <script> 的 HTML

来源：musicdl-master musicdl/modules/common/jbsou.py
"""
import re
import requests
from urllib.parse import urljoin


JBSOU_BASE = 'https://www.jbsou.cn/'

JBSOU_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'Origin': 'https://www.jbsou.cn',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://www.jbsou.cn/',
}

# JBSou 平台代号（musicdl 直接用全名）
JBSOU_PLATFORM_CODE = {
    'netease': 'netease',
    'qq': 'qq',
    'kugou': 'kugou',
    'kuwo': 'kuwo',
}


# ==================== 通用歌词清理 ====================

# musicdl cleanlrc 逻辑：
#   1. 统一换行符 \r\n → \n
#   2. 去除 BOM/零宽字符/首尾空白
#   3. 去掉纯时间戳行 [mm:ss.xxx] / [mm:ss]
#   4. 去掉空行
_CLEANLRC_RE = re.compile(r'^\[(?:\d{2}:)?\d{2}:\d{2}(?:\.\d{1,3})?\]$')


def cleanlrc(text: str) -> str:
    """清理歌词文本（musicdl cleanlrc 移植）"""
    lines = []
    for raw in re.sub(r'\r\n?', '\n', str(text)).split('\n'):
        line = raw.strip('\ufeff\u200b\u200c\u200d\u2060\u00a0 \t').strip()
        if line and not _CLEANLRC_RE.match(line):
            lines.append(line)
    return '\n'.join(lines)


def _strip_html(text: str) -> str:
    """去除 HTML/script 标签（JBSou 歌词响应含追踪脚本）"""
    # 去 <script>...</script>
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # 去其他 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ==================== 搜索结果提取器 ====================

def jbsou_extract_search(platform: str) -> callable:
    """创建 JBSou 搜索结果提取器（按平台返回各 normalizer 期望的字段名）

    JBSou 返回格式统一：{name, artist, album, songid, url, lrc, cover}
    各平台的 normalizer 期望不同字段名，这里做映射。
    """
    # 净版结果，与现有 normalizer 兼容
    field_maps = {
        'netease': lambda item: {
            'id': item.get('songid', ''),
            'name': item.get('name', ''),
            'artist': item.get('artist', ''),
            'album': item.get('album', ''),
            'picUrl': urljoin(JBSOU_BASE, item.get('cover', '')) if item.get('cover') else '',
        },
        'qq': lambda item: {
            'songmid': item.get('songid', ''),
            'songname': item.get('name', ''),
            'singer': item.get('artist', ''),
            'albumname': item.get('album', ''),
            'picUrl': urljoin(JBSOU_BASE, item.get('cover', '')) if item.get('cover') else '',
        },
        'kugou': lambda item: {
            'hash': item.get('songid', ''),
            'SongName': item.get('name', ''),
            'SingerName': item.get('artist', ''),
            'AlbumName': item.get('album', ''),
            'Image': urljoin(JBSOU_BASE, item.get('cover', '')) if item.get('cover') else '',
        },
        'kuwo': lambda item: {
            'rid': item.get('songid', ''),
            'name': item.get('name', ''),
            'artist': item.get('artist', ''),
            'album': item.get('album', ''),
            'picUrl': urljoin(JBSOU_BASE, item.get('cover', '')) if item.get('cover') else '',
        },
    }
    mapper = field_maps.get(platform, field_maps['netease'])

    def extract(d: dict) -> list:
        if not isinstance(d, dict):
            return []
        data = d.get('data', [])
        if not isinstance(data, list):
            return []
        results = []
        for item in data:
            if not isinstance(item, dict) or not item.get('name'):
                continue
            results.append(mapper(item))
        return results

    return extract


# ==================== URL 提取器 ====================

def jbsou_extract_url(d: dict) -> str:
    """从 JBSou search-by-id 响应提取音频 URL

    流程：
      1. 解析响应 JSON，取 data[0].url（相对路径如 api.php?get=url&...）
      2. 拼接为完整 URL
      3. chain 随后会用 HEAD 验证并跟随 302 跳转到真实音频地址
    """
    if not isinstance(d, dict):
        return ''
    data = d.get('data')
    if isinstance(data, list) and data and isinstance(data[0], dict):
        url_path = data[0].get('url', '')
        if url_path:
            return urljoin(JBSOU_BASE, url_path)
    return ''


# ==================== 歌词提取器 ====================

def jbsou_extract_lyric(d: dict) -> str:
    """从 JBSou search-by-id 响应提取歌词

    需要额外 HTTP 请求获取 lrc 字段指向的 URL 内容。
    """
    if not isinstance(d, dict):
        return ''
    data = d.get('data')
    if isinstance(data, list) and data and isinstance(data[0], dict):
        lrc_path = data[0].get('lrc', '')
        if not lrc_path:
            return ''
        lrc_url = urljoin(JBSOU_BASE, lrc_path)
        try:
            r = requests.get(lrc_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }, timeout=10)
            r.raise_for_status()
            raw = r.text
            # JBSou 的歌词响应含 <script> 追踪代码，剥离后 cleanlrc
            cleaned = _strip_html(raw)
            return cleanlrc(cleaned)
        except Exception:
            return ''
    return ''
