#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
配置管理模块

支持从文件、环境变量、命令行参数加载配置。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class Config:
    """配置类"""

    # API配置
    apikey: str = ""
    secret: str = ""
    testnet: bool = True
    proxy: Optional[str] = None

    # 交易配置
    symbol: str = "BTC/USDT"
    timeframe: str = "1m"
    market_type: str = "spot"  # spot, linear, inverse

    # Broker配置
    paper_trading: bool = True
    initial_cash: float = 10000.0
    commission: float = 0.001

    # 策略配置
    strategy_params: Dict[str, Any] = None

    # 回测配置
    backtest: bool = False
    fromdate: Optional[str] = None
    todate: Optional[str] = None

    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None

    def __post_init__(self):
        if self.strategy_params is None:
            self.strategy_params = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载"""
        return cls(
            apikey=os.getenv("BYBIT_API_KEY", ""),
            secret=os.getenv("BYBIT_API_SECRET", ""),
            testnet=os.getenv("BYBIT_TESTNET", "true").lower() == "true",
            proxy=os.getenv("BYBIT_PROXY"),
            symbol=os.getenv("BYBIT_SYMBOL", "BTC/USDT"),
            timeframe=os.getenv("BYBIT_TIMEFRAME", "1m"),
            market_type=os.getenv("BYBIT_MARKET_TYPE", "spot"),
            paper_trading=os.getenv("BYBIT_PAPER_TRADING", "true").lower() == "true",
            initial_cash=float(os.getenv("BYBIT_INITIAL_CASH", "10000.0")),
            commission=float(os.getenv("BYBIT_COMMISSION", "0.001")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def save_to_file(self, filepath: str):
        """保存到文件"""
        with open(filepath, "w") as f:
            f.write(self.to_json())
        print(f"✓ Config saved to {filepath}")

    def update(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


def load_config_from_file(filepath: str) -> Config:
    """
    从文件加载配置

    支持 JSON 和 Python 文件格式。

    Args:
        filepath: 配置文件路径

    Returns:
        Config 对象
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Config file not found: {filepath}")

    # JSON 格式
    if filepath.endswith(".json"):
        with open(filepath, "r") as f:
            data = json.load(f)
        return Config.from_dict(data)

    # Python 格式
    elif filepath.endswith(".py"):
        import importlib.util

        spec = importlib.util.spec_from_file_location("config", filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 提取大写变量作为配置
        config_dict = {
            k.lower(): v for k, v in vars(module).items() if k.isupper()
        }
        return Config.from_dict(config_dict)

    else:
        raise ValueError(f"Unsupported config file format: {filepath}")


def create_default_config(filepath: str = "config.json"):
    """
    创建默认配置文件

    Args:
        filepath: 保存路径
    """
    config = Config()
    config.save_to_file(filepath)
    return config
