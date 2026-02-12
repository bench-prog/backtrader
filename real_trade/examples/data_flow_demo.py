#!/usr/bin/env python3
"""
数据流集成完整示例
展示如何使用统一的数据流处理和缓存机制
"""

import os
import sys
from typing import Dict

import numpy as np
import pandas as pd

import backtrader as bt

# 添加项目路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from real_trade.analyzers.dynamic_risk_analyzer import DynamicRiskAnalyzer
from real_trade.analyzers.market_state_analyzer import MarketStateAnalyzer
from real_trade.core.data_flow import DataFlowMixin, data_flow_manager
from real_trade.strategies.smart_base import SmartTradingStrategy


class DataFlowStrategy(SmartTradingStrategy, DataFlowMixin):
    """
    数据流集成策略示例
    展示统一数据处理和缓存机制的使用
    """

    params = (
        ("use_cache", True),
        ("cache_stats_interval", 50),
    )

    def __init__(self):
        super().__init__()
        DataFlowMixin.__init__(self)

        # 技术指标列表
        self.indicators_needed = ["sma_10", "sma_30", "rsi", "bollinger_bands"]

        # 性能计数器
        self.bar_count = 0
        self.cache_hits = 0
        self.direct_calculations = 0

    def next(self):
        """主逻辑循环"""
        super().next()

        self.bar_count += 1

        # 每隔一定间隔显示缓存统计
        if self.bar_count % self.p.cache_stats_interval == 0:
            self._show_cache_stats()

        # 使用数据流系统计算指标
        indicators = self._get_cached_indicators()

        # 生成交易信号
        self._generate_signals_with_cache(indicators)

        # 发布数据供其他模块使用
        self._publish_analysis_data(indicators)

    def _get_cached_indicators(self) -> Dict:
        """获取缓存的技术指标"""
        try:
            # 使用数据流系统
            indicators = self.get_technical_indicators(
                self.data, self.indicators_needed
            )
            self.cache_hits += 1
            return indicators
        except Exception as e:
            # 回退到直接计算
            print(f"缓存获取失败，使用直接计算: {e}")
            self.direct_calculations += 1
            return self._calculate_indicators_directly()

    def _calculate_indicators_directly(self) -> Dict:
        """直接计算技术指标（无缓存）"""
        # 安全获取价格数据
        close_prices = []
        for i in range(-len(self.data), 0):
            try:
                close_prices.append(self.data.close[i])
            except IndexError:
                break
        close_prices = np.array(close_prices)

        if len(close_prices) < 30:
            return {"sma_10": np.array([]), "sma_30": np.array([]), "rsi": np.array([])}

        # 简单移动平均线
        sma_10 = np.convolve(close_prices, np.ones(10) / 10, mode="valid")
        sma_30 = np.convolve(close_prices, np.ones(30) / 30, mode="valid")

        # RSI
        if len(close_prices) > 14:
            delta = np.diff(close_prices)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_gain = np.convolve(gain, np.ones(14) / 14, mode="valid")
            avg_loss = np.convolve(loss, np.ones(14) / 14, mode="valid")
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))

            # 补齐RSI前面的NaN值
            rsi_full = np.full(len(close_prices), np.nan)
            rsi_full[14:] = rsi
        else:
            rsi_full = np.full(len(close_prices), np.nan)

        return {"sma_10": sma_10, "sma_30": sma_30, "rsi": rsi_full}

    def _generate_signals_with_cache(self, indicators: Dict):
        """使用缓存指标生成信号"""
        if len(self.data) < 30:  # 确保有足够的数据
            return

        current_close = self.data.close[0]
        sma_10 = (
            indicators["sma_10"][-1] if len(indicators["sma_10"]) > 0 else current_close
        )
        sma_30 = (
            indicators["sma_30"][-1] if len(indicators["sma_30"]) > 0 else current_close
        )
        rsi = indicators["rsi"][-1] if not np.isnan(indicators["rsi"][-1]) else 50

        # 金叉信号
        if (
            sma_10 > sma_30
            and len(indicators["sma_10"]) > 1
            and len(indicators["sma_30"]) > 1
            and indicators["sma_10"][-2] <= indicators["sma_30"][-2]
        ):
            confidence = min(1.0, 0.6 + (sma_10 - sma_30) / sma_30 * 2)
            if rsi < 30:  # 超卖确认
                confidence = min(1.0, confidence + 0.2)

            self.add_signal(
                self.data,
                "BUY",
                confidence,
                {
                    "reason": "SMA_GOLDEN_CROSS",
                    "sma_diff": (sma_10 - sma_30) / sma_30,
                    "rsi": rsi,
                },
            )

        # 死叉信号
        elif (
            sma_10 < sma_30
            and len(indicators["sma_10"]) > 1
            and len(indicators["sma_30"]) > 1
            and indicators["sma_10"][-2] >= indicators["sma_30"][-2]
        ):
            confidence = min(1.0, 0.6 + (sma_30 - sma_10) / sma_30 * 2)
            if rsi > 70:  # 超买确认
                confidence = min(1.0, confidence + 0.2)

            self.add_signal(
                self.data,
                "SELL",
                confidence,
                {
                    "reason": "SMA_DEATH_CROSS",
                    "sma_diff": (sma_30 - sma_10) / sma_30,
                    "rsi": rsi,
                },
            )

    def _publish_analysis_data(self, indicators: Dict):
        """发布分析数据"""
        analysis_data = {
            "timestamp": self.datetime.datetime(),
            "close_price": self.data.close[0],
            "indicators": {
                "sma_10": float(indicators["sma_10"][-1])
                if len(indicators["sma_10"]) > 0
                else None,
                "sma_30": float(indicators["sma_30"][-1])
                if len(indicators["sma_30"]) > 0
                else None,
                "rsi": float(indicators["rsi"][-1])
                if len(indicators["rsi"]) > 0 and not np.isnan(indicators["rsi"][-1])
                else None,
            },
            "strategy_state": {
                "cash": self.broker.getcash(),
                "value": self.broker.getvalue(),
                "position_size": self.getposition(self.data).size,
            },
        }

        # 发布到数据流系统
        self.publish_data("strategy_analysis", analysis_data)

    def _show_cache_stats(self):
        """显示缓存统计"""
        cache_stats = data_flow_manager.cache.get_stats()

        print(f"\n=== 数据流缓存统计 (Bar {self.bar_count}) ===")
        print(f"缓存命中率: {cache_stats['hit_rate']:.2%}")
        print(f"缓存大小: {cache_stats['size']}/{cache_stats['max_size']}")
        print(f"总访问次数: {cache_stats['total_access']}")
        print(f"缓存命中次数: {cache_stats['total_hits']}")
        print(f"直接计算次数: {self.direct_calculations}")
        print(f"缓存使用次数: {self.cache_hits}")
        print("=" * 40)

    def stop(self):
        """策略结束"""
        super().stop()
        self._show_cache_stats()


