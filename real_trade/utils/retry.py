#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Retry - 重试/断线重连机制

提供装饰器和配置类。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import functools
import time
from dataclasses import dataclass
from typing import Tuple, Type


@dataclass
class RetryConfig:
    """重试配置"""

    max_retries: int = 3
    base_delay: float = 1.0  # 初始延迟秒数
    max_delay: float = 60.0  # 最大延迟秒数
    backoff_factor: float = 2.0  # 指数退避因子
    exceptions: Tuple[Type[Exception], ...] = (Exception,)


def retry(config: RetryConfig = None, **kwargs):
    """
    重试装饰器

    支持指数退避。

    Usage::

        @retry(max_retries=3, base_delay=1.0)
        def fetch_data():
            ...

        # 或使用 RetryConfig
        @retry(RetryConfig(max_retries=5))
        def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig(**kwargs)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            last_exception = None
            delay = config.base_delay

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kw)
                except config.exceptions as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        sleep_time = min(delay, config.max_delay)
                        print(
                            f"[retry] {func.__name__} attempt {attempt + 1}/"
                            f"{config.max_retries} failed: {e}. "
                            f"Retrying in {sleep_time:.1f}s..."
                        )
                        time.sleep(sleep_time)
                        delay *= config.backoff_factor

            raise last_exception

        return wrapper

    return decorator
