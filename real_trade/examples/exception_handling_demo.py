#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Exception Usage Examples - 异常处理使用示例

展示如何在real-trade模块中使用统一的异常处理机制。
"""

import asyncio
import time
from typing import Dict

from ..utils import (
    BusinessError,
    ConfigError,
    ConnectionError,
    DataError,
    ErrorCode,
    NetworkError,
    RealTradeError,
    SystemError,
    TimeoutError,
    TradingError,
    exception_handler,
    handle_exception,
    safe_call,
)


class MockExchangeAPI:
    """模拟交易所API，用于演示异常处理"""

    def __init__(self, api_key: str = "", timeout: float = 5.0):
        self.api_key = api_key
        self.timeout = timeout
        self.connected = False

    def connect(self) -> bool:
        """模拟连接"""
        if not self.api_key:
            raise ConfigError("API密钥不能为空", {"field": "api_key"})

        # 模拟连接失败
        if self.api_key == "invalid":
            raise AuthenticationError("API密钥无效")

        # 模拟超时
        if self.timeout < 1.0:
            raise TimeoutError("连接超时", {"timeout": self.timeout})

        self.connected = True
        return True

    def fetch_market_data(self, symbol: str) -> Dict:
        """获取市场数据"""
        if not self.connected:
            raise ConnectionError("未建立连接")

        # 模拟数据错误
        if symbol == "INVALID":
            raise DataError("无效交易对", {"symbol": symbol})

        # 模拟网络错误
        if symbol == "NETWORK_ERROR":
            raise NetworkError("网络请求失败")

        return {
            "symbol": symbol,
            "price": 50000.0,
            "volume": 1000.0,
            "timestamp": time.time(),
        }

    def place_order(self, symbol: str, side: str, amount: float) -> Dict:
        """下单"""
        if not self.connected:
            raise ConnectionError("未建立连接")

        # 模拟资金不足
        if amount > 10000:
            raise TradingError(
                "资金不足", {"requested": amount, "available": 10000, "symbol": symbol}
            )

        # 模拟订单被拒绝
        if symbol == "REJECT":
            raise OrderRejectedError("订单被交易所拒绝", {"reason": "市场波动过大"})

        return {
            "order_id": f"order_{int(time.time())}",
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "status": "filled",
        }


class AuthenticationError(SystemError):
    """认证错误"""

    def __init__(self, message: str = "", details: Dict = None):
        super().__init__(message, details)
        self.code = ErrorCode.AUTHENTICATION_FAILED


class OrderRejectedError(TradingError):
    """订单被拒绝"""

    def __init__(self, message: str = "", details: Dict = None):
        super().__init__(message, details)
        self.code = ErrorCode.ORDER_REJECTED


@exception_handler(default_return=None)
def safe_connect(api: MockExchangeAPI) -> bool:
    """安全连接示例"""
    return api.connect()


@exception_handler(default_return={})
def safe_fetch_data(api: MockExchangeAPI, symbol: str) -> Dict:
    """安全获取数据示例"""
    return api.fetch_market_data(symbol)


def demonstrate_basic_exceptions():
    """基础异常使用演示"""
    print("=== 基础异常使用演示 ===\n")

    # 1. 直接抛出异常
    try:
        raise ConfigError("缺少必要配置", {"missing_field": "api_secret"})
    except RealTradeError as e:
        print(f"捕获异常: {e}")
        print(f"错误码: {e.code}")
        print(f"错误详情: {e.details}")
        print()

    # 2. 异常转换
    try:
        raise ValueError("无效的数值")
    except Exception as e:
        rt_error = handle_exception(e, "数据处理")
        print(f"转换后的异常: {rt_error}")
        print()


def demonstrate_api_integration():
    """API集成演示"""
    print("=== API集成异常处理演示 ===\n")

    api = MockExchangeAPI()

    # 1. 配置错误
    print("1. 配置错误处理:")
    try:
        api.connect()
    except RealTradeError as e:
        print(f"   错误: {e}")
        print(f"   错误码: {e.code.name} ({e.code.value})")
        print()

    # 2. 认证错误
    print("2. 认证错误处理:")
    api_invalid = MockExchangeAPI("invalid")
    try:
        api_invalid.connect()
    except RealTradeError as e:
        print(f"   错误: {e}")
        print(f"   错误码: {e.code.name}")
        print()

    # 3. 正常连接
    print("3. 正常连接:")
    api_valid = MockExchangeAPI("valid_key")
    try:
        result = api_valid.connect()
        print(f"   连接成功: {result}")
    except RealTradeError as e:
        print(f"   连接失败: {e}")
    print()

    # 4. 数据获取错误
    print("4. 数据获取错误处理:")
    if api_valid.connected:
        test_symbols = ["BTC/USDT", "INVALID", "NETWORK_ERROR"]
        for symbol in test_symbols:
            try:
                data = api_valid.fetch_market_data(symbol)
                print(f"   {symbol}: {data}")
            except RealTradeError as e:
                print(f"   {symbol} 获取失败: [{e.code.name}] {e.message}")
        print()


def demonstrate_safe_operations():
    """安全操作演示"""
    print("=== 安全操作演示 ===\n")

    api = MockExchangeAPI("valid_key", 0.5)  # 设置短超时来触发异常

    # 1. 使用safe_call
    print("1. safe_call使用:")
    result = safe_call(api.connect, default=False)
    print(f"   安全连接结果: {result}")
    print()

    # 2. 使用装饰器
    print("2. 装饰器使用:")
    api2 = MockExchangeAPI("valid_key")
    connected = safe_connect(api2)
    print(f"   装饰器连接结果: {connected}")

    data = safe_fetch_data(api2, "BTC/USDT")
    print(f"   装饰器数据获取: {data}")
    print()


def demonstrate_error_hierarchy():
    """错误层次结构演示"""
    print("=== 错误层次结构演示 ===\n")

    errors = [
        SystemError("系统错误"),
        NetworkError("网络错误"),
        ConnectionError("连接错误"),
        TimeoutError("超时错误"),
        DataError("数据错误"),
        TradingError("交易错误"),
        ConfigError("配置错误"),
        BusinessError("业务错误"),
    ]

    print("错误继承关系:")
    for error in errors:
        print(f"  {type(error).__name__} -> {error.code.name} ({error.code.value})")
    print()


def demonstrate_error_details():
    """错误详情演示"""
    print("=== 错误详情演示 ===\n")

    # 创建带详细信息的异常
    error = TradingError(
        "交易失败",
        {
            "symbol": "BTC/USDT",
            "side": "buy",
            "amount": 1.5,
            "available_balance": 1000,
            "required_amount": 50000,
        },
    )

    print("错误详情:")
    print(f"  消息: {error.message}")
    print(f"  错误码: {error.code.name}")
    print(f"  详情: {error.details}")
    print(f"  字典格式: {error.to_dict()}")
    print()


async def async_example():
    """异步异常处理示例"""
    print("=== 异步异常处理示例 ===\n")

    async def async_operation():
        await asyncio.sleep(0.1)
        raise NetworkError("异步网络错误")

    try:
        await async_operation()
    except RealTradeError as e:
        print(f"异步操作异常: {e}")


if __name__ == "__main__":
    demonstrate_basic_exceptions()
    demonstrate_api_integration()
    demonstrate_safe_operations()
    demonstrate_error_hierarchy()
    demonstrate_error_details()

    # 运行异步示例
    asyncio.run(async_example())
