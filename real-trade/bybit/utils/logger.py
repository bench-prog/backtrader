#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
日志模块

提供统一的日志记录功能。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "bybit",
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径
        format_string: 日志格式

    Returns:
        Logger 对象
    """
    logger = logging.getLogger(name)

    # 清除已有处理器
    logger.handlers.clear()

    # 设置日志级别
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    logger.setLevel(level_map.get(level.upper(), logging.INFO))

    # 日志格式
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Logging to file: {log_file}")

    return logger


def get_logger(name: str = "bybit") -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志器名称

    Returns:
        Logger 对象
    """
    return logging.getLogger(name)


# 默认日志器
default_logger = setup_logger()
