"""Fallback 框架单元测试

不依赖外部网络，全部用本地 mock 验证：
  - ApiSource 声明
  - FallbackChain 串行/并行 fallback
  - prepare_request 有状态回调
  - URL/post_data 占位符替换
  - extractors 标准化
  - 健康监控
"""
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, '/Users/Awan/Public/Repository/wan-music/backend')

from clients.fallback.api_source import ApiSource
from clients.fallback.chain import FallbackChain
from clients.fallback.extractors import (
    extract_first_url, normalize_netease_song, normalize_qq_song,
    normalize_kugou_song, normalize_bodian_song, url_quote, quality_to_br,
)
from clients.fallback.bodian_stateful import (
    BodianSession, _signquery, prepare_bodian_search,
)


class TestApiSource(unittest.TestCase):
    """ApiSource 数据类测试"""

    def test_basic_construction(self):
        s = ApiSource(name='test', platform='netease')
        self.assertEqual(s.name, 'test')
        self.assertEqual(s.platform, 'netease')
        self.assertTrue(s.enabled)
        self.assertEqual(s.priority, 100)

    def test_capability_flags(self):
        s = ApiSource(
            name='t', platform='qq',
            can_search=True, can_parse_url=True,
        )
        self.assertTrue(s.supports('search'))
        self.assertTrue(s.supports('parse_url'))
        self.assertFalse(s.supports('parse_info'))
        self.assertFalse(s.supports('parse_lyric'))

    def test_disabled_source(self):
        s = ApiSource(name='t', platform='qq', enabled=False, can_search=True)
        self.assertFalse(s.supports('search'))

    def test_to_dict(self):
        s = ApiSource(name='t', platform='qq', can_search=True, search_url='http://test/{q}')
        d = s.to_dict()
        self.assertEqual(d['name'], 't')
        self.assertEqual(d['search_url'], 'http://test/{q}')
        self.assertNotIn('_stats', d)


