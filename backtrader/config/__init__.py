#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级配置管理中心
Enterprise Configuration Management Center for Backtrader

模块结构:
├── manager.py      # 配置管理核心
├── templates.py    # 环境模板和工具
└── __init__.py     # 模块初始化
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# 配置管理核心组件
from .manager import (
    ConfigValidationError,
    EnvironmentManager,
    CryptoManager,
    SecretManager,
    ConfigValidator,
    ConfigVersionManager,
    ConfigurationManager,
    create_config_manager,
    load_config_from_environment
)

# 环境模板和工具
from .templates import (
    EnvironmentTemplates,
    ConfigUtils,
    EnvironmentSwitcher,
    setup_project_structure,
    initialize_environment
)

__all__ = [
    # 核心管理器
    'ConfigValidationError',
    'EnvironmentManager',
    'CryptoManager',
    'SecretManager',
    'ConfigValidator',
    'ConfigVersionManager',
    'ConfigurationManager',
    'create_config_manager',
    'load_config_from_environment',
    
    # 模板和工具
    'EnvironmentTemplates',
    'ConfigUtils',
    'EnvironmentSwitcher',
    'setup_project_structure',
    'initialize_environment',
]

__version__ = '1.0.0'
__author__ = 'Backtrader Configuration Team'