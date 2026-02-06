#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
验证器模块

提供参数验证功能。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from typing import Tuple, Optional
import re


# 支持的时间周期
VALID_TIMEFRAMES = [
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "12h",
    "1d",
    "1w",
    "1M",
]


def validate_symbol(symbol: str) -> Tuple[bool, Optional[str]]:
    """
    验证交易对格式

    Args:
        symbol: 交易对字符串

    Returns:
        (是否有效, 错误信息)
    """
    if not symbol:
        return False, "Symbol cannot be empty"

    # 基本格式检查：BASE/QUOTE
    if "/" not in symbol:
        return False, "Symbol must be in format BASE/QUOTE (e.g., BTC/USDT)"

    parts = symbol.split("/")
    if len(parts) != 2:
        return False, "Symbol must contain exactly one '/'"

    base, quote = parts
    if not base or not quote:
        return False, "Both base and quote currencies must be specified"

    # 检查是否只包含字母和数字
    if not re.match(r"^[A-Z0-9]+$", base):
        return False, f"Invalid base currency: {base}"

    if not re.match(r"^[A-Z0-9]+$", quote):
        return False, f"Invalid quote currency: {quote}"

    return True, None


def validate_timeframe(timeframe: str) -> Tuple[bool, Optional[str]]:
    """
    验证时间周期

    Args:
        timeframe: 时间周期字符串

    Returns:
        (是否有效, 错误信息)
    """
    if timeframe not in VALID_TIMEFRAMES:
        return (
            False,
            f"Invalid timeframe: {timeframe}. Valid options: {VALID_TIMEFRAMES}",
        )

    return True, None


def validate_api_keys(apikey: str, secret: str) -> Tuple[bool, Optional[str]]:
    """
    验证 API 密钥

    Args:
        apikey: API Key
        secret: API Secret

    Returns:
        (是否有效, 错误信息)
    """
    if not apikey:
        return False, "API key cannot be empty"

    if not secret:
        return False, "API secret cannot be empty"

    # 基本长度检查
    if len(apikey) < 10:
        return False, "API key too short"

    if len(secret) < 10:
        return False, "API secret too short"

    return True, None


def validate_order_size(size: float, min_size: float = 0.0) -> Tuple[bool, Optional[str]]:
    """
    验证订单大小

    Args:
        size: 订单大小
        min_size: 最小订单大小

    Returns:
        (是否有效, 错误信息)
    """
    if size <= 0:
        return False, "Order size must be positive"

    if size < min_size:
        return False, f"Order size must be at least {min_size}"

    return True, None


def validate_price(price: float) -> Tuple[bool, Optional[str]]:
    """
    验证价格

    Args:
        price: 价格

    Returns:
        (是否有效, 错误信息)
    """
    if price <= 0:
        return False, "Price must be positive"

    return True, None


def validate_commission(commission: float) -> Tuple[bool, Optional[str]]:
    """
    验证手续费率

    Args:
        commission: 手续费率

    Returns:
        (是否有效, 错误信息)
    """
    if commission < 0:
        return False, "Commission cannot be negative"

    if commission > 1:
        return False, "Commission cannot exceed 100%"

    return True, None


def validate_cash(cash: float) -> Tuple[bool, Optional[str]]:
    """
    验证初始资金

    Args:
        cash: 初始资金

    Returns:
        (是否有效, 错误信息)
    """
    if cash <= 0:
        return False, "Initial cash must be positive"

    return True, None
