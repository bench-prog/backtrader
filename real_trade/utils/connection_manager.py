#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Connection Manager - 连接管理器

提供连接池管理、心跳检测、自动重连等功能。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set


class ConnectionState(Enum):
    """连接状态枚举"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionStats:
    """连接统计信息"""

    total_connections: int = 0
    active_connections: int = 0
    failed_attempts: int = 0
    last_heartbeat: Optional[float] = None
    avg_response_time: float = 0.0
    total_requests: int = 0


class Connection(ABC):
    """连接抽象基类"""

    def __init__(self, connection_id: str, config: Dict[str, Any]):
        self.id = connection_id
        self.config = config
        self.state = ConnectionState.DISCONNECTED
        self.created_at = time.time()
        self.last_used = time.time()
        self.stats = ConnectionStats()
        self._lock = threading.RLock()

    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接"""
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        """检查连接是否存活"""
        pass

    @abstractmethod
    def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """执行操作"""
        pass

    def heartbeat(self) -> bool:
        """发送心跳"""
        try:
            return self.is_alive()
        except Exception:
            return False

    def update_stats(self, success: bool = True, response_time: float = 0.0):
        """更新统计信息"""
        with self._lock:
            self.stats.total_requests += 1
            self.stats.last_heartbeat = time.time()

            if success:
                self.stats.active_connections = 1
                self.stats.avg_response_time = (
                    self.stats.avg_response_time * (self.stats.total_requests - 1)
                    + response_time
                ) / self.stats.total_requests
            else:
                self.stats.failed_attempts += 1
                self.stats.active_connections = 0


