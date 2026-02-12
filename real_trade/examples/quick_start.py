#!/usr/bin/env python3
"""
Backtrader快速开始示例
最简单的完整使用流程
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

from real_trade.analyzers.dynamic_risk_analyzer import DynamicRiskAnalyzer
from real_trade.strategies.smart_base import SmartTradingStrategy


class SimpleStrategy(SmartTradingStrategy):
    """简单策略示例"""

    def __init__(self):
        super().__init__()
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.data, period=10)
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.data, period=30)

    def generate_signals(self):
        if (
            self.sma_fast[0] > self.sma_slow[0]
            and self.sma_fast[-1] <= self.sma_slow[-1]
        ):
            self.add_signal(self.data, "BUY", 0.8)
        elif (
            self.sma_fast[0] < self.sma_slow[0]
            and self.sma_fast[-1] >= self.sma_slow[-1]
        ):
            self.add_signal(self.data, "SELL", 0.8)


def load_real_btc_data():
    """加载真实BTC数据"""
    # 使用绝对路径
    import os

    data_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "datas",
        "binance-btc-2015-2026.txt",
    )

    try:
        # 读取真实数据
        df = pd.read_csv(data_file)
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)

        print("📊 加载真实BTC数据:")
        print(f"   时间范围: {df.index[0].date()} 到 {df.index[-1].date()}")
        print(f"   数据点数: {len(df)} 天")
        print(f"   价格范围: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}")

        return df

    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        print("🔄 使用模拟数据替代...")
        return create_quick_data()


def create_quick_data():
    """快速创建测试数据（备用）"""
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    prices = 100 + np.cumsum(np.random.normal(0, 0.5, 100))

    df = pd.DataFrame(
        {
            "Open": prices * (1 + np.random.normal(0, 0.01, 100)),
            "High": prices * (1 + abs(np.random.normal(0, 0.02, 100))),
            "Low": prices * (1 - abs(np.random.normal(0, 0.02, 100))),
            "Close": prices,
            "Volume": np.random.randint(1000, 10000, 100),
        },
        index=dates,
    )

    return df


def quick_start():
    """快速开始"""
    print("🚀 Backtrader快速开始示例")
    print("=" * 40)

    # 1. 加载真实数据
    data = load_real_btc_data()
    print(f"📊 数据加载完成: {len(data)} 个数据点")

    # 2. 创建回测引擎
    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=data))
    print("🔧 回测引擎初始化完成")

    # 3. 添加策略
    cerebro.addstrategy(SimpleStrategy, printlog=True)
    print("🧠 策略添加完成")

    # 4. 添加风险管理
    cerebro.addanalyzer(DynamicRiskAnalyzer, _name="risk")
    print("🛡️  风险管理添加完成")

    # 5. 设置初始资金
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    print("💰 初始资金设置: $10,000")

    # 6. 运行回测
    print("\n📈 开始回测...")
    initial = cerebro.broker.getvalue()
    results = cerebro.run()
    final = cerebro.broker.getvalue()

    # 7. 显示结果
    strategy = results[0]
    risk_analysis = strategy.analyzers.risk.get_analysis()

    print("\n🎯 回测完成!")
    print(f"初始资金: ${initial:,.2f}")
    print(f"最终资金: ${final:,.2f}")
    print(f"收益率: {(final - initial) / initial:.2%}")
    print(f"最大回撤: {risk_analysis['max_drawdown']:.2%}")
    print(f"风险等级: {risk_analysis['risk_level']}")

    return results


if __name__ == "__main__":
    quick_start()
