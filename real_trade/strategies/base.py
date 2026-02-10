#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
RealTradeStrategyBase - 实盘策略基类

所有实盘策略的公共基类，提供：
- 统一的日志输出
- 订单/交易通知
- 止损止盈检查
- 仓位计算
- 交易统计
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt


class RealTradeStrategyBase(bt.Strategy):
    """
    实盘策略基类

    所有 real_trade 策略应继承此类，而非直接继承 bt.Strategy。
    """

    params = (
        ("printlog", True),
        ("log_trades", True),
        ("stop_loss", None),  # 止损百分比，如 0.02 = 2%
        ("take_profit", None),  # 止盈百分比
        ("max_position_pct", 1.0),  # 最大仓位占比
    )

    def __init__(self):
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # 交易统计
        self.trade_count = 0
        self.win_count = 0
        self.lose_count = 0
        self.total_pnl = 0.0

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------

    def log(self, txt, dt=None, level="INFO"):
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.datetime(0)
            print(f"{dt.isoformat()} [{level}] {txt}")

    # ------------------------------------------------------------------
    # 通知回调
    # ------------------------------------------------------------------

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            if order.isbuy():
                self.log(
                    f"BUY  Price={order.executed.price:.4f}  "
                    f"Size={order.executed.size:.6f}  "
                    f"Comm={order.executed.comm:.4f}"
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(
                    f"SELL Price={order.executed.price:.4f}  "
                    f"Size={order.executed.size:.6f}  "
                    f"Comm={order.executed.comm:.4f}"
                )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order {order.Status[order.status]}", level="WARN")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.trade_count += 1
        self.total_pnl += trade.pnlcomm
        if trade.pnl > 0:
            self.win_count += 1
        else:
            self.lose_count += 1

        if self.params.log_trades:
            self.log(
                f"TRADE #{self.trade_count}  "
                f"Gross={trade.pnl:.4f}  Net={trade.pnlcomm:.4f}"
            )

    # ------------------------------------------------------------------
    # 风控辅助
    # ------------------------------------------------------------------

    def check_stop_loss(self) -> bool:
        """检查是否触发止损"""
        if not self.position or self.params.stop_loss is None:
            return False
        if self.buyprice:
            pct = (self.data.close[0] - self.buyprice) / self.buyprice
            if pct <= -self.params.stop_loss:
                self.log(f"STOP LOSS  loss={pct:.2%}", level="WARN")
                return True
        return False

    def check_take_profit(self) -> bool:
        """检查是否触发止盈"""
        if not self.position or self.params.take_profit is None:
            return False
        if self.buyprice:
            pct = (self.data.close[0] - self.buyprice) / self.buyprice
            if pct >= self.params.take_profit:
                self.log(f"TAKE PROFIT  profit={pct:.2%}")
                return True
        return False

    def calc_position_size(self, risk_pct: float = 0.02) -> float:
        """
        根据风险百分比计算仓位大小

        Args:
            risk_pct: 单笔风险占账户比例（默认 2%）
        """
        value = self.broker.getvalue()
        price = self.data.close[0]

        if self.params.stop_loss and self.params.stop_loss > 0:
            risk_per_unit = price * self.params.stop_loss
            size = (value * risk_pct) / risk_per_unit
        else:
            size = (value * risk_pct) / price

        # 仓位上限
        max_size = (value * self.params.max_position_pct) / price
        return min(size, max_size)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def stop(self):
        self.log("=" * 50)
        self.log("STRATEGY COMPLETED")
        self.log(f"Final Value : ${self.broker.getvalue():.2f}")
        self.log(f"Total Trades: {self.trade_count}")
        self.log(f"Total P&L   : ${self.total_pnl:.2f}")
        if self.trade_count > 0:
            wr = self.win_count / self.trade_count
            self.log(f"Win Rate    : {wr:.2%} ({self.win_count}/{self.trade_count})")
        self.log("=" * 50)
