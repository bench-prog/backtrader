#!/usr/bin/env python3
"""
多因子量化策略全流程示例
结合技术面、基本面和市场情绪的综合策略
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


class MultiFactorQuantStrategy(SmartTradingStrategy):
    """
    多因子量化策略
    融合技术因子、动量因子、波动率因子和市场状态因子
    """

    params = (
        ("momentum_period", 20),  # 动量周期
        ("volatility_period", 30),  # 波动率周期
        ("rsi_period", 14),  # RSI周期
        ("macd_fast", 12),  # MACD快线
        ("macd_slow", 26),  # MACD慢线
        ("macd_signal", 9),  # MACD信号线
        ("confidence_threshold", 0.6),  # 信号置信度阈值
    )

    def __init__(self):
        super().__init__()

        # 技术指标族
        self.sma_10 = bt.indicators.SimpleMovingAverage(self.data, period=10)
        self.sma_20 = bt.indicators.SimpleMovingAverage(self.data, period=20)
        self.sma_50 = bt.indicators.SimpleMovingAverage(self.data, period=50)
        self.rsi = bt.indicators.RSI(self.data, period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(
            self.data,
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal,
        )
        self.bbands = bt.indicators.BollingerBands(self.data, period=20)
        self.stochastic = bt.indicators.Stochastic(self.data)

        # 动量和波动率指标
        self.momentum = bt.indicators.Momentum(self.data, period=self.p.momentum_period)
        self.atr = bt.indicators.AverageTrueRange(self.data, period=14)

        # 因子权重
        self.factor_weights = {
            "trend": 0.3,
            "momentum": 0.25,
            "volatility": 0.2,
            "mean_reversion": 0.15,
            "volume": 0.1,
        }

        # 状态跟踪
        self.trend_score_history = []
        self.momentum_score_history = []

    def generate_signals(self):
        """生成多因子综合信号"""
        if len(self.data) < max(self.p.momentum_period, self.p.volatility_period, 50):
            return

        current_price = self.data.close[0]
        position = self.getposition(self.data)

        # 计算各因子得分
        trend_score = self._calculate_trend_factor()
        momentum_score = self._calculate_momentum_factor()
        volatility_score = self._calculate_volatility_factor()
        mean_rev_score = self._calculate_mean_reversion_factor()
        volume_score = self._calculate_volume_factor()

        # 综合因子得分
        composite_score = (
            trend_score * self.factor_weights["trend"]
            + momentum_score * self.factor_weights["momentum"]
            + volatility_score * self.factor_weights["volatility"]
            + mean_rev_score * self.factor_weights["mean_reversion"]
            + volume_score * self.factor_weights["volume"]
        )

        # 计算置信度
        confidence = self._calculate_confidence(
            trend_score, momentum_score, volatility_score
        )

        # 交易决策
        if (
            composite_score > 0.3
            and confidence > self.p.confidence_threshold
            and position.size <= 0
        ):
            self.add_signal(
                self.data, "BUY", confidence, reason=f"综合得分:{composite_score:.2f}"
            )

        elif (
            composite_score < -0.3
            and confidence > self.p.confidence_threshold
            and position.size >= 0
        ):
            self.add_signal(
                self.data, "SELL", confidence, reason=f"综合得分:{composite_score:.2f}"
            )

        # 更新历史记录
        self._update_factor_history(trend_score, momentum_score)

    def _calculate_trend_factor(self):
        """计算趋势因子"""
        score = 0

        # 价格相对于均线位置
        if self.data.close[0] > self.sma_10[0]:
            score += 0.3
        if self.sma_10[0] > self.sma_20[0]:
            score += 0.3
        if self.sma_20[0] > self.sma_50[0]:
            score += 0.4

        # MACD趋势
        if self.macd.macd[0] > self.macd.signal[0]:
            score += 0.2
        if self.macd.macd[0] > self.macd.macd[-1]:
            score += 0.1

        return min(score, 1.0)

    def _calculate_momentum_factor(self):
        """计算动量因子"""
        score = 0

        # 价格动量
        if self.momentum[0] > 0:
            score += 0.4
        if self.momentum[0] > self.momentum[-1]:
            score += 0.3

        # RSI动量
        if 50 < self.rsi[0] < 70:
            score += 0.3
        elif 30 < self.rsi[0] < 50:
            score -= 0.3

        return max(min(score, 1.0), -1.0)

    def _calculate_volatility_factor(self):
        """计算波动率因子"""
        if len(self.data) < 30:
            return 0

        # 计算历史波动率
        prices = [self.data.close[i] for i in range(-30, 0)]
        returns = np.diff(np.log(prices))
        current_vol = np.std(returns)

        # 波动率标准化得分
        if hasattr(self, "_vol_history"):
            avg_vol = np.mean(self._vol_history)
            vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
            score = 1.0 - vol_ratio  # 低波动率偏好
        else:
            score = 0.5
            self._vol_history = []

        self._vol_history.append(current_vol)
        if len(self._vol_history) > 50:
            self._vol_history.pop(0)

        return max(min(score, 1.0), -1.0)

    def _calculate_mean_reversion_factor(self):
        """计算均值回归因子"""
        score = 0

        # 布林带位置
        bb_position = (self.data.close[0] - self.bbands.bot[0]) / (
            self.bbands.top[0] - self.bbands.bot[0]
        )
        if bb_position < 0.2:
            score += 0.5  # 超卖区域
        elif bb_position > 0.8:
            score -= 0.5  # 超买区域

        # 随机指标
        if self.stochastic.percK[0] < 20:
            score += 0.3
        elif self.stochastic.percK[0] > 80:
            score -= 0.3

        return max(min(score, 1.0), -1.0)

    def _calculate_volume_factor(self):
        """计算成交量因子"""
        if len(self.data) < 10 or "volume" not in self.data.__dict__:
            return 0

        # 成交量动量
        vol_ma = np.mean([self.data.volume[i] for i in range(-10, 0)])
        current_vol = self.data.volume[0]

        if current_vol > vol_ma * 1.5:
            return 0.3
        elif current_vol < vol_ma * 0.5:
            return -0.3
        return 0

    def _calculate_confidence(self, trend_score, momentum_score, volatility_score):
        """计算信号置信度"""
        # 基于因子一致性计算置信度
        scores = [trend_score, momentum_score, volatility_score]
        consistency = 1.0 - np.std(scores)  # 分数越一致，置信度越高

        # 基于历史表现调整
        if len(self.trend_score_history) > 10:
            recent_accuracy = self._calculate_recent_accuracy()
            consistency *= 0.5 + recent_accuracy * 0.5

        return min(max(consistency, 0.1), 1.0)

    def _calculate_recent_accuracy(self):
        """计算近期预测准确性"""
        if len(self.trend_score_history) < 10:
            return 0.5

        correct_predictions = 0
        total_predictions = min(len(self.trend_score_history) - 1, 10)

        for i in range(-total_predictions, -1):
            predicted_direction = 1 if self.trend_score_history[i] > 0 else -1
            actual_direction = 1 if self.data.close[i + 1] > self.data.close[i] else -1
            if predicted_direction == actual_direction:
                correct_predictions += 1

        return correct_predictions / total_predictions if total_predictions > 0 else 0.5

    def _update_factor_history(self, trend_score, momentum_score):
        """更新因子历史记录"""
        self.trend_score_history.append(trend_score)
        self.momentum_score_history.append(momentum_score)

        # 保持历史长度
        if len(self.trend_score_history) > 100:
            self.trend_score_history.pop(0)
        if len(self.momentum_score_history) > 100:
            self.momentum_score_history.pop(0)

    def next(self):
        """主逻辑循环"""
        super().next()

        # 定期输出因子状态
        if len(self) % 30 == 0:  # 每30天
            self.log(
                f"因子状态 - 趋势:{self._calculate_trend_factor():.2f}, "
                f"动量:{self._calculate_momentum_factor():.2f}, "
                f"波动率:{self._calculate_volatility_factor():.2f}"
            )


def create_multi_asset_backtest():
    """创建多资产回测场景"""
    print("📈 多因子量化策略全流程示例")
    print("=" * 50)

    # 加载BTC数据
    import os

    data_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "datas",
        "binance-btc-2015-2026.txt",
    )
    df = pd.read_csv(data_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)

    print(f"📊 数据范围: {df.index[0].date()} 到 {df.index[-1].date()}")
    print(f"📊 数据点数: {len(df)}")

    # 创建回测引擎
    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(MultiFactorQuantStrategy, printlog=True)

    # 添加分析器
    cerebro.addanalyzer(DynamicRiskAnalyzer, _name="risk")
    cerebro.addanalyzer(MarketStateAnalyzer, _name="market")

    # 设置初始条件
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    print("\n💰 初始资金: $100,000.00")
    print("🔧 开始多因子策略回测...")

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
    buy_hold = (df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0]
    sharpe_ratio = returns / (risk_analysis["max_drawdown"] + 0.01)  # 简化夏普比率

    print("\n⚖️  策略对比:")
    print(f"   BTC持有收益: {buy_hold:.2%}")
    print(f"   多因子策略: {returns:.2%}")
    print(f"   超额收益: {returns - buy_hold:.2%}")
    print(f"   风险调整收益(Sharpe): {sharpe_ratio:.2f}")

    return results


if __name__ == "__main__":
    create_multi_asset_backtest()
