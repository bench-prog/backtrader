#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
quickstart.py - 快速上手示例

演示如何用最少代码启动一个策略回测。
"""

import backtrader as bt
from real_trade.strategies.trend import MACrossStrategy


def main():
    # 方式一：使用 TradingRunner（推荐）
    from real_trade.engine import TradingRunner

    runner = TradingRunner(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        strategy_cls=MACrossStrategy,
        strategy_params={"fast_period": 10, "slow_period": 30},
        testnet=True,
        paper_trading=True,
        backtest=True,
        historical_limit=500,
    )
    runner.run()


def main_manual():
    # 方式二：手动组装
    from real_trade.binance import create_binance_engine

    store, broker, data = create_binance_engine(
        symbol="BTC/USDT",
        timeframe="1h",
        testnet=True,
        paper_trading=True,
        backtest=True,
        historical_limit=500,
    )

    cerebro = bt.Cerebro()
    cerebro.setbroker(broker)
    cerebro.adddata(data)
    cerebro.addstrategy(MACrossStrategy, fast_period=10, slow_period=30)
    cerebro.run()


if __name__ == "__main__":
    main()
