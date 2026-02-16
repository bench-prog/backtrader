#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级事前风控引擎 (Pre-Trade Risk Engine)
基于backtrader架构的企业级风险管理模块

核心功能：
1. 订单预检查系统
2. 资金充足性验证
3. 杠杆率限制检查
4. 集中度风险检查
5. 市场冲击成本估算
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
from collections import defaultdict

import backtrader as bt


class PreTradeRiskEngine(object):
    """
    事前风控引擎 - 在订单提交前进行全方位风险检查

    自动从全局配置获取参数，无需手动配置
    """

    def __init__(self, broker):
        """
        初始化风控引擎

        Args:
            broker: Broker 实例（可以是 Cerebro 或 Broker）
        """
        # 兼容旧版接口：如果传入 cerebro，从中获取 broker
        if hasattr(broker, 'broker'):
            self.cerebro = broker
            self.broker = broker.broker
        else:
            self.broker = broker
            self.cerebro = None

        # 风控配置参数（默认值）
        self.config = {
            "max_leverage": 2.0,  # 最大杠杆率
            "max_position_concentration": 0.3,  # 单品种最大仓位占比
            "max_daily_loss_limit": 0.05,  # 日最大亏损限制
            "max_order_size_ratio": 0.1,  # 单笔订单最大资金占比
            "market_impact_threshold": 0.02,  # 市场冲击成本阈值
            "enable_fund_sufficiency_check": True,  # 资金充足性检查
            "enable_leverage_check": True,  # 杠杆检查
            "enable_concentration_check": True,  # 集中度检查
        }

        # 尝试从全局配置加载（延迟导入避免循环依赖）
        self._load_config_from_global()

        # 风控状态跟踪
        self.daily_losses = defaultdict(float)  # 按日期跟踪亏损
        self.position_values = {}  # 各品种持仓市值
        self.last_check_date = None

        # 风控统计
        self.risk_checks_passed = 0
        self.risk_checks_failed = 0
        self.rejected_orders = []

    def _load_config_from_global(self):
        """从全局配置加载风控参数（延迟导入）"""
        try:
            from backtrader.config import get_config_manager
            config_mgr = get_config_manager()
            risk_config = config_mgr.get_config('risk', {})
            if risk_config:
                self.config.update(risk_config)
        except:
            pass  # 配置不存在时使用默认值

    def configure(self, **kwargs):
        """配置风控参数"""
        self.config.update(kwargs)

    def check_order(self, order):
        """
        订单预检查主入口
        返回: (allowed: bool, reason: str)
        """
        checks = [
            self._check_fund_sufficiency,
            self._check_leverage_limit,
            self._check_position_concentration,
            self._check_daily_loss_limit,
            self._check_order_size_limit,
            self._check_market_impact,
        ]

        for check_func in checks:
            if self.config.get(f"enable_{check_func.__name__[6:]}", True):
                allowed, reason = check_func(order)
                if not allowed:
                    self.risk_checks_failed += 1
                    self.rejected_orders.append(
                        {
                            "timestamp": datetime.datetime.now(),
                            "order": order,
                            "reason": reason,
                        }
                    )
                    return False, reason

        self.risk_checks_passed += 1
        return True, "风控检查通过"

    def _check_fund_sufficiency(self, order):
        """资金充足性检查"""
        if not self.config["enable_fund_sufficiency_check"]:
            return True, ""

        required_margin = self._calculate_required_margin(order)
        available_cash = self.broker.getcash()

        if required_margin > available_cash:
            return (
                False,
                f"资金不足: 需要 {required_margin:.2f}, 可用 {available_cash:.2f}",
            )

        return True, ""

    def _check_leverage_limit(self, order):
        """杠杆率限制检查"""
        if not self.config["enable_leverage_check"]:
            return True, ""

        current_leverage = self._calculate_current_leverage()
        max_leverage = self.config["max_leverage"]

        if current_leverage >= max_leverage:
            return False, f"杠杆超限: 当前 {current_leverage:.2f}, 最大 {max_leverage}"

        return True, ""

    def _check_position_concentration(self, order):
        """持仓集中度检查"""
        if not self.config["enable_concentration_check"]:
            return True, ""

        # 计算新持仓后的集中度
        new_position_value = self._calculate_position_value_after_order(order)
        total_portfolio_value = self.broker.getvalue()
        concentration = new_position_value / total_portfolio_value

        max_concentration = self.config["max_position_concentration"]
        if concentration > max_concentration:
            return (
                False,
                f"持仓集中度过高: {concentration:.2%}, 限制 {max_concentration:.2%}",
            )

        return True, ""

    def _check_daily_loss_limit(self, order):
        """日亏损限制检查"""
        today = datetime.date.today()

        # 重置每日统计
        if self.last_check_date != today:
            self.daily_losses[today] = 0
            self.last_check_date = today

        # 预估此订单可能带来的亏损
        estimated_loss = self._estimate_order_loss(order)
        projected_daily_loss = self.daily_losses[today] + estimated_loss

        max_daily_loss = self.broker.getvalue() * self.config["max_daily_loss_limit"]
        if projected_daily_loss > max_daily_loss:
            return (
                False,
                f"预计日亏损超限: 预计 {projected_daily_loss:.2f}, 限制 {max_daily_loss:.2f}",
            )

        return True, ""

    def _calculate_required_margin(self, order):
        """计算所需保证金"""
        # 获取订单价格，如果未指定则使用当前收盘价
        price = order.price if order.price else order.data.close[0]
        # 简化计算：假设现货交易，所需资金 = 订单金额
        return abs(order.size * price)

    def _calculate_current_leverage(self):
        """计算当前杠杆率"""
        total_value = self.broker.getvalue()
        cash = self.broker.getcash()
        if cash <= 0:
            return float("inf")
        return total_value / cash

    def _calculate_position_value_after_order(self, order):
        """计算下单后的持仓价值"""
        current_position = self.broker.getposition(order.data)
        new_size = current_position.size + order.size
        price = order.price if order.price else order.data.close[0]
        return abs(new_size * price)

    def _estimate_order_loss(self, order):
        """预估订单可能的亏损"""
        # 简化估计：假设最大可能亏损为订单金额
        price = order.price if order.price else order.data.close[0]
        return abs(order.size * price) * 0.1  # 假设最多亏损10%

    def _check_order_size_limit(self, order):
        """订单规模限制检查"""
        price = order.price if order.price else order.data.close[0]
        order_value = abs(order.size * price)
        total_value = self.broker.getvalue()
        order_ratio = order_value / total_value

        max_ratio = self.config["max_order_size_ratio"]
        if order_ratio > max_ratio:
            return False, f"订单规模过大: 占比 {order_ratio:.2%}, 限制 {max_ratio:.2%}"

        return True, ""

    def _check_market_impact(self, order):
        """市场冲击成本检查"""
        impact_cost = self._calculate_market_impact(order)

        if impact_cost > self.config["market_impact_threshold"]:
            return (
                False,
                f"市场冲击成本过高: {impact_cost:.2%}, 阈值 {self.config['market_impact_threshold']:.2%}",
            )

        return True, ""

    def _calculate_market_impact(self, order):
        """计算市场冲击成本"""
        # 简化模型：基于订单规模相对于市场流动性的比例
        price = order.price if order.price else order.data.close[0]
        order_value = abs(order.size * price)
        # 假设市场日交易量为持仓价值的10倍
        market_volume = self.broker.getvalue() * 10
        return order_value / market_volume if market_volume > 0 else 0

    def get_statistics(self):
        """获取风控统计信息"""
        total_checks = self.risk_checks_passed + self.risk_checks_failed
        pass_rate = self.risk_checks_passed / total_checks if total_checks > 0 else 0

        return {
            "total_checks": total_checks,
            "passed": self.risk_checks_passed,
            "failed": self.risk_checks_failed,
            "pass_rate": pass_rate,
            "rejected_orders_count": len(self.rejected_orders),
            "current_leverage": self._calculate_current_leverage(),
            "config": self.config.copy(),
        }

    def reset_daily_stats(self):
        """重置每日统计数据"""
        today = datetime.date.today()
        self.daily_losses[today] = 0
        self.last_check_date = today


