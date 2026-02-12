#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Binance Data Feed Implementation
Based on IBData design pattern
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
from datetime import datetime, timedelta

from backtrader.feed import DataBase
from backtrader import TimeFrame, date2num
from backtrader.metabase import MetaParams
from backtrader.utils.py3 import with_metaclass, iteritems


class MetaBinanceData(DataBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaBinanceData, cls).__init__(name, bases, dct)
        # Register the class in the store
        from ..stores.binance import BinanceStore
        BinanceStore.DataCls = cls


class BinanceData(with_metaclass(MetaBinanceData, DataBase)):
    """
    Binance Data实现（参考IBData设计模式）
    
    参数说明：
      - ``symbol`` (default: ``BTC/USDT``): 交易对符号
      - ``timeframe`` (default: ``1h``): 时间周期 ('1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w')
      - ``historical`` (default: ``False``): 是否只下载历史数据
      - ``qcheck`` (default: ``0.5``): 检查事件的超时时间（秒）
      - ``backfill_start`` (default: ``True``): 是否在开始时进行回填
      - ``backfill`` (default: ``True``): 重连时是否进行回填
      - ``backfill_from`` (default: ``None``): 用于回填的额外数据源
      - ``latethrough`` (default: ``False``): 是否让迟到的样本通过
    """

    params = (
        ('symbol', 'BTC/USDT'),       # 交易对符号
        ('timeframe', '1h'),          # 时间周期
        ('historical', False),        # 只下载历史数据
        ('qcheck', 0.5),              # 超时检查时间
        ('backfill_start', True),     # 开始时回填
        ('backfill', True),           # 重连时回填
        ('backfill_from', None),      # 额外的回填数据源
        ('latethrough', False),       # 让迟到样本通过
        ('tradename', None),          # 交易资产名称（如果与数据资产不同）
        ('_debug', False),            # 调试模式
    )

    _store = None  # 将在运行时设置

    # 状态机状态
    _ST_FROM, _ST_START, _ST_LIVE, _ST_HISTORBACK, _ST_OVER = range(5)

    # Binance时间周期映射
    _BTFREQS = {
        '1m': ('1m', 1),
        '3m': ('3m', 1),
        '5m': ('5m', 1),
        '15m': ('15m', 1),
        '30m': ('30m', 1),
        '1h': ('1h', 1),
        '2h': ('2h', 1),
        '4h': ('4h', 1),
        '6h': ('6h', 1),
        '8h': ('8h', 1),
        '12h': ('12h', 1),
        '1d': ('1d', 1),
        '3d': ('3d', 1),
        '1w': ('1w', 1),
        '1M': ('1M', 1),
    }

    def __init__(self, store):
        super(BinanceData, self).__init__()
        self.store = store
        
        # 状态管理
        self._state = self._ST_OVER
        self._statelivereconn = False  # 实时状态重连标志
        
        # 数据缓冲
        self._dataBuffer = collections.deque()  # 数据缓冲区
        self._storedmsg = dict()  # 存储待处理的消息
        
        # 时间管理
        self._last_ts = None  # 上一个时间戳
        self._first_ts = None  # 第一个时间戳
        
        # 设置交易名称
        if self.p.tradename is None:
            self.tradeasset = self.p.symbol
        else:
            self.tradeasset = self.p.tradename

    def start(self):
        """启动数据feed"""
        super(BinanceData, self).start()
        
        # 设置初始状态
        if self.p.backfill_from is not None:
            self._state = self._ST_FROM
            self.p.backfill_from.setenvironment(self._env)
            self.p.backfill_from._start()
        else:
            self._state = self._ST_START  # 初始状态
            
        self._statelivereconn = False  # 重连状态标志
        self._storedmsg = dict()  # 清空存储消息
        
        # 检查连接
        if not self.store.is_connected:
            self.put_notification(self.DISCONNECTED)
            return
            
        self.put_notification(self.CONNECTED)
        
        # 获取合约详情
        contract_details = self.store.get_contract_details(self.p.symbol)
        if contract_details is None:
            self.put_notification(self.DISCONNECTED)
            return
            
        if self.p._debug:
            print(f"BinanceData: 合约详情获取成功 - {contract_details}")

    def stop(self):
        """停止数据feed"""
        super(BinanceData, self).stop()
        self._state = self._ST_OVER

    def _load(self):
        """加载数据的核心方法"""
        if self._state == self._ST_OVER:
            return False

        # 处理回填数据源
        if self._state == self._ST_FROM:
            if self.p.backfill_from is None:
                self._state = self._ST_START
            else:
                ret = self.p.backfill_from._load()
                if ret:
                    return True
                else:
                    self._state = self._ST_START

        # 开始状态 - 加载历史数据
        if self._state == self._ST_START:
            if not self._start_finish():
                return False

        # 历史回填状态
        if self._state == self._ST_HISTORBACK:
            if self._historback_fill():
                return True
            else:
                # 历史数据加载完成，进入实时状态
                self._state = self._ST_LIVE
                self._statelivereconn = False
                self.put_notification(self.LIVE)

        # 实时状态
        if self._state == self._ST_LIVE:
            return self._load_live()

        return False

    def _start_finish(self):
        """完成启动过程"""
        try:
            # 如果需要回填历史数据
            if self.p.backfill_start:
                if not self._load_history():
                    return False
                    
            # 进入实时状态
            self._state = self._ST_LIVE
            self.put_notification(self.LIVE)
            return True
            
        except Exception as e:
            if self.p._debug:
                print(f"BinanceData: 启动失败 - {e}")
            self.put_notification(self.DISCONNECTED)
            return False

    def _load_history(self):
        """加载历史数据"""
        try:
            # 计算历史数据时间范围
            end_time = int(datetime.now().timestamp() * 1000)
            # 默认加载最近30天的数据
            start_time = end_time - (30 * 24 * 60 * 60 * 1000)
            
            # 获取OHLCV数据
            ohlcv_data = self.store.fetch_ohlcv(
                self.p.symbol,
                self.p.timeframe,
                since=start_time,
                limit=1000  # Binance API限制
            )
            
            if not ohlcv_data:
                return True  # 没有数据也返回成功
                
            # 将数据放入缓冲区
            for candle in ohlcv_data:
                self._dataBuffer.append(candle)
                
            if self.p._debug:
                print(f"BinanceData: 历史数据加载完成，共{len(ohlcv_data)}条记录")
                
            return True
            
        except Exception as e:
            if self.p._debug:
                print(f"BinanceData: 历史数据加载失败 - {e}")
            return False

    def _historback_fill(self):
        """历史回填数据填充"""
        try:
            if not self._dataBuffer:
                return False
                
            # 从缓冲区取出一条数据
            candle = self._dataBuffer.popleft()
            
            # 解析K线数据
            timestamp, open_price, high_price, low_price, close_price, volume = candle
            
            # 转换时间戳
            dt = datetime.fromtimestamp(timestamp / 1000)
            
            # 设置数据
            self.lines.datetime[0] = date2num(dt)
            self.lines.open[0] = open_price
            self.lines.high[0] = high_price
            self.lines.low[0] = low_price
            self.lines.close[0] = close_price
            self.lines.volume[0] = volume
            self.lines.openinterest[0] = 0
            
            # 更新时间戳跟踪
            self._last_ts = timestamp
            
            return True
            
        except Exception as e:
            if self.p._debug:
                print(f"BinanceData: 历史数据填充失败 - {e}")
            return False

    def _load_live(self):
        """加载实时数据"""
        try:
            # 获取最新的K线数据
            ohlcv_data = self.store.fetch_ohlcv(
                self.p.symbol,
                self.p.timeframe,
                limit=10  # 获取最近10条数据
            )
            
            if not ohlcv_data:
                return None
                
            # 找到最新的数据点
            latest_candle = ohlcv_data[-1]
            timestamp, open_price, high_price, low_price, close_price, volume = latest_candle
            
            # 检查是否是新数据
            if self._last_ts and timestamp <= self._last_ts:
                return None  # 不是新数据
                
            # 转换时间戳
            dt = datetime.fromtimestamp(timestamp / 1000)
            
            # 设置数据
            self.lines.datetime[0] = date2num(dt)
            self.lines.open[0] = open_price
            self.lines.high[0] = high_price
            self.lines.low[0] = low_price
            self.lines.close[0] = close_price
            self.lines.volume[0] = volume
            self.lines.openinterest[0] = 0
            
            # 更新时间戳
            self._last_ts = timestamp
            
            if self.p._debug:
                print(f"BinanceData: 实时数据更新 - {dt} {close_price}")
                
            return True
            
        except Exception as e:
            if self.p._debug:
                print(f"BinanceData: 实时数据加载失败 - {e}")
            return None

    def haslivedata(self):
        """检查是否有实时数据"""
        return self._state == self._ST_LIVE and self._last_ts is not None

    def islive(self):
        """检查是否是实时数据feed"""
        return not self.p.historical

    @classmethod
    def from_timeframe_string(cls, timeframe_str: str, store, symbol: str, **kwargs):
        """
        从时间周期字符串创建Data实例
        
        Args:
            timeframe_str: 时间周期字符串 ('1h', '1d'等)
            store: Store实例
            symbol: 交易对符号
            **kwargs: 其他参数
            
        Returns:
            Data实例
        """
        return cls(store, timeframe=timeframe_str, symbol=symbol, **kwargs)

    def _timeoffset(self):
        """获取时间偏移（参考IBData）"""
        # Binance使用UTC时间，通常不需要偏移
        return 0.0

    def _gettz(self):
        """获取时区信息"""
        # Binance使用UTC时间
        return None