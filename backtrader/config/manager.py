#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级配置管理中心 (Enterprise Configuration Management Center)
基于backtrader架构的配置管理和环境隔离解决方案

核心功能：
1. 集中式配置管理
2. 多环境隔离 (dev/test/staging/prod)
3. 密钥安全管理
4. 配置版本控制
5. 配置热更新
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import copy
import datetime
import hashlib
import json
import os
import threading
from collections import OrderedDict, defaultdict
from typing import Any, Dict, List

import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class ConfigValidationError(Exception):
    """配置验证错误"""

    pass


class EnvironmentManager:
    """
    环境管理器 - 管理不同环境的配置
    """

    ENVIRONMENTS = ["development", "testing", "staging", "production"]
    DEFAULT_ENV = "development"

    def __init__(self):
        self.current_env = self.DEFAULT_ENV
        self.env_configs = {}
        self._lock = threading.RLock()

    def set_environment(self, env: str):
        """设置当前环境"""
        with self._lock:
            if env not in self.ENVIRONMENTS:
                raise ValueError(f"无效环境: {env}, 支持的环境: {self.ENVIRONMENTS}")
            self.current_env = env
            print(f"🌍 环境已切换到: {env}")

    def get_environment(self) -> str:
        """获取当前环境"""
        return self.current_env

    def get_available_environments(self) -> List[str]:
        """获取可用环境列表"""
        return self.ENVIRONMENTS.copy()

    def load_environment_config(self, env: str, config_data: Dict):
        """加载环境配置"""
        with self._lock:
            self.env_configs[env] = config_data

    def get_environment_config(self, env: str = None) -> Dict:
        """获取指定环境的配置"""
        target_env = env or self.current_env
        return self.env_configs.get(target_env, {})

    def merge_configs(self, base_config: Dict, env_config: Dict) -> Dict:
        """合并基础配置和环境配置"""
        merged = copy.deepcopy(base_config)

        def deep_merge(base, override):
            for key, value in override.items():
                if (
                    key in base
                    and isinstance(base[key], dict)
                    and isinstance(value, dict)
                ):
                    deep_merge(base[key], value)
                else:
                    base[key] = copy.deepcopy(value)

        deep_merge(merged, env_config)
        return merged


