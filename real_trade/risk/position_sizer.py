#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
PositionSizer - 仓位计算

提供多种仓位管理策略：
- FixedRatioSizer:  固定比例（每笔风险占账户 N%）
- KellySizer:       凯利公式
- ATRSizer:         基于 ATR 波动率
"""

from __future__ import absolute_import, division, print_function, unicode_literals


class FixedRatioSizer:
    """固定比例仓位计算"""

    def __init__(self, risk_pct: float = 0.02, max_position_pct: float = 1.0):
        self.risk_pct = risk_pct
        self.max_position_pct = max_position_pct

    def calc(self, broker, data) -> float:
        value = broker.getvalue()
        price = data.close[0]
        if price <= 0:
            return 0.0

        size = (value * self.risk_pct) / price
        max_size = (value * self.max_position_pct) / price
        return min(size, max_size)


class KellySizer:
    """
    凯利公式仓位计算

    f* = (bp - q) / b
    b = 平均盈亏比, p = 胜率, q = 1-p
    """

    def __init__(
        self,
        win_rate: float = 0.5,
        avg_win_loss_ratio: float = 1.5,
        fraction: float = 0.5,  # 半凯利，更保守
        max_position_pct: float = 0.3,
    ):
        self.win_rate = win_rate
        self.avg_win_loss_ratio = avg_win_loss_ratio
        self.fraction = fraction
        self.max_position_pct = max_position_pct

    def update_stats(self, win_rate: float, avg_win_loss_ratio: float):
        """根据实际交易结果更新统计"""
        self.win_rate = win_rate
        self.avg_win_loss_ratio = avg_win_loss_ratio

    def calc(self, broker, data) -> float:
        value = broker.getvalue()
        price = data.close[0]
        if price <= 0:
            return 0.0

        b = self.avg_win_loss_ratio
        p = self.win_rate
        q = 1.0 - p

        kelly_pct = (b * p - q) / b if b > 0 else 0.0
        kelly_pct = max(0.0, kelly_pct) * self.fraction
        kelly_pct = min(kelly_pct, self.max_position_pct)

        return (value * kelly_pct) / price


class ATRSizer:
    """
    基于 ATR 波动率的仓位计算

    仓位 = (账户价值 * risk_pct) / (ATR * multiplier)
    波动越大仓位越小。
    """

    def __init__(
        self,
        risk_pct: float = 0.02,
        atr_multiplier: float = 2.0,
        max_position_pct: float = 0.3,
    ):
        self.risk_pct = risk_pct
        self.atr_multiplier = atr_multiplier
        self.max_position_pct = max_position_pct

    def calc(self, broker, data, atr_value: float = 0.0) -> float:
        """
        Args:
            atr_value: 当前 ATR 值（需从策略中传入）
        """
        value = broker.getvalue()
        price = data.close[0]
        if price <= 0 or atr_value <= 0:
            return 0.0

        risk_amount = value * self.risk_pct
        risk_per_unit = atr_value * self.atr_multiplier
        size = risk_amount / risk_per_unit

        max_size = (value * self.max_position_pct) / price
        return min(size, max_size)
