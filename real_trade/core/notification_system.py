#!/usr/bin/env python3
"""
Backtrader标准化通知和信号传递系统
实现统一的消息传递、事件处理和信号广播机制
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List

import backtrader as bt


class SignalType(Enum):
    """信号类型枚举"""

    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"
    ADJUST_POSITION = "ADJUST_POSITION"
    RISK_ALERT = "RISK_ALERT"
    MARKET_REGIME_CHANGE = "MARKET_REGIME_CHANGE"


class NotificationType(Enum):
    """通知类型枚举"""

    ORDER_STATUS = "ORDER_STATUS"
    TRADE_EXECUTION = "TRADE_EXECUTION"
    RISK_VIOLATION = "RISK_VIOLATION"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    SYSTEM_EVENT = "SYSTEM_EVENT"


@dataclass
class TradingSignal:
    """交易信号数据类"""

    signal_type: SignalType
    data: bt.DataBase
    confidence: float
    strength: float  # 信号强度 0-1
    timestamp: datetime
    strategy_name: str
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "signal_type": self.signal_type.value,
            "data_name": self.data._name,
            "confidence": self.confidence,
            "strength": self.strength,
            "timestamp": self.timestamp.isoformat(),
            "strategy_name": self.strategy_name,
            "metadata": self.metadata or {},
        }


@dataclass
class SystemNotification:
    """系统通知数据类"""

    notification_type: NotificationType
    level: str  # INFO, WARNING, ERROR, CRITICAL
    message: str
    timestamp: datetime
    source: str  # 发送方标识
    data: Dict[str, Any] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "notification_type": self.notification_type.value,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data or {},
        }


class SignalBroadcaster:
    """信号广播器 - 实现发布-订阅模式"""

    def __init__(self):
        self._subscribers: Dict[SignalType, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
        self.logger = logging.getLogger(__name__)

    def subscribe(self, signal_type: SignalType, callback: Callable):
        """订阅特定类型的信号"""
        if signal_type not in self._subscribers:
            self._subscribers[signal_type] = []
        self._subscribers[signal_type].append(callback)
        self.logger.info(f"订阅信号: {signal_type.value}")

    def subscribe_all(self, callback: Callable):
        """订阅所有信号"""
        self._global_subscribers.append(callback)
        self.logger.info("订阅所有信号")

    def unsubscribe(self, signal_type: SignalType, callback: Callable):
        """取消订阅"""
        if signal_type in self._subscribers:
            try:
                self._subscribers[signal_type].remove(callback)
                self.logger.info(f"取消订阅信号: {signal_type.value}")
            except ValueError:
                pass

    def broadcast(self, signal: TradingSignal):
        """广播信号"""
        # 通知特定类型订阅者
        if signal.signal_type in self._subscribers:
            for callback in self._subscribers[signal.signal_type]:
                try:
                    callback(signal)
                except Exception as e:
                    self.logger.error(f"信号回调执行失败: {e}")

        # 通知全局订阅者
        for callback in self._global_subscribers:
            try:
                callback(signal)
            except Exception as e:
                self.logger.error(f"全局信号回调执行失败: {e}")

        self.logger.info(
            f"广播信号: {signal.signal_type.value}, 置信度: {signal.confidence:.2f}"
        )


class NotificationManager:
    """通知管理器"""

    def __init__(self):
        self._handlers: Dict[NotificationType, List[Callable]] = {}
        self._global_handlers: List[Callable] = []
        self.logger = logging.getLogger(__name__)

    def register_handler(self, notification_type: NotificationType, handler: Callable):
        """注册通知处理器"""
        if notification_type not in self._handlers:
            self._handlers[notification_type] = []
        self._handlers[notification_type].append(handler)
        self.logger.info(f"注册通知处理器: {notification_type.value}")

    def register_global_handler(self, handler: Callable):
        """注册全局通知处理器"""
        self._global_handlers.append(handler)
        self.logger.info("注册全局通知处理器")

    def notify(self, notification: SystemNotification):
        """发送通知"""
        # 特定类型处理器
        if notification.notification_type in self._handlers:
            for handler in self._handlers[notification.notification_type]:
                try:
                    handler(notification)
                except Exception as e:
                    self.logger.error(f"通知处理器执行失败: {e}")

        # 全局处理器
        for handler in self._global_handlers:
            try:
                handler(notification)
            except Exception as e:
                self.logger.error(f"全局通知处理器执行失败: {e}")

        # 日志记录
        log_method = getattr(self.logger, notification.level.lower(), self.logger.info)
        log_method(f"[{notification.source}] {notification.message}")


class IntegratedNotificationMixin:
    """集成通知混入类 - 为策略提供标准通知功能"""

    def __init__(self):
        super().__init__()
        self.signal_broadcaster = SignalBroadcaster()
        self.notification_manager = NotificationManager()
        self._signal_buffer = []  # 信号缓冲区

    def emit_signal(
        self,
        signal_type: SignalType,
        data: bt.DataBase,
        confidence: float,
        strength: float = 1.0,
        metadata: Dict = None,
    ) -> TradingSignal:
        """发出交易信号"""
        signal = TradingSignal(
            signal_type=signal_type,
            data=data,
            confidence=confidence,
            strength=strength,
            timestamp=self.datetime.datetime(),
            strategy_name=self.__class__.__name__,
            metadata=metadata or {},
        )

        # 广播信号
        self.signal_broadcaster.broadcast(signal)

        # 发送通知
        notification = SystemNotification(
            notification_type=NotificationType.SIGNAL_GENERATED,
            level="INFO",
            message=f"生成{signal_type.value}信号，置信度{confidence:.2f}",
            timestamp=signal.timestamp,
            source=self.__class__.__name__,
            data=signal.to_dict(),
        )
        self.notification_manager.notify(notification)

        return signal

    def emit_notification(
        self,
        notification_type: NotificationType,
        level: str,
        message: str,
        data: Dict = None,
    ):
        """发出系统通知"""
        notification = SystemNotification(
            notification_type=notification_type,
            level=level,
            message=message,
            timestamp=self.datetime.datetime(),
            source=self.__class__.__name__,
            data=data or {},
        )
        self.notification_manager.notify(notification)

    def subscribe_to_signals(self, signal_type: SignalType, callback: Callable):
        """订阅信号"""
        self.signal_broadcaster.subscribe(signal_type, callback)

    def subscribe_to_all_signals(self, callback: Callable):
        """订阅所有信号"""
        self.signal_broadcaster.subscribe_all(callback)

    def register_notification_handler(
        self, notification_type: NotificationType, handler: Callable
    ):
        """注册通知处理器"""
        self.notification_manager.register_handler(notification_type, handler)

    def register_global_notification_handler(self, handler: Callable):
        """注册全局通知处理器"""
        self.notification_manager.register_global_handler(handler)


# 便捷的装饰器
def signal_handler(signal_types: List[SignalType] = None):
    """信号处理装饰器"""

    def decorator(func):
        func._signal_handler = True
        func._signal_types = signal_types or list(SignalType)
        return func

    return decorator


def notification_handler(notification_types: List[NotificationType] = None):
    """通知处理装饰器"""

    def decorator(func):
        func._notification_handler = True
        func._notification_types = notification_types or list(NotificationType)
        return func

    return decorator


# 预定义的通知处理器
class ConsoleNotificationHandler:
    """控制台通知处理器"""

    @staticmethod
    def handle_notification(notification: SystemNotification):
        """处理通知并打印到控制台"""
        timestamp = notification.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[{timestamp}] [{notification.level}] [{notification.source}] "
            f"{notification.message}"
        )


class FileNotificationHandler:
    """文件通知处理器"""

    def __init__(self, log_file: str):
        self.log_file = log_file

    def handle_notification(self, notification: SystemNotification):
        """处理通知并写入文件"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                log_entry = {
                    "timestamp": notification.timestamp.isoformat(),
                    "level": notification.level,
                    "source": notification.source,
                    "message": notification.message,
                    "type": notification.notification_type.value,
                    "data": notification.data,
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"写入日志文件失败: {e}")
