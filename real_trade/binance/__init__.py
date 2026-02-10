#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Binance Real Trade Module

快速开始::

    from real_trade.binance import create_binance_engine
    import backtrader as bt

    store, broker, data = create_binance_engine(
        symbol='BTC/USDT', timeframe='1h',
        testnet=True, paper_trading=True, backtest=True,
    )

    cerebro = bt.Cerebro()
    cerebro.setbroker(broker)
    cerebro.adddata(data)
    cerebro.addstrategy(MyStrategy)
    cerebro.run()
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from .broker import BinanceBroker
from .datafeed import BinanceData
from .store import BinanceStore

__all__ = [
    "BinanceStore",
    "BinanceBroker",
    "BinanceData",
    "create_binance_engine",
]


def create_binance_engine(
    apikey: str = "",
    secret: str = "",
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    testnet: bool = True,
    paper_trading: bool = True,
    cash: float = 10000.0,
    commission: float = 0.001,
    proxy: str = None,
    backtest: bool = False,
    market_type: str = "spot",
    **kwargs,
):
    """
    快速创建 Binance 交易引擎

    Args:
        apikey: API Key
        secret: API Secret
        symbol: 交易对
        timeframe: 时间周期
        testnet: 是否使用测试网
        paper_trading: 是否模拟交易
        cash: 初始资金
        commission: 佣金比例
        proxy: 代理地址
        backtest: 回测模式（加载历史数据，不需要 API 密钥）
        market_type: 市场类型 (spot / future / delivery)
        **kwargs: 传递给 DataFeed 的额外参数（historical_limit, fromdate, todate）

    Returns:
        (store, broker, data) 元组
    """
    # 回测模式：无需 API 密钥，使用公共数据端点
    use_apikey = apikey if not backtest else ""
    use_secret = secret if not backtest else ""
    use_testnet = testnet if not backtest else False

    store = BinanceStore.get_instance(
        apikey=use_apikey,
        secret=use_secret,
        testnet=use_testnet,
        proxy=proxy,
        market_type=market_type,
    )

    broker = BinanceBroker(store, paper_trading=paper_trading, cash=cash)
    if commission > 0:
        broker.setcommission(commission=commission)

    data = BinanceData.from_timeframe_string(
        timeframe,
        store,
        symbol=symbol,
        backtest=backtest,
        **kwargs,
    )

    return store, broker, data
