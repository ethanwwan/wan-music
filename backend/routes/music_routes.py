"""音乐相关路由"""

from flask import Blueprint, request, jsonify
import logging

from services.music_service import music_service
from utils.api_response import APIResponse

logger = logging.getLogger(__name__)

music_bp = Blueprint('music', __name__)


@music_bp.route('/song', methods=['POST'])
def get_song_info():
    """获取歌曲信息（支持多种类型：url/name/lyric/json）"""
    try:
        data = request.get_data(as_text=True)
        params = {}
        for pair in data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key] = value
        
        ids = params.get('ids', '')
        music_id = ids.split(',')[0] if ids else params.get('id', '')
        
        # 尝试从URL中提取平台信息
        source = params.get('source', '')
        
        # 如果没有传递source，尝试从ID中判断
        if not source:
            # QQ音乐的songmid是字母数字混合，网易云是纯数字
            if music_id and not music_id.isdigit():
                source = 'qq'
        
        if not music_id:
            return jsonify(APIResponse.error("请提供歌曲ID", 400))
        
        info_type = params.get('type', 'json')
        level = params.get('level', 'lossless')
        
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
    """获取歌单详情"""
    try:
        data = request.get_data(as_text=True)
        params = {}
        for pair in data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key] = value
        
        playlist_id = params.get('id', '')
        source = params.get('source', '')
        
        # 如果没有传递source，尝试从ID中判断
        if not source:
            # QQ音乐的songmid是字母数字混合，网易云是纯数字
            if playlist_id and not playlist_id.isdigit():
                source = 'qq'
        
        if not playlist_id:
            return jsonify(APIResponse.error("请提供歌单ID", 400))
        
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
