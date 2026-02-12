#!/usr/bin/env python3
"""
事件驱动交易全流程示例
基于市场事件和新闻情绪的智能交易系统
"""

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

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


@dataclass
class MarketEvent:
    """市场事件数据结构"""

    timestamp: datetime
    event_type: (
        str  # 'BREAKOUT', 'SUPPORT_RESISTANCE', 'VOLUME_SPIKE', 'VOLATILITY_JUMP'
    )
    strength: float  # 事件强度 0-1
    direction: int  # 1=看涨, -1=看跌, 0=中性
    confidence: float  # 事件可信度 0-1


class EventDrivenStrategy(SmartTradingStrategy):
    """
    事件驱动交易策略
    基于技术事件、市场结构变化和异常行为进行交易
    """

    params = (
        ("event_detection_window", 20),  # 事件检测窗口
        ("breakout_threshold", 0.03),  # 突破阈值 3%
        ("volume_spike_threshold", 2.0),  # 成交量激增阈值 2倍
        ("volatility_threshold", 0.02),  # 波动率跳跃阈值 2%
        ("support_resistance_window", 50),  # 支撑阻力识别窗口
        ("reaction_time", 3),  # 事件反应时间(天)
    )

    def __init__(self):
        super().__init__()

        # 技术指标
        self.sma_20 = bt.indicators.SimpleMovingAverage(self.data, period=20)
        self.atr = bt.indicators.AverageTrueRange(self.data, period=14)
        self.bbands = bt.indicators.BollingerBands(self.data, period=20)

        # 事件检测相关
        self.price_history = []
        self.volume_history = []
        self.detected_events = []
        self.pending_reactions = {}  # 等待反应的事件

        # 支撑阻力位
        self.support_levels = []
        self.resistance_levels = []

        # 状态跟踪
        self.consolidation_periods = 0
        self.breakout_confirmed = False

    def generate_signals(self):
        """基于事件生成交易信号"""
        if len(self.data) < self.p.event_detection_window:
            return

        current_price = self.data.close[0]
        current_time = self.data.datetime.date(0)

        # 更新历史数据
        self._update_history()

        # 检测各类市场事件
        events = self._detect_market_events()

        # 处理检测到的事件
        for event in events:
            self._process_event(event, current_price, current_time)

        # 检查待反应事件
        self._check_pending_reactions(current_price, current_time)

        # 更新支撑阻力位
        self._update_support_resistance()

    def _update_history(self):
        """更新价格和成交量历史"""
        self.price_history.append(self.data.close[0])
        if hasattr(self.data, "volume"):
            self.volume_history.append(self.data.volume[0])
        else:
            self.volume_history.append(1.0)  # 默认成交量

        # 保持历史长度
        max_history = max(
            self.p.event_detection_window, self.p.support_resistance_window
        )
        if len(self.price_history) > max_history:
            self.price_history.pop(0)
            self.volume_history.pop(0)

    def _detect_market_events(self) -> List[MarketEvent]:
        """检测市场事件"""
        events = []
        current_time = self.data.datetime.datetime(0)

        # 1. 检测突破事件
        breakout_event = self._detect_breakout()
        if breakout_event:
            events.append(breakout_event)

        # 2. 检测成交量激增
        volume_event = self._detect_volume_spike()
        if volume_event:
            events.append(volume_event)

        # 3. 检测波动率跳跃
        volatility_event = self._detect_volatility_jump()
        if volatility_event:
            events.append(volatility_event)

        # 4. 检测支撑阻力突破
        sr_event = self._detect_support_resistance_break()
        if sr_event:
            events.append(sr_event)

        return events

    def _detect_breakout(self) -> Optional[MarketEvent]:
        """检测价格突破事件"""
        if len(self.price_history) < self.p.event_detection_window:
            return None

        current_price = self.price_history[-1]
        recent_prices = self.price_history[-self.p.event_detection_window :]

        # 计算区间高低点
        consolidation_high = max(recent_prices[:-1])
        consolidation_low = min(recent_prices[:-1])
        range_size = consolidation_high - consolidation_low

        if range_size == 0:
            return None

        # 检测向上突破
        if current_price > consolidation_high * (1 + self.p.breakout_threshold):
            return MarketEvent(
                timestamp=self.data.datetime.datetime(0),
                event_type="BREAKOUT",
                strength=min((current_price - consolidation_high) / range_size, 1.0),
                direction=1,
                confidence=0.8,
            )

        # 检测向下突破
        elif current_price < consolidation_low * (1 - self.p.breakout_threshold):
            return MarketEvent(
                timestamp=self.data.datetime.datetime(0),
                event_type="BREAKOUT",
                strength=min((consolidation_low - current_price) / range_size, 1.0),
                direction=-1,
                confidence=0.8,
            )

        return None

    def _detect_volume_spike(self) -> Optional[MarketEvent]:
        """检测成交量激增事件"""
        if len(self.volume_history) < 10:
            return None

        current_volume = self.volume_history[-1]
        avg_volume = np.mean(self.volume_history[-10:-1])

        if avg_volume == 0:
            return None

        volume_ratio = current_volume / avg_volume

        if volume_ratio > self.p.volume_spike_threshold:
            price_change = (self.data.close[0] - self.data.close[-1]) / self.data.close[
                -1
            ]
            direction = 1 if price_change > 0 else (-1 if price_change < 0 else 0)

            return MarketEvent(
                timestamp=self.data.datetime.datetime(0),
                event_type="VOLUME_SPIKE",
                strength=min((volume_ratio - 1) / 2, 1.0),  # 标准化强度
                direction=direction,
                confidence=min(volume_ratio / 3, 1.0),  # 成交量越大，可信度越高
            )

        return None

    def _detect_volatility_jump(self) -> Optional[MarketEvent]:
        """检测波动率跳跃事件"""
        if len(self.price_history) < 20:
            return None

        # 计算当前波动率
        recent_returns = np.diff(np.log(self.price_history[-10:]))
        current_vol = np.std(recent_returns)

        # 计算历史平均波动率
        historical_returns = np.diff(np.log(self.price_history[-20:-10]))
        avg_vol = np.std(historical_returns)

        if avg_vol == 0:
            return None

        vol_ratio = current_vol / avg_vol

        if vol_ratio > (1 + self.p.volatility_threshold / 0.01):  # 转换为倍数
            # 判断方向：大幅上涨还是下跌
            recent_change = (
                self.price_history[-1] - self.price_history[-5]
            ) / self.price_history[-5]
            direction = (
                1 if recent_change > 0.02 else (-1 if recent_change < -0.02 else 0)
            )

            return MarketEvent(
                timestamp=self.data.datetime.datetime(0),
                event_type="VOLATILITY_JUMP",
                strength=min((vol_ratio - 1) / 2, 1.0),
                direction=direction,
                confidence=0.7,
            )

        return None

    def _detect_support_resistance_break(self) -> Optional[MarketEvent]:
        """检测支撑阻力突破"""
        if not self.support_levels or not self.resistance_levels:
            return None

        current_price = self.data.close[0]

        # 检测阻力突破
        for resistance in sorted(self.resistance_levels, reverse=True):
            if current_price > resistance * 1.01:  # 突破1%以上
                return MarketEvent(
                    timestamp=self.data.datetime.datetime(0),
                    event_type="RESISTANCE_BREAK",
                    strength=0.6,
                    direction=1,
                    confidence=0.75,
                )

        # 检测支撑跌破
        for support in sorted(self.support_levels):
            if current_price < support * 0.99:  # 跌破1%以上
                return MarketEvent(
                    timestamp=self.data.datetime.datetime(0),
                    event_type="SUPPORT_BREAK",
                    strength=0.6,
                    direction=-1,
                    confidence=0.75,
                )

        return None

    def _process_event(
        self, event: MarketEvent, current_price: float, current_time: datetime
    ):
        """处理检测到的事件"""
        self.log(
            f"🔔 检测到事件: {event.event_type}, 强度:{event.strength:.2f}, 方向:{event.direction}"
        )

        # 记录事件
        self.detected_events.append(event)
        if len(self.detected_events) > 100:  # 限制事件历史
            self.detected_events.pop(0)

        # 设置反应计划
        reaction_datetime = self.data.datetime.datetime(0) + timedelta(
            days=self.p.reaction_time
        )
        self.pending_reactions[reaction_datetime] = {
            "event": event,
            "trigger_price": current_price,
            "processed": False,
        }

    def _check_pending_reactions(self, current_price: float, current_time: datetime):
        """检查待反应事件"""
        reactions_to_remove = []

        for reaction_time, reaction_data in self.pending_reactions.items():
            # 确保时间类型一致
            if (
                isinstance(current_time, type(reaction_time))
                and current_time >= reaction_time
                and not reaction_data["processed"]
            ):
                self._execute_reaction(reaction_data, current_price)
                reaction_data["processed"] = True
                reactions_to_remove.append(reaction_time)

        # 清理已处理的反应
        for reaction_time in reactions_to_remove:
            del self.pending_reactions[reaction_time]

    def _execute_reaction(self, reaction_data: dict, current_price: float):
        """执行事件反应"""
        event = reaction_data["event"]
        trigger_price = reaction_data["trigger_price"]
        position = self.getposition(self.data)

        # 基于事件强度和方向计算置信度
        confidence = event.confidence * event.strength
        confidence = min(confidence, 1.0)

        # 买入反应
        if event.direction > 0 and position.size <= 0:
            self.add_signal(
                self.data, "BUY", confidence, reason=f"{event.event_type}_BUY"
            )
            self.log(f"📈 基于{event.event_type}事件买入, 置信度:{confidence:.2f}")

        # 卖出反应
        elif event.direction < 0 and position.size >= 0:
            self.add_signal(
                self.data, "SELL", confidence, reason=f"{event.event_type}_SELL"
            )
            self.log(f"📉 基于{event.event_type}事件卖出, 置信度:{confidence:.2f}")

    def _update_support_resistance(self):
        """更新支撑阻力位"""
        if len(self.price_history) < self.p.support_resistance_window:
            return

        prices = self.price_history[-self.p.support_resistance_window :]

        # 简单的支撑阻力识别
        price_changes = np.diff(prices)
        local_maxima = []
        local_minima = []

        for i in range(1, len(prices) - 1):
            if prices[i] > prices[i - 1] and prices[i] > prices[i + 1]:
                local_maxima.append(prices[i])
            elif prices[i] < prices[i - 1] and prices[i] < prices[i + 1]:
                local_minima.append(prices[i])

        # 更新支撑阻力位（保留最近的几个）
        if local_maxima:
            self.resistance_levels = sorted(local_maxima)[-3:]  # 最高的3个
        if local_minima:
            self.support_levels = sorted(local_minima)[:3]  # 最低的3个


