#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级日志增强系统 (Enterprise Logging Enhancement)
基于Loguru的结构化日志解决方案

核心功能：
1. 结构化日志记录
2. 多级别日志分离
3. 自动轮转和保留
4. JSON序列化支持
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import threading
from typing import Dict

from loguru import logger

import backtrader as bt


class TradingLogger:
    """
    交易日志管理器
    """

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self._configured = False
        self._lock = threading.RLock()

        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)

    def setup(self, retention_days: int = 30, rotation_time: str = "00:00"):
        """
        设置日志配置

        Args:
            retention_days: 日志保留天数
            rotation_time: 轮转时间 (HH:MM格式)
        """
        with self._lock:
            if self._configured:
                return

            # 移除默认的日志处理器
            logger.remove()

            # 主日志文件 - 包含所有级别
            logger.add(
                f"{self.log_dir}/trading_{{time:YYYY-MM-DD}}.log",
                rotation=rotation_time,
                retention=f"{retention_days} days",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
                level="DEBUG",
                enqueue=True,  # 线程安全
                serialize=False,
            )

            # 错误日志文件 - 仅包含ERROR及以上级别
            logger.add(
                f"{self.log_dir}/error_{{time:YYYY-MM-DD}}.log",
                rotation=rotation_time,
                retention=f"{retention_days} days",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
                level="ERROR",
                enqueue=True,
            )

            # 订单专用日志
            logger.add(
                f"{self.log_dir}/orders_{{time:YYYY-MM-DD}}.log",
                rotation=rotation_time,
                retention=f"{retention_days} days",
                format="{time:YYYY-MM-DD HH:mm:ss} | ORDER | {extra[symbol]} | {extra[action]} | {extra[price]} | {extra[size]}",
                filter=lambda record: "order" in record["extra"],
                enqueue=True,
            )

            # 风控日志
            logger.add(
                f"{self.log_dir}/risk_{{time:YYYY-MM-DD}}.log",
                rotation=rotation_time,
                retention=f"{retention_days} days",
                format="{time:YYYY-MM-DD HH:mm:ss} | RISK | {extra[check_type]} | {extra[result]} | {extra[details]}",
                filter=lambda record: "risk" in record["extra"],
                enqueue=True,
            )

            # JSON格式日志（用于ELK等系统）
            logger.add(
                f"{self.log_dir}/structured_{{time:YYYY-MM-DD}}.json",
                rotation=rotation_time,
                retention=f"{retention_days} days",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
                serialize=True,
                enqueue=True,
            )

            self._configured = True
            print(f"✅ 日志系统已配置，日志目录: {self.log_dir}")

    def log_order(
        self, symbol: str, action: str, price: float, size: float, order_ref: str = None
    ):
        """
        记录订单日志

        Args:
            symbol: 交易对
            action: 操作类型 (BUY/SELL)
            price: 价格
            size: 数量
            order_ref: 订单引用号
        """
        logger.bind(
            order=True,
            symbol=symbol,
            action=action,
            price=price,
            size=size,
            order_ref=order_ref,
        ).info("订单执行")

    def log_risk_check(self, check_type: str, result: str, details: Dict = None):
        """
        记录风控检查日志

        Args:
            check_type: 检查类型
            result: 检查结果 (PASS/FAIL)
            details: 详细信息
        """
        logger.bind(
            risk=True,
            check_type=check_type,
            result=result,
            details=json.dumps(details or {}, ensure_ascii=False),
        ).info("风控检查")

    def log_strategy_event(
        self, event_type: str, strategy_name: str, details: Dict = None
    ):
        """
        记录策略事件日志

        Args:
            event_type: 事件类型
            strategy_name: 策略名称
            details: 详细信息
        """
        logger.bind(
            strategy=True,
            event_type=event_type,
            strategy_name=strategy_name,
            details=json.dumps(details or {}, ensure_ascii=False),
        ).info("策略事件")

    def log_performance(self, metrics: Dict):
        """
        记录性能指标日志

        Args:
            metrics: 性能指标字典
        """
        logger.bind(
            performance=True, metrics=json.dumps(metrics, ensure_ascii=False)
        ).info("性能指标")