class RiskAwareBroker(bt.brokers.BackBroker):
    """
    风控感知型Broker - 集成事前风控引擎

    自动集成配置管理和告警系统，无需手动传参
    """

    def __init__(self):
        super(RiskAwareBroker, self).__init__()
        # 延迟初始化风控引擎
        self._risk_engine = None
        self._initialized = False

    @property
    def risk_engine(self):
        """延迟初始化风控引擎"""
        if self._risk_engine is None:
            # 创建风控引擎（需要 cerebro，所以在第一次访问时创建）
            self._risk_engine = PreTradeRiskEngine(self)

            # 尝试从全局配置加载风控参数
            try:
                from backtrader.config import get_config_manager
                config_mgr = get_config_manager()
                risk_config = config_mgr.get_config('risk', {})
                if risk_config:
                    self._risk_engine.configure(**risk_config)
            except:
                pass  # 配置不存在时使用默认值

        return self._risk_engine

    def set_risk_engine(self, risk_engine):
        """设置风控引擎"""
        self._risk_engine = risk_engine

    def submit(self, order, check=True):
        """
        提交订单 - 集成风控检查

        Args:
            order: 订单对象
            check: 是否执行风控检查（默认 True）
        """
        if check and self.risk_engine:
            allowed, reason = self.risk_engine.check_order(order)
            if not allowed:
                # 订单被风控拒绝
                order.reject(self)

                # 触发告警（如果配置了告警系统）
                try:
                    from backtrader.monitoring import get_alert_manager
                    alert_mgr = get_alert_manager()
                    from backtrader.monitoring.alerting_system import Alert
                    alert_mgr.send_alert(Alert(
                        level='WARNING',
                        title='订单被风控拒绝',
                        message=f'订单 {order.ref} 被拒绝: {reason}',
                        context={'order': order, 'reason': reason}
                    ))
                except:
                    pass  # 告警系统未配置时静默失败

                self.notify(order)
                return order

        # 通过风控检查，正常提交
        return super(RiskAwareBroker, self).submit(order)


