#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
RSI 超买超卖均值回归策略

RSI 跌入超卖区做多，升入超买区平仓。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
from real_trade.strategies.base import RealTradeStrategyBase


class RSIReversionStrategy(RealTradeStrategyBase):
    """RSI 均值回归策略"""

    params = (
        ("rsi_period", 14),
        ("oversold", 30),
        ("overbought", 70),
        ("order_size", None),
    )

    def __init__(self):
        super().__init__()
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)

    def next(self):
        if self.order:
            return

        if self.position:
            if self.check_stop_loss() or self.check_take_profit():
                self.order = self.sell(size=self.position.size)
                return
            if self.rsi[0] >= self.params.overbought:
                self.order = self.sell(size=self.position.size)
        else:
            if self.rsi[0] <= self.params.oversold:
                size = self.params.order_size or self.calc_position_size()
                self.order = self.buy(size=size)
