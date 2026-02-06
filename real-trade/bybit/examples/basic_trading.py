#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
基础交易示例

展示如何使用 Bybit 模块进行基础的策略回测和模拟交易。
"""

import backtrader as bt
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from real_trade.bybit import create_bybit_engine, Config


class SimpleMAStrategy(bt.Strategy):
    """简单的移动平均策略"""

    params = (
        ("fast_period", 10),
        ("slow_period", 30),
    )

    def __init__(self):
        self.fast_ma = bt.indicators.SMA(period=self.p.fast_period)
        self.slow_ma = bt.indicators.SMA(period=self.p.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        else:
            if self.crossover < 0:
                self.sell()


def main():
    """主函数"""
    # 从环境变量读取配置
    config = Config.from_env()

    # 或者手动配置
    config = Config(
        apikey="YOUR_API_KEY",  # 替换为你的 API Key
        secret="YOUR_SECRET",  # 替换为你的 Secret
        symbol="BTC/USDT",
        timeframe="1h",
        testnet=True,
        paper_trading=True,  # 使用模拟交易
        initial_cash=10000.0,
    )

    # 创建 Bybit 引擎
    store, broker, data = create_bybit_engine(
        apikey=config.apikey,
        secret=config.secret,
        symbol=config.symbol,
        timeframe=config.timeframe,
        testnet=config.testnet,
        paper_trading=config.paper_trading,
        cash=config.initial_cash,
    )

    # 创建 Cerebro
    cerebro = bt.Cerebro()

    # 设置 Broker
    cerebro.setbroker(broker)

    # 添加数据
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(SimpleMAStrategy)

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

    # 打印初始信息
    print(f"\n{'='*60}")
    print(f"Starting Portfolio Value: ${cerebro.broker.getvalue():,.2f}")
    print(f"{'='*60}\n")

    # 运行策略
    results = cerebro.run()

    # 打印结果
    print(f"\n{'='*60}")
    print(f"Final Portfolio Value: ${cerebro.broker.getvalue():,.2f}")
    print(f"{'='*60}\n")

    # 打印分析结果
    strat = results[0]

    print("Performance Metrics:")
    print("-" * 60)

    sharpe = strat.analyzers.sharpe.get_analysis()
    if sharpe.get("sharperatio"):
        print(f"Sharpe Ratio: {sharpe['sharperatio']:.3f}")

    drawdown = strat.analyzers.drawdown.get_analysis()
    print(f"Max Drawdown: {drawdown['max']['drawdown']:.2f}%")

    returns = strat.analyzers.returns.get_analysis()
    print(f"Total Return: {returns['rtot']:.2%}")

    print("-" * 60)


if __name__ == "__main__":
    main()
