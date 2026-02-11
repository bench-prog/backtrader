#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Feeds Module - 数据源

提供各交易所的 Data Feed 实现。
"""

from .basedata import BaseData
from .basewebsocket import BaseWebSocket

try:
    from .binancedata import BinanceData
except ImportError:
    pass  # backtrader not installed

__all__ = ["BaseData", "BaseWebSocket", "BinanceData"]
