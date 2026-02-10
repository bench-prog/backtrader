#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
BaseWebSocket - WebSocket 实时数据基类

为交易所 WebSocket 连接提供统一接口：
- 自动重连
- 心跳保活
- 消息分发
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional


class BaseWebSocket:
    """
    WebSocket 基类

    子类需实现:
    - _get_ws_url(): 返回 WebSocket 连接地址
    - _on_message(msg): 处理收到的消息
    - _build_subscribe_msg(channels): 构建订阅消息

    Usage::

        class BinanceWS(BaseWebSocket):
            def _get_ws_url(self):
                return "wss://stream.binance.com:9443/ws"

            def _build_subscribe_msg(self, channels):
                return {"method": "SUBSCRIBE", "params": channels, "id": 1}

            def _on_message(self, msg):
                # 处理收到的消息
                pass
    """

    def __init__(
        self,
        ping_interval: float = 20.0,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 10,
    ):
        self.ping_interval = ping_interval
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts

        self._ws = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, List[Callable]] = {}

    # ------------------------------------------------------------------
    # 子类必须实现
    # ------------------------------------------------------------------

    def _get_ws_url(self) -> str:
        raise NotImplementedError

    def _build_subscribe_msg(self, channels: List[str]) -> Dict[str, Any]:
        raise NotImplementedError

    def _on_message(self, msg: Dict[str, Any]):
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def on(self, event: str, callback: Callable):
        """注册事件回调"""
        self._callbacks.setdefault(event, []).append(callback)

    def emit(self, event: str, data: Any = None):
        """触发事件"""
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                print(f"[WS] Callback error for '{event}': {e}")

    def start(self, channels: Optional[List[str]] = None):
        """启动 WebSocket 连接"""
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, args=(channels,), daemon=True
        )
        self._thread.start()

    def stop(self):
        """停止连接"""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass

    def send(self, data: Dict[str, Any]):
        """发送消息"""
        if self._ws:
            try:
                self._ws.send(json.dumps(data))
            except Exception as e:
                print(f"[WS] Send error: {e}")

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and self._running

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _run_loop(self, channels: Optional[List[str]] = None):
        """主循环（带自动重连）"""
        attempt = 0

        while self._running and attempt < self.max_reconnect_attempts:
            try:
                self._connect(channels)
                attempt = 0  # 成功连接后重置计数
            except Exception as e:
                attempt += 1
                print(
                    f"[WS] Connection failed (attempt {attempt}/"
                    f"{self.max_reconnect_attempts}): {e}"
                )
                if self._running:
                    time.sleep(self.reconnect_delay)

        if self._running:
            print("[WS] Max reconnect attempts reached")
            self.emit("max_reconnect")

    def _connect(self, channels: Optional[List[str]] = None):
        """建立单次连接"""
        try:
            import websocket
        except ImportError:
            print(
                "[WS] websocket-client not installed. "
                "Install with: pip install websocket-client"
            )
            self._running = False
            return

        url = self._get_ws_url()
        print(f"[WS] Connecting to {url}")

        self._ws = websocket.WebSocketApp(
            url,
            on_open=lambda ws: self._handle_open(ws, channels),
            on_message=lambda ws, msg: self._handle_message(msg),
            on_error=lambda ws, err: self._handle_error(err),
            on_close=lambda ws, code, reason: self._handle_close(code, reason),
        )

        self._ws.run_forever(
            ping_interval=self.ping_interval,
            ping_timeout=10,
        )

    def _handle_open(self, ws, channels):
        print("[WS] Connected")
        self.emit("connected")
        if channels:
            msg = self._build_subscribe_msg(channels)
            self.send(msg)

    def _handle_message(self, raw_msg):
        try:
            msg = json.loads(raw_msg)
            self._on_message(msg)
        except json.JSONDecodeError:
            pass

    def _handle_error(self, error):
        print(f"[WS] Error: {error}")
        self.emit("error", error)

    def _handle_close(self, code, reason):
        print(f"[WS] Closed (code={code}, reason={reason})")
        self._ws = None
        self.emit("disconnected")
