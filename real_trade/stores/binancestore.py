#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
BinanceStore - Binance 交易所连接管理

继承 BaseStore，实现 Binance 特定的 CCXT 初始化。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import threading
from typing import Optional

from .basestore import BaseStore


class BinanceStore(BaseStore):
    """
    Binance 交易所连接管理

    通过 CCXT 统一接口连接 Binance，支持 spot / future / delivery。
    testnet 模式使用 CCXT enable_demo_trading（需 CCXT >= 4.5.6）。
    """

    _instances = {}
    _lock = threading.Lock()

    @classmethod
    def get_instance(
        cls,
        apikey: str = "",
        secret: str = "",
        testnet: bool = True,
        proxy: Optional[str] = None,
        **kwargs,
    ) -> "BinanceStore":
        instance_key = f"{apikey}_{testnet}"
        if instance_key not in cls._instances:
            with cls._lock:
                if instance_key not in cls._instances:
                    cls._instances[instance_key] = cls(
                        apikey=apikey,
                        secret=secret,
                        testnet=testnet,
                        proxy=proxy,
                        **kwargs,
                    )
        return cls._instances[instance_key]

    def __init__(
        self,
        apikey: str = "",
        secret: str = "",
        testnet: bool = True,
        proxy: Optional[str] = None,
        market_type: str = "spot",
        **kwargs,
    ):
        super().__init__(
            apikey=apikey, secret=secret, testnet=testnet, proxy=proxy, **kwargs
        )
        self.market_type = market_type
        self._create_exchange(market_type=market_type, **kwargs)

    def _create_exchange(self, market_type: str = "spot", **kwargs):
        import ccxt

        config = {
            "apiKey": self.apikey,
            "secret": self.secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": market_type,
            },
        }

        if self.proxy:
            config["proxies"] = {
                "http": self.proxy,
                "https": self.proxy,
            }

        self._exchange = ccxt.binance(config)

        if self.testnet:
            try:
                self._exchange.enable_demo_trading(True)
            except AttributeError:
                raise RuntimeError(
                    f"CCXT {ccxt.__version__} does not support "
                    "enable_demo_trading(). Upgrade: pip install -U ccxt"
                )

        mode = "Demo Trading" if self.testnet else "Production"
        print(f"[BinanceStore] {mode}, market_type={market_type}")