class HTTPConnection(Connection):
    """HTTP连接实现"""

    def __init__(self, connection_id: str, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        self.session = None
        self.base_url = config.get("base_url", "")
        self.timeout = config.get("timeout", 30)
        self.headers = config.get("headers", {})

    def connect(self) -> bool:
        """建立HTTP连接"""
        with self._lock:
            try:
                import requests
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry

                self.state = ConnectionState.CONNECTING

                # 创建会话
                self.session = requests.Session()

                # 配置重试策略
                retry_strategy = Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                )

                adapter = HTTPAdapter(max_retries=retry_strategy)
                self.session.mount("http://", adapter)
                self.session.mount("https://", adapter)

                # 设置超时和头部
                self.session.timeout = self.timeout
                self.session.headers.update(self.headers)

                # 测试连接
                test_response = self.session.get(f"{self.base_url}/ping", timeout=5)
                if test_response.status_code == 200:
                    self.state = ConnectionState.CONNECTED
                    self.stats.total_connections += 1
                    return True
                else:
                    self.state = ConnectionState.FAILED
                    return False

            except Exception as e:
                self.state = ConnectionState.FAILED
                raise ConnectionError(f"HTTP连接失败: {e}")

    def disconnect(self) -> bool:
        """断开HTTP连接"""
        with self._lock:
            try:
                if self.session:
                    self.session.close()
                    self.session = None
                self.state = ConnectionState.DISCONNECTED
                return True
            except Exception:
                self.state = ConnectionState.FAILED
                return False

    def is_alive(self) -> bool:
        """检查HTTP连接是否存活"""
        if not self.session or self.state != ConnectionState.CONNECTED:
            return False

        try:
            response = self.session.get(f"{self.base_url}/ping", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """执行HTTP操作"""
        if not self.session or self.state != ConnectionState.CONNECTED:
            from .exceptions import ConnectionError

            raise ConnectionError("连接未建立或已断开")

        start_time = time.time()
        try:
            result = operation(self.session, *args, **kwargs)
            response_time = time.time() - start_time
            self.update_stats(success=True, response_time=response_time)
            self.last_used = time.time()
            return result
        except Exception as e:
            response_time = time.time() - start_time
            from .exceptions import NetworkError

            self.update_stats(success=False, response_time=response_time)
            raise NetworkError(f"HTTP操作失败: {e}")


class WebSocketConnection(Connection):
    """WebSocket连接实现"""

    def __init__(self, connection_id: str, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        self.ws = None
        self.url = config.get("url", "")
        self.reconnect_count = 0
        self.max_reconnects = config.get("max_reconnects", 5)
        self.reconnect_interval = config.get("reconnect_interval", 5)
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._ws_thread = None

    def connect(self) -> bool:
        """建立WebSocket连接"""
        with self._lock:
            try:
                import websocket

                self.state = ConnectionState.CONNECTING

                def on_message(ws, message):
                    self._handle_message(message)

                def on_error(ws, error):
                    self.logger.error(f"WebSocket错误: {error}")
                    self.state = ConnectionState.FAILED

                def on_close(ws, close_status_code, close_msg):
                    self.logger.info(
                        f"WebSocket关闭: {close_status_code} - {close_msg}"
                    )
                    self.state = ConnectionState.DISCONNECTED
                    if self._running and self.reconnect_count < self.max_reconnects:
                        self._schedule_reconnect()

                def on_open(ws):
                    self.logger.info("WebSocket连接已建立")
                    self.state = ConnectionState.CONNECTED
                    self.stats.total_connections += 1
                    self.reconnect_count = 0

                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                )

                # 在单独线程中运行
                self._running = True
                self._ws_thread = threading.Thread(
                    target=self._run_websocket, daemon=True
                )
                self._ws_thread.start()

                # 等待连接建立
                timeout = 10
                while timeout > 0 and self.state == ConnectionState.CONNECTING:
                    time.sleep(0.1)
                    timeout -= 0.1

                return self.state == ConnectionState.CONNECTED

            except Exception as e:
                self.state = ConnectionState.FAILED
                raise ConnectionError(f"WebSocket连接失败: {e}")

    def _run_websocket(self):
        """运行WebSocket循环"""
        try:
            self.ws.run_forever()
        except Exception as e:
            self.logger.error(f"WebSocket运行异常: {e}")

    def _schedule_reconnect(self):
        """安排重连"""

        def reconnect_task():
            time.sleep(self.reconnect_interval)
            if self._running:
                self.reconnect_count += 1
                self.logger.info(f"尝试第{self.reconnect_count}次重连")
                self.connect()

        thread = threading.Thread(target=reconnect_task, daemon=True)
        thread.start()

    def _handle_message(self, message):
        """处理收到的消息"""
        # 这里可以解析消息并分发给相应的处理器
        for handlers in self._message_handlers.values():
            for handler in handlers:
                try:
                    handler(message)
                except Exception as e:
                    self.logger.error(f"消息处理错误: {e}")

    def disconnect(self) -> bool:
        """断开WebSocket连接"""
        with self._lock:
            try:
                self._running = False
                if self.ws:
                    self.ws.close()
                    self.ws = None
                if self._ws_thread and self._ws_thread.is_alive():
                    self._ws_thread.join(timeout=5)
                self.state = ConnectionState.DISCONNECTED
                return True
            except Exception:
                self.state = ConnectionState.FAILED
                return False

    def is_alive(self) -> bool:
        """检查WebSocket连接是否存活"""
        return (
            self.ws is not None
            and self.state == ConnectionState.CONNECTED
            and self._running
        )

    def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """执行WebSocket操作（如发送消息）"""
        if not self.ws or self.state != ConnectionState.CONNECTED:
            from .exceptions import ConnectionError

            raise ConnectionError("WebSocket未连接")

        try:
            return operation(self.ws, *args, **kwargs)
        except Exception as e:
            from .exceptions import NetworkError

            raise NetworkError(f"WebSocket操作失败: {e}")

    def subscribe(self, channel: str, handler: Callable):
        """订阅频道"""
        if channel not in self._message_handlers:
            self._message_handlers[channel] = []
        self._message_handlers[channel].append(handler)

    def unsubscribe(self, channel: str, handler: Callable = None):
        """取消订阅"""
        if handler:
            if channel in self._message_handlers:
                try:
                    self._message_handlers[channel].remove(handler)
                except ValueError:
                    pass
        else:
            self._message_handlers.pop(channel, None)


class ConnectionPool:
    """连接池管理器"""

    def __init__(self, pool_size: int = 10, idle_timeout: int = 300):
        self.pool_size = pool_size
        self.idle_timeout = idle_timeout
        self.connections: Dict[str, Connection] = {}
        self.available_connections: Deque[str] = deque()
        self.in_use_connections: Set[str] = set()
        self.connection_config: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._running = False
        from .logger import get_logger

        self.logger = get_logger("connection_pool")

    def initialize(self):
        """初始化连接池"""
        self._running = True
        self._start_cleanup_thread()

    def shutdown(self):
        """关闭连接池"""
        self._running = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join()

        # 关闭所有连接
        with self._lock:
            for conn_id in list(self.connections.keys()):
                self._close_connection(conn_id)

    def register_connection_type(self, conn_type: str, config: Dict[str, Any]):
        """注册连接类型配置"""
        self.connection_config[conn_type] = config

    def get_connection(self, conn_type: str) -> Optional[Connection]:
        """获取连接"""
        with self._lock:
            # 首先尝试从可用连接中获取
            while self.available_connections:
                conn_id = self.available_connections.popleft()
                conn = self.connections.get(conn_id)
                if conn and conn.state == ConnectionState.CONNECTED:
                    self.in_use_connections.add(conn_id)
                    conn.last_used = time.time()
                    return conn
                else:
                    # 移除失效连接
                    self.connections.pop(conn_id, None)

            # 如果没有可用连接，创建新连接（如果未达到池大小限制）
            if len(self.connections) < self.pool_size:
                return self._create_new_connection(conn_type)

            # 如果达到池大小限制，等待或返回None
            return None

    def return_connection(self, connection: Connection):
        """归还连接"""
        with self._lock:
            if connection.id in self.in_use_connections:
                self.in_use_connections.remove(connection.id)
                if (
                    connection.state == ConnectionState.CONNECTED
                    and len(self.available_connections) < self.pool_size
                ):
                    self.available_connections.append(connection.id)
                else:
                    # 连接已失效，关闭并移除
                    self._close_connection(connection.id)

    def _create_new_connection(self, conn_type: str) -> Optional[Connection]:
        """创建新连接"""
        config = self.connection_config.get(conn_type)
        if not config:
            from .exceptions import ConfigError

            raise ConfigError(f"未找到连接类型配置: {conn_type}")

        try:
            conn_id = f"{conn_type}_{int(time.time() * 1000)}"

            # 根据类型创建连接
            if conn_type.startswith("http"):
                connection = HTTPConnection(conn_id, config)
            elif conn_type.startswith("ws"):
                connection = WebSocketConnection(conn_id, config)
            else:
                from .exceptions import ConfigError

                raise ConfigError(f"不支持的连接类型: {conn_type}")

            # 建立连接
            if connection.connect():
                self.connections[conn_id] = connection
                self.in_use_connections.add(conn_id)
                return connection
            else:
                return None

        except Exception as e:
            self.logger.error(f"创建连接失败: {e}")
            return None

    def _close_connection(self, conn_id: str):
        """关闭连接"""
        connection = self.connections.pop(conn_id, None)
        if connection:
            try:
                connection.disconnect()
            except Exception as e:
                self.logger.error(f"关闭连接时出错: {e}")

        # 从使用中和可用连接中移除
        self.in_use_connections.discard(conn_id)
        if conn_id in self.available_connections:
            self.available_connections.remove(conn_id)

    def _start_cleanup_thread(self):
        """启动清理线程"""

        def cleanup_task():
            while self._running:
                try:
                    self._cleanup_idle_connections()
                    time.sleep(60)  # 每分钟检查一次
                except Exception as e:
                    self.logger.error(f"清理线程错误: {e}")

        self._cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_idle_connections(self):
        """清理空闲连接"""
        current_time = time.time()
        with self._lock:
            # 清理超时空闲连接
            idle_connections = []
            for conn_id in self.available_connections:
                conn = self.connections.get(conn_id)
                if conn and (current_time - conn.last_used) > self.idle_timeout:
                    idle_connections.append(conn_id)

            for conn_id in idle_connections:
                self._close_connection(conn_id)
                if conn_id in self.available_connections:
                    self.available_connections.remove(conn_id)


class HeartbeatMonitor:
    """心跳监控器"""

    def __init__(self, interval: int = 30):
        self.interval = interval
        self.monitored_connections: Dict[str, Connection] = {}
        self._lock = threading.RLock()
        self._monitor_thread = None
        self._running = False
        from .logger import get_logger

        self.logger = get_logger("heartbeat_monitor")

    def start(self):
        """启动心跳监控"""
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        """停止心跳监控"""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join()

    def add_connection(self, connection: Connection):
        """添加要监控的连接"""
        with self._lock:
            self.monitored_connections[connection.id] = connection

    def remove_connection(self, connection_id: str):
        """移除监控的连接"""
        with self._lock:
            self.monitored_connections.pop(connection_id, None)

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                self._perform_heartbeats()
                time.sleep(self.interval)
            except Exception as e:
                self.logger.error(f"心跳监控错误: {e}")

    def _perform_heartbeats(self):
        """执行心跳检测"""
        with self._lock:
            dead_connections = []
            for conn_id, connection in self.monitored_connections.items():
                try:
                    if not connection.heartbeat():
                        self.logger.warning(f"连接 {conn_id} 心跳失败")
                        dead_connections.append(conn_id)
                except Exception as e:
                    self.logger.error(f"心跳检测异常 {conn_id}: {e}")
                    dead_connections.append(conn_id)

            # 移除死亡连接
            for conn_id in dead_connections:
                self.monitored_connections.pop(conn_id, None)


# 全局连接管理器实例
_connection_manager = None
_heartbeat_monitor = None


def get_connection_manager() -> ConnectionPool:
    """获取全局连接管理器"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionPool()
        _connection_manager.initialize()
    return _connection_manager


def get_heartbeat_monitor() -> HeartbeatMonitor:
    """获取全局心跳监控器"""
    global _heartbeat_monitor
    if _heartbeat_monitor is None:
        _heartbeat_monitor = HeartbeatMonitor()
        _heartbeat_monitor.start()
    return _heartbeat_monitor


def shutdown_connection_managers():
    """关闭所有连接管理器"""
    global _connection_manager, _heartbeat_monitor
    if _connection_manager:
        _connection_manager.shutdown()
        _connection_manager = None
    if _heartbeat_monitor:
        _heartbeat_monitor.stop()
        _heartbeat_monitor = None


__all__ = [
    "ConnectionState",
    "ConnectionStats",
    "Connection",
    "HTTPConnection",
    "WebSocketConnection",
    "ConnectionPool",
    "HeartbeatMonitor",
    "get_connection_manager",
    "get_heartbeat_monitor",
    "shutdown_connection_managers",
]