def run_event_driven_backtest():
    """运行事件驱动回测"""
    print("🔔 事件驱动交易全流程示例")
    print("=" * 50)

    # 加载数据
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
    cerebro.addstrategy(EventDrivenStrategy, printlog=True)

    # 添加风险管理
    cerebro.addanalyzer(DynamicRiskAnalyzer, _name="risk")

    # 设置初始条件
    cerebro.broker.setcash(50000.0)
    cerebro.broker.setcommission(commission=0.001)

    print("\n💰 初始资金: $50,000.00")
    print("🔧 开始事件驱动策略回测...")

    # 运行回测
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()

    # 分析结果
    strategy = results[0]
    risk_analysis = strategy.analyzers.risk.get_analysis()

    returns = (final_value - initial_value) / initial_value

    print("\n🎯 回测结果:")
    print(f"💵 最终资金: ${final_value:,.2f}")
    print(f"📈 总收益率: {returns:.2%}")
    print(f"📉 最大回撤: {risk_analysis['max_drawdown']:.2%}")
    print(f"🛡️  风险等级: {risk_analysis['risk_level']}")

    # 与基准对比
    buy_hold = (df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0]
    print("\n⚖️  策略对比:")
    print(f"   BTC持有收益: {buy_hold:.2%}")
    print(f"   事件驱动策略: {returns:.2%}")
    print(f"   超额收益: {returns - buy_hold:.2%}")

    return results


if __name__ == "__main__":
    run_event_driven_backtest()
