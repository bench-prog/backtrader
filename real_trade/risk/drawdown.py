#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
DrawdownGuard - 回撤控制

当账户从峰值回撤超过阈值时，暂停开仓。
"""

from __future__ import absolute_import, division, print_function, unicode_literals


class DrawdownGuard:
    """最大回撤保护"""

    def __init__(self, max_drawdown_pct: float = 0.20):
        """
        Args:
            max_drawdown_pct: 最大允许回撤比例，如 0.20 = 20%
        """
        self.max_drawdown_pct = max_drawdown_pct

    def allow(self, current_value: float, peak_value: float) -> bool:
        """
        当前是否允许开仓

        Args:
            current_value: 当前账户总价值
            peak_value: 历史最高价值
        """
        if peak_value <= 0:
            return True

        drawdown = (peak_value - current_value) / peak_value
        return drawdown < self.max_drawdown_pct

    @staticmethod
    def calc_drawdown(current_value: float, peak_value: float) -> float:
        """计算当前回撤比例"""
        if peak_value <= 0:
            return 0.0
        return (peak_value - current_value) / peak_value
