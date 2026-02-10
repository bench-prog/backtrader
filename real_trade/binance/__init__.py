#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Binance Real Trade Module

快速开始::

    from real_trade.binance import create_binance_engine
    import backtrader as bt

    store, broker, data = create_binance_engine(
        symbol='BTC/USDT', timeframe='1h',
        testnet=True, paper_trading=True, backtest=True,
    )

    cerebro = bt.Cerebro()
    cerebro.setbroker(broker)
    cerebro.adddata(data)
    cerebro.addstrategy(MyStrategy)
    cerebro.run()

从配置文件创建::

    from real_trade.binance import create_binance_engine_from_config

    store, broker, data = create_binance_engine_from_config("my_config.json")
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import os
from typing import Optional, Union

from .broker import BinanceBroker
from .datafeed import BinanceData
from .store import BinanceStore

__all__ = [
    "BinanceStore",
    "BinanceBroker",
    "BinanceData",
    "create_binance_engine",
    "create_binance_engine_from_config",
]


def _validate_params(symbol: str, timeframe: str, cash: float, commission: float):
    """参数前置校验，失败直接抛出 ValueError"""
    from real_trade.utils.validators import (
        validate_positive,
        validate_symbol,
        validate_timeframe,
    )

    ok, msg = validate_symbol(symbol)
    if not ok:
        raise ValueError(msg)

    ok, msg = validate_timeframe(timeframe)
    if not ok:
        raise ValueError(msg)

    ok, msg = validate_positive(cash, "cash")
    if not ok:
        raise ValueError(msg)

    if commission < 0:
        raise ValueError(f"commission must be >= 0, got {commission}")


def create_binance_engine(
    apikey: str = "",
    secret: str = "",
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    testnet: bool = True,
    paper_trading: bool = True,
    cash: float = 10000.0,
    commission: float = 0.001,
    proxy: str = None,
    backtest: bool = False,
    market_type: str = "spot",
    **kwargs,
):
    """
    快速创建 Binance 交易引擎

    Args:
        apikey: API Key
        secret: API Secret
        symbol: 交易对 (e.g. BTC/USDT)
        timeframe: 时间周期 (1m, 5m, 15m, 1h, 4h, 1d ...)
        testnet: 是否使用测试网
        paper_trading: 是否模拟交易
        cash: 初始资金
        commission: 佣金比例
        proxy: 代理地址
        backtest: 回测模式（加载历史数据，不需要 API 密钥）
        market_type: 市场类型 (spot / future / delivery)
        **kwargs: 传递给 DataFeed 的额外参数（historical_limit, fromdate, todate）

    Returns:
        (store, broker, data) 元组
    """
    # 参数校验
    _validate_params(symbol, timeframe, cash, commission)

    # 回测模式：无需 API 密钥，使用公共数据端点
    use_apikey = apikey if not backtest else ""
    use_secret = secret if not backtest else ""
    use_testnet = testnet if not backtest else False

    store = BinanceStore.get_instance(
        apikey=use_apikey,
        secret=use_secret,
        testnet=use_testnet,
        proxy=proxy,
        market_type=market_type,
    )

    broker = BinanceBroker(store, paper_trading=paper_trading, cash=cash)
    if commission > 0:
        broker.setcommission(commission=commission)

    data = BinanceData.from_timeframe_string(
        timeframe,
        store,
        symbol=symbol,
        backtest=backtest,
        **kwargs,
    )

    return store, broker, data


def create_binance_engine_from_config(
    config: Union[str, "GlobalConfig", dict],
    config_dir: Optional[str] = None,
):
    """
    从配置创建 Binance 交易引擎

    Args:
        config: 配置来源，支持三种类型:
            - str: JSON 文件路径（相对路径基于 config_dir 或 binance/config/）
            - GlobalConfig: 全局配置对象
            - dict: 配置字典（扁平或嵌套均可）
        config_dir: JSON 文件搜索目录（仅 config 为文件名时使用）

    Returns:
        (store, broker, data) 元组

    Usage::

        # 从 JSON 文件
        store, broker, data = create_binance_engine_from_config("my_config.json")

        # 从 GlobalConfig
        from real_trade.utils import GlobalConfig
        cfg = GlobalConfig(symbol="ETH/USDT", timeframe="15m", backtest=True)
        store, broker, data = create_binance_engine_from_config(cfg)

        # 从字典
        store, broker, data = create_binance_engine_from_config({
            "symbol": "ETH/USDT", "timeframe": "15m", "backtest": True,
        })
    """
    from real_trade.utils.config import GlobalConfig

    if isinstance(config, str):
        # JSON 文件路径
        if not os.path.isabs(config) and not os.path.exists(config):
            # 在默认 config 目录中查找
            if config_dir is None:
                config_dir = os.path.join(os.path.dirname(__file__), "config")
            config = os.path.join(config_dir, config)

        if not os.path.exists(config):
            raise FileNotFoundError(f"Config file not found: {config}")

        cfg = GlobalConfig.from_json(config)

    elif isinstance(config, dict):
        # 判断是嵌套还是扁平
        nested_keys = {"api", "trading", "data"}
        if nested_keys & set(config.keys()):
            cfg = GlobalConfig.from_nested_dict(config)
        else:
            cfg = GlobalConfig.from_dict(config)

    elif isinstance(config, GlobalConfig):
        cfg = config

    else:
        raise TypeError(
            f"config must be str/dict/GlobalConfig, got {type(config).__name__}"
        )

    # 处理日期字符串 → datetime
    data_kwargs = {}
    if cfg.historical_limit != 1000:
        data_kwargs["historical_limit"] = cfg.historical_limit
    if cfg.fromdate:
        data_kwargs["fromdate"] = datetime.datetime.fromisoformat(cfg.fromdate)
    if cfg.todate:
        data_kwargs["todate"] = datetime.datetime.fromisoformat(cfg.todate)

    return create_binance_engine(
        apikey=cfg.apikey,
        secret=cfg.secret,
        symbol=cfg.symbol,
        timeframe=cfg.timeframe,
        testnet=cfg.testnet,
        paper_trading=cfg.paper_trading,
        cash=cfg.cash,
        commission=cfg.commission,
        proxy=cfg.proxy,
        backtest=cfg.backtest,
        market_type=cfg.market_type,
        **data_kwargs,
    )
