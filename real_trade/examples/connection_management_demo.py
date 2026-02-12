#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Connection Management Examples - 连接管理使用示例

展示如何使用连接池和心跳监控功能。
"""

import json
import os
import sys
import threading
import time

# 添加项目路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

try:
    from real_trade.utils import (
        HTTPConnection,
        get_connection_manager,
        get_heartbeat_monitor,
    )
except ImportError:
    # 如果导入失败，创建模拟类
    class HTTPConnection:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            print("模拟连接")

        def disconnect(self):
            print("模拟断开")

    def get_connection_manager():
        return HTTPConnection()

    def get_heartbeat_monitor():
        return HTTPConnection()


class MockHTTPServer:
    """模拟HTTP服务器用于测试"""

    def __init__(self, port: int = 8080):
        self.port = port
        self.running = False
        self.thread = None

    def start(self):
        """启动模拟服务器"""
        if self.running:
            return

        def server_worker():
            from http.server import BaseHTTPRequestHandler, HTTPServer

            class MockHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == "/ping":
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'{"status": "ok"}')
                    elif self.path == "/api/data":
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        data = {"symbol": "BTC/USDT", "price": 50000.0}
                        self.wfile.write(json.dumps(data).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()

                def log_message(self, format, *args):
                    pass  # 静默日志

            server = HTTPServer(("localhost", self.port), MockHandler)
            self.running = True
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                server.shutdown()
                self.running = False

        self.thread = threading.Thread(target=server_worker, daemon=True)
        self.thread.start()
        time.sleep(0.1)  # 等待服务器启动

    def stop(self):
        """停止模拟服务器"""
        self.running = False


def demonstrate_http_connection():
    """HTTP连接演示"""
    print("=== HTTP连接演示 ===\n")

    # 启动模拟服务器
    server = MockHTTPServer(8081)
    server.start()

    try:
        # 创建HTTP连接
        config = {
            "base_url": "http://localhost:8081",
            "timeout": 10,
            "headers": {"User-Agent": "real-trade-test"},
        }

        connection = HTTPConnection("http_test_1", config)

        # 建立连接
        print("1. 建立连接:")
        if connection.connect():
            print(f"   连接成功: {connection.state}")
            print(f"   统计信息: {connection.stats}")
        else:
            print("   连接失败")
            return

        print()

        # 执行操作
        print("2. 执行HTTP操作:")

        def fetch_data(session):
            response = session.get("/api/data")
            return response.json()

        try:
            data = connection.execute(fetch_data)
            print(f"   获取数据: {data}")
            print(f"   更新后的统计: {connection.stats}")
        except Exception as e:
            print(f"   操作失败: {e}")

        print()

        # 心跳检测
        print("3. 心跳检测:")
        is_alive = connection.heartbeat()
        print(f"   连接存活: {is_alive}")

        # 断开连接
        print("\n4. 断开连接:")
        connection.disconnect()
        print(f"   连接状态: {connection.state}")

    finally:
        server.stop()


def demonstrate_connection_pool():
    """连接池演示"""
    print("\n=== 连接池演示 ===\n")

    # 启动模拟服务器
    server = MockHTTPServer(8082)
    server.start()

    try:
        # 获取连接管理器
        pool = get_connection_manager()

        # 注册连接配置
        http_config = {
            "base_url": "http://localhost:8082",
            "timeout": 5,
            "headers": {"User-Agent": "real-trade-pool"},
        }
        pool.register_connection_type("http_api", http_config)

        print("1. 连接池配置:")
        print(f"   池大小: {pool.pool_size}")
        print(f"   空闲超时: {pool.idle_timeout}秒")
        print(f"   已注册连接类型: {list(pool.connection_config.keys())}")
        print()

        # 获取多个连接
        print("2. 获取连接:")
        connections = []
        for i in range(3):
            conn = pool.get_connection("http_api")
            if conn:
                connections.append(conn)
                print(f"   连接 {i + 1}: {conn.id} - {conn.state}")
            else:
                print(f"   连接 {i + 1}: 获取失败")

        print()

        # 使用连接执行操作
        print("3. 使用连接执行操作:")

        def fetch_ping(session):
            response = session.get("/ping")
            return response.json()

        for i, conn in enumerate(connections):
            try:
                result = conn.execute(fetch_ping)
                print(f"   连接 {i + 1} 执行结果: {result}")
            except Exception as e:
                print(f"   连接 {i + 1} 执行失败: {e}")

        print()

        # 归还连接
        print("4. 归还连接:")
        for conn in connections:
            pool.return_connection(conn)
            print(f"   归还连接: {conn.id}")

        print(f"   可用连接数: {len(pool.available_connections)}")
        print(f"   使用中连接数: {len(pool.in_use_connections)}")

    finally:
        server.stop()
        # 清理连接池
        pool.shutdown()


def demonstrate_heartbeat_monitor():
    """心跳监控演示"""
    print("\n=== 心跳监控演示 ===\n")

    # 启动模拟服务器
    server = MockHTTPServer(8083)
    server.start()

    try:
        # 创建连接
        config = {"base_url": "http://localhost:8083", "timeout": 5}
        connection = HTTPConnection("heartbeat_test", config)
        connection.connect()

        # 获取心跳监控器
        monitor = get_heartbeat_monitor()

        print("1. 添加连接到监控:")
        monitor.add_connection(connection)
        print(f"   监控的连接数: {len(monitor.monitored_connections)}")
        print()

        # 等待几轮心跳
        print("2. 监控心跳 (观察5秒):")
        for i in range(5):
            time.sleep(1)
            stats = connection.stats
            print(
                f"   第{i + 1}秒: 最后心跳={stats.last_heartbeat}, "
                f"总请求数={stats.total_requests}"
            )

        print()

        # 模拟连接断开
        print("3. 模拟连接断开:")
        server.stop()
        time.sleep(2)  # 等待心跳检测发现问题

        # 重启服务器测试重连
        print("\n4. 重启服务器测试重连:")
        server = MockHTTPServer(8083)
        server.start()
        time.sleep(2)

        # 检查连接状态
        is_alive = connection.heartbeat()
        print(f"   重连后连接状态: {is_alive}")

        # 移除监控
        print("\n5. 移除连接监控:")
        monitor.remove_connection(connection.id)
        print(f"   监控的连接数: {len(monitor.monitored_connections)}")

    finally:
        server.stop()
        connection.disconnect()
        # 停止监控器
        monitor.stop()


def demonstrate_websocket_connection():
    """WebSocket连接演示"""
    print("\n=== WebSocket连接演示 ===\n")

    # 注意：这需要真实的WebSocket服务器
    # 这里只是展示API使用方式

    print("WebSocket连接示例:")
    print("1. 创建WebSocket连接配置:")
    ws_config = {
        "url": "wss://echo.websocket.org",
        "max_reconnects": 3,
        "reconnect_interval": 2,
    }

    print("   配置:", ws_config)
    print()

    print("2. WebSocket连接使用方式:")
    print("   # 创建连接")
    print("   ws_conn = WebSocketConnection('ws_test', ws_config)")
    print("   ")
    print("   # 连接")
    print("   ws_conn.connect()")
    print("   ")
    print("   # 订阅消息")
    print("   def message_handler(message):")
    print("       print(f'收到消息: {message}')")
    print("   ")
    print("   ws_conn.subscribe('ticker', message_handler)")
    print("   ")
    print("   # 发送消息")
    print("   def send_message(ws):")
    print("       ws.send('Hello WebSocket')")
    print("   ")
    print("   ws_conn.execute(send_message)")
    print("   ")
    print("   # 断开连接")
    print("   ws_conn.disconnect()")

    print("\n注意: 实际使用需要真实的WebSocket服务器")


def demonstrate_error_handling():
    """错误处理演示"""
    print("\n=== 连接错误处理演示 ===\n")

    # 测试连接失败的情况
    print("1. 连接到不存在的服务器:")
    config = {
        "base_url": "http://localhost:9999",  # 不存在的端口
        "timeout": 2,
    }

    connection = HTTPConnection("error_test", config)

    try:
        connection.connect()
        print("   意外成功连接")
    except Exception as e:
        print(f"   连接失败 (预期): {e}")
        print(f"   错误类型: {type(e).__name__}")

    print()

    # 测试操作超时
    print("2. 操作超时测试:")
    config["base_url"] = "http://httpbin.org/delay/5"  # 5秒延迟
    config["timeout"] = 1  # 1秒超时

    connection2 = HTTPConnection("timeout_test", config)

    try:
        connection2.connect()

        def slow_request(session):
            return session.get("/delay/5").text

        result = connection2.execute(slow_request)
        print("   操作意外成功")
    except Exception as e:
        print(f"   操作超时 (预期): {e}")
        print(f"   错误类型: {type(e).__name__}")


if __name__ == "__main__":
    demonstrate_http_connection()
    demonstrate_connection_pool()
    demonstrate_heartbeat_monitor()
    demonstrate_websocket_connection()
    demonstrate_error_handling()

    print("\n=== 演示完成 ===")
    print("所有连接管理器已自动清理")
