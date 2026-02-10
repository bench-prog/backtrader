#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
GlobalConfig - 全局配置管理

统一管理 real_trade 各模块的配置，支持环境变量、JSON 文件。
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

    # 交易
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    paper_trading: bool = True
    initial_cash: float = 10000.0
    commission: float = 0.001

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

    # 额外参数
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlobalConfig":
        known = {k for k in cls.__dataclass_fields__}
        extra = {k: v for k, v in data.items() if k not in known}
        filtered = {k: v for k, v in data.items() if k in known}
        filtered["extra"] = extra
        return cls(**filtered)

    @classmethod
    def from_json(cls, filepath: str) -> "GlobalConfig":
        with open(filepath, "r") as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def from_env(cls, prefix: str = "RT_") -> "GlobalConfig":
        """从环境变量加载，变量名格式: RT_EXCHANGE, RT_APIKEY 等"""
        data = {}
        for field_name, field_obj in cls.__dataclass_fields__.items():
            env_key = f"{prefix}{field_name.upper()}"
            env_val = os.getenv(env_key)
            if env_val is not None:
                # 类型转换
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
