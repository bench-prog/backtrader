#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
放量突破策略

价格突破近期高点 + 成交量放大确认，做多。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
from real_trade.strategies.base import RealTradeStrategyBase


class VolumeBreakoutStrategy(RealTradeStrategyBase):
    """放量突破策略"""

    params = (
        ("breakout_period", 20),  # 突破回看周期
        ("vol_ma_period", 20),  # 成交量均线周期
        ("vol_multiplier", 1.5),  # 成交量放大倍数
        ("atr_period", 14),  # ATR 周期（用于追踪止损）
        ("atr_stop_mult", 2.0),  # ATR 止损倍数
        ("order_size", None),
    )

    def __init__(self):
        super().__init__()
        self.highest = bt.indicators.Highest(
            self.data.high, period=self.params.breakout_period
        )
        self.vol_ma = bt.indicators.SMA(
            self.data.volume, period=self.params.vol_ma_period
        )
        self.atr = bt.indicators.ATR(period=self.params.atr_period)

    def next(self):
        if self.order:
            return

        if self.position:
            if self.check_stop_loss() or self.check_take_profit():
                self.order = self.sell(size=self.position.size)
                return
            # ATR 追踪止损
            if self.buyprice:
                trail_stop = (
                    self.data.close[0] - self.atr[0] * self.params.atr_stop_mult
                )
                if self.data.close[0] < trail_stop:
                    self.log(f"ATR TRAIL STOP  price={self.data.close[0]:.4f}")
                    self.order = self.sell(size=self.position.size)
        else:
            # 价格突破 + 放量
            is_breakout = self.data.close[0] > self.highest[-1]
            is_vol_surge = (
                self.data.volume[0] > self.vol_ma[0] * self.params.vol_multiplier
            )

            if is_breakout and is_vol_surge:
                size = self.params.order_size or self.calc_position_size()
                self.order = self.buy(size=size)
