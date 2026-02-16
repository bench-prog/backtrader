#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级配置管理中心
Enterprise Configuration Management Center for Backtrader

模块结构:
├── manager.py      # 配置管理核心
├── templates.py    # 环境模板和工具
└── __init__.py     # 模块初始化

使用方式（简化版）:
    # 1. 初始化配置（可选，有默认值）
    from backtrader.config import get_config_manager
    config = get_config_manager()

    # 2. 在 Cerebro 中自动使用
    cerebro = bt.Cerebro()
    # 配置会自动被风控和监控模块使用
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# 配置管理核心组件
from .manager import (
    ConfigurationManager,
    ConfigValidationError,
    ConfigValidator,
    ConfigVersionManager,
    CryptoManager,
    EnvironmentManager,
    SecretManager,
    create_config_manager,
    load_config_from_environment,
)

# 环境模板和工具
from .templates import (
    ConfigUtils,
    EnvironmentSwitcher,
    EnvironmentTemplates,
    initialize_environment,
    setup_project_structure,
)

# 全局配置管理器单例
_global_config_manager = None

def get_config_manager():
    """
    获取全局配置管理器单例

    如果未初始化，会创建一个默认的配置管理器

    Returns:
        ConfigurationManager: 配置管理器实例
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigurationManager()
    return _global_config_manager

def set_config_manager(config_manager):
    """
    设置全局配置管理器

    Args:
        config_manager: ConfigurationManager 实例
    """
    global _global_config_manager
    _global_config_manager = config_manager

__all__ = [
    # 核心管理器
    "ConfigValidationError",
    "EnvironmentManager",
    "CryptoManager",
    "SecretManager",
    "ConfigValidator",
    "ConfigVersionManager",
    "ConfigurationManager",
    "create_config_manager",
    "load_config_from_environment",
    # 模板和工具
    "EnvironmentTemplates",
    "ConfigUtils",
    "EnvironmentSwitcher",
    "setup_project_structure",
    "initialize_environment",
    # 全局访问函数
    "get_config_manager",
    "set_config_manager",
]

__version__ = "1.0.0"
__author__ = "Backtrader Configuration Team"
