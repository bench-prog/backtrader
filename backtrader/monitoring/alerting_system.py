#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级实时监控告警系统 (Enterprise Monitoring & Alerting System)
基于backtrader架构的实时监控和告警解决方案

核心功能：
1. 系统资源监控 (CPU/内存/网络)
2. 策略运行状态监控
3. 业务指标监控 (订单/仓位/资金)
4. 多渠道告警通知
5. 告警规则引擎
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import psutil
import threading
import time
import logging
import json
import datetime
from collections import deque, defaultdict
from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Any, Optional
import queue
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests


class SystemMetricsCollector:
    """
    系统指标收集器 - 收集系统资源使用情况
    """
    
    def __init__(self, collect_interval: float = 1.0):
        self.collect_interval = collect_interval
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self._running = False
        self._thread = None
        
    def start(self):
        """启动指标收集"""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._collect_loop, daemon=True)
            self._thread.start()
            
    def stop(self):
        """停止指标收集"""
        self._running = False
        if self._thread:
            self._thread.join()
            
    def _collect_loop(self):
        """指标收集循环"""
        while self._running:
            try:
                metrics = self._collect_system_metrics()
                timestamp = datetime.datetime.now()
                
                # 存储指标
                for key, value in metrics.items():
                    self.metrics_history[key].append((timestamp, value))
                    
                time.sleep(self.collect_interval)
            except Exception as e:
                print(f"指标收集错误: {e}")
                
    def _collect_system_metrics(self) -> Dict[str, float]:
        """收集系统指标"""
        metrics = {}
        
        try:
            # CPU使用率
            metrics['cpu_percent'] = psutil.cpu_percent(interval=0.1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            metrics['memory_percent'] = memory.percent
            metrics['memory_available_mb'] = memory.available / 1024 / 1024
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            metrics['disk_percent'] = disk.percent
            
            # 网络IO
            net_io = psutil.net_io_counters()
            metrics['network_bytes_sent'] = net_io.bytes_sent
            metrics['network_bytes_recv'] = net_io.bytes_recv
            
            # 进程信息
            current_process = psutil.Process()
            metrics['process_cpu_percent'] = current_process.cpu_percent()
            metrics['process_memory_mb'] = current_process.memory_info().rss / 1024 / 1024
            
        except Exception as e:
            print(f"系统指标收集失败: {e}")
            
        return metrics
    
    def get_current_metrics(self) -> Dict[str, float]:
        """获取当前指标"""
        current_metrics = {}
        for key, history in self.metrics_history.items():
            if history:
                current_metrics[key] = history[-1][1]
        return current_metrics
    
    def get_metrics_history(self, metric_name: str, minutes: int = 5) -> List[tuple]:
        """获取指定时间段的历史指标"""
        if metric_name not in self.metrics_history:
            return []
            
        cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=minutes)
        return [(ts, val) for ts, val in self.metrics_history[metric_name] if ts >= cutoff_time]


class BusinessMetricsCollector(bt.Observer):
    """
    业务指标收集器 - 收集交易相关业务指标
    """
    
    lines = ('orders_count', 'positions_value', 'daily_pnl', 'win_rate')
    plotinfo = dict(plot=True, subplot=True)
    
    params = (
        ('collect_interval', 60),  # 收集间隔(秒)
    )
    
    def __init__(self):
        super(BusinessMetricsCollector, self).__init__()
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.last_collect_time = None
        self.orders_tracker = defaultdict(int)
        self.trades_history = deque(maxlen=1000)
        
    def next(self):
        """每周期收集业务指标"""
        current_time = time.time()
        
        # 定期收集指标
        if (self.last_collect_time is None or 
            current_time - self.last_collect_time >= self.p.collect_interval):
            
            metrics = self._collect_business_metrics()
            timestamp = datetime.datetime.now()
            
            # 存储指标
            for key, value in metrics.items():
                self.metrics_history[key].append((timestamp, value))
                # 更新线条值用于绘图
                if hasattr(self.lines, key):
                    getattr(self.lines, key)[0] = value
                    
            self.last_collect_time = current_time
    
    def _collect_business_metrics(self) -> Dict[str, float]:
        """收集业务指标"""
        metrics = {}
        
        try:
            # 订单统计
            metrics['active_orders'] = len([o for o in self._getorders() if o.alive()])
            metrics['completed_orders'] = len([o for o in self._getorders() if not o.alive()])
            
            # 持仓价值
            total_position_value = 0
            for data in self.datas:
                position = self.broker.getposition(data)
                if position.size != 0:
                    total_position_value += position.size * data.close[0]
            metrics['positions_value'] = total_position_value
            
            # 资金状况
            metrics['cash'] = self.broker.getcash()
            metrics['portfolio_value'] = self.broker.getvalue()
            
            # 计算日盈亏
            daily_pnl = self._calculate_daily_pnl()
            metrics['daily_pnl'] = daily_pnl
            metrics['daily_pnl_percent'] = daily_pnl / self.broker.getvalue() if self.broker.getvalue() > 0 else 0
            
            # 胜率计算
            win_rate = self._calculate_win_rate()
            metrics['win_rate'] = win_rate
            
        except Exception as e:
            print(f"业务指标收集失败: {e}")
            
        return metrics
    
    def _getorders(self):
        """获取所有订单"""
        # 这里需要根据backtrader的具体实现来获取订单
        return []
    
    def _calculate_daily_pnl(self) -> float:
        """计算当日盈亏"""
        # 简化实现
        return 0.0
    
    def _calculate_win_rate(self) -> float:
        """计算胜率"""
        if not self.trades_history:
            return 0.0
        winning_trades = sum(1 for trade in self.trades_history if trade.pnl > 0)
        return winning_trades / len(self.trades_history)
    
    def notify_order(self, order):
        """订单通知"""
        if order.status == order.Completed:
            self.orders_tracker['completed'] += 1
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.orders_tracker['failed'] += 1
    
    def notify_trade(self, trade):
        """交易通知"""
        if trade.isclosed:
            self.trades_history.append(trade)


