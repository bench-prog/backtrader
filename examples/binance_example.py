#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Binance Integration Usage Example
Demonstrates how to use the integrated Binance components
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt


class SimpleMovingAverageStrategy(bt.Strategy):
    """简单的移动平均线策略示例"""

    params = (
        ("maperiod", 15),
        ("printlog", True),
    )

    def log(self, txt, dt=None, doprint=False):
        """日志函数"""
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print("%s, %s" % (dt.isoformat(), txt))

    def __init__(self):
        # 保存收盘价的引用
        self.data_close = self.datas[0].close

        # 跟踪挂起的订单
        self.order = None

        # 添加移动平均线指标
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod
        )

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 买单/卖单已提交/已被经纪人接受 - 无需操作
            return

        # 检查订单是否已完成
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    "BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
            else:  # 卖单
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        # 重置订单
        self.order = None

    def next(self):
        """每个周期调用"""
        # 记录收盘价
        self.log("Close, %.2f" % self.data_close[0])

        # 检查是否有挂起的订单...如果有，则不发送第二个订单
        if self.order:
            return

        # 检查是否在市场中
        if not self.position:
            # 还没有...如果满足条件就买入
            if self.data_close[0] > self.sma[0]:
                # 当前价格高于移动平均线
                self.log("BUY CREATE, %.2f" % self.data_close[0])
                # 跟踪创建的订单以避免第二个订单
                self.order = self.buy()

        else:
            # 在市场中...如果满足条件就卖出
            if self.data_close[0] < self.sma[0]:
                # 当前价格低于移动平均线
                self.log("SELL CREATE, %.2f" % self.data_close[0])
                # 跟踪创建的订单以避免第二个订单
                self.order = self.sell()


def run_example():
    """运行示例"""
    print("=== Binance 集成使用示例 ===\n")

    # 创建Cerebro引擎
    cerebro = bt.Cerebro()

    # 创建Binance Store（测试网配置）
    store = bt.stores.BinanceStore(
        apikey="",  # 实际使用时填写真实的API密钥
        secret="",  # 实际使用时填写真实的API密钥
        testnet=True,  # 使用测试网
        _debug=False,
    )

    print("1. 创建Binance Store...")

    # 创建数据feed
    data = bt.feeds.BinanceData(
        store,
        symbol="BTC/USDT",
        timeframe=bt.TimeFrame.Days,
        compression=1,
        historical=True,  # 只获取历史数据进行回测
    )

    print("2. 创建数据feed...")

    # 添加数据到Cerebro
    cerebro.adddata(data)

    # 设置初始资金
    cerebro.broker.setcash(10000.0)
    print("3. 设置初始资金: $10,000.00")

    # 设置佣金 - Binance现货交易费率约为0.1%
    cerebro.broker.setcommission(commission=0.001)
    print("4. 设置交易佣金: 0.1%")

    # 添加策略
    cerebro.addstrategy(SimpleMovingAverageStrategy)
    print("5. 添加交易策略...")

    # 打印初始资金
    print(f"6. 回测开始时账户价值: ${cerebro.broker.getvalue():.2f}")

    # 运行回测
    print("7. 开始回测...")
    cerebro.run()

    # 打印最终资金
    print(f"8. 回测结束时账户价值: ${cerebro.broker.getvalue():.2f}")

    # 计算收益率
    initial_value = 10000.0
    final_value = cerebro.broker.getvalue()
    profit = final_value - initial_value
    roi = (profit / initial_value) * 100

    print("\n=== 回测结果 ===")
    print(f"初始资金: ${initial_value:.2f}")
    print(f"最终资金: ${final_value:.2f}")
    print(f"盈利: ${profit:.2f}")
    print(f"收益率: {roi:.2f}%")

    print("\n=== 示例运行完成 ===")


if __name__ == "__main__":
    run_example()