class CryptoManager:
    """
    加密管理器 - 处理密钥加密和解密
    """

    def __init__(self, master_password: str = None):
        self.master_password = master_password or self._generate_default_password()
        self.key = self._derive_key(self.master_password)
        self.cipher = Fernet(self.key)
        self._lock = threading.RLock()

    def _generate_default_password(self) -> str:
        """生成默认密码"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    def _derive_key(self, password: str) -> bytes:
        """从密码派生加密密钥"""
        salt = b"backtrader_config_salt"  # 在生产环境中应该使用随机盐值
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def encrypt(self, data: str) -> str:
        """加密数据"""
        with self._lock:
            encrypted_data = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        with self._lock:
            try:
                encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
                decrypted_data = self.cipher.decrypt(encrypted_bytes)
                return decrypted_data.decode()
            except Exception as e:
                raise ValueError(f"解密失败: {e}")

    def change_master_password(self, new_password: str):
        """更换主密码"""
        with self._lock:
            # 重新加密所有密钥
            self.master_password = new_password
            self.key = self._derive_key(new_password)
            self.cipher = Fernet(self.key)


class SecretManager:
    """
    密钥管理器 - 管理敏感信息
    """

    def __init__(self, crypto_manager: CryptoManager):
        self.crypto_manager = crypto_manager
        self.secrets = {}
        self.access_log = []
        self._lock = threading.RLock()

    def store_secret(self, key: str, value: str, description: str = ""):
        """存储密钥"""
        with self._lock:
            encrypted_value = self.crypto_manager.encrypt(value)
            self.secrets[key] = {
                "value": encrypted_value,
                "description": description,
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat(),
            }

            self._log_access("STORE", key, description)

    def retrieve_secret(self, key: str) -> str:
        """获取密钥"""
        with self._lock:
            if key not in self.secrets:
                raise KeyError(f"密钥不存在: {key}")

            encrypted_value = self.secrets[key]["value"]
            decrypted_value = self.crypto_manager.decrypt(encrypted_value)

            self._log_access("RETRIEVE", key, self.secrets[key].get("description", ""))
            return decrypted_value

    def update_secret(self, key: str, value: str, description: str = ""):
        """更新密钥"""
        with self._lock:
            if key not in self.secrets:
                raise KeyError(f"密钥不存在: {key}")

            encrypted_value = self.crypto_manager.encrypt(value)
            self.secrets[key].update(
                {
                    "value": encrypted_value,
                    "description": description,
                    "updated_at": datetime.datetime.now().isoformat(),
                }
            )

            self._log_access("UPDATE", key, description)

    def delete_secret(self, key: str):
        """删除密钥"""
        with self._lock:
            if key in self.secrets:
                description = self.secrets[key].get("description", "")
                del self.secrets[key]
                self._log_access("DELETE", key, description)

    def list_secrets(self) -> List[Dict]:
        """列出所有密钥信息（不含实际值）"""
        with self._lock:
            return [
                {
                    "key": key,
                    "description": info["description"],
                    "created_at": info["created_at"],
                    "updated_at": info["updated_at"],
                }
                for key, info in self.secrets.items()
            ]

    def _log_access(self, action: str, key: str, description: str):
        """记录访问日志"""
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "action": action,
            "key": key,
            "description": description,
        }
        self.access_log.append(log_entry)

        # 限制日志大小
        if len(self.access_log) > 1000:
            self.access_log = self.access_log[-500:]

    def get_access_log(self, limit: int = 50) -> List[Dict]:
        """获取访问日志"""
        return self.access_log[-limit:]


class ConfigValidator:
    """
    配置验证器 - 验证配置的有效性
    """

    def __init__(self):
        self.validators = {}
        self.required_fields = defaultdict(set)

    def add_validator(
        self, section: str, field: str, validator_func: callable, required: bool = False
    ):
        """添加字段验证器"""
        if section not in self.validators:
            self.validators[section] = {}
        self.validators[section][field] = validator_func

        if required:
            self.required_fields[section].add(field)

    def validate(self, config: Dict) -> Dict[str, List[str]]:
        """验证配置"""
        errors = defaultdict(list)

        # 检查必需字段
        for section, required_fields in self.required_fields.items():
            if section not in config:
                errors[section].append(f"缺少必需的节: {section}")
                continue

            section_config = config[section]
            for field in required_fields:
                if field not in section_config:
                    errors[section].append(f"缺少必需字段: {field}")

        # 执行字段验证
        for section, section_validators in self.validators.items():
            if section not in config:
                continue

            section_config = config[section]
            for field, validator in section_validators.items():
                if field in section_config:
                    try:
                        validator(section_config[field])
                    except Exception as e:
                        errors[section].append(f"字段 {field} 验证失败: {str(e)}")

        return dict(errors)

    def register_common_validators(self):
        """注册常用验证器"""
        # 数值验证
        self.add_validator(
            "risk", "max_leverage", lambda x: x > 0 and x <= 10, required=True
        )
        self.add_validator(
            "risk", "max_position_size", lambda x: x > 0 and x <= 1, required=True
        )

        # 数据库验证（可选 - 仅在使用数据库时需要）
        self.add_validator(
            "database",
            "host",
            lambda x: isinstance(x, str) and len(x) > 0,
            required=False,
        )
        self.add_validator(
            "database",
            "port",
            lambda x: isinstance(x, int) and 1 <= x <= 65535,
            required=False,
        )

        # 布尔验证
        self.add_validator(
            "logging", "enabled", lambda x: isinstance(x, bool), required=True
        )


class ConfigVersionManager:
    """
    配置版本管理器 - 管理配置版本和变更历史
    """

    def __init__(self):
        self.versions = OrderedDict()
        self.current_version = None
        self._lock = threading.RLock()

    def create_version(self, config: Dict, description: str = "") -> str:
        """创建新版本"""
        with self._lock:
            version_hash = self._calculate_hash(config)
            timestamp = datetime.datetime.now().isoformat()

            version_info = {
                "hash": version_hash,
                "config": copy.deepcopy(config),
                "description": description,
                "created_at": timestamp,
                "author": "system",
            }

            self.versions[version_hash] = version_info
            self.current_version = version_hash

            # 限制版本数量
            if len(self.versions) > 100:
                # 删除最老的版本
                oldest_key = next(iter(self.versions))
                del self.versions[oldest_key]

            return version_hash

    def get_version(self, version_hash: str) -> Dict:
        """获取指定版本"""
        with self._lock:
            if version_hash not in self.versions:
                raise KeyError(f"版本不存在: {version_hash}")
            return copy.deepcopy(self.versions[version_hash])

    def get_current_version(self) -> Dict:
        """获取当前版本"""
        with self._lock:
            if not self.current_version:
                raise ValueError("没有当前版本")
            return self.get_version(self.current_version)

    def list_versions(self, limit: int = 20) -> List[Dict]:
        """列出版本历史"""
        with self._lock:
            versions_list = list(self.versions.values())
            return versions_list[-limit:]

    def rollback_to_version(self, version_hash: str) -> Dict:
        """回滚到指定版本"""
        with self._lock:
            if version_hash not in self.versions:
                raise KeyError(f"版本不存在: {version_hash}")

            target_config = copy.deepcopy(self.versions[version_hash]["config"])
            new_version = self.create_version(
                target_config, f"回滚到版本 {version_hash}"
            )
            return target_config

    def compare_versions(self, version1: str, version2: str) -> Dict:
        """比较两个版本的差异"""
        with self._lock:
            if version1 not in self.versions or version2 not in self.versions:
                raise KeyError("版本不存在")

            config1 = self.versions[version1]["config"]
            config2 = self.versions[version2]["config"]

            return self._deep_compare(config1, config2)

    def _calculate_hash(self, config: Dict) -> str:
        """计算配置哈希"""
        config_str = json.dumps(config, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def _deep_compare(self, dict1: Dict, dict2: Dict) -> Dict:
        """深度比较两个字典"""
        added = {}
        removed = {}
        modified = {}

        # 找出新增和修改的键
        for key in set(dict1.keys()) | set(dict2.keys()):
            if key not in dict1:
                added[key] = dict2[key]
            elif key not in dict2:
                removed[key] = dict1[key]
            elif dict1[key] != dict2[key]:
                if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                    # 递归比较嵌套字典
                    nested_diff = self._deep_compare(dict1[key], dict2[key])
                    if any(nested_diff.values()):
                        modified[key] = nested_diff
                else:
                    modified[key] = {"from": dict1[key], "to": dict2[key]}

        return {"added": added, "removed": removed, "modified": modified}


class ConfigurationManager:
    """
    配置管理器 - 核心配置管理类
    """

    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.expanduser("~/.backtrader/config")
        self.environment_manager = EnvironmentManager()
        self.crypto_manager = CryptoManager()
        self.secret_manager = SecretManager(self.crypto_manager)
        self.validator = ConfigValidator()
        self.version_manager = ConfigVersionManager()

        # 注册常用验证器
        self.validator.register_common_validators()

        # 当前配置
        self.current_config = {}
        self._config_lock = threading.RLock()
        self._watchers = []

        # 自动加载配置
        self._load_default_configs()

    def _load_default_configs(self):
        """加载默认配置"""
        default_config = {
            "system": {
                "name": "Backtrader Trading System",
                "version": "1.0.0",
                "timezone": "UTC",
            },
            "risk": {
                "max_leverage": 2.0,
                "max_position_size": 0.1,
                "max_daily_loss": 0.05,
            },
            "logging": {"enabled": True, "level": "INFO", "file": "logs/trading.log"},
        }

        self.set_config(default_config, "默认配置")

    def set_config(self, key_or_config, value_or_description=None, description=""):
        """
        设置配置（支持多种用法）

        用法1: set_config({'risk': {'max_leverage': 3.0}}, "描述")  # 完整配置字典
        用法2: set_config('risk', {'max_leverage': 3.0})  # 设置某个section
        用法3: set_config('risk.max_leverage', 3.0)  # 使用点号设置单个值
        """
        with self._config_lock:
            # 判断使用哪种API
            if isinstance(key_or_config, dict):
                # 用法1: 完整配置字典
                config = key_or_config
                desc = value_or_description if value_or_description else description

                # 验证配置
                validation_errors = self.validator.validate(config)
                if validation_errors:
                    error_msg = "配置验证失败:\n"
                    for section, errors in validation_errors.items():
                        error_msg += f"  {section}: {', '.join(errors)}\n"
                    raise ConfigValidationError(error_msg)

                # 创建新版本
                version_hash = self.version_manager.create_version(config, desc)

                # 更新当前配置
                self.current_config = copy.deepcopy(config)

                # 通知监听器
                self._notify_watchers(
                    "config_updated", {"version": version_hash, "description": desc}
                )

                print(f"✅ 配置已更新 (版本: {version_hash[:8]})")

            elif isinstance(key_or_config, str) and value_or_description is not None:
                # 用法2和3: 字符串key
                if '.' in key_or_config:
                    # 用法3: 点号分隔的key
                    parts = key_or_config.split('.', 1)
                    section = parts[0]
                    key = parts[1] if len(parts) > 1 else None
                else:
                    # 用法2: section
                    section = key_or_config
                    key = None

                # 使用update_config来更新
                if key and isinstance(value_or_description, (str, int, float, bool)):
                    # 单个值
                    self.update_config(section, key, value_or_description, description)
                elif isinstance(value_or_description, dict):
                    # 整个section
                    if section not in self.current_config:
                        self.current_config[section] = {}
                    self.current_config[section].update(value_or_description)

                    # 验证更新后的配置
                    validation_errors = self.validator.validate(self.current_config)
                    if validation_errors:
                        error_msg = "配置验证失败:\n"
                        for sect, errors in validation_errors.items():
                            error_msg += f"  {sect}: {', '.join(errors)}\n"
                        raise ConfigValidationError(error_msg)

                    version_hash = self.version_manager.create_version(
                        self.current_config, description or f"更新section: {section}"
                    )
                    print(f"✅ 配置已更新 (版本: {version_hash[:8]})")
            else:
                raise ValueError("Invalid arguments for set_config")

    def get_config(self, key_or_section=None, default=None):
        """
        获取配置值（支持多种用法）

        用法1: get_config()  # 获取全部配置
        用法2: get_config('risk')  # 获取某个section
        用法3: get_config('risk.max_leverage')  # 使用点号获取单个值
        用法4: get_config('risk.max_leverage', default=2.0)  # 带默认值
        """
        with self._config_lock:
            if key_or_section is None:
                return copy.deepcopy(self.current_config)

            # 处理点号分隔的key
            if isinstance(key_or_section, str) and '.' in key_or_section:
                parts = key_or_section.split('.', 1)
                section = parts[0]
                key = parts[1] if len(parts) > 1 else None
            else:
                section = key_or_section
                key = None

            if section not in self.current_config:
                return default

            section_config = self.current_config[section]

            if key is None:
                return copy.deepcopy(section_config)

            return section_config.get(key, default)

    def update_config(self, section: str, key: str, value: Any, description: str = ""):
        """更新配置项"""
        with self._config_lock:
            if section not in self.current_config:
                self.current_config[section] = {}

            self.current_config[section][key] = value

            # 验证更新后的配置
            validation_errors = self.validator.validate(self.current_config)
            if validation_errors:
                # 回滚更改
                if key in self.current_config[section]:
                    del self.current_config[section][key]
                raise ConfigValidationError(f"配置更新验证失败: {validation_errors}")

            # 创建新版本
            version_hash = self.version_manager.create_version(
                self.current_config, f"更新 {section}.{key}: {description}"
            )

            # 通知监听器
            self._notify_watchers(
                "config_item_updated",
                {
                    "section": section,
                    "key": key,
                    "value": value,
                    "version": version_hash,
                },
            )

            print(f"✅ 配置项已更新: {section}.{key}")

    def add_watcher(self, callback: callable):
        """添加配置变更监听器"""
        self._watchers.append(callback)

    def _notify_watchers(self, event_type: str, data: Dict):
        """通知监听器"""
        for watcher in self._watchers:
            try:
                watcher(event_type, data)
            except Exception as e:
                print(f"监听器执行错误: {e}")

    def save_to_file(self, filepath: str = None, format: str = "json"):
        """保存配置到文件"""
        if filepath is None:
            filepath = os.path.join(self.config_dir, f"config.{format}")

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with self._config_lock:
            if format.lower() == "json":
                with open(filepath, "w") as f:
                    json.dump(self.current_config, f, indent=2, default=str)
            elif format.lower() in ["yaml", "yml"]:
                with open(filepath, "w") as f:
                    yaml.dump(self.current_config, f, default_flow_style=False)

    def load_from_file(self, filepath: str, format: str = None):
        """从文件加载配置"""
        if format is None:
            if filepath.endswith(".json"):
                format = "json"
            elif filepath.endswith((".yaml", ".yml")):
                format = "yaml"
            else:
                raise ValueError("无法确定文件格式，请指定format参数")

        if format.lower() == "json":
            with open(filepath, "r") as f:
                config = json.load(f)
        elif format.lower() in ["yaml", "yml"]:
            with open(filepath, "r") as f:
                config = yaml.safe_load(f)

        self.set_config(config, f"从文件加载: {filepath}")

    def get_secret(self, key: str) -> str:
        """获取密钥"""
        return self.secret_manager.retrieve_secret(key)

    def set_secret(self, key: str, value: str, description: str = ""):
        """设置密钥"""
        self.secret_manager.store_secret(key, value, description)

    def list_secrets(self) -> List[Dict]:
        """列出密钥信息"""
        return self.secret_manager.list_secrets()

    def get_version_history(self) -> List[Dict]:
        """获取版本历史"""
        return self.version_manager.list_versions()

    def rollback_config(self, version_hash: str):
        """回滚配置"""
        config = self.version_manager.rollback_to_version(version_hash)
        self.current_config = config
        print(f"✅ 配置已回滚到版本: {version_hash[:8]}")


# 便捷函数
def create_config_manager(config_dir: str = None) -> ConfigurationManager:
    """创建配置管理器实例"""
    return ConfigurationManager(config_dir)


def load_config_from_environment(
    config_manager: ConfigurationManager, env_prefix: str = "BT_"
) -> None:
    """从环境变量加载配置"""
    config_updates = {}

    # 系统配置
    if f"{env_prefix}TIMEZONE" in os.environ:
        config_updates.setdefault("system", {})["timezone"] = os.environ[
            f"{env_prefix}TIMEZONE"
        ]

    # 风控配置
    if f"{env_prefix}MAX_LEVERAGE" in os.environ:
        config_updates.setdefault("risk", {})["max_leverage"] = float(
            os.environ[f"{env_prefix}MAX_LEVERAGE"]
        )

    if f"{env_prefix}MAX_POSITION_SIZE" in os.environ:
        config_updates.setdefault("risk", {})["max_position_size"] = float(
            os.environ[f"{env_prefix}MAX_POSITION_SIZE"]
        )

    # 日志配置
    if f"{env_prefix}LOG_LEVEL" in os.environ:
        config_updates.setdefault("logging", {})["level"] = os.environ[
            f"{env_prefix}LOG_LEVEL"
        ]

    if config_updates:
        config_manager.set_config(config_updates, "从环境变量加载")


# 使用示例
if __name__ == "__main__":
    # 创建配置管理器
    config_mgr = create_config_manager()

    # 设置环境
    config_mgr.environment_manager.set_environment("development")

    # 更新配置
    config_mgr.update_config("risk", "max_leverage", 3.0, "提高最大杠杆")
    config_mgr.update_config("risk", "max_position_size", 0.15, "调整最大仓位")

    # 设置密钥
    config_mgr.set_secret("binance_api_key", "your_api_key_here", "Binance API密钥")
    config_mgr.set_secret("binance_secret", "your_secret_here", "Binance API密钥")

    # 查看当前配置
    print("当前配置:")
    print(json.dumps(config_mgr.get_config(), indent=2))

    # 查看版本历史
    print("\n版本历史:")
    for version in config_mgr.get_version_history():
        print(f"  {version['hash'][:8]} - {version['description']}")

    # 保存配置
    config_mgr.save_to_file("config_backup.json")
