#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
环境配置模板和工具函数
Environment Configuration Templates and Utility Functions
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import os
import json
from typing import Dict, List, Any
import datetime


class EnvironmentTemplates:
    """
    环境配置模板
    """
    
    @staticmethod
    def get_development_template() -> Dict[str, Any]:
        """开发环境模板"""
        return {
            'environment': {
                'name': 'development',
                'debug': True,
                'log_level': 'DEBUG'
            },
            'database': {
                'host': 'localhost',
                'port': 5432,
                'database': 'backtrader_dev',
                'username': 'dev_user',
                'password': '${DB_PASSWORD}',  # 使用环境变量
                'pool_size': 5
            },
            'risk': {
                'max_leverage': 5.0,           # 开发环境允许更高杠杆
                'max_position_size': 0.2,      # 更大的仓位限制
                'max_daily_loss': 0.1,         # 更宽松的亏损限制
                'paper_trading': True          # 使用模拟交易
            },
            'trading': {
                'symbols': ['BTC/USDT', 'ETH/USDT'],
                'timeframes': ['1h', '4h'],
                'initial_capital': 10000.0,
                'commission': 0.001
            },
            'monitoring': {
                'enabled': True,
                'check_interval': 30,
                'alert_channels': ['console']
            }
        }
    
    @staticmethod
    def get_testing_template() -> Dict[str, Any]:
        """测试环境模板"""
        return {
            'environment': {
                'name': 'testing',
                'debug': True,
                'log_level': 'INFO'
            },
            'database': {
                'host': 'test-db.example.com',
                'port': 5432,
                'database': 'backtrader_test',
                'username': 'test_user',
                'password': '${DB_PASSWORD}',
                'pool_size': 10
            },
            'risk': {
                'max_leverage': 3.0,
                'max_position_size': 0.15,
                'max_daily_loss': 0.08,
                'paper_trading': True
            },
            'trading': {
                'symbols': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
                'timeframes': ['1h', '4h', '1d'],
                'initial_capital': 50000.0,
                'commission': 0.001
            },
            'monitoring': {
                'enabled': True,
                'check_interval': 60,
                'alert_channels': ['console', 'email']
            }
        }
    
    @staticmethod
    def get_staging_template() -> Dict[str, Any]:
        """预发布环境模板"""
        return {
            'environment': {
                'name': 'staging',
                'debug': False,
                'log_level': 'WARNING'
            },
            'database': {
                'host': 'staging-db.example.com',
                'port': 5432,
                'database': 'backtrader_staging',
                'username': 'staging_user',
                'password': '${DB_PASSWORD}',
                'pool_size': 20
            },
            'risk': {
                'max_leverage': 2.0,
                'max_position_size': 0.1,
                'max_daily_loss': 0.05,
                'paper_trading': True  # 仍使用模拟交易
            },
            'trading': {
                'symbols': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT'],
                'timeframes': ['1h', '4h', '1d'],
                'initial_capital': 100000.0,
                'commission': 0.001
            },
            'monitoring': {
                'enabled': True,
                'check_interval': 30,
                'alert_channels': ['email', 'webhook']
            }
        }
    
    @staticmethod
    def get_production_template() -> Dict[str, Any]:
        """生产环境模板"""
        return {
            'environment': {
                'name': 'production',
                'debug': False,
                'log_level': 'ERROR'
            },
            'database': {
                'host': 'prod-db.example.com',
                'port': 5432,
                'database': 'backtrader_prod',
                'username': 'prod_user',
                'password': '${DB_PASSWORD}',
                'pool_size': 50,
                'ssl_enabled': True
            },
            'risk': {
                'max_leverage': 1.5,           # 生产环境严格限制
                'max_position_size': 0.05,     # 更严格的仓位限制
                'max_daily_loss': 0.03,        # 更严格的亏损限制
                'paper_trading': False         # 实盘交易
            },
            'trading': {
                'symbols': ['BTC/USDT', 'ETH/USDT'],
                'timeframes': ['1h', '4h', '1d'],
                'initial_capital': 1000000.0,   # 真实资金
                'commission': 0.001
            },
            'monitoring': {
                'enabled': True,
                'check_interval': 15,
                'alert_channels': ['email', 'sms', 'webhook'],
                'critical_alerts_only': True
            },
            'security': {
                'encryption_enabled': True,
                'audit_logging': True,
                'rate_limiting': True
            }
        }


