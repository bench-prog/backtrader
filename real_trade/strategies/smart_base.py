#!/usr/bin/env python3
"""
Backtrader智能交易策略基类
集成所有高级分析功能的标准策略模板
"""

import logging
from typing import Dict

import backtrader as bt

# 导入我们的分析器和通知系统
from ..analyzers.dynamic_risk_analyzer import DynamicRiskAnalyzer
from ..analyzers.market_state_analyzer import MarketStateAnalyzer, MarketStateFilter
from ..core.notification_system import (
    IntegratedNotificationMixin,
    NotificationType,
    SignalType,
)


class SmartTradingStrategy(bt.Strategy, IntegratedNotificationMixin):
    """
    智能交易策略基类
    集成动态风险管理、市场状态分析、自适应止损等高级功能
    """

    params = (
        # 基础参数
        ("printlog", True),
        ("debug_mode", False),
        # 风险管理参数
        ("max_risk_per_trade", 0.02),  # 单笔最大风险
        ("max_portfolio_risk", 0.10),  # 组合最大风险
        ("max_drawdown_limit", 0.15),  # 最大回撤限制
        # 信号过滤参数
        ("min_signal_confidence", 0.7),  # 最小信号置信度
        ("enable_market_filter", True),  # 是否启用市场状态过滤
        # 止损止盈参数
        ("stop_loss_multiplier", 2.0),  # 止损倍数
        ("take_profit_multiplier", 3.0),  # 止盈倍数
        ("trailing_stop_enabled", True),  # 是否启用移动止损
    )

    def __init__(self):
        """初始化策略"""
        super().__init__()
        IntegratedNotificationMixin.__init__(self)

        # 设置日志
        self.logger = logging.getLogger(self.__class__.__name__)

        # 初始化分析器引用
        self.risk_analyzer = None
        self.market_analyzer = None
        self.market_filter = None

        # 订单和位置跟踪
        self.active_orders = {}  # order_ref -> order_info
        self.position_tracking = {}  # data -> position_info
        self.stop_losses = {}  # data -> stop_loss_price
        self.take_profits = {}  # data -> take_profit_price

        # 性能统计
        self.trade_count = 0
        self.win_count = 0
        self.total_pnl = 0.0
        self.max_equity = self.broker.getvalue()
        self.start_value = self.broker.getvalue()

        # 信号缓冲区
        self.pending_signals = []  # 待处理的信号

    def log(self, txt: str, level: str = "INFO"):
        """日志记录"""
        if self.p.printlog:
            timestamp = self.datetime.datetime().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} | {level} | {txt}")

        if self.p.debug_mode:
            getattr(self.logger, level.lower())(txt)

    def notify_analyzer(self, analyzer):
        """分析器通知回调"""
        # 关联分析器
        if isinstance(analyzer, DynamicRiskAnalyzer):
            self.risk_analyzer = analyzer
        elif isinstance(analyzer, MarketStateAnalyzer):
            self.market_analyzer = analyzer
            self.market_filter = MarketStateFilter(analyzer)

    def notify_order(self, order):
        """订单状态变化通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，无需处理
            return

        order_info = self.active_orders.get(order.ref)
        if not order_info:
            return

        data_name = order.data._name
        executed_price = order.executed.price
        executed_size = order.executed.size
        executed_value = order.executed.value
        executed_comm = order.executed.comm

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"买入执行: {data_name}, 价格={executed_price:.2f}, 数量={executed_size}"
                )
                # 设置止损和止盈
                self._set_stop_loss_take_profit(order.data, executed_price, "BUY")
            else:
                self.log(
                    f"卖出执行: {data_name}, 价格={executed_price:.2f}, 数量={executed_size}"
                )
                pnl = (
                    executed_value
                    - order_info["cost"]
                    - executed_comm
                    - order_info["commission"]
                )
                self.total_pnl += pnl
                if pnl > 0:
                    self.win_count += 1
                self.trade_count += 1

            # 清理已完成订单
            del self.active_orders[order.ref]

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            status_text = {
                order.Canceled: "取消",
                order.Margin: "保证金不足",
                order.Rejected: "拒绝",
            }[order.status]
            self.log(f"订单{status_text}: {data_name}", "WARNING")
            if order.ref in self.active_orders:
                del self.active_orders[order.ref]

    def notify_trade(self, trade):
        """交易完成通知"""
        if trade.isclosed:
            self.log(
                f"交易关闭: {trade.data._name}, "
                f"毛利={trade.pnl:.2f}, 净利={trade.pnlcomm:.2f}"
            )

    def next(self):
        """主逻辑循环"""
        # 更新最高权益
        current_value = self.broker.getvalue()
        self.max_equity = max(self.max_equity, current_value)

        # 检查风险限制
        if not self._check_risk_limits():
            return

        # 更新止损
        self._update_trailing_stops()

        # 处理待定信号
        self._process_pending_signals()

        # 生成新信号（由子类实现）
        self.generate_signals()

    def _check_risk_limits(self) -> bool:
        """检查风险限制"""
        if not self.risk_analyzer:
            return True

        analysis = self.risk_analyzer.get_analysis()

        # 检查最大回撤
        if analysis["max_drawdown"] > self.p.max_drawdown_limit:
            self.log(f"超过最大回撤限制: {analysis['max_drawdown']:.2%}", "WARNING")
            return False

        # 检查当前风险水平
        if analysis["risk_level"] == "HIGH":
            self.log("当前风险水平过高，暂停新交易", "WARNING")
            return False

        return True

    def _set_stop_loss_take_profit(self, data, entry_price: float, direction: str):
        """设置止损和止盈"""
        if not self.risk_analyzer:
            return

        # 获取波动率
        analysis = self.risk_analyzer.get_analysis()
        volatility = analysis.get("current_volatility", 0.02)

        # 计算止损止盈价格
        if direction == "BUY":
            stop_loss = entry_price * (1 - self.p.stop_loss_multiplier * volatility)
            take_profit = entry_price * (1 + self.p.take_profit_multiplier * volatility)
        else:
            stop_loss = entry_price * (1 + self.p.stop_loss_multiplier * volatility)
            take_profit = entry_price * (1 - self.p.take_profit_multiplier * volatility)

        self.stop_losses[data] = stop_loss
        self.take_profits[data] = take_profit

        self.log(f"设置止损: {stop_loss:.2f}, 止盈: {take_profit:.2f}")

    def _update_trailing_stops(self):
        """更新移动止损"""
        if not self.p.trailing_stop_enabled:
            return

        for data, stop_loss in self.stop_losses.items():
            position = self.getposition(data)
            if not position or position.size == 0:
                continue

            current_price = data.close[0]

            # 更新多头移动止损
            if position.size > 0 and current_price > position.price:
                new_stop = current_price * (1 - self.p.stop_loss_multiplier * 0.02)
                if new_stop > stop_loss:
                    self.stop_losses[data] = new_stop
                    self.log(f"更新移动止损: {new_stop:.2f}")

            # 更新空头移动止损
            elif position.size < 0 and current_price < position.price:
                new_stop = current_price * (1 + self.p.stop_loss_multiplier * 0.02)
                if new_stop < stop_loss:
                    self.stop_losses[data] = new_stop
                    self.log(f"更新移动止损: {new_stop:.2f}")

    def _process_pending_signals(self):
        """处理待定信号"""
        executed_signals = []

        for signal in self.pending_signals:
            if self._execute_signal(signal):
                executed_signals.append(signal)

        # 移除已执行的信号
        for signal in executed_signals:
            self.pending_signals.remove(signal)

    def _execute_signal(self, signal: Dict) -> bool:
        """执行交易信号"""
        data = signal["data"]
        signal_type = signal["type"]
        confidence = signal["confidence"]

        # 市场状态过滤
        if self.p.enable_market_filter and self.market_filter:
            should_execute, adjusted_confidence = self.market_filter.filter_signal(
                signal_type, confidence
            )
            if not should_execute:
                return False
            confidence = adjusted_confidence

        # 置信度过滤
        if confidence < self.p.min_signal_confidence:
            return False

        # 风险调整仓位
        size = self._calculate_position_size(data, signal_type, confidence)
        if size == 0:
            return False

        # 执行交易
        if signal_type == "BUY":
            order = self.buy(data=data, size=size)
            self.emit_notification(
                NotificationType.ORDER_STATUS,
                "INFO",
                f"发出买单，数量={size}，价格≈{data.close[0]:.2f}",
            )
        elif signal_type == "SELL":
            order = self.sell(data=data, size=size)
            self.emit_notification(
                NotificationType.ORDER_STATUS,
                "INFO",
                f"发出卖单，数量={size}，价格≈{data.close[0]:.2f}",
            )
        else:
            return False

        # 记录订单
        self.active_orders[order.ref] = {
            "signal": signal,
            "cost": abs(size * data.close[0]),
            "commission": 0.0,
        }

        self.log(f"执行信号: {signal_type}, 置信度={confidence:.2f}, 仓位={size}")
        return True

    def _calculate_position_size(
        self, data, signal_type: str, confidence: float
    ) -> int:
        """计算仓位大小"""
        available_cash = self.broker.getcash()
        current_price = data.close[0]

        # 基础仓位计算
        base_risk = self.p.max_risk_per_trade * confidence
        position_value = self.broker.getvalue() * base_risk
        size = int(position_value / current_price)

        # 确保不超过可用资金
        max_affordable = int(available_cash * 0.95 / current_price)
        size = min(size, max_affordable)

        # 确保符合最小交易单位
        if size <= 0:
            return 0

        return size

    def add_signal(
        self, data, signal_type: str, confidence: float, metadata: Dict = None
    ):
        """添加交易信号"""
        # 转换信号类型
        signal_enum = {"BUY": SignalType.BUY, "SELL": SignalType.SELL}.get(
            signal_type.upper(), SignalType.BUY
        )

        # 发出信号
        signal = self.emit_signal(
            signal_type=signal_enum,
            data=data,
            confidence=confidence,
            strength=confidence,  # 使用置信度作为强度
            metadata=metadata,
        )

        # 添加到待处理队列
        self.pending_signals.append(
            {
                "signal": signal,
                "data": data,
                "type": signal_type,
                "confidence": confidence,
                "timestamp": self.datetime.datetime(),
                "metadata": metadata or {},
            }
        )

    def generate_signals(self):
        """
        生成交易信号 - 由子类实现
        示例实现会在具体策略中覆盖此方法
        """
        pass

    def stop(self):
        """策略结束时调用"""
        if self.trade_count > 0:
            win_rate = self.win_count / self.trade_count
            total_return = (
                self.broker.getvalue() - self.start_value
            ) / self.start_value

            self.log("=" * 50)
            self.log("策略执行完成")
            self.log(f"总交易次数: {self.trade_count}")
            self.log(f"胜率: {win_rate:.2%}")
            self.log(f"总收益: {total_return:.2%}")
            self.log(f"最终资产: {self.broker.getvalue():.2f}")
            self.log("=" * 50)


# 便捷的策略工厂函数
def create_smart_strategy(base_class=None, **params):
    """
    创建智能策略的工厂函数
    """
    if base_class is None:
        base_class = SmartTradingStrategy

    class CustomSmartStrategy(base_class):
        params = base_class.params._gettuple() + tuple(params.items())

    return CustomSmartStrategy
