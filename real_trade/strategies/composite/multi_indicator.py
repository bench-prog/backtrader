#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
多指标复合策略

同时使用趋势（EMA）+ 动量（RSI）+ 波动（BB）三重确认，
只有当多个指标同时确认时才开仓，降低假信号。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
from real_trade.strategies.base import RealTradeStrategyBase


class MultiIndicatorStrategy(RealTradeStrategyBase):
    """三重确认复合策略"""

    params = (
        # 趋势
        ("ema_fast", 12),
        ("ema_slow", 26),
        # 动量
        ("rsi_period", 14),
        ("rsi_entry", 40),  # RSI > 此值 = 动量确认
        ("rsi_exit", 60),  # RSI > 此值 = 超买退出
        # 波动
        ("bb_period", 20),
        ("bb_devfactor", 2.0),
        # 确认
        ("min_signals", 2),  # 至少需要几个指标确认（1-3）
        ("order_size", None),
    )

    def __init__(self):
        super().__init__()
        self.ema_fast = bt.indicators.EMA(period=self.params.ema_fast)
        self.ema_slow = bt.indicators.EMA(period=self.params.ema_slow)
        self.rsi = bt.indicators.RSI(period=self.params.rsi_period)
        self.bb = bt.indicators.BollingerBands(
            period=self.params.bb_period,
            devfactor=self.params.bb_devfactor,
        )

    def _count_buy_signals(self) -> int:
        count = 0
        # 趋势确认：快线在慢线之上
        if self.ema_fast[0] > self.ema_slow[0]:
            count += 1
        # 动量确认：RSI 有上升动量
        if self.rsi[0] > self.params.rsi_entry:
            count += 1
        # 波动确认：价格靠近下轨（便宜）
        if self.data.close[0] <= self.bb.mid[0]:
            count += 1
        return count

    def _count_sell_signals(self) -> int:
        count = 0
        if self.ema_fast[0] < self.ema_slow[0]:
            count += 1
        if self.rsi[0] > self.params.rsi_exit:
            count += 1
        if self.data.close[0] >= self.bb.top[0]:
            count += 1
        return count

    def next(self):
        if self.order:
            return

        if self.position:
            if self.check_stop_loss() or self.check_take_profit():
                self.order = self.sell(size=self.position.size)
                return
            sell_signals = self._count_sell_signals()
            if sell_signals >= self.params.min_signals:
                self.log(f"COMPOSITE SELL  signals={sell_signals}/3")
                self.order = self.sell(size=self.position.size)
        else:
            buy_signals = self._count_buy_signals()
            if buy_signals >= self.params.min_signals:
                self.log(f"COMPOSITE BUY   signals={buy_signals}/3")
                size = self.params.order_size or self.calc_position_size()
                self.order = self.buy(size=size)