class ConfigUtils:
    """
    配置工具函数
    """
    
    @staticmethod
    def merge_configs(base_config: Dict, override_config: Dict) -> Dict:
        """
        深度合并配置字典
        """
        result = base_config.copy()
        
        for key, value in override_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigUtils.merge_configs(result[key], value)
            else:
                result[key] = value
                
        return result
    
    @staticmethod
    def substitute_env_vars(config: Dict, env_prefix: str = "") -> Dict:
        """
        替换配置中的环境变量占位符
        支持格式: ${VAR_NAME} 或 ${PREFIX_VAR_NAME}
        """
        def substitute_value(value):
            if isinstance(value, str) and '${' in value:
                import re
                pattern = r'\$\{([^}]+)\}'
                def replace_var(match):
                    var_name = match.group(1)
                    # 如果没有前缀且指定了env_prefix，则添加前缀
                    if '_' not in var_name and env_prefix:
                        var_name = f"{env_prefix}_{var_name}"
                    return os.environ.get(var_name, match.group(0))
                return re.sub(pattern, replace_var, value)
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            return value
        
        return substitute_value(config)
    
    @staticmethod
    def validate_environment_config(config: Dict) -> List[str]:
        """
        验证环境配置的完整性
        """
        errors = []
        
        # 检查必需的节
        required_sections = ['environment', 'risk', 'trading']
        for section in required_sections:
            if section not in config:
                errors.append(f"缺少必需的配置节: {section}")
        
        # 检查环境信息
        if 'environment' in config:
            env_config = config['environment']
            if 'name' not in env_config:
                errors.append("environment节缺少name字段")
            if 'debug' not in env_config:
                errors.append("environment节缺少debug字段")
        
        # 检查风控配置
        if 'risk' in config:
            risk_config = config['risk']
            required_risk_fields = ['max_leverage', 'max_position_size', 'max_daily_loss']
            for field in required_risk_fields:
                if field not in risk_config:
                    errors.append(f"risk节缺少{field}字段")
        
        # 检查交易配置
        if 'trading' in config:
            trading_config = config['trading']
            required_trading_fields = ['symbols', 'timeframes', 'initial_capital']
            for field in required_trading_fields:
                if field not in trading_config:
                    errors.append(f"trading节缺少{field}字段")
        
        return errors
    
    @staticmethod
    def generate_env_file(config: Dict, filepath: str):
        """
        根据配置生成环境变量文件(.env)
        """
        env_vars = []
        
        # 提取数据库配置
        if 'database' in config:
            db_config = config['database']
            env_vars.extend([
                f"DB_HOST={db_config.get('host', 'localhost')}",
                f"DB_PORT={db_config.get('port', 5432)}",
                f"DB_DATABASE={db_config.get('database', 'backtrader')}",
                f"DB_USERNAME={db_config.get('username', 'user')}",
                f"DB_PASSWORD=your_password_here"  # 密码需要手动设置
            ])
        
        # 提取API密钥（如果存在）
        # 注意：实际使用时应该从密钥管理器获取
        
        # 写入文件
        with open(filepath, 'w') as f:
            f.write("# Backtrader Environment Variables\n")
            f.write("# Generated on " + datetime.datetime.now().isoformat() + "\n\n")
            for var in env_vars:
                f.write(var + "\n")
        
        print(f"✅ 环境变量文件已生成: {filepath}")
        print("⚠️  请手动设置敏感信息（如密码）")
    
    @staticmethod
    def create_directory_structure(base_path: str):
        """
        创建标准的配置目录结构
        """
        directories = [
            'config',
            'config/environments',
            'config/secrets',
            'logs',
            'data',
            'strategies',
            'reports'
        ]
        
        for directory in directories:
            full_path = os.path.join(base_path, directory)
            os.makedirs(full_path, exist_ok=True)
            print(f"📁 创建目录: {full_path}")
        
        # 创建README文件
        readme_content = """
# Backtrader 项目目录结构

## 目录说明

- `config/` - 配置文件目录
  - `environments/` - 环境配置文件
  - `secrets/` - 加密的密钥文件
- `logs/` - 日志文件
- `data/` - 数据文件
- `strategies/` - 策略文件
- `reports/` - 报告文件

## 使用说明

1. 复制相应环境的配置文件到config/目录
2. 设置环境变量或修改配置文件中的敏感信息
3. 运行策略
        """
        
        with open(os.path.join(base_path, 'README.md'), 'w') as f:
            f.write(readme_content.strip())


