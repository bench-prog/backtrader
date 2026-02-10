#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Real Trade Module

实盘交易模块集合。

模块结构:
    common/          通用基类（BaseStore, BaseBroker, BaseData, BaseWebSocket）
    binance/         Binance 交易所
    strategies/      共享策略库（趋势/均值回归/动量/网格/复合）
    risk/            风控模块（仓位管理/止损/限制/回撤控制）
    engine/          交易引擎（统一运行器/调度/生命周期）
    monitor/         监控模块（绩效追踪/健康检查/报告）
    notifications/   通知模块（Telegram/钉钉/Webhook/邮件）
    utils/           公共工具（日志/配置/校验/重试/时间）
    tests/           统一测试
    examples/        使用示例
"""

__version__ = "2.0.0"

from . import binance, engine, monitor, notifications, risk, strategies, utils

__all__ = [
    "binance",
    "strategies",
    "risk",
    "engine",
    "monitor",
    "notifications",
    "utils",
]
