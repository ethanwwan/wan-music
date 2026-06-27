"""波点音乐（酷我）有状态鉴权辅助

波点官方 API（bd-api.kuwo.cn）需要：
  1. 动态 devid（每次会话生成，md5(uuid4)）
  2. devid / qimei36 请求头
  3. _signquery 签名（HMAC-MD5）

这些是有状态的（devid 在会话中保持一致），无法用纯静态 ApiSource 描述，
所以通过 prepare_request 回调注入。

参考 musicdl bodian 实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/bodian.py
"""
import hashlib
import time
import uuid
from typing import Dict, Any
from urllib.parse import urlencode


class BodianSession:
    """波点会话：保持 devid 一致性

    同一会话内 devid 保持不变，避免被服务端识别为机器人。
    """
    _instance = None

    def __init__(self):
        self.uid = '-1'
        self.token = ''
        # devid 每次启动生成一次，会话内复用
        self.dev_id = hashlib.md5(uuid.uuid4().bytes).hexdigest()

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def auth_headers(self) -> Dict[str, str]:
        """返回鉴权相关的 headers"""
        return {
            'devid': self.dev_id,
            'qimei36': self.dev_id,
        }


def _signquery(path: str, params: Dict[str, Any], body_text: str = '') -> str:
    """波点 API 签名

    算法（参考 musicdl）：
        seed = "kuwotest" + 排序后的参数字符串（仅 alnum）
        if body: seed += md5(body + "kuwotest")
        sign = md5(seed + path)
    """
    seed = 'kuwotest' + ''.join(sorted(ch for ch in urlencode(params) if ch.isalnum()))
    if body_text:
        seed += hashlib.md5(f'{body_text}kuwotest'.encode('utf-8')).hexdigest()
    return hashlib.md5(f'{seed}{path}'.encode('utf-8')).hexdigest()


def _append_query(url: str, extra_params: Dict[str, Any]) -> str:
    """给 URL 追加 query 参数"""
    if '?' in url:
        sep = '&'
    else:
        sep = '?'
    return url + sep + urlencode(extra_params)


def prepare_bodian_search(url: str, method: str, headers: dict,
                          post_data: Any, is_json: bool, kwargs: dict) -> dict:
    """波点搜索 prepare_request：加 devid/qimei36 headers + sign 参数

    适用于：/api/search/music/list
    """
    sess = BodianSession.get()
    headers = dict(headers)
    headers.update(sess.auth_headers())

    # 提取 path
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path

    # 计算 sign（追加到 url 的 query string）
    from urllib.parse import parse_qs
    existing = parse_qs(parsed.query, keep_blank_values=True)
    flat = {k: v[0] if isinstance(v, list) and v else '' for k, v in existing.items()}

    # 添加时间戳
    flat['timestamp'] = str(int(time.time() * 1000))
    flat['uid'] = sess.uid
    flat['token'] = sess.token

    sign = _signquery(path, flat)
    flat['sign'] = sign

    # 重新组装 url
    new_url = f'{parsed.scheme}://{parsed.netloc}{path}?' + urlencode(flat)
    return {
        'url': new_url,
        'method': method,
        'headers': headers,
        'post_data': post_data,
        'is_json': is_json,
    }


def prepare_bodian_audio_url(url: str, method: str, headers: dict,
                             post_data: Any, is_json: bool, kwargs: dict) -> dict:
    """波点获取音频 URL prepare_request（GET 形式，加 sign）

    适用于：/api/play/music/v2/audioUrl
    """
    sess = BodianSession.get()
    headers = dict(headers)
    headers.update(sess.auth_headers())
    headers['uid'] = sess.uid
    headers['token'] = sess.token

    # 提取 path
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    path = parsed.path

    existing = parse_qs(parsed.query, keep_blank_values=True)
    flat = {k: v[0] if isinstance(v, list) and v else '' for k, v in existing.items()}

    flat['timestamp'] = str(int(time.time() * 1000))
    flat['devId'] = sess.dev_id
    flat['uid'] = sess.uid
    flat['token'] = sess.token

    sign = _signquery(path, flat)
    flat['sign'] = sign

    new_url = f'{parsed.scheme}://{parsed.netloc}{path}?' + urlencode(flat)
    return {
        'url': new_url,
        'method': method,
        'headers': headers,
        'post_data': post_data,
        'is_json': is_json,
    }


def prepare_kuwo_official(url: str, method: str, headers: dict,
                          post_data: Any, is_json: bool, kwargs: dict) -> dict:
    """酷我官方 mobi.s 接口 prepare_request（GET，br 参数已在 url 中）

    适用于：mobi.kuwo.cn/mobi.s?type=convert_url_with_sign&br=2000kflac&rid=...
    """
    sess = BodianSession.get()
    headers = dict(headers)
    headers.update(sess.auth_headers())
    headers['uid'] = sess.uid
    headers['token'] = sess.token

    from urllib.parse import urlparse
    parsed = urlparse(url)

    # mobi 接口的 sign 是 user 参数的固定 salt，不需要额外计算
    # 关键是 headers 正确
    return {
        'url': url,
        'method': method,
        'headers': headers,
        'post_data': post_data,
        'is_json': is_json,
    }
