"""
统一集成框架
解决各模块间集成问题，提供统一的模块管理、数据流协调和配置管理
"""

import importlib
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModuleType(Enum):
    """模块类型枚举"""

    RISK_MANAGER = "risk_manager"
    ANALYZER = "analyzer"
    OPTIMIZER = "optimizer"
    DEBUGGER = "debugger"
    PREDICTOR = "predictor"
    POSITION_MANAGER = "position_manager"


@dataclass
class ModuleInfo:
    """模块信息"""

    name: str
    module_type: ModuleType
    version: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    api_version: str = "1.0"


class ModuleRegistry:
    """模块注册中心"""

    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self._instances: Dict[str, Any] = {}

    def register_module(self, module_name: str, module_info: ModuleInfo):
        """注册模块"""
        self._modules[module_name] = module_info
        logger.info(f"注册模块: {module_name} ({module_info.module_type.value})")

    def get_module_info(self, module_name: str) -> Optional[ModuleInfo]:
        """获取模块信息"""
        return self._modules.get(module_name)

    def list_modules(self, module_type: Optional[ModuleType] = None) -> List[str]:
        """列出模块"""
        if module_type:
            return [
                name
                for name, info in self._modules.items()
                if info.module_type == module_type
            ]
        return list(self._modules.keys())

    def create_instance(self, module_name: str, **kwargs) -> Any:
        """创建模块实例"""
        if module_name not in self._modules:
            raise ValueError(f"模块未注册: {module_name}")

        # 动态导入模块
        module_path = (
            f"real_trade.{self._modules[module_name].module_type.value}.{module_name}"
        )
        try:
            module = importlib.import_module(module_path)
            # 查找主要类
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and name.lower().endswith("engine")
                    or name.lower().endswith("manager")
                ):
                    instance = obj(**kwargs)
                    self._instances[module_name] = instance
                    return instance
        except Exception as e:
            logger.error(f"创建模块实例失败: {module_name}, 错误: {e}")
            raise

    def get_instance(self, module_name: str) -> Any:
        """获取模块实例"""
        return self._instances.get(module_name)


class DataManager:
    """统一数据管理器"""

    def __init__(self):
        self._cache = {}
        self._subscriptions = {}

    def publish_data(self, topic: str, data: Any, metadata: Dict = None):
        """发布数据"""
        self._cache[topic] = {
            "data": data,
            "timestamp": datetime.now(),
            "metadata": metadata or {},
        }

        # 通知订阅者
        if topic in self._subscriptions:
            for callback in self._subscriptions[topic]:
                try:
                    callback(data, metadata)
                except Exception as e:
                    logger.error(f"数据回调执行失败: {e}")

    def subscribe(self, topic: str, callback: Callable):
        """订阅数据"""
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
        self._subscriptions[topic].append(callback)

    def get_data(self, topic: str) -> Optional[Any]:
        """获取数据"""
        cached = self._cache.get(topic)
        return cached["data"] if cached else None


class ConfigManager:
    """统一配置管理器"""

    def __init__(self):
        self._configs = {}
        self._defaults = {}

    def set_config(self, module_name: str, config: Dict[str, Any]):
        """设置模块配置"""
        self._configs[module_name] = config

    def get_config(self, module_name: str, key: str = None, default=None):
        """获取配置"""
        config = self._configs.get(module_name, {})
        if key:
            return config.get(key, default)
        return config

    def set_default(self, module_name: str, defaults: Dict[str, Any]):
        """设置默认配置"""
        self._defaults[module_name] = defaults

    def get_effective_config(self, module_name: str) -> Dict[str, Any]:
        """获取生效配置（合并默认配置）"""
        defaults = self._defaults.get(module_name, {})
        user_config = self._configs.get(module_name, {})
        # 用户配置覆盖默认配置
        effective = defaults.copy()
        effective.update(user_config)
        return effective


class IntegrationFramework:
    """主集成框架"""

    def __init__(self):
        self.registry = ModuleRegistry()
        self.data_manager = DataManager()
        self.config_manager = ConfigManager()
        self.logger = logging.getLogger(__name__)

    def initialize_module(self, module_name: str, **kwargs) -> Any:
        """初始化模块"""
        # 获取生效配置
        config = self.config_manager.get_effective_config(module_name)
        config.update(kwargs)

        # 创建实例
        instance = self.registry.create_instance(module_name, **config)

        # 注册数据订阅（如果有data_topic属性）
        if hasattr(instance, "data_topic"):
            self.data_manager.subscribe(instance.data_topic, instance.on_data_update)

        self.logger.info(f"模块初始化完成: {module_name}")
        return instance

    def get_module(self, module_name: str):
        """获取模块实例"""
        return self.registry.get_instance(module_name)

    def publish_global_data(self, topic: str, data: Any, metadata: Dict = None):
        """发布全局数据"""
        self.data_manager.publish_data(topic, data, metadata)

    def subscribe_global_data(self, topic: str, callback: Callable):
        """订阅全局数据"""
        self.data_manager.subscribe(topic, callback)


# 全局集成框架实例
framework = IntegrationFramework()


def register_module_decorator(module_type: ModuleType, version: str = "1.0"):
    """模块注册装饰器"""

    def decorator(cls):
        module_name = cls.__name__.lower().replace("engine", "").replace("manager", "")
        module_info = ModuleInfo(
            name=module_name,
            module_type=module_type,
            version=version,
            description=getattr(cls, "__doc__", "")[0:100] if cls.__doc__ else "",
        )
        framework.registry.register_module(module_name, module_info)
        return cls

    return decorator
