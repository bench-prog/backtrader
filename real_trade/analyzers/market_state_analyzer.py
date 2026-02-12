#!/usr/bin/env python3
"""
Backtrader市场状态分析器
将市场状态识别系统重构为标准的backtrader Analyzer组件
"""

from collections import deque
from typing import Dict, List, Tuple

import numpy as np

import backtrader as bt


class MarketStateAnalyzer(bt.Analyzer):
    """
    市场状态分析器
    继承自bt.Analyzer，实时识别市场趋势、波动率和支撑阻力位
    """

    params = (
        ("trend_window", 20),  # 趋势判断窗口
        ("volatility_window", 30),  # 波动率计算窗口
        ("support_resistance_window", 50),  # 支撑阻力窗口
        ("min_trend_strength", 0.6),  # 最小趋势强度阈值
        ("volume_confirmation", True),  # 是否需要成交量确认
    )

    def __init__(self):
        super().__init__()

        # 数据存储
        self.prices = deque(
            maxlen=max(
                self.p.trend_window,
                self.p.volatility_window,
                self.p.support_resistance_window,
            )
        )
        self.volumes = deque(maxlen=self.p.support_resistance_window)
        self.highs = deque(maxlen=self.p.support_resistance_window)
        self.lows = deque(maxlen=self.p.support_resistance_window)

        # 状态历史
        self.trend_history = []
        self.volatility_history = []
        self.support_resistance_history = []

        # 当前状态
        self.current_trend = "NEUTRAL"
        self.trend_strength = 0.0
        self.current_volatility = 0.0
        self.support_levels = []
        self.resistance_levels = []
        self.market_regime = "CONSOLIDATION"

    def _detect_trend(self, prices: List[float]) -> Tuple[str, float]:
        """检测趋势方向和强度"""
        if len(prices) < self.p.trend_window:
            return "NEUTRAL", 0.0

        # 计算移动平均线
        prices_array = np.array(prices)
        short_ma = np.mean(prices_array[-10:])
        long_ma = np.mean(prices_array[-self.p.trend_window :])

        # 趋势强度计算
        price_changes = np.diff(prices_array[-self.p.trend_window :])
        positive_changes = np.sum(price_changes > 0)
        negative_changes = np.sum(price_changes < 0)

        trend_strength = abs(positive_changes - negative_changes) / len(price_changes)

        # 趋势判断
        if short_ma > long_ma and trend_strength >= self.p.min_trend_strength:
            return "UP", trend_strength
        elif short_ma < long_ma and trend_strength >= self.p.min_trend_strength:
            return "DOWN", trend_strength
        else:
            return "NEUTRAL", trend_strength

    def _calculate_volatility(self, prices: List[float]) -> float:
        """计算波动率"""
        if len(prices) < self.p.volatility_window:
            return 0.0

        prices_array = np.array(prices[-self.p.volatility_window :])
        returns = np.diff(np.log(prices_array))
        return np.std(returns) * np.sqrt(252)  # 年化波动率

    def _detect_support_resistance(
        self, highs: List[float], lows: List[float], prices: List[float]
    ) -> Tuple[List[float], List[float]]:
        """检测支撑阻力位"""
        if len(prices) < 20:
            return [], []

        # 转换为numpy数组
        highs_array = np.array(highs)
        lows_array = np.array(lows)
        prices_array = np.array(prices)

        # 寻找局部极值点
        support_candidates = []
        resistance_candidates = []

        # 检测支撑位（局部低点）
        for i in range(5, len(lows_array) - 5):
            if (
                lows_array[i] <= lows_array[i - 5 : i].min()
                and lows_array[i] <= lows_array[i + 1 : i + 6].min()
            ):
                support_candidates.append(lows_array[i])

        # 检测阻力位（局部高点）
        for i in range(5, len(highs_array) - 5):
            if (
                highs_array[i] >= highs_array[i - 5 : i].max()
                and highs_array[i] >= highs_array[i + 1 : i + 6].max()
            ):
                resistance_candidates.append(highs_array[i])

        # 聚类相似价位
        support_levels = self._cluster_levels(support_candidates)
        resistance_levels = self._cluster_levels(resistance_candidates)

        return support_levels, resistance_levels

    def _cluster_levels(
        self, levels: List[float], threshold: float = 0.01
    ) -> List[float]:
        """聚类相近的价格水平"""
        if not levels:
            return []

        levels_sorted = sorted(levels)
        clusters = [[levels_sorted[0]]]

        for level in levels_sorted[1:]:
            if abs(level - clusters[-1][-1]) / clusters[-1][-1] <= threshold:
                clusters[-1].append(level)
            else:
                clusters.append([level])

        # 返回每个聚类的平均值
        return [np.mean(cluster) for cluster in clusters]

    def _determine_market_regime(
        self, trend: str, trend_strength: float, volatility: float
    ) -> str:
        """确定市场制度"""
        if trend != "NEUTRAL" and trend_strength > 0.7:
            if volatility > 0.3:
                return "VOLATILE_TREND"
            else:
                return "STABLE_TREND"
        elif volatility > 0.4:
            return "HIGH_VOLATILITY"
        else:
            return "CONSOLIDATION"

    def next(self):
        """每个bar执行"""
        # 收集数据
        self.prices.append(self.data.close[0])
        self.highs.append(self.data.high[0])
        self.lows.append(self.data.low[0])
        self.volumes.append(self.data.volume[0])

        # 分析市场状态
        if len(self.prices) >= max(10, self.p.trend_window):
            # 趋势分析
            self.current_trend, self.trend_strength = self._detect_trend(
                list(self.prices)
            )
            self.trend_history.append(
                (
                    self.strategy.datetime.datetime(),
                    self.current_trend,
                    self.trend_strength,
                )
            )

            # 波动率分析
            self.current_volatility = self._calculate_volatility(list(self.prices))
            self.volatility_history.append(
                (self.strategy.datetime.datetime(), self.current_volatility)
            )

            # 支撑阻力分析
            if len(self.highs) >= 20:
                self.support_levels, self.resistance_levels = (
                    self._detect_support_resistance(
                        list(self.highs), list(self.lows), list(self.prices)
                    )
                )
                self.support_resistance_history.append(
                    (
                        self.strategy.datetime.datetime(),
                        self.support_levels[:3],  # 只保存前3个
                        self.resistance_levels[:3],
                    )
                )

            # 市场制度判定
            self.market_regime = self._determine_market_regime(
                self.current_trend, self.trend_strength, self.current_volatility
            )

    def get_analysis(self) -> Dict:
        """获取分析结果"""
        return {
            "current_trend": self.current_trend,
            "trend_strength": self.trend_strength,
            "current_volatility": self.current_volatility,
            "market_regime": self.market_regime,
            "support_levels": self.support_levels,
            "resistance_levels": self.resistance_levels,
            "trend_history": self.trend_history,
            "volatility_history": self.volatility_history,
            "support_resistance_history": self.support_resistance_history,
        }

    def get_signal_adjustment(self) -> float:
        """获取信号调整系数"""
        adjustment = 1.0

        # 根据市场制度调整
        regime_multipliers = {
            "STABLE_TREND": 1.2,  # 稳定趋势，增加信号权重
            "VOLATILE_TREND": 0.8,  # 波动趋势，减少信号权重
            "HIGH_VOLATILITY": 0.6,  # 高波动，大幅减少信号权重
            "CONSOLIDATION": 0.4,  # 震荡市，最小信号权重
        }

        adjustment *= regime_multipliers.get(self.market_regime, 1.0)

        # 根据趋势强度调整
        adjustment *= 0.5 + 0.5 * self.trend_strength

        return adjustment


