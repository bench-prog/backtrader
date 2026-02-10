#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
布林带均值回归策略

价格触及下轨做多，触及上轨平仓（或做空），回归中轨为目标。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
from real_trade.strategies.base import RealTradeStrategyBase


class BollingerBandStrategy(RealTradeStrategyBase):
    """布林带回归策略"""

    params = (
        ("bb_period", 20),
        ("bb_devfactor", 2.0),
        ("order_size", None),
        ("use_mid_exit", True),  # True=触及中轨平仓, False=触及上轨平仓
    )

    def __init__(self):
        super().__init__()
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period,
            devfactor=self.params.bb_devfactor,
        )

    def next(self):
        if self.order:
            return

        if self.position:
            if self.check_stop_loss() or self.check_take_profit():
                self.order = self.sell(size=self.position.size)
                return

            exit_line = self.bb.mid if self.params.use_mid_exit else self.bb.top
            if self.data.close[0] >= exit_line[0]:
                self.order = self.sell(size=self.position.size)
        else:
            if self.data.close[0] <= self.bb.bot[0]:
                size = self.params.order_size or self.calc_position_size()
                self.order = self.buy(size=size)
