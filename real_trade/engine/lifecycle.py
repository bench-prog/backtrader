#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
LifecycleManager - 生命周期管理

管理交易系统的启动、停止、重连和异常恢复。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import signal
import threading
from typing import Callable, List


class LifecycleManager:
    """
    交易系统生命周期管理

    - 优雅关闭（捕获 SIGINT/SIGTERM）
    - 自动重连
    - 异常恢复
    - 回调钩子

    Usage::

        lm = LifecycleManager()
        lm.on_start(lambda: print("started"))
        lm.on_stop(lambda: print("stopped"))

        with lm:
            runner.run()
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self._start_hooks: List[Callable] = []
        self._stop_hooks: List[Callable] = []
        self._error_hooks: List[Callable] = []

        self._running = False
        self._shutdown_event = threading.Event()

    def on_start(self, func: Callable):
        self._start_hooks.append(func)

    def on_stop(self, func: Callable):
        self._stop_hooks.append(func)

    def on_error(self, func: Callable):
        self._error_hooks.append(func)

    def _signal_handler(self, signum, frame):
        sig_name = signal.Signals(signum).name
        print(f"\n[Lifecycle] Received {sig_name}, shutting down...")
        self._shutdown_event.set()

    def __enter__(self):
        self._running = True
        self._shutdown_event.clear()

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        for hook in self._start_hooks:
            try:
                hook()
            except Exception as e:
                print(f"[Lifecycle] Start hook error: {e}")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._running = False

        for hook in self._stop_hooks:
            try:
                hook()
            except Exception as e:
                print(f"[Lifecycle] Stop hook error: {e}")

        if exc_type:
            for hook in self._error_hooks:
                try:
                    hook(exc_val)
                except Exception:
                    pass

        # 不抑制异常
        return False

    def run_with_retry(self, func: Callable, *args, **kwargs):
        """带重试的运行"""
        retries = 0
        while retries <= self.max_retries and not self._shutdown_event.is_set():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                retries += 1
                for hook in self._error_hooks:
                    try:
                        hook(e)
                    except Exception:
                        pass

                if retries > self.max_retries:
                    print(f"[Lifecycle] Max retries ({self.max_retries}) exceeded")
                    raise

                print(
                    f"[Lifecycle] Retry {retries}/{self.max_retries} "
                    f"in {self.retry_delay}s... Error: {e}"
                )
                self._shutdown_event.wait(self.retry_delay)

    @property
    def should_stop(self) -> bool:
        return self._shutdown_event.is_set()

    def request_stop(self):
        self._shutdown_event.set()
