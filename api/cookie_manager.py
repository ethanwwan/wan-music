"""Cookie管理器模块

提供网易云音乐Cookie管理功能，从.env文件读取MUSIC_COOKIE
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
import logging


class CookieException(Exception):
    """Cookie相关异常类（保留用于向后兼容）"""
    pass


def setup_logger(name: str = None) -> logging.Logger:
    """配置日志系统

    Args:
        name: 日志器名称

    Returns:
        配置好的日志器
    """
    env = os.getenv('APP_ENV', 'prod')
    is_dev = env == 'dev'
    log_level = logging.DEBUG if is_dev else logging.WARNING

    logger = logging.getLogger(name) if name else logging.getLogger()
    logger.setLevel(log_level)

    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


class CookieManager:
    """Cookie管理器主类，从环境变量读取Cookie"""
    
    def __init__(self):
        """
        初始化Cookie管理器
        """
        load_dotenv()
        self.logger = setup_logger(__name__)
        
        self.cookie_key = 'MUSIC_COOKIE'
        
        self.important_cookies = {
            'MUSIC_U',
            'MUSIC_A',
            '__csrf',
            'NMTID',
            'WEVNSM',
            'WNMCID',
        }
    
    def read_cookie(self) -> str:
        """从.env读取Cookie
        
        Returns:
            Cookie字符串内容
        """
        cookie = os.getenv(self.cookie_key, '').strip()
        
        if not cookie:
            self.logger.warning(f"{self.cookie_key} 未在.env中配置")
            return ""
        
        self.logger.debug(f"成功读取Cookie，长度: {len(cookie)}")
        return cookie
    
    def parse_cookies(self) -> Dict[str, str]:
        """解析Cookie字符串为字典
        
        Returns:
            Cookie字典
        """
        cookie_content = self.read_cookie()
        if not cookie_content:
            return {}
        
        return self.parse_cookie_string(cookie_content)
    
    def parse_cookie_string(self, cookie_string: str) -> Dict[str, str]:
        """解析Cookie字符串
        
        Args:
            cookie_string: Cookie字符串
            
        Returns:
            Cookie字典
        """
        if not cookie_string or not cookie_string.strip():
            return {}
        
        cookies = {}
        
        try:
            cookie_string = cookie_string.strip()
            
            cookie_pairs = []
            if ';' in cookie_string:
                cookie_pairs = cookie_string.split(';')
            elif '\n' in cookie_string:
                cookie_pairs = cookie_string.split('\n')
            else:
                cookie_pairs = [cookie_string]
            
            for pair in cookie_pairs:
                pair = pair.strip()
                if not pair or '=' not in pair:
                    continue
                
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key and value:
                    cookies[key] = value
            
            self.logger.debug(f"解析得到 {len(cookies)} 个Cookie项")
            return cookies
            
        except Exception as e:
            self.logger.error(f"解析Cookie字符串失败: {e}")
            return {}
    
    def validate_cookie_format(self, cookie_string: str) -> bool:
        """验证Cookie格式是否有效
        
        Args:
            cookie_string: Cookie字符串
            
        Returns:
            是否格式有效
        """
        if not cookie_string or not cookie_string.strip():
            return False
        
        try:
            cookies = self.parse_cookie_string(cookie_string)
            
            if not cookies:
                return False
            
            for name, value in cookies.items():
                if not name or not isinstance(name, str):
                    return False
                if not isinstance(value, str):
                    return False
                if any(char in name for char in [' ', '\t', '\n', '\r', ';', ',']):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def is_cookie_valid(self) -> bool:
        """检查Cookie是否有效
        
        Returns:
            Cookie是否有效
        """
        try:
            cookies = self.parse_cookies()
            
            if not cookies:
                self.logger.warning("Cookie为空")
                return False
            
            missing_cookies = self.important_cookies - set(cookies.keys())
            if missing_cookies:
                self.logger.warning(f"缺少重要Cookie: {missing_cookies}")
                return False
            
            music_u = cookies.get('MUSIC_U', '')
            if not music_u or len(music_u) < 10:
                self.logger.warning("MUSIC_U Cookie无效")
                return False
            
            self.logger.debug("Cookie验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"Cookie验证失败: {e}")
            return False
    
    def get_cookie_info(self) -> Dict[str, Any]:
        """获取Cookie详细信息
        
        Returns:
            包含Cookie信息的字典
        """
        try:
            cookies = self.parse_cookies()
            
            info = {
                'source': 'env',
                'env_key': self.cookie_key,
                'cookie_count': len(cookies),
                'is_valid': self.is_cookie_valid(),
                'important_cookies_present': list(self.important_cookies & set(cookies.keys())),
                'missing_important_cookies': list(self.important_cookies - set(cookies.keys())),
                'all_cookie_names': list(cookies.keys())
            }
            
            return info
            
        except Exception as e:
            return {
                'error': str(e),
                'source': 'env',
                'is_valid': False
            }
    
    def get_cookie_for_request(self) -> Dict[str, str]:
        """获取用于HTTP请求的Cookie字典
        
        Returns:
            适用于requests库的Cookie字典
        """
        try:
            cookies = self.parse_cookies()
            filtered_cookies = {k: v for k, v in cookies.items() if k and v}
            return filtered_cookies
            
        except Exception as e:
            self.logger.error(f"获取请求Cookie失败: {e}")
            return {}
    
    def format_cookie_string(self, cookies: Dict[str, str]) -> str:
        """将Cookie字典格式化为字符串
        
        Args:
            cookies: Cookie字典
            
        Returns:
            Cookie字符串
        """
        if not cookies:
            return ""
        
        return '; '.join(f"{k}={v}" for k, v in cookies.items() if k and v)
    
    def __str__(self) -> str:
        """字符串表示"""
        info = self.get_cookie_info()
        return f"CookieManager(source=env, valid={info['is_valid']}, count={info['cookie_count']})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return self.__str__()


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    manager = CookieManager()
    
    print("Cookie管理器模块")
    print("支持的功能:")
    print("- 从.env读取Cookie")
    print("- Cookie格式验证")
    print("- Cookie有效性检查")
    print("- Cookie信息查看")
    
    info = manager.get_cookie_info()
    print(f"\n当前Cookie状态: {manager}")
    print(f"详细信息: {info}")
