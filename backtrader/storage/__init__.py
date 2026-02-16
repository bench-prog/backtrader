#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级数据存储系统
Enterprise Data Storage System for Backtrader

模块结构:
├── data_storage.py    # 多类型数据存储实现
└── __init__.py        # 模块初始化
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# 数据存储组件
from .data_storage import (
    DataStorageError,
    ConnectionPool,
    BaseDataStorage,
    TimeSeriesStorage,
    RelationalStorage,
    CacheStorage,
    ObjectStorage,
    DataStorageManager,
    create_data_storage,
    create_storage_manager
)

__all__ = [
    'DataStorageError',
    'ConnectionPool',
    'BaseDataStorage',
    'TimeSeriesStorage',
    'RelationalStorage',
    'CacheStorage',
    'ObjectStorage',
    'DataStorageManager',
    'create_data_storage',
    'create_storage_manager',
]

__version__ = '1.0.0'
__author__ = 'Backtrader Storage Team'