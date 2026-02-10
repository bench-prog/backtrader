#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
SuperTrend 策略

基于 ATR 的趋势跟踪指标，价格突破上轨做多，跌破下轨平仓。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
from real_trade.strategies.base import RealTradeStrategyBase


class _SuperTrend(bt.Indicator):
    """SuperTrend 指标实现"""

    lines = (
        "super_trend",
        "direction",
    )
    params = (
        ("period", 10),
        ("multiplier", 3.0),
    )
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.atr = bt.indicators.ATR(period=self.params.period)
        self.hl2 = (self.data.high + self.data.low) / 2.0

    def next(self):
        atr_val = self.atr[0] * self.params.multiplier
        upper = self.hl2[0] + atr_val
        lower = self.hl2[0] - atr_val

        if len(self) == 1:
            self.lines.super_trend[0] = lower
            self.lines.direction[0] = 1
            return

        prev_st = self.lines.super_trend[-1]
        prev_dir = self.lines.direction[-1]

        if prev_dir == 1:  # 之前多头
            lower = max(lower, prev_st)
            if self.data.close[0] < lower:
                self.lines.super_trend[0] = upper
                self.lines.direction[0] = -1
            else:
                self.lines.super_trend[0] = lower
                self.lines.direction[0] = 1
        else:  # 之前空头
            upper = min(upper, prev_st)
            if self.data.close[0] > upper:
                self.lines.super_trend[0] = lower
                self.lines.direction[0] = 1
            else:
                self.lines.super_trend[0] = upper
                self.lines.direction[0] = -1


class SuperTrendStrategy(RealTradeStrategyBase):
    """SuperTrend 趋势策略"""

    params = (
        ("atr_period", 10),
        ("atr_multiplier", 3.0),
        ("order_size", None),
    )

    def __init__(self):
        super().__init__()
        self.st = _SuperTrend(
            period=self.params.atr_period,
            multiplier=self.params.atr_multiplier,
        )

    def next(self):
        if self.order:
            return

        direction = self.st.direction[0]

        if self.position:
            if self.check_stop_loss() or self.check_take_profit():
                self.order = self.sell(size=self.position.size)
                return
            if direction < 0:
                self.order = self.sell(size=self.position.size)
        else:
            if direction > 0:
                size = self.params.order_size or self.calc_position_size()
                self.order = self.buy(size=size)
