#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Exceptions - 统一异常处理和错误码体系

定义real-trade模块的标准异常类型和错误码，提供统一的异常处理机制。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import enum
import traceback
from typing import Any, Dict, Optional, Union


class ErrorCode(enum.IntEnum):
    """错误码枚举

    错误码分类：
    - 1000-1999: 系统级错误
    - 2000-2999: 网络和连接错误
    - 3000-3999: 数据相关错误
    - 4000-4999: 交易相关错误
    - 5000-5999: 配置相关错误
    - 9000-9999: 业务逻辑错误
    """

    # 系统级错误 (1000-1999)
    SYSTEM_ERROR = 1000
    INVALID_ARGUMENT = 1001
    NOT_IMPLEMENTED = 1002
    INTERNAL_ERROR = 1003

    # 网络和连接错误 (2000-2999)
    NETWORK_ERROR = 2000
    CONNECTION_FAILED = 2001
    CONNECTION_TIMEOUT = 2002
    CONNECTION_LOST = 2003
    AUTHENTICATION_FAILED = 2004
    RATE_LIMIT_EXCEEDED = 2005

    # 数据相关错误 (3000-3999)
    DATA_ERROR = 3000
    INVALID_DATA_FORMAT = 3001
    MISSING_DATA = 3002
    DATA_INTEGRITY_ERROR = 3003
    UNSUPPORTED_TIMEFRAME = 3004
    SYMBOL_NOT_FOUND = 3005

    # 交易相关错误 (4000-4999)
    TRADING_ERROR = 4000
    INSUFFICIENT_FUNDS = 4001
    ORDER_REJECTED = 4002
    ORDER_NOT_FOUND = 4003
    POSITION_NOT_FOUND = 4004
    MARKET_CLOSED = 4005
    TRADING_SUSPENDED = 4006

    # 配置相关错误 (5000-5999)
    CONFIG_ERROR = 5000
    INVALID_CONFIG = 5001
    MISSING_REQUIRED_CONFIG = 5002
    API_KEY_INVALID = 5003

    # 业务逻辑错误 (9000-9999)
    BUSINESS_ERROR = 9000
    STRATEGY_ERROR = 9001
    RISK_VIOLATION = 9002
    INVALID_OPERATION = 9003