class AlertRule(ABC):
    """
    告警规则抽象基类
    """
    
    def __init__(self, name: str, description: str = "", enabled: bool = True):
        self.name = name
        self.description = description
        self.enabled = enabled
        self.trigger_count = 0
        self.last_trigger_time = None
        self.cooldown_until = None  # 冷却时间
        
    @abstractmethod
    def check(self, context: Dict[str, Any]) -> tuple:
        """
        检查是否触发告警
        返回: (triggered: bool, message: str)
        """
        pass
    
    def should_check(self, current_time: datetime.datetime) -> bool:
        """检查是否应该执行检查"""
        if not self.enabled:
            return False
        if self.cooldown_until and current_time < self.cooldown_until:
            return False
        return True
    
    def trigger(self, message: str):
        """触发告警"""
        self.trigger_count += 1
        self.last_trigger_time = datetime.datetime.now()
        return Alert(
            rule_name=self.name,
            message=message,
            timestamp=self.last_trigger_time,
            severity=self.get_severity()
        )
    
    def set_cooldown(self, minutes: int):
        """设置冷却时间"""
        self.cooldown_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    
    def get_severity(self) -> str:
        """获取告警级别"""
        return "WARNING"


class SystemResourceAlertRule(AlertRule):
    """系统资源告警规则"""
    
    def __init__(self, resource_type: str, threshold: float, operator: str = ">", **kwargs):
        super().__init__(f"{resource_type}_alert", f"{resource_type}资源告警", **kwargs)
        self.resource_type = resource_type
        self.threshold = threshold
        self.operator = operator
    
    def check(self, context: Dict[str, Any]) -> tuple:
        current_time = datetime.datetime.now()
        if not self.should_check(current_time):
            return False, ""
        
        current_value = context.get(self.resource_type, 0)
        
        triggered = False
        if self.operator == ">" and current_value > self.threshold:
            triggered = True
        elif self.operator == "<" and current_value < self.threshold:
            triggered = True
        elif self.operator == ">=" and current_value >= self.threshold:
            triggered = True
        elif self.operator == "<=" and current_value <= self.threshold:
            triggered = True
        
        if triggered:
            message = f"{self.resource_type} {self.operator} {self.threshold}, 当前值: {current_value:.2f}"
            alert = self.trigger(message)
            self.set_cooldown(5)  # 5分钟冷却
            return True, message
        
        return False, ""
    
    def get_severity(self) -> str:
        if self.resource_type in ['cpu_percent', 'memory_percent']:
            if self.threshold > 80:
                return "CRITICAL"
        return "WARNING"


class BusinessAlertRule(AlertRule):
    """业务告警规则"""
    
    def __init__(self, metric_name: str, threshold: float, comparison: str = ">", **kwargs):
        super().__init__(f"business_{metric_name}_alert", f"业务{metric_name}告警", **kwargs)
        self.metric_name = metric_name
        self.threshold = threshold
        self.comparison = comparison
    
    def check(self, context: Dict[str, Any]) -> tuple:
        current_time = datetime.datetime.now()
        if not self.should_check(current_time):
            return False, ""
        
        current_value = context.get(self.metric_name, 0)
        
        triggered = False
        if self.comparison == ">" and current_value > self.threshold:
            triggered = True
        elif self.comparison == "<" and current_value < self.threshold:
            triggered = True
        
        if triggered:
            message = f"业务指标 {self.metric_name} {self.comparison} {self.threshold}, 当前值: {current_value:.2f}"
            alert = self.trigger(message)
            self.set_cooldown(10)  # 10分钟冷却
            return True, message
        
        return False, ""


