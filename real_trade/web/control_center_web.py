#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Control Center Web Interface - 控制中枢Web界面
=============================================

提供基于Flask的Web管理界面，用于监控和控制交易系统。
包括实时状态显示、组件管理、风险监控等功能。
"""

from datetime import datetime

from flask import Flask, jsonify, render_template
from flask_cors import CORS

from ..core.control_center import get_control_center
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Flask应用
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# 获取控制中枢实例
control_center = get_control_center()


@app.route("/")
def index():
    """主页"""
    return render_template("control_center.html")


@app.route("/api/system/status")
def get_system_status():
    """获取系统状态"""
    try:
        status = control_center.get_system_status()
        return jsonify({"success": True, "data": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/components")
def get_components():
    """获取所有组件"""
    try:
        components = []
        for component_id, component_info in control_center.components.items():
            components.append(
                {
                    "id": component_id,
                    "type": component_info["type"].value,
                    "status": component_info.get("status", "UNKNOWN"),
                    "registered_at": component_info["registered_at"].isoformat(),
                }
            )

        return jsonify({"success": True, "data": components})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/component/<component_id>/status")
def get_component_status(component_id):
    """获取特定组件状态"""
    try:
        status = control_center.get_component_status(component_id)
        if "error" in status:
            return jsonify({"success": False, "error": status["error"]}), 404

        return jsonify({"success": True, "data": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/system/start", methods=["POST"])
def start_system():
    """启动系统"""
    try:
        if control_center.start():
            return jsonify({"success": True, "message": "系统启动成功"})
        else:
            return jsonify({"success": False, "error": "系统启动失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/system/stop", methods=["POST"])
def stop_system():
    """停止系统"""
    try:
        if control_center.stop():
            return jsonify({"success": True, "message": "系统停止成功"})
        else:
            return jsonify({"success": False, "error": "系统停止失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/system/pause", methods=["POST"])
def pause_system():
    """暂停系统"""
    try:
        if control_center.pause():
            return jsonify({"success": True, "message": "系统已暂停"})
        else:
            return jsonify({"success": False, "error": "系统暂停失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/system/resume", methods=["POST"])
def resume_system():
    """恢复系统"""
    try:
        if control_center.resume():
            return jsonify({"success": True, "message": "系统已恢复"})
        else:
            return jsonify({"success": False, "error": "系统恢复失败"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/metrics/system")
def get_system_metrics():
    """获取系统指标"""
    try:
        # 获取最近的系统指标
        system_metrics = control_center.metrics.get("system", [])
        if system_metrics:
            latest_metric = system_metrics[-1]
            return jsonify({"success": True, "data": latest_metric})
        else:
            return jsonify({"success": True, "data": None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/alerts")
def get_alerts():
    """获取告警信息"""
    try:
        # 这里应该从告警系统获取实际告警
        alerts = [
            {
                "id": "alert_001",
                "level": "WARNING",
                "message": "BTC价格波动超过阈值",
                "timestamp": datetime.now().isoformat(),
                "component": "binance_feed",
            }
        ]

        return jsonify({"success": True, "data": alerts})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def start_web_server(host="0.0.0.0", port=8080, debug=False):
    """启动Web服务器"""
    logger.info(f"🌐 启动控制中枢Web界面: http://{host}:{port}")

    try:
        app.run(host=host, port=port, debug=debug, threaded=True)
    except Exception as e:
        logger.error(f"❌ Web服务器启动失败: {e}")


def create_html_template():
    """创建HTML模板文件"""
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtrader 控制中枢</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .card h3 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background-color: #4CAF50; }
        .status-stopped { background-color: #f44336; }
        .status-paused { background-color: #ff9800; }
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
        }
        .btn:hover { opacity: 0.8; }
        .btn-danger { background: #f44336; }
        .btn-warning { background: #ff9800; }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        .metric-item {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
        }
        .metric-label { font-weight: bold; color: #666; }
        .metric-value { font-size: 1.2em; color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Backtrader 交易控制中枢</h1>
            <p>统一管理系统状态、组件监控和风险控制</p>
        </div>

        <div class="dashboard">
            <!-- 系统状态卡片 -->
            <div class="card">
                <h3>📊 系统状态</h3>
                <div id="system-status">
                    <div class="metric-item">
                        <span class="status-indicator status-running" id="status-indicator"></span>
                        <span class="metric-label">运行状态:</span>
                        <span class="metric-value" id="system-status-text">加载中...</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">运行时间:</span>
                        <span class="metric-value" id="uptime">--</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">健康组件:</span>
                        <span class="metric-value" id="healthy-components">--</span>
                    </div>
                </div>
                <div style="margin-top: 15px;">
                    <button class="btn" onclick="startSystem()">启动</button>
                    <button class="btn btn-warning" onclick="pauseSystem()">暂停</button>
                    <button class="btn" onclick="resumeSystem()">恢复</button>
                    <button class="btn btn-danger" onclick="stopSystem()">停止</button>
                </div>
            </div>

            <!-- 组件概览卡片 -->
            <div class="card">
                <h3>🧩 组件概览</h3>
                <div id="components-overview">
                    <div class="metric-item">
                        <span class="metric-label">总组件数:</span>
                        <span class="metric-value" id="total-components">--</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">数据源:</span>
                        <span class="metric-value" id="data-feeds">--</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">策略:</span>
                        <span class="metric-value" id="strategies">--</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">风险管理:</span>
                        <span class="metric-value" id="risk-managers">--</span>
                    </div>
                </div>
            </div>

            <!-- 系统指标卡片 -->
            <div class="card">
                <h3>📈 系统指标</h3>
                <div class="metrics-grid" id="system-metrics">
                    <div class="metric-item">
                        <span class="metric-label">CPU使用率:</span>
                        <span class="metric-value" id="cpu-usage">--%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">内存使用率:</span>
                        <span class="metric-value" id="memory-usage">--%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">磁盘使用率:</span>
                        <span class="metric-value" id="disk-usage">--%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">网络流量:</span>
                        <span class="metric-value" id="network-io">--</span>
                    </div>
                </div>
            </div>

            <!-- 告警信息卡片 -->
            <div class="card">
                <h3>⚠️ 最新告警</h3>
                <div id="alerts-container">
                    <p>暂无告警信息</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 定时刷新数据
        setInterval(updateDashboard, 5000);
        
        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            updateDashboard();
        });

        function updateDashboard() {
            // 更新系统状态
            fetch('/api/system/status')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const status = data.data;
                        document.getElementById('system-status-text').textContent = status.status;
                        document.getElementById('uptime').textContent = status.uptime;
                        document.getElementById('healthy-components').textContent = 
                            `${status.healthy_components}/${status.components_count}`;
                        
                        // 更新状态指示器颜色
                        const indicator = document.getElementById('status-indicator');
                        indicator.className = 'status-indicator ' + 
                            (status.status === 'RUNNING' ? 'status-running' : 
                             status.status === 'PAUSED' ? 'status-paused' : 'status-stopped');
                    }
                })
                .catch(error => console.error('Error:', error));

            // 更新系统指标
            fetch('/api/metrics/system')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.data) {
                        const metrics = data.data.data;
                        document.getElementById('cpu-usage').textContent = 
                            metrics.cpu_usage ? metrics.cpu_usage.toFixed(1) + '%' : '--%';
                        document.getElementById('memory-usage').textContent = 
                            metrics.memory_usage ? metrics.memory_usage.toFixed(1) + '%' : '--%';
                    }
                })
                .catch(error => console.error('Error:', error));

            // 更新告警信息
            fetch('/api/alerts')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const container = document.getElementById('alerts-container');
                        if (data.data.length > 0) {
                            container.innerHTML = data.data.map(alert => 
                                `<div style="padding: 5px; border-left: 3px solid #ff9800; margin: 5px 0;">
                                    <strong>${alert.level}</strong>: ${alert.message}
                                </div>`
                            ).join('');
                        } else {
                            container.innerHTML = '<p>暂无告警信息</p>';
                        }
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        // 系统控制函数
        function startSystem() {
            fetch('/api/system/start', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('系统启动成功');
                        updateDashboard();
                    } else {
                        alert('系统启动失败: ' + data.error);
                    }
                });
        }

        function stopSystem() {
            if (confirm('确定要停止系统吗？')) {
                fetch('/api/system/stop', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('系统停止成功');
                            updateDashboard();
                        } else {
                            alert('系统停止失败: ' + data.error);
                        }
                    });
            }
        }

        function pauseSystem() {
            fetch('/api/system/pause', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('系统已暂停');
                        updateDashboard();
                    } else {
                        alert('系统暂停失败: ' + data.error);
                    }
                });
        }

        function resumeSystem() {
            fetch('/api/system/resume', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('系统已恢复');
                        updateDashboard();
                    } else {
                        alert('系统恢复失败: ' + data.error);
                    }
                });
        }
    </script>
</body>
</html>
    """

    # 创建模板目录和文件
    import os

    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    os.makedirs(template_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "control_center.html")
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"✅ HTML模板已创建: {template_path}")


if __name__ == "__main__":
    # 创建HTML模板
    create_html_template()

    # 启动Web服务器
    start_web_server(debug=True)