class TestFallbackChainSerial(unittest.TestCase):
    """串行 fallback 测试"""

    def test_first_source_succeeds(self):
        # Source 1 成功
        s1 = ApiSource(name='s1', platform='t', can_parse_url=True,
                       parse_url_url='http://t1/{q}',
                       extract_url=lambda d: d.get('url', ''))
        s2 = ApiSource(name='s2', platform='t', can_parse_url=True,
                       parse_url_url='http://t2/{q}',
                       extract_url=lambda d: d.get('url', ''))
        chain = FallbackChain([s1, s2], platform='t', strategy='serial')

        with patch.object(chain._session, 'get') as mock_get:
            mock_get.return_value.json.return_value = {'url': 'http://ok.com/a.mp3'}
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = '{}'
            url, source = chain.try_fetch('parse_url', q='x')
            self.assertEqual(url, 'http://ok.com/a.mp3')
            self.assertEqual(source, 's1')
            # 第二个 source 不应被调用
            self.assertEqual(mock_get.call_count, 1)

    def test_fallback_to_second_source(self):
        # Source 1 失败，Source 2 成功
        s1 = ApiSource(name='s1', platform='t', can_parse_url=True,
                       parse_url_url='http://t1/{q}',
                       extract_url=lambda d: d.get('url', ''))
        s2 = ApiSource(name='s2', platform='t', can_parse_url=True,
                       parse_url_url='http://t2/{q}',
                       extract_url=lambda d: d.get('url', ''))
        chain = FallbackChain([s1, s2], platform='t', strategy='serial')

        responses = [
            MagicMock(status_code=500, text='err', json=lambda: {}),
            MagicMock(status_code=200, text='{"url":"http://ok.com/b.mp3"}',
                      json=lambda: {'url': 'http://ok.com/b.mp3'}),
        ]
        with patch.object(chain._session, 'get', side_effect=responses):
            url, source = chain.try_fetch('parse_url', q='x')
            self.assertEqual(url, 'http://ok.com/b.mp3')
            self.assertEqual(source, 's2')

    def test_all_sources_fail(self):
        s1 = ApiSource(name='s1', platform='t', can_parse_url=True,
                       parse_url_url='http://t1/{q}',
                       extract_url=lambda d: '')
        chain = FallbackChain([s1], platform='t', strategy='serial')
        with patch.object(chain._session, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {}
            mock_get.return_value.text = '{}'
            url, source = chain.try_fetch('parse_url', q='x')
            self.assertEqual(url, '')
            self.assertIsNone(source)

    def test_health_tracking(self):
        s1 = ApiSource(name='s1', platform='t', can_parse_url=True,
                       parse_url_url='http://t1/{q}',
                       extract_url=lambda d: d.get('url', ''))
        chain = FallbackChain([s1], platform='t', strategy='serial')
        with patch.object(chain._session, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'url': 'http://ok/a.mp3'}
            mock_get.return_value.text = '{}'
            chain.try_fetch('parse_url', q='x')
            health = chain.get_health()
            self.assertEqual(health['s1']['ok'], 1)
            self.assertEqual(health['s1']['fail'], 0)


class TestFallbackChainParallel(unittest.TestCase):
    """并行 fallback 测试（用于 search）"""

    def test_parallel_merges_results(self):
        s1 = ApiSource(name='s1', platform='t', can_search=True,
                       search_url='http://t1/{q}',
                       extract_search=lambda d: d.get('songs', []))
        s2 = ApiSource(name='s2', platform='t', can_search=True,
                       search_url='http://t2/{q}',
                       extract_search=lambda d: d.get('songs', []))
        chain = FallbackChain([s1, s2], platform='t', strategy='parallel')

        # 两个 source 返回不同的歌曲
        resp1 = MagicMock(status_code=200, text='{}',
                          json=lambda: {'songs': [{'id': '1', 'name': 'A'}]})
        resp2 = MagicMock(status_code=200, text='{}',
                          json=lambda: {'songs': [{'id': '2', 'name': 'B'}]})
        with patch.object(chain._session, 'get', side_effect=[resp1, resp2]):
            results, source = chain.try_fetch('search', q='x')
            self.assertEqual(len(results), 2)
            ids = {r['id'] for r in results}
            self.assertEqual(ids, {'1', '2'})
            # 所有 results 都应标记 _source
            for r in results:
                self.assertIn('_source', r)

    def test_parallel_dedup(self):
        # 两个 source 返回相同 id 的歌曲
        s1 = ApiSource(name='s1', platform='t', can_search=True,
                       search_url='http://t1/{q}',
                       extract_search=lambda d: d.get('songs', []))
        s2 = ApiSource(name='s2', platform='t', can_search=True,
                       search_url='http://t2/{q}',
                       extract_search=lambda d: d.get('songs', []))
        chain = FallbackChain([s1, s2], platform='t', strategy='parallel')

        resp1 = MagicMock(status_code=200, text='{}',
                          json=lambda: {'songs': [{'id': '1', 'name': 'A'}]})
        resp2 = MagicMock(status_code=200, text='{}',
                          json=lambda: {'songs': [{'id': '1', 'name': 'A2'}]})
        with patch.object(chain._session, 'get', side_effect=[resp1, resp2]):
            results, _ = chain.try_fetch('search', q='x')
            # 去重：id 相同只保留一个
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['id'], '1')


