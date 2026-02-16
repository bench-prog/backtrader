#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
可视化监控面板 (Visualization Dashboard)
基于backtrader和web技术的实时监控大盘

核心功能：
1. 实时监控大盘
2. 告警看板
3. 性能指标图表
4. Grafana集成支持
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import threading
import time
import json
import datetime
from collections import defaultdict, deque
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import plotly.graph_objects as go
import plotly.utils
import pandas as pd
import numpy as np


class MonitoringDashboard:
    """
    监控仪表板 - 提供Web界面的实时监控
    """
    
    def __init__(self, host='localhost', port=5000, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        
        # Flask应用
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # 数据存储
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.alerts_history = deque(maxlen=1000)
        self.active_alerts = {}
        
        # 监控数据
        self.system_metrics = {}
        self.business_metrics = {}
        self.performance_metrics = {}
        
        # 启动标志
        self._running = False
        self._server_thread = None
        
        # 注册路由和事件
        self._register_routes()
        self._register_socket_events()
    
    def _register_routes(self):
        """注册Flask路由"""
        
        @self.app.route('/')
        def index():
            return render_template('dashboard.html')
        
        @self.app.route('/api/metrics/system')
        def get_system_metrics():
            return jsonify(self.system_metrics)
        
        @self.app.route('/api/metrics/business')
        def get_business_metrics():
            return jsonify(self.business_metrics)
        
        @self.app.route('/api/metrics/performance')
        def get_performance_metrics():
            return jsonify(self.performance_metrics)
        
        @self.app.route('/api/alerts/active')
        def get_active_alerts():
            return jsonify(list(self.active_alerts.values()))
        
        @self.app.route('/api/alerts/history')
        def get_alerts_history():
            return jsonify(list(self.alerts_history))
        
        @self.app.route('/api/charts/system/<metric>')
        def get_system_chart(metric):
            return self._generate_system_chart(metric)
        
        @self.app.route('/api/charts/business/<metric>')
        def get_business_chart(metric):
            return self._generate_business_chart(metric)
    
    def _register_socket_events(self):
        """注册SocketIO事件"""
        
        @self.socketio.on('connect')
        def handle_connect():
            print('客户端已连接')
            # 发送初始数据
            self._emit_all_data()
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('客户端已断开')
        
        @self.socketio.on('request_data')
        def handle_request_data(data_type):
            if data_type == 'metrics':
                self._emit_metrics()
            elif data_type == 'alerts':
                self._emit_alerts()
    
    def _emit_all_data(self):
        """发送所有数据"""
        self._emit_metrics()
        self._emit_alerts()
        self._emit_charts()
    
    def _emit_metrics(self):
        """发送指标数据"""
        data = {
            'system': self.system_metrics,
            'business': self.business_metrics,
            'performance': self.performance_metrics,
            'timestamp': datetime.datetime.now().isoformat()
        }
        self.socketio.emit('metrics_update', data)
    
    def _emit_alerts(self):
        """发送告警数据"""
        data = {
            'active': list(self.active_alerts.values()),
            'history': list(self.alerts_history)[-50:],  # 最近50条
            'timestamp': datetime.datetime.now().isoformat()
        }
        self.socketio.emit('alerts_update', data)
    
    def _emit_charts(self):
        """发送图表数据"""
        # 这里可以发送预生成的图表数据
        pass
    
    def _generate_system_chart(self, metric):
        """生成系统指标图表"""
        if metric not in self.metrics_history:
            return jsonify({'error': '指标不存在'})
        
        # 获取历史数据
        history = list(self.metrics_history[metric])
        if not history:
            return jsonify({'error': '无历史数据'})
        
        timestamps = [ts.isoformat() for ts, _ in history]
        values = [val for _, val in history]
        
        # 创建图表
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=values,
            mode='lines+markers',
            name=metric
        ))
        
        fig.update_layout(
            title=f'{metric} 历史趋势',
            xaxis_title='时间',
            yaxis_title='数值',
            height=400
        )
        
        # 转换为JSON
        chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        return jsonify({'chart': chart_json})
    
    def _generate_business_chart(self, metric):
        """生成业务指标图表"""
        # 类似_system_chart的实现
        pass
    
    def update_system_metrics(self, metrics: dict):
        """更新系统指标"""
        self.system_metrics.update(metrics)
        
        # 记录历史数据
        timestamp = datetime.datetime.now()
        for key, value in metrics.items():
            self.metrics_history[key].append((timestamp, value))
        
        # 实时推送
        if self._running:
            self._emit_metrics()
    
    def update_business_metrics(self, metrics: dict):
        """更新业务指标"""
        self.business_metrics.update(metrics)
        
        # 记录历史数据
        timestamp = datetime.datetime.now()
        for key, value in metrics.items():
            self.metrics_history[f"business_{key}"].append((timestamp, value))
        
        # 实时推送
        if self._running:
            self._emit_metrics()
    
    def update_performance_metrics(self, metrics: dict):
        """更新性能指标"""
        self.performance_metrics.update(metrics)
        
        # 记录历史数据
        timestamp = datetime.datetime.now()
        for key, value in metrics.items():
            self.metrics_history[f"perf_{key}"].append((timestamp, value))
        
        # 实时推送
        if self._running:
            self._emit_metrics()
    
    def add_alert(self, alert_data: dict):
        """添加告警"""
        alert_id = alert_data.get('id', f"alert_{len(self.alerts_history)}")
        alert_data['id'] = alert_id
        alert_data['timestamp'] = datetime.datetime.now().isoformat()
        
        # 添加到历史记录
        self.alerts_history.append(alert_data)
        
        # 如果是活动告警，添加到活动列表
        if alert_data.get('status') == 'ACTIVE':
            self.active_alerts[alert_id] = alert_data
        
        # 实时推送
        if self._running:
            self._emit_alerts()
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id]['status'] = 'RESOLVED'
            self.active_alerts[alert_id]['resolved_time'] = datetime.datetime.now().isoformat()
            # 从活动列表中移除
            del self.active_alerts[alert_id]
            
            # 实时推送
            if self._running:
                self._emit_alerts()
    
    def acknowledge_alert(self, alert_id: str, user: str = "system"):
        """确认告警"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id]['status'] = 'ACKNOWLEDGED'
            self.active_alerts[alert_id]['acknowledged_by'] = user
            self.active_alerts[alert_id]['acknowledged_time'] = datetime.datetime.now().isoformat()
            
            # 实时推送
            if self._running:
                self._emit_alerts()
    
    def start(self):
        """启动仪表板服务"""
        if not self._running:
            self._running = True
            
            # 在后台线程中启动服务器
            self._server_thread = threading.Thread(
                target=lambda: self.socketio.run(
                    self.app, 
                    host=self.host, 
                    port=self.port, 
                    debug=self.debug,
                    use_reloader=False  # 避免重复启动
                ),
                daemon=True
            )
            self._server_thread.start()
            
            print(f"📊 监控仪表板已启动 - http://{self.host}:{self.port}")
    
    def stop(self):
        """停止仪表板服务"""
        self._running = False
        print("🛑 监控仪表板已停止")


class StrategyMonitorMixin:
    """
    策略监控混入类 - 为策略添加监控功能
    """
    
    def __init__(self):
        super(StrategyMonitorMixin, self).__init__()
        self.dashboard = None
        self.monitoring_interval = 60  # 监控间隔（秒）
        self.last_monitoring_update = 0
    
    def set_dashboard(self, dashboard: MonitoringDashboard):
        """设置监控仪表板"""
        self.dashboard = dashboard
    
    def next(self):
        """策略主循环中添加监控"""
        super(StrategyMonitorMixin, self).next()
        
        # 定期更新监控数据
        current_time = time.time()
        if current_time - self.last_monitoring_update >= self.monitoring_interval:
            self._update_monitoring_data()
            self.last_monitoring_update = current_time
    
    def _update_monitoring_data(self):
        """更新监控数据"""
        if not self.dashboard:
            return
        
        try:
            # 更新业务指标
            business_metrics = self._collect_business_metrics()
            self.dashboard.update_business_metrics(business_metrics)
            
            # 更新性能指标
            performance_metrics = self._collect_performance_metrics()
            self.dashboard.update_performance_metrics(performance_metrics)
            
        except Exception as e:
            print(f"监控数据更新失败: {e}")
    
    def _collect_business_metrics(self) -> dict:
        """收集业务指标"""
        metrics = {}
        
        # 持仓信息
        total_positions = 0
        total_position_value = 0
        for data in self.datas:
            position = self.broker.getposition(data)
            if position.size != 0:
                total_positions += 1
                total_position_value += position.size * data.close[0]
        
        metrics['active_positions'] = total_positions
        metrics['positions_value'] = total_position_value
        metrics['cash'] = self.broker.getcash()
        metrics['portfolio_value'] = self.broker.getvalue()
        
        # 订单统计
        metrics['pending_orders'] = len([o for o in self.broker.orders if o.alive()])
        
        # 收益率
        if hasattr(self, '_start_value'):
            current_value = self.broker.getvalue()
            metrics['total_return'] = (current_value - self._start_value) / self._start_value
        else:
            self._start_value = self.broker.getvalue()
            metrics['total_return'] = 0.0
        
        return metrics
    
    def _collect_performance_metrics(self) -> dict:
        """收集性能指标"""
        metrics = {}
        
        # 策略执行频率
        if hasattr(self, '_last_next_time'):
            time_diff = time.time() - self._last_next_time
            metrics['execution_interval'] = time_diff
        self._last_next_time = time.time()
        
        # 内存使用（如果可用）
        try:
            import psutil
            process = psutil.Process()
            metrics['memory_usage_mb'] = process.memory_info().rss / 1024 / 1024
            metrics['cpu_percent'] = process.cpu_percent()
        except:
            pass
        
        return metrics
    
    def notify_order(self, order):
        """订单通知 - 发送告警"""
        super(StrategyMonitorMixin, self).notify_order(order)
        
        if self.dashboard and order.status in [order.Margin, order.Rejected]:
            alert = {
                'type': 'ORDER_ERROR',
                'severity': 'ERROR',
                'message': f'订单{order.Status[order.status]}: {order.ref}',
                'status': 'ACTIVE'
            }
            self.dashboard.add_alert(alert)
    
    def notify_trade(self, trade):
        """交易通知"""
        super(StrategyMonitorMixin, self).notify_trade(trade)
        
        if self.dashboard and trade.isclosed:
            # 发送交易完成告警
            pnl_percent = trade.pnl / trade.value if trade.value > 0 else 0
            severity = 'INFO' if trade.pnl > 0 else 'WARNING'
            
            alert = {
                'type': 'TRADE_COMPLETED',
                'severity': severity,
                'message': f'交易完成: 盈亏 {trade.pnl:.2f} ({pnl_percent:.2%})',
                'status': 'ACTIVE'
            }
            self.dashboard.add_alert(alert)


# HTML模板
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Backtrader监控仪表板</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .panel { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .metric-card { background: #f5f5f5; padding: 10px; margin: 5px 0; border-radius: 3px; }
        .alert { padding: 10px; margin: 5px 0; border-radius: 3px; }
        .alert-ERROR { background: #ffebee; border-left: 4px solid #f44336; }
        .alert-WARNING { background: #fff3e0; border-left: 4px solid #ff9800; }
        .alert-INFO { background: #e8f5e8; border-left: 4px solid #4caf50; }
        .chart-container { height: 300px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>📊 Backtrader实时监控仪表板</h1>
    
    <div class="container">
        <!-- 系统指标面板 -->
        <div class="panel">
            <h2>🖥️ 系统指标</h2>
            <div id="system-metrics"></div>
            <div class="chart-container">
                <div id="cpu-chart"></div>
            </div>
        </div>
        
        <!-- 业务指标面板 -->
        <div class="panel">
            <h2>💼 业务指标</h2>
            <div id="business-metrics"></div>
            <div class="chart-container">
                <div id="portfolio-chart"></div>
            </div>
        </div>
        
        <!-- 告警面板 -->
        <div class="panel" style="grid-column: span 2;">
            <h2>🔔 实时告警</h2>
            <div id="active-alerts"></div>
            <h3>告警历史</h3>
            <div id="alerts-history"></div>
        </div>
    </div>

    <script>
        const socket = io();
        
        // 连接建立
        socket.on('connect', function() {
            console.log('已连接到服务器');
            socket.emit('request_data', 'metrics');
            socket.emit('request_data', 'alerts');
        });
        
        // 接收指标更新
        socket.on('metrics_update', function(data) {
            updateSystemMetrics(data.system);
            updateBusinessMetrics(data.business);
            updatePerformanceMetrics(data.performance);
        });
        
        // 接收告警更新
        socket.on('alerts_update', function(data) {
            updateActiveAlerts(data.active);
            updateAlertsHistory(data.history);
        });
        
        function updateSystemMetrics(metrics) {
            const container = document.getElementById('system-metrics');
            let html = '';
            for (const [key, value] of Object.entries(metrics)) {
                html += `<div class="metric-card"><strong>${key}:</strong> ${value}</div>`;
            }
            container.innerHTML = html;
        }
        
        function updateBusinessMetrics(metrics) {
            const container = document.getElementById('business-metrics');
            let html = '';
            for (const [key, value] of Object.entries(metrics)) {
                html += `<div class="metric-card"><strong>${key}:</strong> ${value}</div>`;
            }
            container.innerHTML = html;
        }
        
        function updatePerformanceMetrics(metrics) {
            // 性能指标更新逻辑
        }
        
        function updateActiveAlerts(alerts) {
            const container = document.getElementById('active-alerts');
            let html = '';
            alerts.forEach(alert => {
                html += `<div class="alert alert-${alert.severity}">
                    <strong>[${alert.severity}] ${alert.type}:</strong> ${alert.message}
                    <br><small>${alert.timestamp}</small>
                </div>`;
            });
            container.innerHTML = html || '<div>暂无活动告警</div>';
        }
        
        function updateAlertsHistory(alerts) {
            const container = document.getElementById('alerts-history');
            let html = '';
            alerts.slice(-10).forEach(alert => {  // 显示最近10条
                html += `<div class="alert alert-${alert.severity}">
                    <strong>[${alert.severity}] ${alert.type}:</strong> ${alert.message}
                    <br><small>${alert.timestamp}</small>
                </div>`;
            });
            container.innerHTML = html || '<div>暂无告警历史</div>';
        }
    </script>
</body>
</html>
'''


def create_monitoring_dashboard(host='localhost', port=5000, debug=False) -> MonitoringDashboard:
    """
    创建监控仪表板实例
    """
    dashboard = MonitoringDashboard(host=host, port=port, debug=debug)
    
    # 创建模板目录和文件（简化版本）
    import os
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    template_file = os.path.join(template_dir, 'dashboard.html')
    with open(template_file, 'w') as f:
        f.write(DASHBOARD_TEMPLATE)
    
    return dashboard


# 集成函数
def integrate_monitoring_dashboard(cerebro, dashboard: MonitoringDashboard):
    """
    将监控仪表板集成到Cerebro
    """
    # 如果策略使用了监控混入，则设置仪表板
    for strategy in cerebro.strategies:
        if hasattr(strategy, 'set_dashboard'):
            strategy.set_dashboard(dashboard)
    
    # 启动仪表板
    dashboard.start()
    
    return dashboard


# 使用示例
if __name__ == "__main__":
    # 创建仪表板
    dashboard = create_monitoring_dashboard(debug=True)
    
    # 模拟数据更新
    def simulate_updates():
        import random
        while True:
            # 模拟系统指标更新
            system_metrics = {
                'cpu_percent': random.uniform(10, 90),
                'memory_percent': random.uniform(30, 80),
                'disk_percent': random.uniform(40, 70)
            }
            dashboard.update_system_metrics(system_metrics)
            
            # 模拟业务指标更新
            business_metrics = {
                'portfolio_value': random.uniform(95000, 105000),
                'cash': random.uniform(10000, 20000),
                'active_positions': random.randint(0, 5)
            }
            dashboard.update_business_metrics(business_metrics)
            
            # 随机生成告警
            if random.random() < 0.1:  # 10%概率生成告警
                alert = {
                    'type': 'TEST_ALERT',
                    'severity': random.choice(['INFO', 'WARNING', 'ERROR']),
                    'message': f'测试告警消息 {random.randint(1, 100)}',
                    'status': 'ACTIVE'
                }
                dashboard.add_alert(alert)
            
            time.sleep(2)
    
    # 启动模拟数据更新
    update_thread = threading.Thread(target=simulate_updates, daemon=True)
    update_thread.start()
    
    # 启动仪表板
    dashboard.start()
    
    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("正在关闭...")
        dashboard.stop()