class Alert:
    """
    告警实体类
    """
    
    def __init__(self, rule_name: str, message: str, timestamp: datetime.datetime, severity: str = "WARNING"):
        self.id = f"{rule_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        self.rule_name = rule_name
        self.message = message
        self.timestamp = timestamp
        self.severity = severity
        self.status = "ACTIVE"  # ACTIVE, ACKNOWLEDGED, RESOLVED
        self.acknowledged_by = None
        self.resolved_time = None
    
    def acknowledge(self, user: str = "system"):
        """确认告警"""
        self.status = "ACKNOWLEDGED"
        self.acknowledged_by = user
    
    def resolve(self):
        """解决告警"""
        self.status = "RESOLVED"
        self.resolved_time = datetime.datetime.now()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'rule_name': self.rule_name,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity,
            'status': self.status,
            'acknowledged_by': self.acknowledged_by,
            'resolved_time': self.resolved_time.isoformat() if self.resolved_time else None
        }


class NotificationChannel(ABC):
    """
    通知渠道抽象基类
    """
    
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
    
    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """发送通知"""
        pass


class EmailNotificationChannel(NotificationChannel):
    """邮件通知渠道"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, 
                 recipients: List[str], **kwargs):
        super().__init__("email", **kwargs)
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients
    
    def send(self, alert: Alert) -> bool:
        if not self.enabled:
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"[{alert.severity}] {alert.rule_name} - 告警通知"
            
            body = f"""
告警详情:
规则名称: {alert.rule_name}
告警时间: {alert.timestamp}
告警级别: {alert.severity}
告警消息: {alert.message}
告警状态: {alert.status}
            """
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False


class WebhookNotificationChannel(NotificationChannel):
    """Webhook通知渠道"""
    
    def __init__(self, url: str, method: str = "POST", headers: Dict = None, **kwargs):
        super().__init__("webhook", **kwargs)
        self.url = url
        self.method = method
        self.headers = headers or {}
    
    def send(self, alert: Alert) -> bool:
        if not self.enabled:
            return False
            
        try:
            payload = alert.to_dict()
            response = requests.post(self.url, json=payload, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Webhook发送失败: {e}")
            return False


class AlertManager:
    """
    告警管理器 - 核心告警引擎
    """
    
    def __init__(self):
        self.rules: List[AlertRule] = []
        self.channels: List[NotificationChannel] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=10000)
        self._lock = threading.Lock()
        
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        with self._lock:
            self.rules.append(rule)
    
    def add_channel(self, channel: NotificationChannel):
        """添加通知渠道"""
        with self._lock:
            self.channels.append(channel)
    
    def check_alerts(self, context: Dict[str, Any]):
        """检查所有告警规则"""
        current_time = datetime.datetime.now()
        
        with self._lock:
            for rule in self.rules:
                try:
                    triggered, message = rule.check(context)
                    if triggered:
                        alert = rule.trigger(message)
                        self._handle_alert(alert)
                except Exception as e:
                    print(f"告警规则检查错误 {rule.name}: {e}")
    
    def _handle_alert(self, alert: Alert):
        """处理告警"""
        # 检查是否已有相同活动告警（去重）
        existing_alert = self.active_alerts.get(alert.rule_name)
        if existing_alert and existing_alert.status == "ACTIVE":
            # 更新现有告警的时间戳
            existing_alert.timestamp = alert.timestamp
            return
        
        # 添加新告警
        self.active_alerts[alert.rule_name] = alert
        self.alert_history.append(alert)
        
        # 发送通知
        self._send_notifications(alert)
    
    def _send_notifications(self, alert: Alert):
        """发送通知"""
        for channel in self.channels:
            try:
                success = channel.send(alert)
                if not success:
                    print(f"通知渠道 {channel.name} 发送失败")
            except Exception as e:
                print(f"通知发送错误 {channel.name}: {e}")
    
    def acknowledge_alert(self, alert_id: str, user: str = "system"):
        """确认告警"""
        with self._lock:
            for alert in self.active_alerts.values():
                if alert.id == alert_id:
                    alert.acknowledge(user)
                    break
    
    def resolve_alert(self, rule_name: str):
        """解决告警"""
        with self._lock:
            if rule_name in self.active_alerts:
                alert = self.active_alerts[rule_name]
                alert.resolve()
                # 从活动告警中移除
                del self.active_alerts[rule_name]
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活动告警"""
        with self._lock:
            return list(self.active_alerts.values())
    
    def get_alert_statistics(self) -> Dict:
        """获取告警统计"""
        with self._lock:
            severity_counts = defaultdict(int)
            rule_counts = defaultdict(int)
            
            for alert in self.alert_history:
                severity_counts[alert.severity] += 1
                rule_counts[alert.rule_name] += 1
            
            return {
                'total_alerts': len(self.alert_history),
                'active_alerts': len(self.active_alerts),
                'severity_distribution': dict(severity_counts),
                'rule_distribution': dict(rule_counts)
            }


