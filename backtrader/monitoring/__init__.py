#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级实时监控告警系统
Enterprise Real-time Monitoring & Alerting System for Backtrader

模块结构:
├── alerting_system.py    # 告警系统核心
├── dashboard.py          # 可视化监控面板
└── __init__.py          # 模块初始化

使用方式（简化版）:
    # 方式1: 作为 Analyzer 自动集成
    cerebro.addanalyzer(RealTimeMonitoringService)

    # 方式2: 使用辅助函数
    from backtrader.monitoring import enable_monitoring
    enable_monitoring(cerebro)
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# 告警系统组件
from .alerting_system import (
    Alert,
    AlertManager,
    AlertRule,
    BusinessAlertRule,
    BusinessMetricsCollector,
    EmailNotificationChannel,
    NotificationChannel,
    RealTimeMonitoringService,
    RealTimeMonitoringAnalyzer,
    SystemMetricsCollector,
    SystemResourceAlertRule,
    WebhookNotificationChannel,
    add_monitoring_to_cerebro,
    create_monitoring_service,
)

# 监控面板组件 (可选依赖 - 需要 Flask 和 Plotly)
try:
    from .dashboard import (
        MonitoringDashboard,
        StrategyMonitorMixin,
        create_monitoring_dashboard,
        integrate_monitoring_dashboard,
    )
    _dashboard_available = True
except ImportError:
    _dashboard_available = False
    # 提供占位符，避免导入错误
    MonitoringDashboard = None
    StrategyMonitorMixin = None
    create_monitoring_dashboard = None
    integrate_monitoring_dashboard = None

# 全局告警管理器单例
_global_alert_manager = None

def get_alert_manager():
    """
    获取全局告警管理器单例

    Returns:
        AlertManager: 告警管理器实例
    """
    global _global_alert_manager
    if _global_alert_manager is None:
        _global_alert_manager = AlertManager()
    return _global_alert_manager

def set_alert_manager(alert_manager):
    """
    设置全局告警管理器

    Args:
        alert_manager: AlertManager 实例
    """
    global _global_alert_manager
    _global_alert_manager = alert_manager

def enable_monitoring(cerebro, email_config=None, webhook_config=None):
    """
    为 Cerebro 启用完整的监控功能（一键集成）

    Args:
        cerebro: Cerebro 实例
        email_config: 邮件通知配置 (可选)
        webhook_config: Webhook 通知配置 (可选)

    Returns:
        AlertManager: 告警管理器实例

    Example:
        cerebro = bt.Cerebro()
        alert_mgr = enable_monitoring(cerebro, email_config={
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'from_addr': 'alerts@example.com',
            'to_addrs': ['admin@example.com'],
            'username': 'user',
            'password': 'pass'
        })
    """
    alert_manager = get_alert_manager()

    # 配置通知渠道
    if email_config:
        email_channel = EmailNotificationChannel(**email_config)
        alert_manager.add_notification_channel(email_channel)

    if webhook_config:
        webhook_channel = WebhookNotificationChannel(**webhook_config)
        alert_manager.add_notification_channel(webhook_channel)

    # 添加监控 Analyzer
    from .alerting_system import RealTimeMonitoringAnalyzer
    cerebro.addanalyzer(RealTimeMonitoringAnalyzer)

    # 存储在 cerebro 对象上，方便访问
    cerebro._alert_manager = alert_manager

    return alert_manager

__all__ = [
    # 告警系统
    "SystemMetricsCollector",
    "BusinessMetricsCollector",
    "AlertRule",
    "SystemResourceAlertRule",
    "BusinessAlertRule",
    "Alert",
    "NotificationChannel",
    "EmailNotificationChannel",
    "WebhookNotificationChannel",
    "AlertManager",
    "RealTimeMonitoringService",
    "RealTimeMonitoringAnalyzer",
    "create_monitoring_service",
    "add_monitoring_to_cerebro",
    # 全局访问和快捷集成
    "get_alert_manager",
    "set_alert_manager",
    "enable_monitoring",
]

# 仅在 dashboard 可用时导出相关组件
if _dashboard_available:
    __all__.extend([
        "MonitoringDashboard",
        "StrategyMonitorMixin",
        "create_monitoring_dashboard",
        "integrate_monitoring_dashboard",
    ])

__version__ = "1.0.0"
__author__ = "Backtrader Monitoring Team"