# 全局日志管理器实例
_global_logger = None
_logger_lock = threading.RLock()


def get_trading_logger(log_dir: str = "logs") -> TradingLogger:
    """
    获取全局交易日志管理器（单例模式）

    Args:
        log_dir: 日志目录

    Returns:
        TradingLogger: 日志管理器实例
    """
    global _global_logger

    with _logger_lock:
        if _global_logger is None:
            _global_logger = TradingLogger(log_dir)
        return _global_logger


def setup_trading_logger(
    log_dir: str = "logs", retention_days: int = 30, rotation_time: str = "00:00"
) -> TradingLogger:
    """
    设置交易日志系统（符合P0集成规范）

    Args:
        log_dir: 日志目录
        retention_days: 保留天数
        rotation_time: 轮转时间

    Returns:
        TradingLogger: 日志管理器实例
    """
    trading_logger = get_trading_logger(log_dir)
    trading_logger.setup(retention_days, rotation_time)

    # 将loguru logger附加到cerebro命名空间以便访问
    bt.logger = logger
    bt.trading_logger = trading_logger

    print("✅ 日志增强功能已启用")
    return trading_logger


def log_order_execution(
    symbol: str, action: str, price: float, size: float, order_ref: str = None
):
    """
    快捷订单日志函数

    Args:
        symbol: 交易对
        action: 操作类型
        price: 价格
        size: 数量
        order_ref: 订单引用
    """
    trading_logger = get_trading_logger()
    if trading_logger._configured:
        trading_logger.log_order(symbol, action, price, size, order_ref)


def log_risk_event(check_type: str, result: str, details: Dict = None):
    """
    快捷风控日志函数

    Args:
        check_type: 检查类型
        result: 检查结果
        details: 详细信息
    """
    trading_logger = get_trading_logger()
    if trading_logger._configured:
        trading_logger.log_risk_check(check_type, result, details)


# Backtrader Strategy Mixin
class LoggingStrategyMixin:
    """
    策略日志混入类 - 为策略添加自动日志功能
    """

    def __init__(self):
        super(LoggingStrategyMixin, self).__init__()
        self.trading_logger = get_trading_logger()

    def log(self, txt, dt=None):
        """增强的日志函数"""
        dt = dt or self.datas[0].datetime.date(0)
        logger.info(f"{dt.isoformat()} - {txt}")

    def notify_order(self, order):
        """自动记录订单通知"""
        super(LoggingStrategyMixin, self).notify_order(order)

        if order.status in [order.Completed]:
            if order.isbuy():
                action = "BUY"
            else:
                action = "SELL"

            log_order_execution(
                symbol=getattr(self.datas[0], "_name", "UNKNOWN"),
                action=action,
                price=order.executed.price,
                size=order.executed.size,
                order_ref=str(order.ref),
            )

    def notify_trade(self, trade):
        """自动记录交易通知"""
        super(LoggingStrategyMixin, self).notify_trade(trade)

        if trade.isclosed:
            logger.bind(
                trade=True, pnl=trade.pnl, pnlcomm=trade.pnlcomm, duration=trade.barlen
            ).info("交易完成")


# 使用示例
if __name__ == "__main__":
    # 设置日志系统
    trading_logger = setup_trading_logger()

    # 记录不同类型日志
    logger.info("系统启动")
    logger.warning("这是一个警告")
    logger.error("这是一个错误")

    # 记录订单日志
    log_order_execution("BTC/USDT", "BUY", 45000.0, 0.001)

    # 记录风控日志
    log_risk_event("leverage_check", "PASS", {"leverage": 2.0, "limit": 3.0})

    # 记录性能指标
    trading_logger.log_performance(
        {"sharpe_ratio": 1.5, "max_drawdown": 0.08, "win_rate": 0.65}
    )

    print("✅ 日志系统测试完成")
