#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
MACD 趋势策略

MACD 金叉做多，死叉平仓，可选 MACD 柱状图过滤。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
from real_trade.strategies.base import RealTradeStrategyBase


class MACDTrendStrategy(RealTradeStrategyBase):
    """MACD 趋势跟踪策略"""

    params = (
        ("fast_ema", 12),
        ("slow_ema", 26),
        ("signal_period", 9),
        ("order_size", None),
        ("histogram_filter", False),  # 是否要求柱状图为正才开仓
    )

    def __init__(self):
        super().__init__()
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_ema,
            period_me2=self.params.slow_ema,
            period_signal=self.params.signal_period,
        )
        self.mcross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

    def next(self):
        if self.order:
            return

        if self.position:
            if self.check_stop_loss() or self.check_take_profit():
                self.order = self.sell(size=self.position.size)
                return
            if self.mcross < 0:
                self.order = self.sell(size=self.position.size)
        else:
            if self.mcross > 0:
                if self.params.histogram_filter and self.macd.macd[0] <= 0:
                    return
                size = self.params.order_size or self.calc_position_size()
                self.order = self.buy(size=size)