class EnvironmentSwitcher:
    """
    环境切换器
    """
    
    def __init__(self, config_manager: 'bt.config.ConfigurationManager'):
        self.config_manager = config_manager
        self.templates = EnvironmentTemplates()
    
    def switch_to_environment(self, env_name: str, save_previous: bool = True):
        """
        切换到指定环境
        """
        # 保存当前环境配置（如果需要）
        if save_previous:
            current_env = self.config_manager.environment_manager.get_environment()
            if current_env != env_name:
                self._save_current_environment_config(current_env)
        
        # 加载目标环境配置
        env_template = self._get_environment_template(env_name)
        if env_template:
            # 替换环境变量
            resolved_config = ConfigUtils.substitute_env_vars(env_template, "BT")
            
            # 验证配置
            errors = ConfigUtils.validate_environment_config(resolved_config)
            if errors:
                raise ValueError(f"环境配置验证失败: {'; '.join(errors)}")
            
            # 应用配置
            self.config_manager.set_config(resolved_config, f"切换到{env_name}环境")
            self.config_manager.environment_manager.set_environment(env_name)
            
            print(f"✅ 已切换到 {env_name} 环境")
        else:
            raise ValueError(f"不支持的环境: {env_name}")
    
    def _get_environment_template(self, env_name: str) -> Dict:
        """获取环境模板"""
        template_methods = {
            'development': self.templates.get_development_template,
            'testing': self.templates.get_testing_template,
            'staging': self.templates.get_staging_template,
            'production': self.templates.get_production_template
        }
        
        if env_name in template_methods:
            return template_methods[env_name]()
        return None
    
    def _save_current_environment_config(self, env_name: str):
        """保存当前环境配置"""
        try:
            config = self.config_manager.get_config()
            filename = f"config_backup_{env_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.config_manager.config_dir, 'backups', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            
            print(f"💾 当前{env_name}环境配置已备份到: {filepath}")
        except Exception as e:
            print(f"⚠️  配置备份失败: {e}")


# 便捷函数
def setup_project_structure(project_path: str = "."):
    """
    设置项目目录结构
    """
    ConfigUtils.create_directory_structure(project_path)


def initialize_environment(env_name: str = "development", 
                          project_path: str = ".",
                          config_manager: 'bt.config.ConfigurationManager' = None):
    """
    初始化指定环境
    """
    if config_manager is None:
        config_manager = bt.config.create_config_manager(
            os.path.join(project_path, 'config')
        )
    
    # 创建目录结构
    setup_project_structure(project_path)
    
    # 切换环境
    switcher = EnvironmentSwitcher(config_manager)
    switcher.switch_to_environment(env_name)
    
    # 生成环境变量文件
    current_config = config_manager.get_config()
    env_file_path = os.path.join(project_path, '.env')
    ConfigUtils.generate_env_file(current_config, env_file_path)
    
    return config_manager


# 使用示例
if __name__ == "__main__":
    # 初始化开发环境
    config_mgr = initialize_environment("development")
    
    # 查看当前配置
    print("当前环境配置:")
    print(json.dumps(config_mgr.get_config(), indent=2))
    
    # 切换到生产环境
    switcher = EnvironmentSwitcher(config_mgr)
    switcher.switch_to_environment("production")