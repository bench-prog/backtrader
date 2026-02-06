#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Real Trade Module

专业的实盘交易模块集合。

当前支持的交易所:
- Bybit

未来计划:
- Binance
- OKX
- Huobi
- Coinbase
"""

__version__ = "1.0.0"

# 导出 Bybit 模块
from . import bybit

__all__ = ["bybit"]