class RealTradeError(Exception):
    """Real-Trade基础异常类"""

    def __init__(
        self,
        code: Union[int, ErrorCode],
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        初始化异常

        Args:
            code: 错误码
            message: 错误描述
            details: 详细信息字典
            cause: 原始异常
        """
        self.code = code if isinstance(code, ErrorCode) else ErrorCode(code)
        self.message = message or self._get_default_message()
        self.details = details or {}
        self.cause = cause

        super().__init__(self.format_message())

    def _get_default_message(self) -> str:
        """获取默认错误消息"""
        default_messages = {
            ErrorCode.SYSTEM_ERROR: "系统错误",
            ErrorCode.INVALID_ARGUMENT: "无效参数",
            ErrorCode.NOT_IMPLEMENTED: "功能未实现",
            ErrorCode.INTERNAL_ERROR: "内部错误",
            ErrorCode.NETWORK_ERROR: "网络错误",
            ErrorCode.CONNECTION_FAILED: "连接失败",
            ErrorCode.CONNECTION_TIMEOUT: "连接超时",
            ErrorCode.CONNECTION_LOST: "连接丢失",
            ErrorCode.AUTHENTICATION_FAILED: "认证失败",
            ErrorCode.RATE_LIMIT_EXCEEDED: "请求频率超限",
            ErrorCode.DATA_ERROR: "数据错误",
            ErrorCode.INVALID_DATA_FORMAT: "数据格式无效",
            ErrorCode.MISSING_DATA: "缺少必要数据",
            ErrorCode.DATA_INTEGRITY_ERROR: "数据完整性错误",
            ErrorCode.UNSUPPORTED_TIMEFRAME: "不支持的时间周期",
            ErrorCode.SYMBOL_NOT_FOUND: "交易对不存在",
            ErrorCode.TRADING_ERROR: "交易错误",
            ErrorCode.INSUFFICIENT_FUNDS: "资金不足",
            ErrorCode.ORDER_REJECTED: "订单被拒绝",
            ErrorCode.ORDER_NOT_FOUND: "订单不存在",
            ErrorCode.POSITION_NOT_FOUND: "持仓不存在",
            ErrorCode.MARKET_CLOSED: "市场已收盘",
            ErrorCode.TRADING_SUSPENDED: "交易暂停",
            ErrorCode.CONFIG_ERROR: "配置错误",
            ErrorCode.INVALID_CONFIG: "配置无效",
            ErrorCode.MISSING_REQUIRED_CONFIG: "缺少必要配置",
            ErrorCode.API_KEY_INVALID: "API密钥无效",
            ErrorCode.BUSINESS_ERROR: "业务逻辑错误",
            ErrorCode.STRATEGY_ERROR: "策略错误",
            ErrorCode.RISK_VIOLATION: "违反风控规则",
            ErrorCode.INVALID_OPERATION: "无效操作",
        }

        return default_messages.get(self.code, "未知错误")

    def format_message(self) -> str:
        """格式化错误消息"""
        msg_parts = [f"[{self.code.name}] {self.message}"]

        if self.details:
            details_str = ", ".join([f"{k}={v}" for k, v in self.details.items()])
            msg_parts.append(f"({details_str})")

        if self.cause:
            msg_parts.append(f"Cause: {str(self.cause)}")

        return " ".join(msg_parts)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code.value,
            "code_name": self.code.name,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
            "stack_trace": traceback.format_exc() if self.__traceback__ else None,
        }


# 具体异常类定义
class SystemError(RealTradeError):
    """系统级错误"""

    def __init__(self, message: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.SYSTEM_ERROR, message, details)


class NetworkError(RealTradeError):
    """网络相关错误"""

    def __init__(self, message: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.NETWORK_ERROR, message, details)


class ConnectionError(NetworkError):
    """连接错误"""

    def __init__(self, message: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.code = ErrorCode.CONNECTION_FAILED


class TimeoutError(NetworkError):
    """超时错误"""

    def __init__(self, message: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.code = ErrorCode.CONNECTION_TIMEOUT


class DataError(RealTradeError):
    """数据相关错误"""

    def __init__(self, message: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.DATA_ERROR, message, details)


class TradingError(RealTradeError):
    """交易相关错误"""

    def __init__(self, message: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.TRADING_ERROR, message, details)


class ConfigError(RealTradeError):
    """配置相关错误"""

    def __init__(self, message: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.CONFIG_ERROR, message, details)


class BusinessError(RealTradeError):
    """业务逻辑错误"""

    def __init__(self, message: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.BUSINESS_ERROR, message, details)


# 异常处理工具函数
def handle_exception(e: Exception, context: Optional[str] = None) -> RealTradeError:
    """
    将普通异常转换为RealTradeError

    Args:
        e: 原始异常
        context: 上下文信息

    Returns:
        RealTradeError实例
    """
    if isinstance(e, RealTradeError):
        return e

    # 根据异常类型映射到相应的错误码
    error_mapping = {
        ValueError: ErrorCode.INVALID_ARGUMENT,
        TypeError: ErrorCode.INVALID_ARGUMENT,
        KeyError: ErrorCode.MISSING_DATA,
        ConnectionError: ErrorCode.CONNECTION_FAILED,
        TimeoutError: ErrorCode.CONNECTION_TIMEOUT,
    }

    code = error_mapping.get(type(e), ErrorCode.SYSTEM_ERROR)
    message = str(e)

    details = {}
    if context:
        details["context"] = context

    return RealTradeError(code, message, details, cause=e)


def safe_call(func, *args, default=None, **kwargs):
    """
    安全调用函数，捕获异常并返回默认值

    Args:
        func: 要调用的函数
        *args: 函数参数
        default: 异常时返回的默认值
        **kwargs: 函数关键字参数

    Returns:
        函数执行结果或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error = handle_exception(e, f"Calling {func.__name__}")
        # 这里可以记录日志
        from .logger import get_logger

        logger = get_logger("exception_handler")
        logger.warning(f"Safe call failed: {error}")
        return default


# 装饰器：自动异常处理
def exception_handler(default_return=None, log_errors=True):
    """
    异常处理装饰器

    Args:
        default_return: 异常时返回的默认值
        log_errors: 是否记录错误日志
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error = handle_exception(e, f"In {func.__name__}")

                if log_errors:
                    from .logger import get_logger

                    logger = get_logger("exception_handler")
                    logger.error(f"Exception in {func.__name__}: {error}")

                if default_return is not None:
                    return default_return
                else:
                    raise error

        return wrapper

    return decorator


__all__ = [
    "ErrorCode",
    "RealTradeError",
    "SystemError",
    "NetworkError",
    "ConnectionError",
    "TimeoutError",
    "DataError",
    "TradingError",
    "ConfigError",
    "BusinessError",
    "handle_exception",
    "safe_call",
    "exception_handler",
]
