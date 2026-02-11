#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
live_trading.py - 实盘交易示例

演示完整的实盘交易流程：引擎 + 风控 + 监控 + 通知。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from real_trade.engine import LifecycleManager, TradingRunner
from real_trade.monitor import HealthChecker, PerformanceTracker, Reporter
from real_trade.risk import RiskManager
from real_trade.strategies.trend import MACrossStrategy


def main():
    # 1. 创建引擎
    runner = TradingRunner(
        exchange="binance",
        apikey="YOUR_API_KEY",
        secret="YOUR_SECRET",
        symbol="BTC/USDT",
        timeframe="1h",
        strategy_cls=MACrossStrategy,
        testnet=True,
        paper_trading=True,  # 先用 paper trading 验证
    )

    # 2. 风控
    risk_mgr = RiskManager(
        max_position_pct=0.3,
        risk_per_trade=0.02,
        max_drawdown_pct=0.15,
        max_daily_trades=20,
    )

    # 3. 监控
    tracker = PerformanceTracker(initial_cash=10000)
    hc = HealthChecker()
    reporter = Reporter()

    # 4. 生命周期管理（优雅关闭）
    lm = LifecycleManager(max_retries=3, retry_delay=10)
    lm.on_start(lambda: print("Trading system started"))
    lm.on_stop(lambda: print(reporter.generate_text(tracker.summary(), hc.status())))
    lm.on_error(lambda e: print(f"Error: {e}"))

    # 5. 运行
    with lm:
        lm.run_with_retry(runner.run)


if __name__ == "__main__":
    main()