class TestPlaceholders(unittest.TestCase):
    """占位符替换测试"""

    def test_url_placeholder_substitution(self):
        s = ApiSource(name='t', platform='t', can_parse_url=True,
                      parse_url_url='http://t.com/{song_id}/{quality}',
                      extract_url=lambda d: d.get('url', ''))
        chain = FallbackChain([s], platform='t', strategy='serial')
        with patch.object(chain._session, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'url': 'http://x'}
            mock_get.return_value.text = '{}'
            chain.try_fetch('parse_url', song_id='123', quality='lossless')
            called_url = mock_get.call_args[0][0]
            self.assertEqual(called_url, 'http://t.com/123/lossless')

    def test_keyword_url_encoding(self):
        s = ApiSource(name='t', platform='t', can_search=True,
                      search_url='http://t.com/s?q={keyword_encoded}',
                      extract_search=lambda d: d.get('songs', []))
        chain = FallbackChain([s], platform='t', strategy='parallel')
        with patch.object(chain._session, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'songs': []}
            mock_get.return_value.text = '{}'
            chain.try_fetch('search', keyword='陈楚生', limit=5)
            called_url = mock_get.call_args[0][0]
            self.assertIn('%E9%99%88', called_url)  # URL encoded

    def test_post_data_placeholder(self):
        s = ApiSource(name='t', platform='t', can_search=True,
                      method='POST',
                      search_url='http://t.com/s',
                      post_data={'q': '{keyword}', 'n': '{limit}'},
                      extract_search=lambda d: d.get('songs', []))
        chain = FallbackChain([s], platform='t', strategy='parallel')
        with patch.object(chain._session, 'post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'songs': []}
            mock_post.return_value.text = '{}'
            chain.try_fetch('search', keyword='foo', limit=10)
            called_data = mock_post.call_args.kwargs['data']
            # is_json 默认 False，post_data 直接以 dict 形式发送
            self.assertEqual(called_data.get('q'), 'foo')
            self.assertEqual(called_data.get('n'), '10')


class TestPrepareRequest(unittest.TestCase):
    """有状态请求准备器测试"""

    def test_prepare_request_modifies_url(self):
        def add_token(url, method, headers, post_data, is_json, kwargs):
            return {
                'url': url + '?token=ABC',
                'method': method,
                'headers': headers,
                'post_data': post_data,
                'is_json': is_json,
            }

        s = ApiSource(name='t', platform='t', can_parse_url=True,
                      parse_url_url='http://t.com/{q}',
                      extract_url=lambda d: d.get('url', ''),
                      prepare_request=add_token)
        chain = FallbackChain([s], platform='t', strategy='serial')
        with patch.object(chain._session, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'url': 'http://ok'}
            mock_get.return_value.text = '{}'
            chain.try_fetch('parse_url', q='x')
            called_url = mock_get.call_args[0][0]
            self.assertIn('token=ABC', called_url)

    def test_prepare_request_modifies_headers(self):
        def add_header(url, method, headers, post_data, is_json, kwargs):
            new_headers = dict(headers)
            new_headers['X-Custom'] = 'Y'
            return {
                'url': url, 'method': method,
                'headers': new_headers, 'post_data': post_data, 'is_json': is_json,
            }

        s = ApiSource(name='t', platform='t', can_parse_url=True,
                      parse_url_url='http://t.com/{q}',
                      extract_url=lambda d: d.get('url', ''),
                      prepare_request=add_header)
        chain = FallbackChain([s], platform='t', strategy='serial')
        with patch.object(chain._session, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'url': 'http://ok'}
            mock_get.return_value.text = '{}'
            chain.try_fetch('parse_url', q='x')
            called_headers = mock_get.call_args.kwargs['headers']
            self.assertEqual(called_headers.get('X-Custom'), 'Y')


class TestBodianStateful(unittest.TestCase):
    """波点有状态鉴权测试"""

    def test_dev_id_is_md5_hex(self):
        sess = BodianSession.get()
        self.assertEqual(len(sess.dev_id), 32)
        self.assertTrue(all(c in '0123456789abcdef' for c in sess.dev_id))

    def test_dev_id_stable_in_session(self):
        sess1 = BodianSession.get()
        sess2 = BodianSession.get()
        self.assertEqual(sess1.dev_id, sess2.dev_id)

    def test_signquery_format(self):
        sign = _signquery('/api/test', {'a': '1', 'b': '2'})
        # 32 chars MD5
        self.assertEqual(len(sign), 32)

    def test_prepare_bodian_search_adds_sign(self):
        result = prepare_bodian_search(
            url='https://bd-api.kuwo.cn/api/search/music/list?pn=0&rn=10&keyword=test&correct=1',
            method='GET', headers={}, post_data=None, is_json=False,
            kwargs={},
        )
        self.assertIn('sign=', result['url'])
        self.assertIn('timestamp=', result['url'])
        self.assertIn('devid', result['headers'])
        self.assertIn('qimei36', result['headers'])


class TestExtractors(unittest.TestCase):
    """标准化函数测试"""

    def test_url_quote(self):
        self.assertEqual(url_quote('陈楚生'), '%E9%99%88%E6%A5%9A%E7%94%9F')
        self.assertEqual(url_quote('a b'), 'a%20b')

    def test_quality_to_br(self):
        self.assertEqual(quality_to_br('standard'), 128)
        self.assertEqual(quality_to_br('exhigh'), 320)
        self.assertEqual(quality_to_br('lossless'), 999)
        self.assertEqual(quality_to_br('unknown'), 999)  # default

    def test_extract_first_url(self):
        self.assertEqual(extract_first_url({'url': 'http://a'}), 'http://a')
        self.assertEqual(extract_first_url({'data': {'url': 'http://b'}}), 'http://b')
        self.assertEqual(extract_first_url({'download_url': 'http://c'}), 'http://c')
        self.assertEqual(extract_first_url({}), '')

    def test_normalize_netease_song(self):
        # Official format
        s = normalize_netease_song({
            'id': 123, 'name': 'Test',
            'ar': [{'name': 'A'}, {'name': 'B'}],
            'al': {'name': 'Album', 'picUrl': 'http://pic'},
            'dt': 200000,
        })
        self.assertEqual(s['id'], '123')
        self.assertEqual(s['artists'], 'A/B')
        self.assertEqual(s['album'], 'Album')
        self.assertEqual(s['duration'], 200000)

    def test_normalize_qq_song(self):
        s = normalize_qq_song({
            'id': 'qq_id', 'name': 'QQ Song',
            'singer': [{'name': 'S1'}, {'name': 'S2'}],
            'album': {'name': 'QQ Album'},
        })
        self.assertEqual(s['id'], 'qq_id')
        self.assertEqual(s['artists'], 'S1/S2')
        self.assertEqual(s['album'], 'QQ Album')

    def test_normalize_kugou_song(self):
        s = normalize_kugou_song({
            'FileHash': 'HASH123', 'SongName': 'KG Song',
            'Singers': [{'name': 'K1'}], 'AlbumName': 'KG Album',
        })
        self.assertEqual(s['id'], 'HASH123')
        self.assertEqual(s['artists'], 'K1')

    def test_normalize_bodian_song(self):
        s = normalize_bodian_song({
            'id': '607298776', 'name': 'BD Song',
            'artist': '陈楚生', 'album': 'BD Album',
        })
        self.assertEqual(s['id'], '607298776')
        self.assertEqual(s['artists'], '陈楚生')


class TestChainDisabledSource(unittest.TestCase):
    """禁用的 source 应该被跳过"""

    def test_disabled_source_skipped(self):
        s1 = ApiSource(name='s1', platform='t', enabled=False, can_parse_url=True,
                       parse_url_url='http://t1/{q}',
                       extract_url=lambda d: d.get('url', ''))
        s2 = ApiSource(name='s2', platform='t', can_parse_url=True,
                       parse_url_url='http://t2/{q}',
                       extract_url=lambda d: d.get('url', ''))
        chain = FallbackChain([s1, s2], platform='t', strategy='serial')
        with patch.object(chain._session, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'url': 'http://ok2'}
            mock_get.return_value.text = '{}'
            url, source = chain.try_fetch('parse_url', q='x')
            # s1 跳过，s2 成功
            self.assertEqual(source, 's2')
            self.assertEqual(url, 'http://ok2')
            self.assertEqual(mock_get.call_count, 1)

    def test_set_source_enabled(self):
        s1 = ApiSource(name='s1', platform='t', can_parse_url=True,
                       parse_url_url='http://t1/{q}',
                       extract_url=lambda d: d.get('url', ''))
        chain = FallbackChain([s1], platform='t', strategy='serial')
        self.assertTrue(chain.set_source_enabled('s1', False))
        self.assertFalse(s1.enabled)
        # 不存在的 source 返回 False
        self.assertFalse(chain.set_source_enabled('nonexistent', False))


if __name__ == '__main__':
    unittest.main(verbosity=2)
