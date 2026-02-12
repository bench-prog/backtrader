#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Binance Store Implementation
Based on IBStore design pattern with ccxt integration
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import itertools
import threading
from collections import deque

from backtrader.metabase import MetaParams
from backtrader.utils.py3 import with_metaclass


class MetaSingleton(MetaParams):
    """Metaclass for singleton pattern"""

    def __init__(cls, name, bases, dct):
        super(MetaSingleton, cls).__init__(name, bases, dct)
        cls._singleton = None

    def __call__(cls, *args, **kwargs):
        if cls._singleton is None:
            cls._singleton = super(MetaSingleton, cls).__call__(*args, **kwargs)

        return cls._singleton


class BinanceStore(with_metaclass(MetaSingleton, object)):
    """
    Binance交易所Store实现（参考IBStore设计模式）

    参数说明：
      - ``host`` (default:``127.0.0.1``): 保持与IB一致的参数名
      - ``port`` (default: ``443``): Binance HTTPS端口
      - ``apikey`` (default: ``''``): API密钥
      - ``secret`` (default: ``''``): API密钥
      - ``testnet`` (default: ``True``): 是否使用测试网
      - ``market_type`` (default: ``spot``): spot, futures, delivery
      - ``recv_window`` (default: ``5000``): 接收窗口毫秒数
      - ``rate_limit`` (default: ``True``): 是否启用速率限制
      - ``notifyall`` (default: ``False``): 是否通知所有消息
      - ``_debug`` (default: ``False``): 调试模式
      - ``reconnect`` (default: ``3``): 重连尝试次数
      - ``timeout`` (default: ``3.0``): 超时时间（秒）
    """

    BrokerCls = None  # broker class will autoregister
    DataCls = None  # data class will auto register

    # 参考IBStore的参数设计
    params = (
        ("host", "127.0.0.1"),  # 保持与IB一致的参数名
        ("port", 443),  # Binance HTTPS端口
        ("apikey", ""),  # API密钥
        ("secret", ""),  # API密钥
        ("testnet", True),  # 是否使用测试网
        ("market_type", "spot"),  # spot, futures, delivery
        ("recv_window", 5000),  # 接收窗口
        ("rate_limit", True),  # 是否启用限速
        ("notifyall", False),  # 是否通知所有消息（参考IB）
        ("_debug", False),  # 调试模式
        ("reconnect", 3),  # 重连次数
        ("timeout", 3.0),  # 超时时间
    )

    # 参考IBStore的请求ID管理
    REQIDBASE = 0x02000000  # Binance请求ID基础值

    @classmethod
    def get_instance(cls, **kwargs):
        """单例模式获取实例（参考IBStore）"""
        if not hasattr(cls, "_instance"):
            cls._instance = cls(**kwargs)
        return cls._instance

    def __init__(self):
        super(BinanceStore, self).__init__()
        self._exchange = None
        self._connected = False
        self._reqId = itertools.count(self.REQIDBASE)  # 请求ID计数器
        self._lock = threading.Lock()  # 线程锁

        # 参考IBStore的消息队列机制
        self.notifs = deque()  # 通知队列

    def nextReqId(self):
        """获取下一个请求ID（参考IBStore）"""
        return next(self._reqId)

    def _create_exchange(self, **kwargs):
        """创建ccxt交易所实例（参考IB连接管理）"""
        try:
            import ccxt

            config = {
                "apiKey": self.p.apikey or kwargs.get("apikey", ""),
                "secret": self.p.secret or kwargs.get("secret", ""),
                "enableRateLimit": self.p.rate_limit,
                "timeout": int(self.p.timeout * 1000),  # 转换为毫秒
                "options": {"defaultType": self.p.market_type},
            }

            # 配置测试网（参考IB的连接配置）
            if self.p.testnet:
                config["urls"] = {
                    "api": {
                        "public": "https://testnet.binance.vision",
                        "private": "https://testnet.binance.vision",
                    }
                }

            self._exchange = ccxt.binance(config)

            # 参考IBStore的消息处理机制
            if self.p._debug:
                print("BinanceStore: 连接已建立")

            return True
        except ImportError:
            raise RuntimeError("ccxt库未安装，请运行: pip install ccxt")
        except Exception as e:
            if self.p._debug:
                print(f"BinanceStore: 连接失败 - {e}")
            return False

    def start(self, **kwargs):
        """启动连接（参考IBStore的start方法）"""
        with self._lock:
            if self._create_exchange(**kwargs):
                self._connected = self.test_connection()
                if self._connected and self.p._debug:
                    print("BinanceStore: 启动成功")
            return self._connected

    def stop(self):
        """停止连接（参考IBStore的stop方法）"""
        with self._lock:
            self._connected = False
            if self._exchange:
                try:
                    self._exchange.close()
                    if self.p._debug:
                        print("BinanceStore: 连接已关闭")
                except Exception as e:
                    if self.p._debug:
                        print(f"BinanceStore: 关闭连接时出错 - {e}")

    def test_connection(self) -> bool:
        """测试连接（参考IBStore的连接测试）"""
        try:
            # 参考IB的简单连接测试
            self._exchange.load_markets()
            return True
        except Exception as e:
            if self.p._debug:
                print(f"BinanceStore: 连接测试失败 - {e}")
            return False

    @property
    def is_connected(self) -> bool:
        """连接状态（参考IBStore）"""
        return self._connected

    # 参考IBStore的核心功能方法
    def get_balance(self, currency: str = None):
        """获取账户余额（参考IB的账户管理）"""
        try:
            balance = self._exchange.fetch_balance()
            if currency:
                return balance["free"].get(currency, 0)
            return balance["free"]
        except Exception as e:
            if self.p._debug:
                print(f"BinanceStore: 获取余额失败 - {e}")
            # 返回默认值而不是抛出异常
            return {} if not currency else 0

    def submit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = "limit",
        price: float = None,
        **kwargs,
    ):
        """提交订单（参考IB的订单管理）"""
        try:
            # 参考IB的订单参数处理
            params = {
                "symbol": symbol,
                "side": side.lower(),
                "amount": amount,
                "type": order_type,
            }

            if price and order_type == "limit":
                params["price"] = price

            # 合并额外参数
            params.update(kwargs)

            order = self._exchange.create_order(**params)
            if self.p._debug:
                print(f"BinanceStore: 订单已提交 - {order}")
            return order
        except Exception as e:
            if self.p._debug:
                print(f"BinanceStore: 订单提交失败 - {e}")
            return None

    def get_contract_details(self, symbol: str):
        """获取合约详情（参考IB的合约管理）"""
        try:
            market = self._exchange.market(symbol)
            return {
                "symbol": market["symbol"],
                "type": market["type"],
                "precision": market["precision"],
                "limits": market["limits"],
            }
        except Exception as e:
            if self.p._debug:
                print(f"BinanceStore: 获取合约详情失败 - {e}")
            return None

    def get_markets(self):
        """获取所有市场信息"""
        try:
            return self._exchange.load_markets()
        except Exception as e:
            if self.p._debug:
                print(f"BinanceStore: 获取市场信息失败 - {e}")
            return {}

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", since: int = None, limit: int = None
    ):
        """获取OHLCV数据"""
        try:
            return self._exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        except Exception as e:
            if self.p._debug:
                print(f"BinanceStore: 获取K线数据失败 - {e}")
            return []

    def cancel_order(self, order_id: str, symbol: str):
        """取消订单"""
        try:
            return self._exchange.cancel_order(order_id, symbol)
        except Exception as e:
            if self.p._debug:
                print(f"BinanceStore: 取消订单失败 - {e}")
            return None

    # 通知机制（参考IBStore）
    def put_notification(self, msg, *args, **kwargs):
        """添加通知消息"""
        if self.p.notifyall or (hasattr(msg, "priority") and msg.priority):
            self.notifs.append((msg, args, kwargs))

    def get_notifications(self):
        """获取通知消息"""
        notifs = list(self.notifs)
        self.notifs.clear()
        return notifs

    @classmethod
    def getdata(cls, store, *args, **kwargs):
        """返回DataCls与参数"""
        return cls.DataCls(store, *args, **kwargs)
