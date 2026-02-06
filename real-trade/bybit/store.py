#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Bybit Store - 统一的交易所连接管理

提供单例模式的交易所连接，避免重复初始化。
支持多种配置方式和连接池管理。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import threading
from typing import Optional, Dict, Any


class BybitStore:
    """
    Bybit 交易所连接管理器

    功能:
    - 单例模式管理 CCXT 连接
    - 支持测试网和主网
    - 连接池管理
    - 线程安全
    """

    _instances: Dict[str, "BybitStore"] = {}
    _lock = threading.Lock()

    @classmethod
    def get_instance(
        cls,
        apikey: str = "",
        secret: str = "",
        testnet: bool = True,
        proxy: Optional[str] = None,
        **kwargs
    ) -> "BybitStore":
        """
        获取 Store 实例（单例模式）

        Args:
            apikey: API Key
            secret: API Secret
            testnet: 是否使用测试网
            proxy: 代理地址
            **kwargs: 其他 CCXT 配置参数

        Returns:
            BybitStore 实例
        """
        # 生成唯一标识
        instance_key = f"{apikey}_{testnet}"

        if instance_key not in cls._instances:
            with cls._lock:
                if instance_key not in cls._instances:
                    cls._instances[instance_key] = cls(
                        apikey=apikey,
                        secret=secret,
                        testnet=testnet,
                        proxy=proxy,
                        **kwargs
                    )

        return cls._instances[instance_key]

    def __init__(
        self,
        apikey: str = "",
        secret: str = "",
        testnet: bool = True,
        proxy: Optional[str] = None,
        market_type: str = "spot",  # spot, linear, inverse
        **kwargs
    ):
        """
        初始化 Bybit Store

        Args:
            apikey: API Key
            secret: API Secret
            testnet: 是否使用测试网
            proxy: 代理地址
            market_type: 市场类型 (spot, linear, inverse)
            **kwargs: 其他 CCXT 配置参数
        """
        try:
            import ccxt
        except ImportError:
            raise Exception("CCXT library required. Install with: pip install ccxt")

        self.apikey = apikey
        self.secret = secret
        self.testnet = testnet
        self.proxy = proxy
        self.market_type = market_type

        # 交易所配置
        exchange_config = {
            "apiKey": apikey,
            "secret": secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": market_type,
            },
        }

        # 合并用户自定义配置
        exchange_config.update(kwargs)

        # 代理配置
        if proxy:
            exchange_config["proxies"] = {
                "http": proxy,
                "https": proxy,
            }

        # 测试网配置
        if testnet:
            exchange_config["urls"] = {
                "api": {
                    "public": "https://api-testnet.bybit.com",
                    "private": "https://api-testnet.bybit.com",
                }
            }

        # 初始化交易所
        self._exchange = ccxt.bybit(exchange_config)
        self._connected = False

        print(f"BybitStore initialized: testnet={testnet}, market_type={market_type}")

    @property
    def exchange(self):
        """获取 CCXT 交易所实例"""
        return self._exchange

    def test_connection(self) -> bool:
        """
        测试连接是否正常

        Returns:
            连接状态
        """
        try:
            self._exchange.fetch_balance()
            self._connected = True
            print("✓ Bybit connection successful")
            return True
        except Exception as e:
            self._connected = False
            print(f"✗ Bybit connection failed: {e}")
            return False

    def get_balance(self, currency: str = "USDT") -> float:
        """
        获取余额

        Args:
            currency: 币种

        Returns:
            可用余额
        """
        try:
            balance = self._exchange.fetch_balance()
            return balance[currency]["free"]
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return 0.0

    def get_total_value(self, currency: str = "USDT") -> float:
        """
        获取账户总价值

        Args:
            currency: 计价币种

        Returns:
            总价值
        """
        try:
            balance = self._exchange.fetch_balance()
            return balance["total"][currency]
        except Exception as e:
            print(f"Error fetching total value: {e}")
            return 0.0

    def get_positions(self, symbols: Optional[list] = None) -> list:
        """
        获取持仓

        Args:
            symbols: 交易对列表，None 表示所有

        Returns:
            持仓列表
        """
        try:
            return self._exchange.fetch_positions(symbols)
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """
        获取未完成订单

        Args:
            symbol: 交易对，None 表示所有

        Returns:
            订单列表
        """
        try:
            return self._exchange.fetch_open_orders(symbol)
        except Exception as e:
            print(f"Error fetching open orders: {e}")
            return []

    def get_markets(self) -> Dict[str, Any]:
        """
        获取市场信息

        Returns:
            市场字典
        """
        try:
            return self._exchange.load_markets()
        except Exception as e:
            print(f"Error loading markets: {e}")
            return {}

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        获取行情快照

        Args:
            symbol: 交易对

        Returns:
            行情信息
        """
        try:
            return self._exchange.fetch_ticker(symbol)
        except Exception as e:
            print(f"Error fetching ticker: {e}")
            return {}

    @property
    def is_connected(self) -> bool:
        """连接状态"""
        return self._connected

    def __repr__(self):
        return (
            f"BybitStore(testnet={self.testnet}, "
            f"market_type={self.market_type}, "
            f"connected={self._connected})"
        )
