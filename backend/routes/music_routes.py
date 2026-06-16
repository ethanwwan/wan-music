"""音乐相关路由"""
from flask import Blueprint, request, jsonify
import logging
from urllib.parse import unquote_plus

from services.music_service import music_service
from utils.api_response import APIResponse
from utils.url_parser import parse_url, is_music_url, is_playlist_url, is_album_url

logger = logging.getLogger(__name__)

music_bp = Blueprint('music', __name__)


@music_bp.route('/parse/url', methods=['POST'])
def parse_url_endpoint():
    """
    解析 URL，返回平台、类型和资源 ID

    请求体（application/x-www-form-urlencoded）：
        url: 要解析的链接

    响应：
        {
            'platform': 'netease' | 'qq' | 'kugou' | 'bodian',
            'type': 'music' | 'playlist' | 'album',
            'id': '资源 ID'
        }
    """
    try:
        data = request.get_data(as_text=True)
        params = {}
        for pair in data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[unquote_plus(key)] = unquote_plus(value)

        url = params.get('url', '')
        if not url:
            return jsonify(APIResponse.error("请提供 URL", 400))

        parsed = parse_url(url)
        if not parsed:
            return jsonify(APIResponse.error("无法识别的 URL", 400))

        return jsonify(APIResponse.success(parsed, "解析成功"))
    except Exception as e:
        logger.error(f"URL 解析异常: {e}")
        return jsonify(APIResponse.error(f"服务器错误: {str(e)}", 500))


@music_bp.route('/parse/validate', methods=['POST'])
def validate_url_endpoint():
    """
    验证 URL 类型

    请求体：
        url: 要验证的链接

    响应：
        {
            'type': 'music' | 'playlist' | 'album' | null,
            'isMusic': true/false,
            'isPlaylist': true/false,
            'isAlbum': true/false
        }
    """
    try:
        data = request.get_data(as_text=True)
        params = {}
        for pair in data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[unquote_plus(key)] = unquote_plus(value)

        url = params.get('url', '')
        parsed = parse_url(url)
        url_type = parsed['type'] if parsed else None

        return jsonify(APIResponse.success({
            'type': url_type,
            'isMusic': url_type == 'music',
            'isPlaylist': url_type == 'playlist',
            'isAlbum': url_type == 'album',
        }, "验证成功"))
    except Exception as e:
        logger.error(f"URL 验证异常: {e}")
        return jsonify(APIResponse.error(f"服务器错误: {str(e)}", 500))


