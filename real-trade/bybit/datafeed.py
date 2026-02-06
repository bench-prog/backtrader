#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Bybit Data Feed - 数据源实现

支持实时数据流和历史数据加载。
提供灵活的时间周期配置。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
from typing import Optional
import backtrader as bt

from .store import BybitStore


class BybitData(bt.DataBase):
    """
    Bybit 数据源

    功能:
    - 实时数据流
    - 历史数据加载
    - 多时间周期支持
    - 自动时间戳转换
    """

    params = (
        ("symbol", "BTC/USDT"),  # 交易对
        ("timeframe", bt.TimeFrame.Minutes),  # 时间周期
        ("compression", 1),  # 压缩比例
        ("ccxt_timeframe", "1m"),  # CCXT 时间周期字符串
        ("backtest", False),  # 是否为回测模式
        ("fromdate", None),  # 开始日期
        ("todate", None),  # 结束日期
        ("historical_limit", 1000),  # 历史数据每次获取数量
    )

    # 时间周期映射
    TIMEFRAME_MAP = {
        "1m": (bt.TimeFrame.Minutes, 1),
        "3m": (bt.TimeFrame.Minutes, 3),
        "5m": (bt.TimeFrame.Minutes, 5),
        "15m": (bt.TimeFrame.Minutes, 15),
        "30m": (bt.TimeFrame.Minutes, 30),
        "1h": (bt.TimeFrame.Minutes, 60),
        "2h": (bt.TimeFrame.Minutes, 120),
        "4h": (bt.TimeFrame.Minutes, 240),
        "6h": (bt.TimeFrame.Minutes, 360),
        "12h": (bt.TimeFrame.Minutes, 720),
        "1d": (bt.TimeFrame.Days, 1),
        "1w": (bt.TimeFrame.Weeks, 1),
        "1M": (bt.TimeFrame.Months, 1),
    }

    def __init__(self, store: BybitStore, **kwargs):
        """
        初始化数据源

        Args:
            store: BybitStore 实例
            **kwargs: 其他参数
        """
        super(BybitData, self).__init__()

        self.store = store
        self.exchange = store.exchange

        # 设置数据名称（用于 broker 识别）
        self._name = self.params.symbol

        # 历史数据相关
        self.historical_data = []
        self.historical_index = 0

        # 加载数据
        if self.params.backtest:
            self._load_historical_data()
        else:
            self.live = True

        print(
            f"BybitData initialized: {self.params.symbol}, "
            f"timeframe={self.params.ccxt_timeframe}, "
            f"backtest={self.params.backtest}"
        )

    @classmethod
    def from_timeframe_string(cls, timeframe_str: str, store: BybitStore, **kwargs):
        """
        从时间周期字符串创建数据源

        Args:
            timeframe_str: 时间周期字符串 (如 '1m', '1h', '1d')
            store: BybitStore 实例
            **kwargs: 其他参数

        Returns:
            BybitData 实例
        """
        if timeframe_str not in cls.TIMEFRAME_MAP:
            raise ValueError(
                f"Invalid timeframe: {timeframe_str}. "
                f"Valid options: {list(cls.TIMEFRAME_MAP.keys())}"
            )

        tf, comp = cls.TIMEFRAME_MAP[timeframe_str]

        return cls(
            store=store,
            timeframe=tf,
            compression=comp,
            ccxt_timeframe=timeframe_str,
            **kwargs
        )

    def _load_historical_data(self):
        """加载历史数据"""
        since = None
        if self.params.fromdate:
            since = int(self.params.fromdate.timestamp() * 1000)

        limit = self.params.historical_limit
        all_ohlcv = []

        print(f"Loading historical data for {self.params.symbol}...")

        try:
            while True:
                ohlcv = self.exchange.fetch_ohlcv(
                    self.params.symbol,
                    timeframe=self.params.ccxt_timeframe,
                    since=since,
                    limit=limit,
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)

                # 检查是否到达结束日期
                if self.params.todate:
                    last_timestamp = ohlcv[-1][0] / 1000
                    if last_timestamp >= self.params.todate.timestamp():
                        # 过滤掉超过结束日期的数据
                        all_ohlcv = [
                            bar
                            for bar in all_ohlcv
                            if bar[0] / 1000 <= self.params.todate.timestamp()
                        ]
                        break

                if len(ohlcv) < limit:
                    break

                since = ohlcv[-1][0] + 1

            self.historical_data = all_ohlcv
            print(f"✓ Loaded {len(self.historical_data)} candles")

        except Exception as e:
            print(f"✗ Error loading historical data: {e}")
            self.historical_data = []

    def _load(self):
        """加载下一条数据"""
        if self.params.backtest:
            return self._load_historical()
        else:
            return self._load_live()

    def _load_historical(self) -> bool:
        """加载历史数据的下一条"""
        if self.historical_index >= len(self.historical_data):
            return False

        ohlcv = self.historical_data[self.historical_index]
        self.historical_index += 1

        # OHLCV 格式: [timestamp, open, high, low, close, volume]
        self.lines.datetime[0] = bt.date2num(
            datetime.datetime.fromtimestamp(ohlcv[0] / 1000)
        )
        self.lines.open[0] = ohlcv[1]
        self.lines.high[0] = ohlcv[2]
        self.lines.low[0] = ohlcv[3]
        self.lines.close[0] = ohlcv[4]
        self.lines.volume[0] = ohlcv[5]
        self.lines.openinterest[0] = 0

        return True

    def _load_live(self) -> Optional[bool]:
        """加载实时数据"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                self.params.symbol, timeframe=self.params.ccxt_timeframe, limit=1
            )

            if not ohlcv:
                return None

            bar = ohlcv[-1]

            self.lines.datetime[0] = bt.date2num(
                datetime.datetime.fromtimestamp(bar[0] / 1000)
            )
            self.lines.open[0] = bar[1]
            self.lines.high[0] = bar[2]
            self.lines.low[0] = bar[3]
            self.lines.close[0] = bar[4]
            self.lines.volume[0] = bar[5]
            self.lines.openinterest[0] = 0

            return True

        except Exception as e:
            print(f"Error loading live data: {e}")
            return None

    def islive(self) -> bool:
        """是否为实时数据"""
        return not self.params.backtest

    def __repr__(self):
        mode = "Backtest" if self.params.backtest else "Live"
        return (
            f"BybitData({self.params.symbol}, "
            f"mode={mode}, "
            f"timeframe={self.params.ccxt_timeframe})"
        )
