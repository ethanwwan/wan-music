"""搜索相关路由"""

from flask import Blueprint, request, jsonify
import logging

from services.music_service import music_service
from utils.api_response import APIResponse

logger = logging.getLogger(__name__)

search_bp = Blueprint('search', __name__)


@search_bp.route('/search', methods=['POST'])
def search():
    """搜索歌曲"""
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        
        if not keyword:
            return jsonify(APIResponse.error("请输入搜索关键词", 400))
        
        platform = data.get('source')
        limit = data.get('limit', 10)
        
        results = music_service.search_songs(keyword, platform, limit)
        
        return jsonify(APIResponse.success(results, "搜索成功"))
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return jsonify(APIResponse.error(f"搜索失败: {str(e)}", 500))


@search_bp.route('/search/playlist', methods=['POST'])
def search_playlist():
    """搜索歌单"""
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        
        if not keyword:
            return jsonify(APIResponse.error("请输入搜索关键词", 400))
        
        platform = data.get('source')
        limit = data.get('limit', 20)
        
        results = music_service.search_playlists(keyword, platform, limit)
        
        return jsonify(APIResponse.success(results, "搜索成功"))
    except Exception as e:
        logger.error(f"搜索歌单失败: {e}")
        return jsonify(APIResponse.error(f"搜索失败: {str(e)}", 500))
