#!/usr/bin/env python3
"""
Backtrader框架集成完整示例
展示如何使用重构后的Analyzer组件和智能策略基类
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
from real_trade.strategies.smart_base import SmartTradingStrategy


class MovingAverageCrossoverStrategy(SmartTradingStrategy):
    """
    移动平均线交叉策略示例
    集成所有高级功能的完整实现
    """

    params = (
        ("fast_period", 10),
        ("slow_period", 30),
        ("rsi_period", 14),
        ("rsi_overbought", 70),
        ("rsi_oversold", 30),
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
        self.rsi = bt.indicators.RSI(self.data, period=self.p.rsi_period)

        # 交叉信号
        self.cross_up = bt.ind.CrossUp(self.sma_fast, self.sma_slow)
        self.cross_down = bt.ind.CrossDown(self.sma_fast, self.sma_slow)

    def generate_signals(self):
        """生成交易信号"""
        # 基础交叉信号
        if self.cross_up > 0:
            # 多头信号
            confidence = self._calculate_signal_confidence("BUY")
            if confidence > 0:
                self.add_signal(
                    self.data,
                    "BUY",
                    confidence,
                    {
                        "reason": "MA_CROSS_UP",
                        "fast_ma": self.sma_fast[0],
                        "slow_ma": self.sma_slow[0],
                    },
                )

        elif self.cross_down > 0:
            # 空头信号
            confidence = self._calculate_signal_confidence("SELL")
            if confidence > 0:
                self.add_signal(
                    self.data,
                    "SELL",
                    confidence,
                    {
                        "reason": "MA_CROSS_DOWN",
                        "fast_ma": self.sma_fast[0],
                        "slow_ma": self.sma_slow[0],
                    },
                )

    def _calculate_signal_confidence(self, signal_type: str) -> float:
        """计算信号置信度"""
        confidence = 0.5  # 基础置信度

        # MA分离程度
        ma_diff = abs(self.sma_fast[0] - self.sma_slow[0]) / self.sma_slow[0]
        confidence += min(0.3, ma_diff * 10)  # 最大增加0.3

        # RSI确认
        if signal_type == "BUY" and self.rsi[0] < self.p.rsi_oversold:
            confidence += 0.1
        elif signal_type == "SELL" and self.rsi[0] > self.p.rsi_overbought:
            confidence += 0.1

        # 趋势确认
        if self.market_analyzer:
            trend = self.market_analyzer.current_trend
            if (signal_type == "BUY" and trend == "UP") or (
                signal_type == "SELL" and trend == "DOWN"
            ):
                confidence += 0.1

        return min(1.0, confidence)


def create_sample_data():
    """创建示例数据"""
    # 生成模拟价格数据
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=200, freq="D")

    # 生成趋势性价格序列
    returns = np.random.normal(0.001, 0.02, 200)
    prices = 100 * np.exp(np.cumsum(returns))

    # 添加一些趋势和波动
    trend_component = np.linspace(0, 0.1, 200)
    prices = prices * (1 + trend_component)

    # 生成OHLCV数据
    df = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.005, 200)),
            "high": prices * (1 + abs(np.random.normal(0, 0.01, 200))),
            "low": prices * (1 - abs(np.random.normal(0, 0.01, 200))),
            "close": prices,
            "volume": np.random.randint(1000, 10000, 200),
        },
        index=dates,
    )

    return df


def run_backtest():
    """运行回测"""
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()

    # 添加数据
    data_df = create_sample_data()
    data = bt.feeds.PandasData(dataname=data_df)
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(
        MovingAverageCrossoverStrategy,
        printlog=True,
        debug_mode=False,
        max_risk_per_trade=0.02,
        min_signal_confidence=0.6,
    )

    # 添加分析器
    cerebro.addanalyzer(
        DynamicRiskAnalyzer, _name="risk", lookback_period=30, confidence_level=0.95
    )

    cerebro.addanalyzer(
        MarketStateAnalyzer, _name="market", trend_window=20, volatility_window=30
    )

    # 添加观察器
    cerebro.addobserver(bt.observers.BuySell)
    cerebro.addobserver(bt.observers.Value)
    cerebro.addobserver(bt.observers.DrawDown)

    # 设置初始资金和佣金
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    # 设置基于风险的仓位管理
    cerebro.addsizer(RiskBasedSizer, risk_per_trade=0.02)

    # 运行回测
    print("开始回测...")
    print(f"初始资金: {cerebro.broker.getvalue():.2f}")

    results = cerebro.run()
    strategy = results[0]

    print(f"最终资金: {cerebro.broker.getvalue():.2f}")
    print(f"总收益率: {(cerebro.broker.getvalue() - 100000) / 100000:.2%}")

    # 分析结果
    analyze_results(strategy)

    return results


def analyze_results(strategy):
    """分析回测结果"""
    print("\n=== 风险分析结果 ===")
    risk_analysis = strategy.analyzers.risk.get_analysis()
    print(f"最终VaR: {risk_analysis['current_var']:.4f}")
    print(f"最大回撤: {risk_analysis['max_drawdown']:.2%}")
    print(f"当前波动率: {risk_analysis['current_volatility']:.2%}")
    print(f"风险等级: {risk_analysis['risk_level']}")

    print("\n=== 市场状态分析结果 ===")
    market_analysis = strategy.analyzers.market.get_analysis()
    print(f"当前趋势: {market_analysis['current_trend']}")
    print(f"趋势强度: {market_analysis['trend_strength']:.2f}")
    print(f"市场制度: {market_analysis['market_regime']}")
    print(f"支撑位数量: {len(market_analysis['support_levels'])}")
    print(f"阻力位数量: {len(market_analysis['resistance_levels'])}")


if __name__ == "__main__":
    try:
        results = run_backtest()
        print("\n回测完成!")
    except Exception as e:
        print(f"回测出错: {e}")
        import traceback

        traceback.print_exc()
