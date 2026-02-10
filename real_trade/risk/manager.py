#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
RiskManager - 风控管理器

统一入口，组合仓位计算、止损策略、交易限制等子模块。
可作为 backtrader Sizer 或独立使用。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from typing import Any, Dict, Optional

from .drawdown import DrawdownGuard
from .limits import TradeLimiter
from .position_sizer import FixedRatioSizer
from .stop_loss import FixedStopLoss


class RiskManager:
    """
    风控管理器

    将仓位计算、止损、限制、回撤控制组合为统一的风控决策层。

    Usage::

        rm = RiskManager(
            max_position_pct=0.3,
            max_drawdown_pct=0.15,
            max_daily_trades=20,
        )

        # 在策略中
        size = rm.calc_size(broker, data)
        if rm.allow_trade(broker):
            order = self.buy(size=size)
    """

    def __init__(
        self,
        max_position_pct: float = 0.3,
        risk_per_trade: float = 0.02,
        max_drawdown_pct: float = 0.20,
        max_daily_trades: int = 50,
        max_daily_loss: float = 0.0,
        stop_loss_pct: Optional[float] = None,
    ):
        self.sizer = FixedRatioSizer(
            risk_pct=risk_per_trade,
            max_position_pct=max_position_pct,
        )
        self.stop_loss = FixedStopLoss(pct=stop_loss_pct) if stop_loss_pct else None
        self.limiter = TradeLimiter(
            max_daily_trades=max_daily_trades,
            max_daily_loss=max_daily_loss,
        )
        self.drawdown_guard = DrawdownGuard(max_drawdown_pct=max_drawdown_pct)

        self._peak_value = 0.0

    def calc_size(self, broker, data) -> float:
        """计算建议仓位"""
        return self.sizer.calc(broker, data)

    def allow_trade(self, broker) -> bool:
        """综合判断是否允许开仓"""
        current_value = broker.getvalue()
        self._peak_value = max(self._peak_value, current_value)

        if not self.limiter.allow():
            return False
        if not self.drawdown_guard.allow(current_value, self._peak_value):
            return False
        return True

    def record_trade(self, pnl: float = 0.0):
        """记录一笔交易，更新限制器状态"""
        self.limiter.record(pnl)

    def get_stop_price(self, entry_price: float, side: str = "long") -> Optional[float]:
        """获取止损价"""
        if self.stop_loss is None:
            return None
        return self.stop_loss.calc_stop(entry_price, side)

    def status(self) -> Dict[str, Any]:
        return {
            "daily_trades": self.limiter.daily_trade_count,
            "daily_pnl": self.limiter.daily_pnl,
            "peak_value": self._peak_value,
        }
