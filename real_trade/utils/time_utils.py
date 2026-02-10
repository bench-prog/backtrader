#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
TimeUtils - 时间工具

时间戳转换、时间周期计算等。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

# 时间周期 -> 秒数映射
_TIMEFRAME_SECONDS = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "12h": 43200,
    "1d": 86400,
    "1w": 604800,
    "1M": 2592000,  # 近似 30 天
}


def timestamp_to_datetime(ts_ms: int) -> datetime.datetime:
    """毫秒时间戳 -> datetime"""
    return datetime.datetime.fromtimestamp(ts_ms / 1000.0)


def datetime_to_timestamp(dt: datetime.datetime) -> int:
    """datetime -> 毫秒时间戳"""
    return int(dt.timestamp() * 1000)


def timeframe_to_seconds(timeframe: str) -> int:
    """时间周期字符串 -> 秒数"""
    if timeframe not in _TIMEFRAME_SECONDS:
        raise ValueError(f"Unknown timeframe: {timeframe}")
    return _TIMEFRAME_SECONDS[timeframe]


def now_ms() -> int:
    """当前毫秒时间戳"""
    return int(datetime.datetime.now().timestamp() * 1000)


def format_duration(seconds: float) -> str:
    """秒数 -> 可读时间字符串"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    elif seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    else:
        return f"{seconds / 86400:.1f}d"
