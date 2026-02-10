#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Base Store - 通用的交易所连接管理基类

所有交易所的 Store 都继承此基类，实现统一接口。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import threading
import subprocess
import re
from typing import Optional, Dict, Any


class BaseStore:
    """
    交易所连接管理基类

    所有交易所 Store 必须实现的接口。
    """

    _instances: Dict[str, "BaseStore"] = {}
    _lock = threading.Lock()

    @staticmethod
    def _detect_system_proxy() -> Optional[str]:
        """
        自动检测系统代理设置

        Returns:
            代理地址字符串，格式为 "http://host:port"，如果未找到则返回 None
        """
        try:
            # 尝试在 macOS 上获取系统代理
            result = subprocess.run(
                ['scutil', '--proxy'],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0:
                output = result.stdout

                # 查找 HTTP 代理设置
                http_enabled = re.search(r'HTTPEnable\s*:\s*(\d+)', output)
                if http_enabled and http_enabled.group(1) == '1':
                    http_proxy = re.search(r'HTTPProxy\s*:\s*(\S+)', output)
                    http_port = re.search(r'HTTPPort\s*:\s*(\d+)', output)

                    if http_proxy and http_port:
                        proxy_url = f"http://{http_proxy.group(1)}:{http_port.group(1)}"
                        print(f"✓ 检测到系统代理: {proxy_url}")
                        return proxy_url
        except Exception as e:
            # 静默失败，不影响正常使用
            pass

        return None

    @classmethod
    def get_instance(cls, **kwargs) -> "BaseStore":
        """
        获取单例实例

        子类应该重写此方法以实现自己的单例逻辑。
        """
        raise NotImplementedError("Subclass must implement get_instance()")

    def __init__(
        self,
        apikey: str = "",
        secret: str = "",
        testnet: bool = True,
        proxy: Optional[str] = None,
        **kwargs
    ):
        """
        初始化基类

        Args:
            apikey: API Key
            secret: API Secret
            testnet: 是否使用测试网
            proxy: 代理地址，如果为 None 则自动检测系统代理
            **kwargs: 其他参数
        """
        self.apikey = apikey
        self.secret = secret
        self.testnet = testnet

        # 如果未提供代理，尝试自动检测系统代理
        if proxy is None:
            proxy = self._detect_system_proxy()

        self.proxy = proxy
        self._exchange = None
        self._connected = False

    def _create_exchange(self, **kwargs):
        """
        创建交易所实例（子类必须实现）

        Returns:
            CCXT 交易所实例
        """
        raise NotImplementedError("Subclass must implement _create_exchange()")

    @property
    def exchange(self):
        """获取交易所实例"""
        return self._exchange

    def test_connection(self) -> bool:
        """
        测试连接

        Returns:
            连接状态
        """
        try:
            self._exchange.fetch_balance()
            self._connected = True
            print(f"✓ {self.__class__.__name__} connection successful")
            return True
        except Exception as e:
            self._connected = False
            print(f"✗ {self.__class__.__name__} connection failed: {e}")
            return False

    def get_balance(self, currency: str = "USDT") -> float:
        """获取余额"""
        try:
            balance = self._exchange.fetch_balance()
            return balance[currency]["free"]
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return 0.0

    def get_total_value(self, currency: str = "USDT") -> float:
        """获取账户总价值"""
        try:
            balance = self._exchange.fetch_balance()
            return balance["total"][currency]
        except Exception as e:
            print(f"Error fetching total value: {e}")
            return 0.0

    def get_positions(self, symbols: Optional[list] = None) -> list:
        """获取持仓"""
        try:
            return self._exchange.fetch_positions(symbols)
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """获取未完成订单"""
        try:
            return self._exchange.fetch_open_orders(symbol)
        except Exception as e:
            print(f"Error fetching open orders: {e}")
            return []

    def get_markets(self) -> Dict[str, Any]:
        """获取市场信息"""
        try:
            return self._exchange.load_markets()
        except Exception as e:
            print(f"Error loading markets: {e}")
            return {}

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取行情快照"""
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
            f"{self.__class__.__name__}("
            f"testnet={self.testnet}, "
            f"connected={self._connected})"
        )
