#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
BinanceBroker - Binance 交易经纪商

继承 BaseBroker，Binance 订单逻辑与基类完全兼容。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from real_trade.common import BaseBroker


class BinanceBroker(BaseBroker):
    """Binance Broker — 直接复用 BaseBroker。"""

    pass
