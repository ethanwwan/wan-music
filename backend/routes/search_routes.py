"""搜索相关路由"""

from flask import Blueprint, request, jsonify
import logging

from services.music_service import music_service
from utils.api_response import APIResponse

logger = logging.getLogger(__name__)

search_bp = Blueprint('search', __name__)


@search_bp.route('/search', methods=['POST'])
def search():
    """统一搜索接口

    接受参数：
      - keyword: 搜索内容（可以是关键词或 URL）
      - type: 搜索类型（0=全部 / 1=歌曲 / 2=歌单），仅在 keyword 不是 URL 时生效
      - source: 数据源（netease/qq/kugou/bodian）
      - limit: 返回数量

    返回：{type, data: [...]}，每项带 _type 字段
    """
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        search_type = int(data.get('type', 0))
        platform = data.get('source')
        limit = data.get('limit', 50)

        logger.info(f"[搜索请求] keyword={keyword!r}, type={search_type}, source={platform}, limit={limit}")

        if not keyword:
            return jsonify(APIResponse.error("请输入搜索关键词", 400))

        result = music_service.search(keyword, search_type, platform, limit)

        logger.info(f"[搜索结果] type={result.get('type')}, 结果数量={len(result.get('data', []))}")

        return jsonify(APIResponse.success(result, "搜索成功"))
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return jsonify(APIResponse.error(f"搜索失败: {str(e)}", 500))


@search_bp.route('/search/playlist', methods=['POST'])
def search_playlist():
    """歌单搜索（兼容旧接口，内部转调统一搜索 type=2）"""
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        platform = data.get('source')
        limit = data.get('limit', 20)

        if not keyword:
            return jsonify(APIResponse.error("请输入搜索关键词", 400))

        result = music_service.search(keyword, 2, platform, limit)
        return jsonify(APIResponse.success({
            'playlists': result.get('data', []),
            'warnings': result.get('warnings', [])
        }, "搜索成功"))
    except Exception as e:
        logger.error(f"搜索歌单失败: {e}")
        return jsonify(APIResponse.error(f"搜索失败: {str(e)}", 500))



