#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Logger - 统一日志

基于标准库 logging，提供结构化日志输出。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import sys
from typing import Optional

_LOGGERS = {}


def setup_logger(
    name: str = "real_trade",
    level: str = "INFO",
    log_file: Optional[str] = None,
    fmt: str = "%(asctime)s [%(name)s] %(levelname)s %(message)s",
) -> logging.Logger:
    """
    创建/获取 logger

    Args:
        name: logger 名称
        level: 日志级别
        log_file: 日志文件路径（None=仅控制台）
        fmt: 日志格式
    """
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # 控制台
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    # 文件
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    _LOGGERS[name] = logger
    return logger


def get_logger(name: str = "real_trade") -> logging.Logger:
    """获取已创建的 logger，如不存在则自动创建"""
    if name not in _LOGGERS:
        return setup_logger(name)
    return _LOGGERS[name]
