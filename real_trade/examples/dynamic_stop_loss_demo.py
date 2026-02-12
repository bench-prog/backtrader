#!/usr/bin/env python3
"""
动态止损全流程示例
展示自适应止损、风险管理和仓位控制的完整应用
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
from real_trade.analyzers.market_state_analyzer import MarketStateAnalyzer
from real_trade.strategies.smart_base import SmartTradingStrategy


class AdaptiveStopLossStrategy(SmartTradingStrategy):
    """
    自适应止损策略
    结合动态风险评估和智能止损机制
    """

    params = (
        ("stop_loss_percent", 0.02),  # 基础止损比例 2%
        ("take_profit_percent", 0.04),  # 止盈比例 4%
        ("volatility_window", 20),  # 波动率计算窗口
        ("max_positions", 3),  # 最大持仓数
        ("risk_multiplier", 1.5),  # 风险倍数
    )

    def __init__(self):
        super().__init__()

        # 技术指标
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.data, period=10)
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.data, period=30)
        self.atr = bt.indicators.AverageTrueRange(self.data, period=14)
        self.rsi = bt.indicators.RSI(self.data, period=14)

        # 动态止损相关
        self.entry_prices = {}  # 记录每个持仓的入场价格
        self.stop_losses = {}  # 动态止损价格
        self.take_profits = {}  # 止盈价格

        # 波动率计算
        self.volatility_history = []

    def generate_signals(self):
        """生成交易信号并设置动态止损"""
        if len(self.data) < self.p.volatility_window:
            return

        current_price = self.data.close[0]
        position = self.getposition(self.data)

        # 计算动态波动率
        self._update_volatility()
        dynamic_stop_pct = self._calculate_dynamic_stop()

        # 技术信号
        tech_signal = self._get_technical_signal()

        # 风险调整后的仓位大小
        position_size = self._calculate_position_size(dynamic_stop_pct)

        # 买入信号
        if (
            tech_signal == 1
            and position.size <= 0
            and len(self.positions) < self.p.max_positions
        ):
            # 记录入场信息
            self.entry_prices[self.data] = current_price
            # 设置动态止损和止盈
            self.stop_losses[self.data] = current_price * (1 - dynamic_stop_pct)
            self.take_profits[self.data] = current_price * (
                1 + self.p.take_profit_percent
            )

            # 执行买入
            position_size = self._calculate_position_size(dynamic_stop_pct)
            self.buy(size=position_size)
            self.log(
                f"📈 买入: 价格${current_price:.2f}, 数量{position_size}, 动态止损{dynamic_stop_pct:.2%}"
            )

        # 卖出信号
        elif tech_signal == -1 and position.size > 0:
            self.sell(size=position.size)
            self.log(f"📉 卖出: 价格${current_price:.2f}, 数量{position.size}")
            self._clear_position_tracking()

        # 检查止损和止盈
        self._check_exits(current_price)

    def _update_volatility(self):
        """更新波动率历史"""
        if len(self.data) >= self.p.volatility_window:
            prices = [self.data.close[i] for i in range(-self.p.volatility_window, 0)]
            returns = np.diff(np.log(prices))
            volatility = np.std(returns)
            self.volatility_history.append(volatility)

            # 保持历史长度
            if len(self.volatility_history) > 50:
                self.volatility_history.pop(0)

    def _calculate_dynamic_stop(self):
        """计算动态止损比例"""
        if not self.volatility_history:
            return self.p.stop_loss_percent

        # 基于历史波动率调整止损
        avg_volatility = np.mean(self.volatility_history)
        dynamic_stop = self.p.stop_loss_percent * (1 + avg_volatility * 10)

        # 限制在合理范围内
        return min(max(dynamic_stop, 0.01), 0.05)  # 1%-5%之间

    def _get_technical_signal(self):
        """获取技术信号"""
        signal = 0

        # MA交叉
        if (
            self.sma_fast[0] > self.sma_slow[0]
            and self.sma_fast[-1] <= self.sma_slow[-1]
        ):
            signal += 1
        elif (
            self.sma_fast[0] < self.sma_slow[0]
            and self.sma_fast[-1] >= self.sma_slow[-1]
        ):
            signal -= 1

        # RSI过滤
        if self.rsi[0] < 30:
            signal += 0.5
        elif self.rsi[0] > 70:
            signal -= 0.5

        return np.sign(signal)

    def _calculate_position_size(self, stop_loss_pct):
        """基于风险的仓位计算"""
        cash = self.broker.getcash()
        risk_amount = cash * 0.02  # 每笔交易风险2%

        if stop_loss_pct > 0:
            position_size = int(risk_amount / (self.data.close[0] * stop_loss_pct))
            max_size = int(cash * 0.1 / self.data.close[0])  # 最大10%资金
            return min(position_size, max_size)
        return 1

    def _check_exits(self, current_price):
        """检查止损和止盈条件"""
        position = self.getposition(self.data)

        if position.size > 0 and self.data in self.entry_prices:
            entry_price = self.entry_prices[self.data]

            # 止损退出
            if current_price <= self.stop_losses.get(self.data, 0):
                self.log(
                    f"🚨 止损退出: 入场${entry_price:.2f} -> 当前${current_price:.2f}"
                )
                self.sell(size=position.size)
                self._clear_position_tracking()

            # 止盈退出
            elif current_price >= self.take_profits.get(self.data, float("inf")):
                self.log(
                    f"💰 止盈退出: 入场${entry_price:.2f} -> 当前${current_price:.2f}"
                )
                self.sell(size=position.size)
                self._clear_position_tracking()

            # 动态调整止损
            else:
                self._adjust_stop_loss(current_price, entry_price)

    def _adjust_stop_loss(self, current_price, entry_price):
        """动态调整止损位"""
        # 移动止损：随着价格上涨，提高止损位
        if current_price > entry_price * 1.02:  # 盈利超过2%
            new_stop = current_price * 0.98  # 设置为当前价格的98%
            if new_stop > self.stop_losses.get(self.data, 0):
                self.stop_losses[self.data] = new_stop
                self.log(f"📈 移动止损调整: ${new_stop:.2f}")

    def _clear_position_tracking(self):
        """清除持仓跟踪信息"""
        self.entry_prices.pop(self.data, None)
        self.stop_losses.pop(self.data, None)
        self.take_profits.pop(self.data, None)

    def notify_order(self, order):
        """订单通知"""
        super().notify_order(order)
        if order.status == order.Completed:
            if order.isbuy():
                self.log(
                    f"✅ 买入执行: 价格${order.executed.price:.2f}, 数量{order.executed.size}"
                )
            else:
                self.log(
                    f"✅ 卖出执行: 价格${order.executed.price:.2f}, 数量{order.executed.size}"
                )


def load_btc_data_with_volatility():
    """加载BTC数据并分析波动率特征"""
    # 使用绝对路径
    import os

    data_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "datas",
        "binance-btc-2015-2026.txt",
    )
    df = pd.read_csv(data_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)

    # 计算波动率特征
    df["Returns"] = df["Close"].pct_change()
    df["Volatility"] = df["Returns"].rolling(20).std() * np.sqrt(365)  # 年化波动率

    print("📊 BTC波动率分析:")
    print(f"平均年化波动率: {df['Volatility'].mean():.2%}")
    print(f"最大年化波动率: {df['Volatility'].max():.2%}")
    print(f"最小年化波动率: {df['Volatility'].min():.2%}")

    return df


def main():
    """主函数"""
    print("🎯 动态止损全流程示例")
    print("=" * 50)

    # 加载数据
    btc_data = load_btc_data_with_volatility()

    # 创建回测引擎
    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(dataname=btc_data)
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(AdaptiveStopLossStrategy, printlog=True)

    # 添加风险管理
    cerebro.addanalyzer(DynamicRiskAnalyzer, _name="risk")
    cerebro.addanalyzer(MarketStateAnalyzer, _name="market")

    # 设置初始条件
    cerebro.broker.setcash(50000.0)
    cerebro.broker.setcommission(commission=0.001)

    print("💰 初始资金: $50,000.00")
    print("🔧 开始动态止损策略回测...")

    # 运行回测
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()

    # 分析结果
    strategy = results[0]
    risk_analysis = strategy.analyzers.risk.get_analysis()
    market_analysis = strategy.analyzers.market.get_analysis()

    returns = (final_value - initial_value) / initial_value

    print("\n🎯 回测结果:")
    print(f"💵 最终资金: ${final_value:,.2f}")
    print(f"📈 总收益率: {returns:.2%}")
    print(f"📉 最大回撤: {risk_analysis['max_drawdown']:.2%}")
    print(f"🛡️  风险等级: {risk_analysis['risk_level']}")
    print(f"📊 市场制度: {market_analysis['market_regime']}")

    # 与基准对比
    buy_hold = (btc_data["Close"].iloc[-1] - btc_data["Close"].iloc[0]) / btc_data[
        "Close"
    ].iloc[0]
    print("\n⚖️  策略对比:")
    print(f"   BTC持有收益: {buy_hold:.2%}")
    print(f"   动态止损策略: {returns:.2%}")
    print(f"   超额收益: {returns - buy_hold:.2%}")

    return results


if __name__ == "__main__":
    main()
