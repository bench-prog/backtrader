#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Strategies - 共享策略库

按策略类型分类：
- trend:           趋势跟踪策略（均线交叉、MACD、SuperTrend 等）
- mean_reversion:  均值回归策略（布林带、RSI 超买超卖等）
- momentum:        动量策略（RSI 动量、放量突破等）
- grid:            网格策略（等差网格、动态网格等）
- composite:       复合策略（多指标组合等）
"""

from .base import RealTradeStrategyBase

__all__ = [
    "RealTradeStrategyBase",
]