def create_sample_data():
    """创建样本数据"""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=200, freq="D")

    # 生成趋势性价格序列
    returns = np.random.normal(0.001, 0.02, 200)
    prices = 100 * np.exp(np.cumsum(returns))

    # 添加趋势和周期性
    trend = np.linspace(0, 0.1, 200)
    cycle = 0.05 * np.sin(np.linspace(0, 4 * np.pi, 200))
    prices = prices * (1 + trend + cycle)

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


def main():
    """主函数"""
    print("=== Backtrader数据流集成演示 ===\n")

    # 创建引擎
    cerebro = bt.Cerebro()

    # 添加数据
    data_df = create_sample_data()
    data = bt.feeds.PandasData(dataname=data_df)
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(
        DataFlowStrategy, printlog=True, use_cache=True, cache_stats_interval=50
    )

    # 添加分析器
    cerebro.addanalyzer(DynamicRiskAnalyzer, _name="risk")
    cerebro.addanalyzer(MarketStateAnalyzer, _name="market")

    # 设置初始条件
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    # 运行回测
    print("开始回测...")
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    strategy = results[0]

    final_value = cerebro.broker.getvalue()
    print(f"\n初始资产: {initial_value:.2f}")
    print(f"最终资产: {final_value:.2f}")
    print(f"总收益率: {(final_value - initial_value) / initial_value:.2%}")

    # 显示最终统计
    risk_analysis = strategy.analyzers.risk.get_analysis()
    market_analysis = strategy.analyzers.market.get_analysis()

    print("\n=== 最终分析结果 ===")
    print(f"最大回撤: {risk_analysis['max_drawdown']:.2%}")
    print(f"风险等级: {risk_analysis['risk_level']}")
    print(f"最终趋势: {market_analysis['current_trend']}")
    print(f"市场制度: {market_analysis['market_regime']}")


if __name__ == "__main__":
    main()
