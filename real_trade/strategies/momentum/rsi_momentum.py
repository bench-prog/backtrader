#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
RSI 动量策略

RSI 突破 50 中轴做多（确认上升动量），跌破 50 平仓。
与 RSI 均值回归不同，此策略利用 RSI 作为动量确认信号。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
from real_trade.strategies.base import RealTradeStrategyBase


class RSIMomentumStrategy(RealTradeStrategyBase):
    """RSI 动量策略"""

    params = (
        ("rsi_period", 14),
        ("entry_level", 55),  # RSI 高于此值 = 动量确认
        ("exit_level", 45),  # RSI 低于此值 = 动量衰减
        ("sma_filter", 50),  # SMA 趋势过滤周期，0=不过滤
        ("order_size", None),
    )

    def __init__(self):
        super().__init__()
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.sma = None
        if self.params.sma_filter > 0:
            self.sma = bt.indicators.SMA(self.data.close, period=self.params.sma_filter)

    def next(self):
        if self.order:
            return

        if self.position:
            if self.check_stop_loss() or self.check_take_profit():
                self.order = self.sell(size=self.position.size)
                return
            if self.rsi[0] < self.params.exit_level:
                self.order = self.sell(size=self.position.size)
        else:
            if self.rsi[0] > self.params.entry_level:
                # 可选 SMA 趋势过滤
                if self.sma and self.data.close[0] < self.sma[0]:
                    return
                size = self.params.order_size or self.calc_position_size()
                self.order = self.buy(size=size)
