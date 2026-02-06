#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
策略基类和通用策略工具
"""

import backtrader as bt
from typing import Optional, Dict, Any


class BybitStrategyBase(bt.Strategy):
    """
    Bybit 策略基类

    提供通用的日志、通知和风险管理功能。
    """

    params = (
        ("printlog", True),  # 是否打印日志
        ("log_trades", True),  # 是否记录交易
        ("stop_loss", None),  # 止损百分比
        ("take_profit", None),  # 止盈百分比
    )

    def __init__(self):
        # 订单跟踪
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # 统计
        self.trade_count = 0
        self.win_count = 0
        self.lose_count = 0

    def log(self, txt, dt=None, level="INFO"):
        """日志函数"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.datetime(0)
            print(f"{dt.isoformat()} [{level}] {txt}")

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BUY EXECUTED: Price={order.executed.price:.2f}, "
                    f"Cost={order.executed.value:.2f}, "
                    f"Comm={order.executed.comm:.2f}"
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell():
                self.log(
                    f"SELL EXECUTED: Price={order.executed.price:.2f}, "
                    f"Cost={order.executed.value:.2f}, "
                    f"Comm={order.executed.comm:.2f}"
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected", level="WARNING")

        self.order = None

    def notify_trade(self, trade):
        """交易完成通知"""
        if not trade.isclosed:
            return

        self.trade_count += 1
        if trade.pnl > 0:
            self.win_count += 1
        else:
            self.lose_count += 1

        if self.params.log_trades:
            self.log(
                f"TRADE #{self.trade_count}: "
                f"Gross P&L={trade.pnl:.2f}, "
                f"Net P&L={trade.pnlcomm:.2f}"
            )

    def check_stop_loss(self):
        """检查止损"""
        if not self.position or self.params.stop_loss is None:
            return False

        if self.buyprice:
            loss_pct = (self.data.close[0] - self.buyprice) / self.buyprice
            if loss_pct <= -self.params.stop_loss:
                self.log(
                    f"STOP LOSS TRIGGERED: Loss={loss_pct:.2%}", level="WARNING"
                )
                return True

        return False

    def check_take_profit(self):
        """检查止盈"""
        if not self.position or self.params.take_profit is None:
            return False

        if self.buyprice:
            profit_pct = (self.data.close[0] - self.buyprice) / self.buyprice
            if profit_pct >= self.params.take_profit:
                self.log(f"TAKE PROFIT TRIGGERED: Profit={profit_pct:.2%}")
                return True

        return False

    def get_position_size(self, risk_pct: float = 0.02) -> float:
        """
        根据风险百分比计算仓位大小

        Args:
            risk_pct: 风险百分比（如 0.02 = 2%）

        Returns:
            仓位大小
        """
        account_value = self.broker.getvalue()
        risk_amount = account_value * risk_pct

        if self.params.stop_loss:
            # 根据止损计算仓位
            price = self.data.close[0]
            stop_price = price * (1 - self.params.stop_loss)
            risk_per_unit = price - stop_price
            if risk_per_unit > 0:
                size = risk_amount / risk_per_unit
                return size

        # 默认使用固定百分比
        return (account_value * risk_pct) / self.data.close[0]

    def stop(self):
        """策略结束时调用"""
        self.log("=" * 60)
        self.log("STRATEGY COMPLETED")
        self.log(f"Final Portfolio Value: ${self.broker.getvalue():.2f}")
        self.log(f"Total Trades: {self.trade_count}")
        if self.trade_count > 0:
            win_rate = self.win_count / self.trade_count
            self.log(f"Win Rate: {win_rate:.2%} ({self.win_count}/{self.trade_count})")
        self.log("=" * 60)


class SimpleMAStrategy(BybitStrategyBase):
    """
    简单的移动平均线交叉策略示例
    """

    params = (
        ("fast_period", 10),
        ("slow_period", 30),
        ("order_size", 0.01),
    )

    def __init__(self):
        super().__init__()

        # 添加指标
        self.fast_ma = bt.indicators.SMA(period=self.params.fast_period)
        self.slow_ma = bt.indicators.SMA(period=self.params.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        # 检查是否有待处理的订单
        if self.order:
            return

        # 检查止损止盈
        if self.position:
            if self.check_stop_loss() or self.check_take_profit():
                self.order = self.sell(size=self.position.size)
                return

        # 交易逻辑
        if not self.position:
            # 金叉：买入
            if self.crossover > 0:
                self.order = self.buy(size=self.params.order_size)

        else:
            # 死叉：卖出
            if self.crossover < 0:
                self.order = self.sell(size=self.position.size)
