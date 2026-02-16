#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级日志增强系统
Enterprise Logging Enhancement for Backtrader

模块结构:
├── enhanced_logging.py    # 日志增强核心实现
└── __init__.py            # 模块初始化和便捷接口
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# 核心组件
from .enhanced_logging import (
    TradingLogger,
    get_trading_logger,
    setup_trading_logger,
    log_order_execution,
    log_risk_event,
    LoggingStrategyMixin
)

__all__ = [
    'TradingLogger',
    'get_trading_logger',
    'setup_trading_logger',
    'log_order_execution',
    'log_risk_event',
    'LoggingStrategyMixin',
]

__version__ = '1.0.0'
__author__ = 'Backtrader Logging Team'


# 保持与您示例一致的API接口
def setup_trading_logger(log_dir="logs", retention_days=30, rotation_time="00:00"):
    """
    设置交易日志系统（P0标准接口）
    
    示例:
        logger = setup_trading_logger()
        logger.add("logs/app.log", rotation="00:00")
    """
    from .enhanced_logging import setup_trading_logger as _setup_trading_logger
    return _setup_trading_logger(log_dir, retention_days, rotation_time)