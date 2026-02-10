#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""趋势跟踪策略"""

from .ma_cross import MACrossStrategy
from .macd_trend import MACDTrendStrategy
from .supertrend import SuperTrendStrategy

__all__ = ["MACrossStrategy", "MACDTrendStrategy", "SuperTrendStrategy"]
