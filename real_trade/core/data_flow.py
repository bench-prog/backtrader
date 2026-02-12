#!/usr/bin/env python3
"""
Backtrader统一数据流和缓存系统
实现高效的数据处理、缓存管理和跨模块数据共享
"""

import hashlib
import threading
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import numpy as np

import backtrader as bt


@dataclass
class DataCacheEntry:
    """数据缓存条目"""

    data: Any
    timestamp: datetime
    expiry_time: Optional[datetime]
    access_count: int = 0
    hit_count: int = 0


class DataCache:
    """数据缓存管理器"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, DataCacheEntry] = OrderedDict()
        self.lock = threading.Lock()

    def _generate_key(self, data_type: str, **kwargs) -> str:
        """生成缓存键"""
        key_data = f"{data_type}_{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def put(
        self, data_type: str, data: Any, ttl: Optional[int] = None, **kwargs
    ) -> str:
        """放入缓存"""
        with self.lock:
            # 检查缓存大小
            if len(self.cache) >= self.max_size:
                # 移除最少使用的项
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]

            key = self._generate_key(data_type, **kwargs)
            expiry = datetime.now() + timedelta(seconds=ttl or self.default_ttl)

            self.cache[key] = DataCacheEntry(
                data=data, timestamp=datetime.now(), expiry_time=expiry
            )

            # 移动到末尾（标记为最新）
            self.cache.move_to_end(key)

            return key

    def get(self, data_type: str, **kwargs) -> Optional[Any]:
        """获取缓存数据"""
        with self.lock:
            key = self._generate_key(data_type, **kwargs)

            if key not in self.cache:
                return None

            entry = self.cache[key]

            # 检查过期时间
            if entry.expiry_time and datetime.now() > entry.expiry_time:
                del self.cache[key]
                return None

            # 更新访问统计
            entry.access_count += 1
            entry.hit_count += 1

            # 移动到末尾
            self.cache.move_to_end(key)

            return entry.data

    def invalidate(self, data_type: str, **kwargs):
        """使缓存失效"""
        with self.lock:
            key = self._generate_key(data_type, **kwargs)
            if key in self.cache:
                del self.cache[key]

    def clear_expired(self):
        """清理过期缓存"""
        with self.lock:
            current_time = datetime.now()
            expired_keys = [
                key
                for key, entry in self.cache.items()
                if entry.expiry_time and current_time > entry.expiry_time
            ]

            for key in expired_keys:
                del self.cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total_access = sum(entry.access_count for entry in self.cache.values())
            total_hits = sum(entry.hit_count for entry in self.cache.values())

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_rate": total_hits / total_access if total_access > 0 else 0,
                "total_access": total_access,
                "total_hits": total_hits,
            }


class DataProcessor:
    """数据处理器基类"""

    def __init__(self, cache: Optional[DataCache] = None):
        self.cache = cache or DataCache()

    def process_series(
        self, data: Union[List, np.ndarray], processor_name: str, **kwargs
    ) -> np.ndarray:
        """处理数据序列"""
        # 检查缓存
        cache_key = f"{processor_name}_{hash(str(sorted(kwargs.items())))}"
        cached_result = self.cache.get("series_processing", key=cache_key)

        if cached_result is not None:
            return cached_result

        # 转换为numpy数组
        if not isinstance(data, np.ndarray):
            data = np.array(data)

        # 执行处理
        result = self._process_impl(data, **kwargs)

        # 缓存结果
        self.cache.put("series_processing", result, key=cache_key, ttl=1800)

        return result

    def _process_impl(self, data: np.ndarray, **kwargs) -> np.ndarray:
        """具体的处理实现 - 由子类实现"""
        raise NotImplementedError


class TechnicalIndicatorsProcessor(DataProcessor):
    """技术指标处理器"""

    def calculate_sma(self, prices: Union[List, np.ndarray], period: int) -> np.ndarray:
        """计算简单移动平均线"""
        return self.process_series(prices, "sma", period=period)

    def calculate_ema(self, prices: Union[List, np.ndarray], period: int) -> np.ndarray:
        """计算指数移动平均线"""
        return self.process_series(prices, "ema", period=period)

    def calculate_rsi(
        self, prices: Union[List, np.ndarray], period: int = 14
    ) -> np.ndarray:
        """计算RSI指标"""
        return self.process_series(prices, "rsi", period=period)

    def calculate_bollinger_bands(
        self,
        prices: Union[List, np.ndarray],
        period: int = 20,
        std_multiplier: float = 2.0,
    ) -> tuple:
        """计算布林带"""
        cache_key = f"bb_{period}_{std_multiplier}"
        cached_result = self.cache.get("bollinger_bands", key=cache_key)

        if cached_result is not None:
            return cached_result

        prices_array = (
            np.array(prices) if not isinstance(prices, np.ndarray) else prices
        )

        sma = self.calculate_sma(prices_array, period)
        std = self.process_series(prices_array, "std", period=period)

        upper_band = sma + (std * std_multiplier)
        lower_band = sma - (std * std_multiplier)

        result = (upper_band, sma, lower_band)
        self.cache.put("bollinger_bands", result, key=cache_key, ttl=1800)

        return result

    def _process_impl(self, data: np.ndarray, **kwargs) -> np.ndarray:
        """实现各种技术指标计算"""
        processor_name = kwargs.get("processor_name", kwargs.get("name", ""))

        if "sma" in processor_name:
            period = kwargs["period"]
            if len(data) < period:
                return np.array([])
            return np.convolve(data, np.ones(period) / period, mode="valid")

        elif "ema" in processor_name:
            period = kwargs["period"]
            if len(data) == 0:
                return np.array([])
            alpha = 2.0 / (period + 1)
            ema = np.zeros_like(data)
            ema[0] = data[0]
            for i in range(1, len(data)):
                ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
            return ema

        elif "rsi" in processor_name:
            period = kwargs["period"]
            if len(data) <= period:
                return np.full(len(data), np.nan)
            delta = np.diff(data)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)

            if len(gain) < period:
                return np.full(len(data), np.nan)

            avg_gain = np.convolve(gain, np.ones(period) / period, mode="valid")
            avg_loss = np.convolve(loss, np.ones(period) / period, mode="valid")

            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))

            # 补齐前面的NaN值
            result = np.full(len(data), np.nan)
            result[period:] = rsi
            return result

        elif "std" in processor_name:
            period = kwargs["period"]
            if len(data) == 0:
                return np.array([])
            return np.array(
                [np.std(data[max(0, i - period + 1) : i + 1]) for i in range(len(data))]
            )

        else:
            raise ValueError(f"未知的处理器类型: {processor_name}")


class DataFlowManager:
    """数据流管理器"""

    def __init__(self):
        self.cache = DataCache()
        self.processor = TechnicalIndicatorsProcessor(self.cache)
        self.subscribers: Dict[str, List[callable]] = {}

    def register_subscriber(self, data_topic: str, callback: callable):
        """注册数据订阅者"""
        if data_topic not in self.subscribers:
            self.subscribers[data_topic] = []
        self.subscribers[data_topic].append(callback)

    def publish_data(self, topic: str, data: Any, metadata: Dict = None):
        """发布数据"""
        # 缓存数据
        self.cache.put("published_data", data, topic=topic, ttl=3600)

        # 通知订阅者
        if topic in self.subscribers:
            for callback in self.subscribers[topic]:
                try:
                    callback(data, metadata or {})
                except Exception as e:
                    print(f"数据回调执行失败: {e}")

    def get_cached_data(self, topic: str) -> Optional[Any]:
        """获取缓存数据"""
        return self.cache.get("published_data", topic=topic)

    def calculate_technical_indicators(
        self, data_feed: bt.DataBase, indicators: List[str]
    ) -> Dict[str, np.ndarray]:
        """计算技术指标"""
        # 获取价格数据
        # 安全获取价格数据
        close_prices = []
        for i in range(-len(data_feed), 0):
            try:
                close_prices.append(data_feed.close[i])
            except IndexError:
                break
        close_prices = np.array(close_prices)
        high_prices = []
        for i in range(-len(data_feed), 0):
            try:
                high_prices.append(data_feed.high[i])
            except IndexError:
                break
        high_prices = np.array(high_prices)

        low_prices = []
        for i in range(-len(data_feed), 0):
            try:
                low_prices.append(data_feed.low[i])
            except IndexError:
                break
        low_prices = np.array(low_prices)

        results = {}

        for indicator in indicators:
            if indicator.startswith("sma"):
                period = int(indicator.split("_")[1])
                results[indicator] = self.processor.calculate_sma(close_prices, period)
            elif indicator.startswith("ema"):
                period = int(indicator.split("_")[1])
                results[indicator] = self.processor.calculate_ema(close_prices, period)
            elif indicator == "rsi":
                results[indicator] = self.processor.calculate_rsi(close_prices)
            elif indicator == "bollinger_bands":
                upper, middle, lower = self.processor.calculate_bollinger_bands(
                    close_prices
                )
                results["bb_upper"] = upper
                results["bb_middle"] = middle
                results["bb_lower"] = lower

        return results


# 便捷的全局数据流管理器
data_flow_manager = DataFlowManager()


class DataFlowMixin:
    """数据流混入类 - 为策略提供数据流功能"""

    def __init__(self):
        self.data_flow = data_flow_manager
        self._indicator_cache = {}

    def get_technical_indicators(
        self, data: bt.DataBase, indicators: List[str]
    ) -> Dict[str, np.ndarray]:
        """获取技术指标"""
        cache_key = f"{data._name}_{hash(str(sorted(indicators)))}"

        if cache_key not in self._indicator_cache:
            self._indicator_cache[cache_key] = (
                self.data_flow.calculate_technical_indicators(data, indicators)
            )

        return self._indicator_cache[cache_key]

    def subscribe_to_data(self, topic: str, callback: callable):
        """订阅数据主题"""
        self.data_flow.register_subscriber(topic, callback)

    def publish_data(self, topic: str, data: Any, metadata: Dict = None):
        """发布数据"""
        self.data_flow.publish_data(topic, data, metadata)