class RealTimeMonitoringService:
    """
    实时监控服务 - 整合所有监控组件
    """
    
    def __init__(self, check_interval: float = 30.0):
        self.check_interval = check_interval
        self.system_collector = SystemMetricsCollector()
        self.alert_manager = AlertManager()
        self._running = False
        self._thread = None
        
        # 默认告警规则
        self._setup_default_rules()
        
    def _setup_default_rules(self):
        """设置默认告警规则"""
        # 系统资源告警
        self.alert_manager.add_rule(SystemResourceAlertRule("cpu_percent", 80, ">"))
        self.alert_manager.add_rule(SystemResourceAlertRule("memory_percent", 85, ">"))
        self.alert_manager.add_rule(SystemResourceAlertRule("disk_percent", 90, ">"))
        
        # 业务告警
        self.alert_manager.add_rule(BusinessAlertRule("daily_pnl_percent", -0.05, "<"))
        self.alert_manager.add_rule(BusinessAlertRule("win_rate", 0.3, "<"))
    
    def add_notification_channel(self, channel: NotificationChannel):
        """添加通知渠道"""
        self.alert_manager.add_channel(channel)
    
    def add_custom_rule(self, rule: AlertRule):
        """添加自定义告警规则"""
        self.alert_manager.add_rule(rule)
    
    def start(self):
        """启动监控服务"""
        if not self._running:
            self._running = True
            self.system_collector.start()
            self._thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self._thread.start()
            print("📊 实时监控服务已启动")
    
    def stop(self):
        """停止监控服务"""
        self._running = False
        self.system_collector.stop()
        if self._thread:
            self._thread.join()
        print("🛑 实时监控服务已停止")
    
    def _monitoring_loop(self):
        """监控循环"""
        while self._running:
            try:
                # 收集上下文信息
                context = self._collect_monitoring_context()
                
                # 检查告警
                self.alert_manager.check_alerts(context)
                
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"监控循环错误: {e}")
                time.sleep(self.check_interval)
    
    def _collect_monitoring_context(self) -> Dict[str, Any]:
        """收集监控上下文"""
        context = {}
        
        # 系统指标
        system_metrics = self.system_collector.get_current_metrics()
        context.update(system_metrics)
        
        # 业务指标（需要从策略或broker获取）
        # 这里可以扩展为从Cerebro或Strategy获取业务数据
        
        return context
    
    def get_system_metrics(self) -> Dict[str, float]:
        """获取系统指标"""
        return self.system_collector.get_current_metrics()
    
    def get_alert_statistics(self) -> Dict:
        """获取告警统计"""
        return self.alert_manager.get_alert_statistics()
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活动告警"""
        return self.alert_manager.get_active_alerts()


# 便捷函数
def create_monitoring_service(check_interval: float = 30.0) -> RealTimeMonitoringService:
    """创建监控服务实例"""
    return RealTimeMonitoringService(check_interval)


def add_monitoring_to_cerebro(cerebro, monitoring_service: RealTimeMonitoringService):
    """将监控服务集成到Cerebro"""
    # 添加业务指标收集器
    cerebro.addobserver(BusinessMetricsCollector)
    
    # 启动监控服务
    monitoring_service.start()
    
    return monitoring_service


# 使用示例
if __name__ == "__main__":
    # 创建监控服务
    monitor = create_monitoring_service(check_interval=10.0)
    
    # 添加邮件通知渠道
    email_channel = EmailNotificationChannel(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        username="your_email@gmail.com",
        password="your_password",
        recipients=["admin@example.com"]
    )
    monitor.add_notification_channel(email_channel)
    
    # 添加Webhook通知渠道
    webhook_channel = WebhookNotificationChannel(
        url="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    )
    monitor.add_notification_channel(webhook_channel)
    
    # 启动监控
    monitor.start()
    
    try:
        # 运行一段时间
        time.sleep(60)
        
        # 查看统计信息
        stats = monitor.get_alert_statistics()
        print("告警统计:", stats)
        
        active_alerts = monitor.get_active_alerts()
        print(f"活动告警数量: {len(active_alerts)}")
        
    finally:
        monitor.stop()