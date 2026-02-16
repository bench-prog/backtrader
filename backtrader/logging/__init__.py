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
    LoggingStrategyMixin,
    Logger,
    get_logger,
    log_order_execution,
    log_risk_event,
    setup_logger,
)

__all__ = [
    "Logger",
    "get_logger",
    "setup_logger",
    "log_order_execution",
    "log_risk_event",
    "LoggingStrategyMixin",
]

__version__ = "1.0.0"
__author__ = "Backtrader Logging Team"
