#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Real Trade Module

实盘交易模块集合。

模块结构:
    stores/          交易所连接管理（BaseStore, BinanceStore, ...）
    brokers/         交易经纪商（BaseBroker, BinanceBroker, ...）
    feeds/           数据源（BaseData, BinanceData, BaseWebSocket, ...）
    strategies/      共享策略库（趋势/均值回归/动量/网格/复合）
    risk/            风控模块（仓位管理/止损/限制/回撤控制）
    engine/          交易引擎（统一运行器/调度/生命周期）
    monitor/         监控模块（绩效追踪/健康检查/报告）
    notifications/   通知模块（Telegram/钉钉/Webhook/邮件）
    utils/           公共工具（日志/配置/校验/重试/时间）
    tests/           统一测试
    examples/        使用示例

快速开始::

    from real_trade.stores import BinanceStore
    from real_trade.brokers import BinanceBroker
    from real_trade.feeds import BinanceData
    import backtrader as bt

    store = BinanceStore.get_instance(testnet=True)
    broker = BinanceBroker(store, paper_trading=True)
    data = BinanceData.from_timeframe_string("1h", store, symbol="BTC/USDT", backtest=True)

    cerebro = bt.Cerebro()
    cerebro.setbroker(broker)
    cerebro.adddata(data)
    cerebro.addstrategy(MyStrategy)
    cerebro.run()
"""

__version__ = "2.0.0"

from . import (
    brokers,
    engine,
    feeds,
    monitor,
    notifications,
    risk,
    stores,
    strategies,
    utils,
)
from .brokers import BaseBroker, BinanceBroker
from .feeds import BaseData, BaseWebSocket, BinanceData

# 便捷导入
from .stores import BaseStore, BinanceStore

__all__ = [
    # 模块
    "stores",
    "brokers",
    "feeds",
    "strategies",
    "risk",
    "engine",
    "monitor",
    "notifications",
    "utils",
    # 核心类
    "BaseStore",
    "BinanceStore",
    "BaseBroker",
    "BinanceBroker",
    "BaseData",
    "BinanceData",
    "BaseWebSocket",
]
