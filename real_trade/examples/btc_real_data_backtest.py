#!/usr/bin/env python3
"""
真实BTC数据回测示例
使用2017-2025年的真实BTC日线数据进行完整回测
"""

import os
import sys

import pandas as pd

import backtrader as bt

# 添加项目路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from real_trade.analyzers.dynamic_risk_analyzer import DynamicRiskAnalyzer
from real_trade.analyzers.market_state_analyzer import MarketStateAnalyzer
from real_trade.strategies.smart_base import SmartTradingStrategy


class BTCTradingStrategy(SmartTradingStrategy):
    """BTC专用交易策略"""

    params = (
        ("sma_fast", 10),
        ("sma_slow", 30),
        ("rsi_period", 14),
        ("rsi_buy", 30),
        ("rsi_sell", 70),
    )

    def __init__(self):
        super().__init__()

        # 技术指标
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.data, period=self.p.sma_fast
        )
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.data, period=self.p.sma_slow
        )
        self.rsi = bt.indicators.RSI(self.data, period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(self.data)

    def generate_signals(self):
        """生成BTC交易信号"""
        if len(self.data) < self.p.sma_slow:
            return

        current_price = self.data.close[0]
        position = self.getposition(self.data)

        # MA交叉信号
        ma_signal = 0
        if (
            self.sma_fast[0] > self.sma_slow[0]
            and self.sma_fast[-1] <= self.sma_slow[-1]
        ):
            ma_signal = 1  # 金叉买入
        elif (
            self.sma_fast[0] < self.sma_slow[0]
            and self.sma_fast[-1] >= self.sma_slow[-1]
        ):
            ma_signal = -1  # 死叉卖出

        # RSI过滤信号
        rsi_signal = 0
        if self.rsi[0] < self.p.rsi_buy:
            rsi_signal = 1  # 超卖买入
        elif self.rsi[0] > self.p.rsi_sell:
            rsi_signal = -1  # 超买卖出

        # MACD信号
        macd_signal = 0
        if (
            self.macd.macd[0] > self.macd.signal[0]
            and self.macd.macd[-1] <= self.macd.signal[-1]
        ):
            macd_signal = 1
        elif (
            self.macd.macd[0] < self.macd.signal[0]
            and self.macd.macd[-1] >= self.macd.signal[-1]
        ):
            macd_signal = -1

        # 综合信号
        total_signal = ma_signal + rsi_signal + macd_signal

        if total_signal >= 2 and position.size <= 0:
            # 强烈买入信号
            confidence = min(1.0, 0.7 + (abs(total_signal) * 0.1))
            self.add_signal(self.data, "BUY", confidence)

        elif total_signal <= -2 and position.size >= 0:
            # 强烈卖出信号
            confidence = min(1.0, 0.7 + (abs(total_signal) * 0.1))
            self.add_signal(self.data, "SELL", confidence)


def load_real_btc_data():
    """加载真实BTC数据"""
    data_file = os.path.join(project_root, "datas", "binance-btc-2015-2026.txt")

    print("📊 加载真实BTC数据...")
    df = pd.read_csv(data_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)

    print(f"   时间范围: {df.index[0].date()} 到 {df.index[-1].date()}")
    print(f"   数据点数: {len(df)} 天")
    print(f"   价格范围: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}")
    print(
        f"   总体涨幅: {((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]):.2%}"
    )

    return df


def main():
    """主函数"""
    print("🚀 Backtrader真实BTC数据回测演示")
    print("=" * 50)

    # 加载真实数据
    btc_data = load_real_btc_data()

    # 创建回测引擎
    cerebro = bt.Cerebro()

    # 添加数据
    data = bt.feeds.PandasData(dataname=btc_data)
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(BTCTradingStrategy, printlog=True)

    # 添加分析器
    cerebro.addanalyzer(DynamicRiskAnalyzer, _name="risk")
    cerebro.addanalyzer(MarketStateAnalyzer, _name="market")

    # 设置初始条件
    initial_cash = 10000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)  # 0.1%手续费

    print(f"\n💰 初始资金: ${initial_cash:,.2f}")
    print("🔧 开始回测...")

    # 运行回测
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()

    # 分析结果
    strategy = results[0]
    risk_analysis = strategy.analyzers.risk.get_analysis()
    market_analysis = strategy.analyzers.market.get_analysis()

    returns = (final_value - initial_value) / initial_value

    print("\n🎯 回测完成!")
    print("=" * 50)
    print(f"📅 回测期间: {btc_data.index[0].date()} 到 {btc_data.index[-1].date()}")
    print(f"📊 交易天数: {len(btc_data)} 天")
    print(f"💵 初始资金: ${initial_value:,.2f}")
    print(f"💵 最终资金: ${final_value:,.2f}")
    print(f"📈 总收益率: {returns:.2%}")

    # 计算年化收益率
    years = (btc_data.index[-1] - btc_data.index[0]).days / 365.25
    annual_return = (1 + returns) ** (1 / years) - 1 if years > 0 else 0
    print(f"📊 年化收益率: {annual_return:.2%}")

    print(f"📉 最大回撤: {risk_analysis['max_drawdown']:.2%}")
    print(f"🛡️  风险等级: {risk_analysis['risk_level']}")
    print(f"📊 市场制度: {market_analysis['market_regime']}")

    # 与BTC持有策略对比
    buy_hold_return = (
        btc_data["Close"].iloc[-1] - btc_data["Close"].iloc[0]
    ) / btc_data["Close"].iloc[0]
    print("\n⚖️  策略对比:")
    print(f"   BTC持有收益: {buy_hold_return:.2%}")
    print(f"   策略收益: {returns:.2%}")
    print(f"   超额收益: {returns - buy_hold_return:.2%}")

    return results


if __name__ == "__main__":
    main()
