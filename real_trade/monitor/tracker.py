#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
PerformanceTracker - 实时绩效追踪

持续追踪净值曲线、回撤、盈亏比等核心指标。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
from typing import Any, Dict, List


class PerformanceTracker:
    """
    实时绩效追踪器

    Usage::

        tracker = PerformanceTracker(initial_cash=10000)
        # 每根 bar 或每笔交易后
        tracker.update(current_value=10500)
        tracker.record_trade(pnl=50, side="long")
        print(tracker.summary())
    """

    def __init__(self, initial_cash: float = 10000.0):
        self.initial_cash = initial_cash
        self.peak_value = initial_cash
        self.current_value = initial_cash

        # 净值曲线
        self.equity_curve: List[Dict[str, Any]] = []

        # 交易记录
        self.trades: List[Dict[str, Any]] = []
        self.win_count = 0
        self.lose_count = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.max_drawdown = 0.0

    def update(self, current_value: float):
        """更新净值"""
        self.current_value = current_value
        self.peak_value = max(self.peak_value, current_value)

        dd = (
            (self.peak_value - current_value) / self.peak_value
            if self.peak_value > 0
            else 0.0
        )
        self.max_drawdown = max(self.max_drawdown, dd)

        self.equity_curve.append(
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "value": current_value,
                "drawdown": dd,
            }
        )

    def record_trade(self, pnl: float, side: str = "long"):
        """记录交易"""
        self.trades.append(
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "pnl": pnl,
                "side": side,
            }
        )
        if pnl > 0:
            self.win_count += 1
            self.total_profit += pnl
        else:
            self.lose_count += 1
            self.total_loss += abs(pnl)

    @property
    def trade_count(self) -> int:
        return self.win_count + self.lose_count

    @property
    def win_rate(self) -> float:
        return self.win_count / self.trade_count if self.trade_count > 0 else 0.0

    @property
    def profit_factor(self) -> float:
        return (
            self.total_profit / self.total_loss if self.total_loss > 0 else float("inf")
        )

    @property
    def net_pnl(self) -> float:
        return self.total_profit - self.total_loss

    @property
    def return_pct(self) -> float:
        return (
            (self.current_value - self.initial_cash) / self.initial_cash
            if self.initial_cash > 0
            else 0.0
        )

    def summary(self) -> Dict[str, Any]:
        return {
            "initial_cash": self.initial_cash,
            "current_value": self.current_value,
            "return_pct": f"{self.return_pct:.2%}",
            "net_pnl": round(self.net_pnl, 4),
            "max_drawdown": f"{self.max_drawdown:.2%}",
            "trade_count": self.trade_count,
            "win_rate": f"{self.win_rate:.2%}",
            "profit_factor": round(self.profit_factor, 2),
        }
