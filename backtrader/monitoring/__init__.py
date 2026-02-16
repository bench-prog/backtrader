#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级实时监控告警系统
Enterprise Real-time Monitoring & Alerting System for Backtrader

模块结构:
├── alerting_system.py    # 告警系统核心
├── dashboard.py          # 可视化监控面板
└── __init__.py          # 模块初始化
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# 告警系统组件
from .alerting_system import (
    SystemMetricsCollector,
    BusinessMetricsCollector,
    AlertRule,
    SystemResourceAlertRule,
    BusinessAlertRule,
    Alert,
    NotificationChannel,
    EmailNotificationChannel,
    WebhookNotificationChannel,
    AlertManager,
    RealTimeMonitoringService,
    create_monitoring_service,
    add_monitoring_to_cerebro
)

# 监控面板组件
from .dashboard import (
    MonitoringDashboard,
    StrategyMonitorMixin,
    create_monitoring_dashboard,
    integrate_monitoring_dashboard
)

__all__ = [
    # 告警系统
    'SystemMetricsCollector',
    'BusinessMetricsCollector',
    'AlertRule',
    'SystemResourceAlertRule',
    'BusinessAlertRule',
    'Alert',
    'NotificationChannel',
    'EmailNotificationChannel',
    'WebhookNotificationChannel',
    'AlertManager',
    'RealTimeMonitoringService',
    'create_monitoring_service',
    'add_monitoring_to_cerebro',
    
    # 监控面板
    'MonitoringDashboard',
    'StrategyMonitorMixin',
    'create_monitoring_dashboard',
    'integrate_monitoring_dashboard',
]

__version__ = '1.0.0'
__author__ = 'Backtrader Monitoring Team'