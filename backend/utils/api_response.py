"""统一API响应工具类"""

from flask import jsonify, Response
from typing import Any, Dict, Optional


class APIResponse:
    """统一API响应类"""
    
    @staticmethod
    def success(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
        """成功响应"""
        return {
            'success': True,
            'message': message,
            'data': data
        }
    
    @staticmethod
    def error(message: str, code: int = 500, data: Any = None) -> Dict[str, Any]:
        """错误响应"""
        return {
            'success': False,
            'message': message,
            'code': code,
            'data': data
        }
    
    @staticmethod
    def json_success(data: Any = None, message: str = "操作成功") -> Response:
        """返回 JSON 格式的成功响应"""
        return jsonify(APIResponse.success(data, message))
    
    @staticmethod
    def json_error(message: str, code: int = 500, data: Any = None) -> Response:
        """返回 JSON 格式的错误响应"""
        response = jsonify(APIResponse.error(message, code, data))
        response.status_code = code
        return response
