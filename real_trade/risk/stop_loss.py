#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
StopLoss - 止损策略

提供多种止损计算方式：
- FixedStopLoss:    固定百分比止损
- TrailingStopLoss: 移动追踪止损
- ATRStopLoss:      基于 ATR 的动态止损
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from typing import Optional


class FixedStopLoss:
    """固定百分比止损"""

    def __init__(self, pct: float = 0.02):
        self.pct = pct

    def calc_stop(self, entry_price: float, side: str = "long") -> float:
        if side == "long":
            return entry_price * (1.0 - self.pct)
        return entry_price * (1.0 + self.pct)

    def should_stop(
        self, entry_price: float, current_price: float, side: str = "long"
    ) -> bool:
        stop = self.calc_stop(entry_price, side)
        if side == "long":
            return current_price <= stop
        return current_price >= stop


class TrailingStopLoss:
    """
    移动追踪止损

    止损价跟随最高价（多头）或最低价（空头）移动，
    只朝有利方向调整，永不回退。
    """

    def __init__(self, pct: float = 0.03):
        self.pct = pct
        self._best_price: Optional[float] = None
        self._side: str = "long"

    def reset(self, entry_price: float, side: str = "long"):
        self._best_price = entry_price
        self._side = side

    def update(self, current_price: float):
        """更新最优价格（每根 bar 调用一次）"""
        if self._best_price is None:
            self._best_price = current_price
            return

        if self._side == "long":
            self._best_price = max(self._best_price, current_price)
        else:
            self._best_price = min(self._best_price, current_price)

    @property
    def stop_price(self) -> Optional[float]:
        if self._best_price is None:
            return None
        if self._side == "long":
            return self._best_price * (1.0 - self.pct)
        return self._best_price * (1.0 + self.pct)

    def should_stop(self, current_price: float) -> bool:
        self.update(current_price)
        sp = self.stop_price
        if sp is None:
            return False
        if self._side == "long":
            return current_price <= sp
        return current_price >= sp


class ATRStopLoss:
    """
    基于 ATR 的动态止损

    止损距离 = ATR * multiplier，波动大时止损更远。
    """

    def __init__(self, multiplier: float = 2.0):
        self.multiplier = multiplier

    def calc_stop(
        self, entry_price: float, atr_value: float, side: str = "long"
    ) -> float:
        distance = atr_value * self.multiplier
        if side == "long":
            return entry_price - distance
        return entry_price + distance

    def should_stop(
        self,
        entry_price: float,
        current_price: float,
        atr_value: float,
        side: str = "long",
    ) -> bool:
        stop = self.calc_stop(entry_price, atr_value, side)
        if side == "long":
            return current_price <= stop
        return current_price >= stop
