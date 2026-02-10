#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
TradingRunner - 统一运行器

封装 Cerebro 创建、组件装配和运行流程，一行代码启动交易。

Usage::

    runner = TradingRunner(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        strategy_cls=MACrossStrategy,
    )
    runner.run()
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from typing import Any, Dict, Optional, Type

import backtrader as bt

# 交易所工厂注册表
_EXCHANGE_FACTORIES = {}


def register_exchange(name: str, factory_func):
    """注册交易所工厂函数"""
    _EXCHANGE_FACTORIES[name.lower()] = factory_func


def _lazy_register():
    """延迟注册，避免循环导入"""
    if _EXCHANGE_FACTORIES:
        return
    try:
        from real_trade.binance import create_binance_engine

        register_exchange("binance", create_binance_engine)
    except ImportError:
        pass


class TradingRunner:
    """统一交易运行器"""

    def __init__(
        self,
        exchange: str = "binance",
        apikey: str = "",
        secret: str = "",
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        strategy_cls: Optional[Type[bt.Strategy]] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        testnet: bool = True,
        paper_trading: bool = True,
        cash: float = 10000.0,
        commission: float = 0.001,
        proxy: Optional[str] = None,
        backtest: bool = False,
        **engine_kwargs,
    ):
        self.exchange_name = exchange.lower()
        self.strategy_cls = strategy_cls
        self.strategy_params = strategy_params or {}
        self.commission = commission

        _lazy_register()

        if self.exchange_name not in _EXCHANGE_FACTORIES:
            available = list(_EXCHANGE_FACTORIES.keys())
            raise ValueError(f"Unknown exchange '{exchange}'. Available: {available}")

        factory = _EXCHANGE_FACTORIES[self.exchange_name]
        self.store, self.broker, self.data = factory(
            apikey=apikey,
            secret=secret,
            symbol=symbol,
            timeframe=timeframe,
            testnet=testnet,
            paper_trading=paper_trading,
            cash=cash,
            proxy=proxy,
            backtest=backtest,
            **engine_kwargs,
        )

        self.cerebro = None
        self._results = None

    def build(self) -> bt.Cerebro:
        """构建 Cerebro 实例"""
        self.cerebro = bt.Cerebro()
        self.cerebro.setbroker(self.broker)
        self.cerebro.adddata(self.data)

        if self.commission > 0:
            self.broker.setcommission(commission=self.commission)

        if self.strategy_cls:
            self.cerebro.addstrategy(self.strategy_cls, **self.strategy_params)

        return self.cerebro

    def add_analyzer(self, analyzer_cls, **kwargs):
        """添加分析器"""
        if self.cerebro is None:
            self.build()
        self.cerebro.addanalyzer(analyzer_cls, **kwargs)
        return self

    def run(self):
        """运行"""
        if self.cerebro is None:
            self.build()

        self._results = self.cerebro.run()
        return self._results

    @property
    def results(self):
        return self._results
