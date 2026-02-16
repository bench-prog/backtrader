#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级风险管理系统
Enterprise Risk Management System for Backtrader

模块结构:
├── pre_trade_engine.py     # 事前风控引擎
├── real_time_monitor.py    # 实时风险监控
├── config_manager.py       # 风控配置管理
└── __init__.py            # 模块初始化
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# 事前风控引擎
from .pre_trade_engine import (
    PreTradeRiskEngine,
    RiskAwareBroker,
    integrate_pre_trade_risk_engine,
    risk_controlled
)

# 实时风险监控
from .real_time_monitor import (
    RealTimeRiskMonitor,
    DynamicStopLoss,
    add_real_time_risk_monitoring,
    RiskControlMixin
)

# 风控配置管理
from .config_manager import (
    RiskRule,
    LeverageLimitRule,
    PositionConcentrationRule,
    DailyLossLimitRule,
    MarketImpactRule,
    RiskConfigurationManager,
    MultiAccountRiskManager,
    create_default_risk_config,
    load_risk_config_from_file,
    save_risk_config_to_file
)

__all__ = [
    # 事前风控引擎
    'PreTradeRiskEngine',
    'RiskAwareBroker',
    'integrate_pre_trade_risk_engine',
    'risk_controlled',
    
    # 实时风险监控
    'RealTimeRiskMonitor',
    'DynamicStopLoss',
    'add_real_time_risk_monitoring',
    'RiskControlMixin',
    
    # 风控配置管理
    'RiskRule',
    'LeverageLimitRule',
    'PositionConcentrationRule',
    'DailyLossLimitRule',
    'MarketImpactRule',
    'RiskConfigurationManager',
    'MultiAccountRiskManager',
    'create_default_risk_config',
    'load_risk_config_from_file',
    'save_risk_config_to_file',
]

__version__ = '1.0.0'
__author__ = 'Backtrader Risk Management Team'