#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Stores Module - 交易所连接管理

提供各交易所的 Store 实现。
"""

from .basestore import BaseStore

try:
    from .binancestore import BinanceStore
except ImportError:
    pass  # ccxt not installed

__all__ = ["BaseStore", "BinanceStore"]
