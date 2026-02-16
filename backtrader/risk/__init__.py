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

使用方式（简化版）:
    # 方式1: 使用风控 Broker（推荐）
    from backtrader.risk import enable_risk_control
    enable_risk_control(cerebro)

    # 方式2: 手动替换 Broker
    from backtrader.risk import RiskAwareBroker
    cerebro.broker = RiskAwareBroker()

    # 方式3: 作为 Analyzer 添加实时监控
    cerebro.addanalyzer(RealTimeRiskMonitor)
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# 风控配置管理
from .config_manager import (
    DailyLossLimitRule,
    LeverageLimitRule,
    MarketImpactRule,
    MultiAccountRiskManager,
    PositionConcentrationRule,
    RiskConfigurationManager,
    RiskRule,
    create_default_risk_config,
    load_risk_config_from_file,
    save_risk_config_to_file,
)

# 事前风控引擎
from .pre_trade_engine import (
    PreTradeRiskEngine,
    RiskAwareBroker,
    integrate_pre_trade_risk_engine,
    risk_controlled,
)

# 实时风险监控
from .real_time_monitor import (
    DynamicStopLoss,
    RealTimeRiskMonitor,
    RiskControlMixin,
    add_real_time_risk_monitoring,
)

def enable_risk_control(cerebro, risk_config=None):
    """
    为 Cerebro 启用完整的风险控制功能（一键集成）

    Args:
        cerebro: Cerebro 实例
        risk_config: 风控配置字典 (可选)

    Returns:
        RiskAwareBroker: 风控 Broker 实例

    Example:
        cerebro = bt.Cerebro()
        enable_risk_control(cerebro, risk_config={
            'max_leverage': 2.0,
            'max_position_concentration': 0.3,
            'max_daily_loss_limit': 0.05
        })
    """
    # 创建或获取风控 Broker
    if not isinstance(cerebro.broker, RiskAwareBroker):
        # 创建新的风控 Broker
        risk_broker = RiskAwareBroker()
        cerebro.broker = risk_broker
    else:
        risk_broker = cerebro.broker

    # 配置风控参数
    if risk_config:
        risk_broker.risk_engine.configure(**risk_config)

    # 添加实时风险监控 Analyzer
    cerebro.addanalyzer(RealTimeRiskMonitor)

    # 存储在 cerebro 对象上，方便访问
    cerebro._risk_broker = risk_broker

    return risk_broker

__all__ = [
    # 事前风控引擎
    "PreTradeRiskEngine",
    "RiskAwareBroker",
    "integrate_pre_trade_risk_engine",
    "risk_controlled",
    # 实时风险监控
    "RealTimeRiskMonitor",
    "DynamicStopLoss",
    "add_real_time_risk_monitoring",
    "RiskControlMixin",
    # 风控配置管理
    "RiskRule",
    "LeverageLimitRule",
    "PositionConcentrationRule",
    "DailyLossLimitRule",
    "MarketImpactRule",
    "RiskConfigurationManager",
    "MultiAccountRiskManager",
    "create_default_risk_config",
    "load_risk_config_from_file",
    "save_risk_config_to_file",
    # 快捷集成
    "enable_risk_control",
]

__version__ = "1.0.0"
__author__ = "Backtrader Risk Management Team"
