#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
动态网格策略

基于 ATR 自适应调整网格间距，波动大时拉宽间距、波动小时收窄间距。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
from real_trade.strategies.base import RealTradeStrategyBase


class DynamicGridStrategy(RealTradeStrategyBase):
    """ATR 自适应动态网格策略"""

    params = (
        ("atr_period", 14),
        ("atr_multiplier", 1.0),  # 网格间距 = ATR * multiplier
        ("grid_count", 5),  # 上下各几格
        ("order_size", None),
        ("rebalance_bars", 50),  # 每隔多少 bar 重建网格
    )

    def __init__(self):
        super().__init__()
        self.atr = bt.indicators.ATR(period=self.params.atr_period)
        self.grids = []
        self.grid_orders = {}
        self._last_build_bar = -999

    def _build_grids(self):
        """根据当前 ATR 构建动态网格"""
        center = self.data.close[0]
        step = self.atr[0] * self.params.atr_multiplier
        n = self.params.grid_count

        self.grids = [center + step * i for i in range(-n, n + 1)]
        self.grid_orders.clear()
        self._last_build_bar = len(self.data)

        self.log(
            f"DYNAMIC GRID  center={center:.2f}  step={step:.2f}  "
            f"range=[{self.grids[0]:.2f}, {self.grids[-1]:.2f}]"
        )

    def _get_grid_size(self):
        if self.params.order_size:
            return self.params.order_size
        return self.calc_position_size() / (self.params.grid_count * 2)

    def next(self):
        # 定期重建网格
        bars_since = len(self.data) - self._last_build_bar
        if not self.grids or bars_since >= self.params.rebalance_bars:
            self._build_grids()
            return

        price = self.data.close[0]
        prev_price = self.data.close[-1] if len(self.data) > 1 else price
        size = self._get_grid_size()

        for i, grid_price in enumerate(self.grids):
            if i in self.grid_orders:
                continue

            if prev_price > grid_price >= price:
                self.log(f"DYN GRID BUY  grid#{i} price={grid_price:.2f}")
                self.grid_orders[i] = self.buy(size=size)
            elif prev_price < grid_price <= price and self.position:
                sell_size = min(size, self.position.size)
                if sell_size > 0:
                    self.log(f"DYN GRID SELL grid#{i} price={grid_price:.2f}")
                    self.grid_orders[i] = self.sell(size=sell_size)

    def notify_order(self, order):
        super().notify_order(order)
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            to_remove = [k for k, v in self.grid_orders.items() if v is order]
            for k in to_remove:
                del self.grid_orders[k]