def integrate_pre_trade_risk_engine(cerebro, **risk_config):
    """
    集成事前风控引擎到Cerebro

    使用示例:
    cerebro = bt.Cerebro()
    integrate_pre_trade_risk_engine(cerebro,
        max_leverage=2.0,
        max_position_concentration=0.3,
        max_daily_loss_limit=0.05
    )
    """
    # 创建风控感知型Broker
    risk_broker = RiskAwareBroker()
    cerebro.setbroker(risk_broker)

    # 创建并配置风控引擎
    risk_engine = PreTradeRiskEngine(cerebro)
    if risk_config:
        risk_engine.configure(**risk_config)

    # 关联风控引擎
    risk_broker.set_risk_engine(risk_engine)

    return risk_engine


# 便捷的风控装饰器
def risk_controlled(max_leverage=None, max_concentration=None, daily_loss_limit=None):
    """
    策略风控装饰器 - 为策略添加风控约束

    使用示例:
    @risk_controlled(max_leverage=2.0, max_concentration=0.3)
    class MyStrategy(bt.Strategy):
        pass
    """

    def decorator(strategy_class):
        original_init = strategy_class.__init__

        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            # 在策略初始化时配置风控
            if hasattr(self, "cerebro") and self.cerebro.broker.risk_engine:
                config = {}
                if max_leverage:
                    config["max_leverage"] = max_leverage
                if max_concentration:
                    config["max_position_concentration"] = max_concentration
                if daily_loss_limit:
                    config["max_daily_loss_limit"] = daily_loss_limit
                if config:
                    self.cerebro.broker.risk_engine.configure(**config)

        strategy_class.__init__ = new_init
        return strategy_class

    return decorator