@music_bp.route('/song', methods=['POST'])
def get_song_info():
    """获取歌曲信息（支持多种类型：url/name/lyric/json）

    支持以下参数（任选其一）：
        - url: 完整的歌曲链接（推荐，由后端解析）
        - ids 或 id: 歌曲 ID（需配合 source 使用）
        - source: 平台（netease/qq/kugou/bodian），不传则从 URL 推断
    """
    try:
        data = request.get_data(as_text=True)
        params = {}
        for pair in data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[unquote_plus(key)] = unquote_plus(value)

        # 优先使用 url 参数（推荐）
        url = params.get('url', '')
        ids = params.get('ids', '')
        music_id = ids.split(',')[0] if ids else params.get('id', '')
        source = params.get('source', '')

        # 如果传入了 url，则在后端解析
        if url and not music_id:
            parsed = parse_url(url)
            if parsed:
                music_id = parsed['id']
                if not source:
                    source = parsed['platform']

        # 兜底：尝试从 ID 格式判断平台
        if not source and music_id and not music_id.isdigit():
            source = 'qq'

        if not music_id:
            # 区分"没有提供任何参数"和"URL 解析失败"两种情况，给出更具体的错误信息
            if url:
                return jsonify(APIResponse.error("无法识别此歌曲链接，请检查格式", 400))
            return jsonify(APIResponse.error("请提供歌曲链接或 ID", 400))

        info_type = params.get('type', 'json')
        level = params.get('level', 'lossless')

        logger.info(f"[DEBUG] /song 请求: music_id={music_id}, source={source}, type={info_type}, level={level}")
        
        if info_type == 'url':
            result = music_service.get_song_url(music_id, level, source)
            if result and result.get('data') and len(result['data']) > 0:
                song_data = result['data'][0]
                if song_data.get('url'):
                    response_data = {
                        'id': song_data.get('id'),
                        'url': song_data.get('url'),
                        'level': song_data.get('level', level),
                        'type': song_data.get('type', 'mp3'),
                        'source': song_data.get('source', source or 'netease')
                    }
                    return jsonify(APIResponse.success(response_data, "获取歌曲URL成功"))
                else:
                    return jsonify(APIResponse.error("该歌曲因版权限制无法获取播放链接", 403))
            else:
                return jsonify(APIResponse.error("获取音乐URL失败，可能是版权限制或音质不支持", 404))
        
        elif info_type == 'name':
            result = music_service.get_song_detail(music_id, source)
            return jsonify(APIResponse.success(result, "获取歌曲信息成功"))
        
        elif info_type == 'lyric':
            lyric = music_service.get_lyric(music_id, source)
            return jsonify(APIResponse.success({'lyric': lyric}, "获取歌词成功"))
        
        elif info_type == 'json':
            song_info = music_service.get_song_info(music_id, level, source)
            if not song_info:
                logger.info(f"[DEBUG] /song 返回空结果: music_id={music_id}, source={source}, song_info={song_info}")
                return jsonify(APIResponse.error("未找到歌曲信息", 404))
            
            response_data = {
                'id': music_id,
                'name': song_info.get('name', ''),
                'ar_name': song_info.get('artists', ''),
                'al_name': song_info.get('album', ''),
                'pic': song_info.get('picUrl', ''),
                'level': level,
                'source': song_info.get('source', source or 'netease'),
                'lyric': song_info.get('lyric', ''),
                'tlyric': '',
                'fileType': song_info.get('fileType', 'mp3')  # 文件类型（mp3/flac等）
            }
            
            if song_info.get('url'):
                response_data['url'] = song_info['url']
            else:
                response_data['url'] = ''
                response_data['size'] = '获取失败'
            
            return jsonify(APIResponse.success(response_data, "获取歌曲信息成功"))
        
        else:
            return jsonify(APIResponse.error(f"不支持的类型: {info_type}", 400))
    
    except Exception as e:
        if "所有数据源均无法获取" in str(e):
            return jsonify(APIResponse.error("该歌曲因版权限制无法获取播放链接", 403))
        logger.error(f"获取歌曲信息异常: {e}")
        return jsonify(APIResponse.error(f"服务器错误: {str(e)}", 500))


@music_bp.route('/playlist', methods=['POST'])
def get_playlist():
    """获取歌单详情

    支持以下参数（任选其一）：
        - url: 完整的歌单链接（推荐，由后端解析）
        - id: 歌单 ID（需配合 source 使用）
        - source: 平台（netease/qq/kugou/bodian），不传则从 URL 推断
    """
    try:
        data = request.get_data(as_text=True)
        params = {}
        for pair in data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[unquote_plus(key)] = unquote_plus(value)

        url = params.get('url', '')
        playlist_id = params.get('id', '')
        source = params.get('source', '')

        # 优先使用 url 参数（推荐）
        if url and not playlist_id:
            parsed = parse_url(url)
            if parsed:
                playlist_id = parsed['id']
                if not source:
                    source = parsed['platform']

        if not source and playlist_id and not playlist_id.isdigit():
            source = 'qq'

        if not playlist_id:
            return jsonify(APIResponse.error("请提供歌单链接或 ID", 400))

        result = music_service.get_playlist_detail(playlist_id, source)

        return jsonify(APIResponse.success({'playlist': result}, "获取歌单成功"))
    except Exception as e:
        logger.error(f"获取歌单失败: {e}")
        return jsonify(APIResponse.error(f"获取歌单失败: {str(e)}", 500))


@music_bp.route('/api/data-sources', methods=['GET'])
def get_data_sources():
    """获取可用数据源列表"""
    try:
        platforms = music_service.get_platforms()
        return jsonify(APIResponse.success(platforms, "获取数据源列表成功"))
    except Exception as e:
        logger.error(f"获取数据源列表失败: {e}")
        return jsonify(APIResponse.error(f"获取数据源列表失败: {str(e)}", 500))
