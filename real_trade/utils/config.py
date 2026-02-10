#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
GlobalConfig - 全局配置管理

统一管理 real_trade 各模块的配置，支持环境变量、JSON 文件。
兼容两种 JSON 结构：
  - 扁平结构: {"apikey": "xxx", "symbol": "BTC/USDT", ...}
  - 嵌套结构: {"api": {"apikey": "xxx"}, "data": {"symbol": "BTC/USDT"}, ...}
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class GlobalConfig:
    """
    全局配置

    支持从环境变量、JSON文件、字典三种方式加载。
    """

    # 交易所
    exchange: str = "binance"
    apikey: str = ""
    secret: str = ""
    testnet: bool = True
    proxy: Optional[str] = None
    market_type: str = "spot"

    # 交易
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    paper_trading: bool = True
    cash: float = 10000.0
    commission: float = 0.001
    backtest: bool = False

    # 数据
    historical_limit: int = 1000
    fromdate: Optional[str] = None  # ISO 格式 "2024-01-01"
    todate: Optional[str] = None

    # 风控
    max_position_pct: float = 0.3
    risk_per_trade: float = 0.02
    max_drawdown_pct: float = 0.20
    max_daily_trades: int = 50

    # 日志
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # 通知
    notify_on_trade: bool = False
    notify_on_error: bool = True

    # 额外参数（策略参数等）
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlobalConfig":
        """从扁平字典创建配置"""
        known = {k for k in cls.__dataclass_fields__}
        extra = {k: v for k, v in data.items() if k not in known}
        filtered = {k: v for k, v in data.items() if k in known}
        if extra:
            filtered.setdefault("extra", {}).update(extra)
        return cls(**filtered)

    @classmethod
    def from_nested_dict(cls, data: Dict[str, Any]) -> "GlobalConfig":
        """
        从嵌套字典创建配置

        支持 binance/config/ 下的 JSON 格式::

            {
              "api": {"apikey": "", "secret": "", "testnet": true, "market_type": "spot"},
              "trading": {"paper_trading": true, "initial_cash": 10000.0, "commission": 0.001},
              "data": {"symbol": "BTC/USDT", "timeframe": "1h", "backtest": false, ...},
              "strategy": {...},
              "proxy": {"auto_detect": true, "proxy_url": ""}
            }
        """
        flat: Dict[str, Any] = {}

        # api 段
        api = data.get("api", {})
        for key in ("apikey", "secret", "testnet", "market_type"):
            if key in api:
                flat[key] = api[key]

        # trading 段
        trading = data.get("trading", {})
        if "paper_trading" in trading:
            flat["paper_trading"] = trading["paper_trading"]
        if "initial_cash" in trading:
            flat["cash"] = trading["initial_cash"]  # 统一为 cash
        if "commission" in trading:
            flat["commission"] = trading["commission"]

        # data 段
        data_cfg = data.get("data", {})
        for key in ("symbol", "timeframe", "backtest", "historical_limit"):
            if key in data_cfg:
                flat[key] = data_cfg[key]

        # proxy 段
        proxy_cfg = data.get("proxy", {})
        proxy_url = proxy_cfg.get("proxy_url", "")
        if proxy_url:
            flat["proxy"] = proxy_url
        # auto_detect=True 时不设置 proxy，让 BaseStore 自动检测

        # strategy 段 → 放入 extra
        strategy = data.get("strategy", {})
        if strategy:
            flat["extra"] = strategy

        return cls.from_dict(flat)

    @classmethod
    def from_json(cls, filepath: str) -> "GlobalConfig":
        """
        从 JSON 文件创建配置

        自动识别扁平/嵌套结构。
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        # 判断是否为嵌套结构（包含 api/trading/data 等顶层 key）
        nested_keys = {"api", "trading", "data"}
        if nested_keys & set(data.keys()):
            return cls.from_nested_dict(data)
        return cls.from_dict(data)

    @classmethod
    def from_env(cls, prefix: str = "RT_") -> "GlobalConfig":
        """从环境变量加载，变量名格式: RT_EXCHANGE, RT_APIKEY 等"""
        data = {}
        for field_name, field_obj in cls.__dataclass_fields__.items():
            env_key = f"{prefix}{field_name.upper()}"
            env_val = os.getenv(env_key)
            if env_val is not None:
                ft = field_obj.type
                if ft == "bool" or ft is bool:
                    data[field_name] = env_val.lower() in ("true", "1", "yes")
                elif ft == "float" or ft is float:
                    data[field_name] = float(env_val)
                elif ft == "int" or ft is int:
                    data[field_name] = int(env_val)
                else:
                    data[field_name] = env_val
        return cls.from_dict(data)

    def save(self, filepath: str):
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