class MarketStateFilter:
    """
    市场状态过滤器
    根据市场状态分析结果过滤交易信号
    """

    def __init__(self, analyzer: MarketStateAnalyzer):
        self.analyzer = analyzer

    def filter_signal(self, signal_type: str, confidence: float) -> Tuple[bool, float]:
        """
        过滤交易信号
        返回: (是否执行, 调整后的置信度)
        """
        # 获取信号调整系数
        adjustment = self.analyzer.get_signal_adjustment()
        adjusted_confidence = confidence * adjustment

        # 根据市场状态决定是否执行
        market_regime = self.analyzer.market_regime
        trend = self.analyzer.current_trend

        # 在震荡市中过滤掉趋势信号
        if market_regime == "CONSOLIDATION":
            if signal_type in ["BUY", "SELL"] and adjusted_confidence < 0.8:
                return False, adjusted_confidence

        # 在趋势市中加强同向信号
        elif "TREND" in market_regime:
            if (trend == "UP" and signal_type == "BUY") or (
                trend == "DOWN" and signal_type == "SELL"
            ):
                adjusted_confidence = min(1.0, adjusted_confidence * 1.2)
            else:
                # 反向信号需要更高置信度
                if adjusted_confidence < 0.9:
                    return False, adjusted_confidence

        # 高波动市场需要更高置信度
        elif market_regime == "HIGH_VOLATILITY":
            if adjusted_confidence < 0.85:
                return False, adjusted_confidence

        return True, adjusted_confidence
