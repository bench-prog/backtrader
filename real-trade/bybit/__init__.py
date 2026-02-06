#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Bybit Real Trade Module

专业的 Bybit 交易系统核心模块。

主要组件:
- BybitStore: 交易所连接管理
- BybitBroker: 交易经纪商（支持模拟和实盘）
- BybitData: 数据源（支持实时和历史数据）
- Config: 配置管理
- Utils: 工具函数

快速开始:
    ```python
    from real_trade.bybit import BybitStore, BybitBroker, BybitData
    import backtrader as bt

    # 创建 Store
    store = BybitStore.get_instance(
        apikey='YOUR_API_KEY',
        secret='YOUR_SECRET',
        testnet=True
    )

    # 创建 Cerebro
    cerebro = bt.Cerebro()

    # 添加数据源
    data = BybitData.from_timeframe_string('1h', store, symbol='BTC/USDT')
    cerebro.adddata(data)

    # 添加 Broker
    broker = BybitBroker(store, paper_trading=True, cash=10000)
    cerebro.setbroker(broker)

    # 添加策略
    cerebro.addstrategy(MyStrategy)

    # 运行
    cerebro.run()
    ```
"""

from __future__ import absolute_import, division, print_function, unicode_literals

__version__ = "1.0.0"
__author__ = "Backtrader Community"
__license__ = "GPLv3"

# 核心组件
from .store import BybitStore
from .broker import BybitBroker
from .datafeed import BybitData

# 工具模块
from .utils import (
    Config,
    load_config_from_file,
    setup_logger,
    get_logger,
    validate_symbol,
    validate_timeframe,
    validate_api_keys,
)

# 导出所有公共接口
__all__ = [
    # 核心组件
    "BybitStore",
    "BybitBroker",
    "BybitData",
    # 配置
    "Config",
    "load_config_from_file",
    # 日志
    "setup_logger",
    "get_logger",
    # 验证器
    "validate_symbol",
    "validate_timeframe",
    "validate_api_keys",
    # 版本信息
    "__version__",
]


def create_bybit_engine(
    apikey: str = "",
    secret: str = "",
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    testnet: bool = True,
    paper_trading: bool = True,
    cash: float = 10000.0,
    proxy: str = None,
    **kwargs
):
    """
    快速创建 Bybit 交易引擎

    这是一个便捷函数，自动创建并配置所有必需组件。

    Args:
        apikey: API Key
        secret: API Secret
        symbol: 交易对
        timeframe: 时间周期
        testnet: 是否使用测试网
        paper_trading: 是否模拟交易
        cash: 初始资金
        proxy: 代理地址
        **kwargs: 其他参数

    Returns:
        (store, broker, data) 元组

    Example:
        ```python
        store, broker, data = create_bybit_engine(
            apikey='YOUR_KEY',
            secret='YOUR_SECRET',
            symbol='BTC/USDT',
            timeframe='1h',
            testnet=True,
            paper_trading=True
        )

        cerebro = bt.Cerebro()
        cerebro.setbroker(broker)
        cerebro.adddata(data)
        cerebro.addstrategy(MyStrategy)
        cerebro.run()
        ```
    """
    import backtrader as bt

    # 验证参数
    valid, error = validate_symbol(symbol)
    if not valid:
        raise ValueError(error)

    valid, error = validate_timeframe(timeframe)
    if not valid:
        raise ValueError(error)

    if not paper_trading:
        valid, error = validate_api_keys(apikey, secret)
        if not valid:
            raise ValueError(error)

    # 创建 Store
    store = BybitStore.get_instance(
        apikey=apikey, secret=secret, testnet=testnet, proxy=proxy, **kwargs
    )

    # 创建 Broker
    broker = BybitBroker(store, paper_trading=paper_trading, cash=cash)

    # 创建 Data Feed
    data = BybitData.from_timeframe_string(
        timeframe, store, symbol=symbol, backtest=False
    )

    print("\n" + "=" * 60)
    print("Bybit Trading Engine Created")
    print("=" * 60)
    print(f"Mode: {'Paper Trading' if paper_trading else 'Live Trading'}")
    print(f"Symbol: {symbol}")
    print(f"Timeframe: {timeframe}")
    print(f"Testnet: {testnet}")
    print(f"Initial Cash: ${cash:,.2f}")
    print("=" * 60 + "\n")

    return store, broker, data


def print_banner():
    """打印欢迎信息"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██████╗ ██╗   ██╗██████╗ ██╗████████╗                    ║
║   ██╔══██╗╚██╗ ██╔╝██╔══██╗██║╚══██╔══╝                    ║
║   ██████╔╝ ╚████╔╝ ██████╔╝██║   ██║                       ║
║   ██╔══██╗  ╚██╔╝  ██╔══██╗██║   ██║                       ║
║   ██████╔╝   ██║   ██████╔╝██║   ██║                       ║
║   ╚═════╝    ╚═╝   ╚═════╝ ╚═╝   ╚═╝                       ║
║                                                              ║
║             Bybit Real Trade Module v{}            ║
║          Professional Algorithmic Trading System            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """.format(
        __version__
    )
    print(banner)


# 模块加载时打印欢迎信息
if __name__ != "__main__":
    print_banner()
