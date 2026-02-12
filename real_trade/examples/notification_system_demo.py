#!/usr/bin/env python3
"""
带通知系统的完整策略示例
展示如何使用集成的通知和信号传递机制
"""

import os
import sys

import numpy as np
import pandas as pd

import backtrader as bt

# 添加项目路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from real_trade.analyzers.dynamic_risk_analyzer import (
    DynamicRiskAnalyzer,
    RiskBasedSizer,
)
from real_trade.analyzers.market_state_analyzer import MarketStateAnalyzer
from real_trade.core.notification_system import (
    ConsoleNotificationHandler,
    NotificationType,
    SignalType,
)
from real_trade.strategies.smart_base import SmartTradingStrategy


class NotifiedMAStrategy(SmartTradingStrategy):
    """
    带通知的移动平均策略
    展示完整的信号和通知机制使用
    """

    params = (
        ("fast_period", 10),
        ("slow_period", 30),
    )

    def __init__(self):
        super().__init__()

        # 技术指标
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.data, period=self.p.fast_period
        )
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.data, period=self.p.slow_period
        )

        # 交叉信号
        self.cross_up = bt.ind.CrossUp(self.sma_fast, self.sma_slow)
        self.cross_down = bt.ind.CrossDown(self.sma_fast, self.sma_slow)

        # 注册通知处理器
        self.register_global_notification_handler(
            ConsoleNotificationHandler.handle_notification
        )
        self.register_notification_handler(
            NotificationType.RISK_VIOLATION,
            lambda n: print(f"⚠️  风险警报: {n.message}"),
        )

        # 订阅信号
        self.subscribe_to_signals(SignalType.BUY, self._on_buy_signal)
        self.subscribe_to_signals(SignalType.SELL, self._on_sell_signal)

    def _on_buy_signal(self, signal):
        """处理买入信号"""
        print(f"📈 接收到买入信号! 置信度: {signal.confidence:.2f}")

    def _on_sell_signal(self, signal):
        """处理卖出信号"""
        print(f"📉 接收到卖出信号! 置信度: {signal.confidence:.2f}")

    def generate_signals(self):
        """生成交易信号"""
        if self.cross_up > 0:
            # 计算信号强度
            ma_separation = abs(self.sma_fast[0] - self.sma_slow[0]) / self.sma_slow[0]
            confidence = min(1.0, 0.5 + ma_separation * 5)

            self.add_signal(
                self.data,
                "BUY",
                confidence,
                {"reason": "MA_CROSS_UP", "separation": ma_separation},
            )

        elif self.cross_down > 0:
            ma_separation = abs(self.sma_fast[0] - self.sma_slow[0]) / self.sma_slow[0]
            confidence = min(1.0, 0.5 + ma_separation * 5)

            self.add_signal(
                self.data,
                "SELL",
                confidence,
                {"reason": "MA_CROSS_DOWN", "separation": ma_separation},
            )


def create_test_data():
    """创建测试数据"""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=100, freq="D")

    # 生成带趋势的价格数据
    returns = np.random.normal(0.001, 0.02, 100)
    prices = 100 * np.exp(np.cumsum(returns))
    trend = np.linspace(0, 0.05, 100)
    prices = prices * (1 + trend)

    df = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.005, 100)),
            "high": prices * (1 + abs(np.random.normal(0, 0.01, 100))),
            "low": prices * (1 - abs(np.random.normal(0, 0.01, 100))),
            "close": prices,
            "volume": np.random.randint(1000, 10000, 100),
        },
        index=dates,
    )

    return df


def main():
    """主函数"""
    print("=== Backtrader集成通知系统演示 ===\n")

    # 创建引擎
    cerebro = bt.Cerebro()

    # 添加数据
    data_df = create_test_data()
    data = bt.feeds.PandasData(dataname=data_df)
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(NotifiedMAStrategy, printlog=True, debug_mode=True)

    # 添加分析器
    cerebro.addanalyzer(DynamicRiskAnalyzer, _name="risk")
    cerebro.addanalyzer(MarketStateAnalyzer, _name="market")

    # 设置初始条件
    cerebro.broker.setcash(50000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addsizer(RiskBasedSizer, risk_per_trade=0.02)

    # 运行回测
    print("开始回测...")
    results = cerebro.run()
    strategy = results[0]

    print(f"\n最终资产: {cerebro.broker.getvalue():.2f}")
    print(f"收益率: {(cerebro.broker.getvalue() - 50000) / 50000:.2%}")

    # 显示分析结果
    risk_analysis = strategy.analyzers.risk.get_analysis()
    market_analysis = strategy.analyzers.market.get_analysis()

    print("\n=== 风险分析 ===")
    print(f"最大回撤: {risk_analysis['max_drawdown']:.2%}")
    print(f"风险等级: {risk_analysis['risk_level']}")

    print("\n=== 市场状态 ===")
    print(f"当前趋势: {market_analysis['current_trend']}")
    print(f"趋势强度: {market_analysis['trend_strength']:.2f}")
    print(f"市场制度: {market_analysis['market_regime']}")


if __name__ == "__main__":
    main()
