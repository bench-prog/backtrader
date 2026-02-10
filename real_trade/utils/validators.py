#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Validators - 参数校验
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from typing import Tuple

VALID_TIMEFRAMES = {
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
}


def validate_symbol(symbol: str) -> Tuple[bool, str]:
    """
    校验交易对格式

    Returns:
        (is_valid, error_message)
    """
    if not symbol or not isinstance(symbol, str):
        return False, "Symbol cannot be empty"

    if "/" not in symbol:
        return (
            False,
            f"Invalid symbol format: '{symbol}'. Expected 'BASE/QUOTE' (e.g. BTC/USDT)",
        )

    parts = symbol.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False, f"Invalid symbol format: '{symbol}'"

    return True, ""


def validate_timeframe(timeframe: str) -> Tuple[bool, str]:
    """校验时间周期"""
    if timeframe not in VALID_TIMEFRAMES:
        return (
            False,
            f"Invalid timeframe: '{timeframe}'. Valid: {sorted(VALID_TIMEFRAMES)}",
        )
    return True, ""


def validate_api_keys(apikey: str, secret: str) -> Tuple[bool, str]:
    """校验 API 密钥"""
    if not apikey or not isinstance(apikey, str) or len(apikey.strip()) < 10:
        return False, "API key appears invalid (too short or empty)"
    if not secret or not isinstance(secret, str) or len(secret.strip()) < 10:
        return False, "API secret appears invalid (too short or empty)"
    return True, ""


def validate_positive(value: float, name: str) -> Tuple[bool, str]:
    """校验正数"""
    if not isinstance(value, (int, float)) or value <= 0:
        return False, f"{name} must be a positive number, got {value}"
    return True, ""


def validate_percentage(value: float, name: str) -> Tuple[bool, str]:
    """校验百分比 0~1"""
    if not isinstance(value, (int, float)) or value < 0 or value > 1:
        return False, f"{name} must be between 0 and 1, got {value}"
    return True, ""
