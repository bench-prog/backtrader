#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
均线交叉策略

支持 SMA/EMA，快慢线金叉做多、死叉平仓。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
from real_trade.strategies.base import RealTradeStrategyBase


class MACrossStrategy(RealTradeStrategyBase):
    """双均线交叉策略"""

    params = (
        ("fast_period", 10),
        ("slow_period", 30),
        ("ma_type", "sma"),  # "sma" 或 "ema"
        ("order_size", None),  # None = 使用 calc_position_size
    )

    _MA_MAP = {
        "sma": bt.indicators.SMA,
        "ema": bt.indicators.EMA,
    }

    def __init__(self):
        super().__init__()
        ma_cls = self._MA_MAP.get(self.params.ma_type, bt.indicators.SMA)
        self.fast_ma = ma_cls(self.data.close, period=self.params.fast_period)
        self.slow_ma = ma_cls(self.data.close, period=self.params.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if self.order:
            return

        if self.position:
            if self.check_stop_loss() or self.check_take_profit():
                self.order = self.sell(size=self.position.size)
                return
            if self.crossover < 0:
                self.order = self.sell(size=self.position.size)
        else:
            if self.crossover > 0:
                size = self.params.order_size or self.calc_position_size()
                self.order = self.buy(size=size)
