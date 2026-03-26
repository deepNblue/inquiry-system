"""
错误处理模块
"""

import os
import sys
import traceback
from datetime import datetime
from typing import Optional, Callable
from functools import wraps


class InquiryError(Exception):
    """询价系统基础异常"""
    
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or "INQUIRY_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            "error": self.message,
            "code": self.code,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class NetworkError(InquiryError):
    """网络错误"""
    
    def __init__(self, message: str, url: str = None):
        super().__init__(message, "NETWORK_ERROR")
        self.url = url


class DatabaseError(InquiryError):
    """数据库错误"""
    
    def __init__(self, message: str, query: str = None):
        super().__init__(message, "DATABASE_ERROR")
        self.query = query


class EmailError(InquiryError):
    """邮件错误"""
    
    def __init__(self, message: str, recipient: str = None):
        super().__init__(message, "EMAIL_ERROR")
        self.recipient = recipient


class ConfigError(InquiryError):
    """配置错误"""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, "CONFIG_ERROR")
        self.config_key = config_key


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, log_file: str = "logs/errors.log"):
        self.log_file = log_file
        self._ensure_log_dir()
    
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        log_dir = os.path.dirname(self.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
    
    def log_error(self, error: Exception, context: dict = None):
        """记录错误"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = f"""
{'='*60}
时间: {timestamp}
类型: {type(error).__name__}
消息: {str(error)}
{'='*60}
上下文: {context or {}}
{'='*60}
堆栈:
{traceback.format_exc()}
"""
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        return log_entry
    
    def handle(self, error: Exception, context: dict = None, show: bool = True) -> dict:
        """处理错误"""
        log_entry = self.log_error(error, context)
        
        if show:
            self._print_error(error)
        
        return {
            "success": False,
            "error": str(error),
            "code": getattr(error, 'code', 'UNKNOWN'),
            "timestamp": datetime.now().isoformat(),
        }
    
    def _print_error(self, error: Exception):
        """打印错误"""
        if isinstance(error, InquiryError):
            print(f"❌ [{error.code}] {error.message}")
        else:
            print(f"❌ {type(error).__name__}: {str(error)}")


# 全局错误处理器
_handler = None

def get_handler() -> ErrorHandler:
    """获取错误处理器"""
    global _handler
    if _handler is None:
        _handler = ErrorHandler()
    return _handler


def handle_error(context: dict = None):
    """错误处理装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except InquiryError as e:
                return get_handler().handle(e, context)
            except Exception as e:
                return get_handler().handle(e, context)
        return wrapper
    return decorator


def safe_execute(func: Callable, default=None, context: dict = None):
    """安全执行"""
    try:
        return func()
    except Exception as e:
        get_handler().handle(e, context)
        return default
