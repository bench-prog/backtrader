#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
等差网格策略

在固定价格区间内等距设置买卖网格线，价格下穿网格线买入，
上穿网格线卖出，赚取震荡利润。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from real_trade.strategies.base import RealTradeStrategyBase


class FixedGridStrategy(RealTradeStrategyBase):
    """等差网格策略"""

    params = (
        ("grid_upper", 0.0),  # 网格上界（0=自动计算）
        ("grid_lower", 0.0),  # 网格下界（0=自动计算）
        ("grid_count", 10),  # 网格数量
        ("auto_range_period", 50),  # 自动计算区间的回看周期
        ("order_size", None),  # 每格下单量
        ("total_invest", None),  # 总投资额（与 order_size 二选一）
    )

    def __init__(self):
        super().__init__()
        self.grids = []
        self.grid_orders = {}  # {grid_index: order}
        self._grids_built = False

    def _build_grids(self):
        """构建网格"""
        upper = self.params.grid_upper
        lower = self.params.grid_lower

        # 自动计算区间
        if upper == 0.0 or lower == 0.0:
            period = min(self.params.auto_range_period, len(self.data))
            highs = [self.data.high[-i] for i in range(period)]
            lows = [self.data.low[-i] for i in range(period)]
            upper = max(highs) * 1.02
            lower = min(lows) * 0.98

        step = (upper - lower) / self.params.grid_count
        self.grids = [lower + step * i for i in range(self.params.grid_count + 1)]

        self.log(
            f"GRID BUILT  range=[{lower:.2f}, {upper:.2f}]  "
            f"count={self.params.grid_count}  step={step:.2f}"
        )
        self._grids_built = True

    def _get_grid_size(self):
        """计算每格下单量"""
        if self.params.order_size:
            return self.params.order_size
        if self.params.total_invest:
            return (
                self.params.total_invest / self.params.grid_count / self.data.close[0]
            )
        return self.calc_position_size() / self.params.grid_count

    def next(self):
        if not self._grids_built:
            if len(self.data) >= self.params.auto_range_period:
                self._build_grids()
            return

        price = self.data.close[0]
        prev_price = self.data.close[-1] if len(self.data) > 1 else price

        size = self._get_grid_size()

        for i, grid_price in enumerate(self.grids):
            if i in self.grid_orders:
                continue

            # 价格下穿网格线 -> 买入
            if prev_price > grid_price >= price:
                self.log(f"GRID BUY  grid#{i} price={grid_price:.2f}")
                self.grid_orders[i] = self.buy(size=size)

            # 价格上穿网格线 -> 卖出已有仓位
            elif prev_price < grid_price <= price and self.position:
                self.log(f"GRID SELL grid#{i} price={grid_price:.2f}")
                sell_size = min(size, self.position.size)
                if sell_size > 0:
                    self.grid_orders[i] = self.sell(size=sell_size)

    def notify_order(self, order):
        super().notify_order(order)
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            # 清理已完成的网格订单，允许再次触发
            to_remove = [k for k, v in self.grid_orders.items() if v is order]
            for k in to_remove:
                del self.grid_orders[k]
