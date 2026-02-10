#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
BinanceData - Binance 数据源

继承 BaseData，Binance OHLCV 格式与 CCXT 标准一致。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from real_trade.common import BaseData


class BinanceData(BaseData):
    """Binance Data Feed — 直接复用 BaseData。"""

    pass
