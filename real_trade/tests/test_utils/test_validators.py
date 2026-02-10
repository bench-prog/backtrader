#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
测试公共工具 - validators
"""

from real_trade.utils.validators import (
    validate_api_keys,
    validate_percentage,
    validate_positive,
    validate_symbol,
    validate_timeframe,
)


def test_validate_symbol_valid():
    ok, err = validate_symbol("BTC/USDT")
    assert ok
    assert err == ""


def test_validate_symbol_invalid():
    ok, err = validate_symbol("BTCUSDT")
    assert not ok
    assert "BASE/QUOTE" in err


def test_validate_timeframe_valid():
    ok, _ = validate_timeframe("1h")
    assert ok


def test_validate_timeframe_invalid():
    ok, err = validate_timeframe("2d")
    assert not ok


def test_validate_api_keys():
    ok, _ = validate_api_keys("a" * 20, "b" * 20)
    assert ok

    ok, _ = validate_api_keys("short", "b" * 20)
    assert not ok


def test_validate_positive():
    ok, _ = validate_positive(1.0, "test")
    assert ok
    ok, _ = validate_positive(-1.0, "test")
    assert not ok


def test_validate_percentage():
    ok, _ = validate_percentage(0.5, "test")
    assert ok
    ok, _ = validate_percentage(1.5, "test")
    assert not ok
