#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Binance Quick Start Example
Binance快速入门示例 - 展示基本的实盘交易功能
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt


class BinanceQuickStart(bt.Strategy):
    """
    Binance快速入门策略
    展示最基本的Binance实盘交易功能
    """

    params = (
        ("sma_period", 20),
        ("trade_size", 0.001),  # BTC交易数量
        ("printlog", True),
    )

    def __init__(self):
        # 添加简单移动平均线
        self.sma = bt.indicators.SMA(self.data, period=self.p.sma_period)

        # 订单和持仓变量
        self.order = None

        if self.p.printlog:
            print("🎯 Binance快速入门策略初始化完成")
            print(
                f"📊 参数: SMA周期={self.p.sma_period}, 交易数量={self.p.trade_size} BTC"
            )

    def log(self, txt, dt=None):
        """日志函数"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.datetime(0)
            print("%s, %s" % (dt.isoformat(), txt))

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/已接受，等待成交
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    "BUY EXECUTED, Price: %.2f, Size: %.6f, Cost: %.2f, Comm %.2f"
                    % (
                        order.executed.price,
                        order.executed.size,
                        order.executed.value,
                        order.executed.comm,
                    )
                )
            else:
                self.log(
                    "SELL EXECUTED, Price: %.2f, Size: %.6f, Cost: %.2f, Comm %.2f"
                    % (
                        order.executed.price,
                        order.executed.size,
                        order.executed.value,
                        order.executed.comm,
                    )
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        self.order = None

    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return

        self.log("OPERATION PROFIT, GROSS %.2f, NET %.2f" % (trade.pnl, trade.pnlcomm))

    def next(self):
        """每个周期调用"""
        # 记录收盘价和SMA
        self.log("Close, %.2f, SMA, %.2f" % (self.data.close[0], self.sma[0]))

        # 检查是否有挂起的订单
        if self.order:
            return

        # 检查是否在市场中
        if not self.position:
            # SMA向上交叉时买入
            if self.data.close[0] > self.sma[0] and self.data.close[-1] <= self.sma[-1]:
                self.log("BUY CREATE, %.2f" % self.data.close[0])
                self.order = self.buy(size=self.p.trade_size)

        else:
            # 持仓时，SMA向下交叉时卖出
            if self.data.close[0] < self.sma[0] and self.data.close[-1] >= self.sma[-1]:
                self.log("SELL CREATE, %.2f" % self.data.close[0])
                self.order = self.sell(size=self.p.trade_size)

    def stop(self):
        """策略结束"""
        self.log(
            "(SMA Period %2d) Ending Value %.2f"
            % (self.params.sma_period, self.broker.getvalue()),
            doprint=True,
        )


def run_binance_demo():
    """运行Binance演示"""
    print("=== Backtrader Binance快速入门演示 ===\n")

    # 创建Cerebro引擎
    cerebro = bt.Cerebro()

    # 配置Binance Store（测试网）
    binance_store = bt.stores.BinanceStore(
        apikey="ljTajbbnWb5kOwcYXWtD3OKb6BsuMXCXI3SFMioBa5TlKtoulHZ1P9tU94qrHENM",  # 替换为您的API Key
        secret="PIfeJnLsIaglNszrWIgZjUL2WU0QfRBRcfdx5UKF8ryCFdQ8rnirUMXpmHoa138m",  # 替换为您的Secret
        testnet=True,  # 使用测试网
    )

    print("🔐 Binance Store配置完成")
    print("⚠️  请替换示例中的API密钥为您的真实密钥")
    print("💡 建议先使用测试网进行验证\n")

    # 添加数据（BTC/USDT）
    data = bt.stores.BinanceStore.getdata(store=binance_store, dataname="BTCUSDT")
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(BinanceQuickStart, printlog=True)

    # 设置初始资金（USDT）
    cerebro.broker.setcash(10000.0)
    print("💼 初始资金: 10,000 USDT")

    # 设置佣金（Binance现货交易费率约0.1%）
    cerebro.broker.setcommission(commission=0.001)
    print("💰 交易佣金: 0.1%\n")

    # 运行回测（实际使用时替换为run_live）
    print("🚀 开始回测演示...")
    print("📝 注意：这是回测模式，如需实盘请使用 cerebro.run_live()")

    # 显示初始状态
    print(f"📈 回测开始时账户价值: {cerebro.broker.getvalue():.2f} USDT")

    # 运行回测
    cerebro.run()

    # 显示最终结果
    final_value = cerebro.broker.getvalue()
    print(f"\n💰 回测结束时账户价值: {final_value:.2f} USDT")
    print(f"📊 总收益率: {(final_value - 10000) / 10000:.2%}")

    print("\n🎯 演示完成!")
    print("✅ Binance数据连接")
    print("✅ 策略执行")
    print("✅ 订单管理")
    print("✅ 资金结算")


def show_usage_examples():
    """显示使用示例"""
    print("\n" + "=" * 60)
    print("📚 Binance实盘交易使用指南")
    print("=" * 60)

    print("\n1. 基本实盘运行:")
    print("   cerebro.run_live(")
    print("       exchange='binance',")
    print("       symbol='BTCUSDT',")
    print("       timeframe='1d',")
    print("       apikey='your_key',")
    print("       secret='your_secret'")
    print("   )")

    print("\n2. 测试网配置:")
    print("   store = bt.stores.BinanceStore(")
    print("       apikey='test_key',")
    print("       secret='test_secret',")
    print("       testnet=True")
    print("   )")

    print("\n3. 不同交易对:")
    print("   - BTCUSDT: 比特币/泰达币")
    print("   - ETHUSDT: 以太坊/泰达币")
    print("   - BNBUSDT: 币安币/泰达币")

    print("\n4. 重要提醒:")
    print("   ⚠️  请妥善保管API密钥")
    print("   ⚠️  建议先在测试网验证策略")
    print("   ⚠️  实盘交易有风险，请谨慎操作")
    print("   ⚠️  确保有足够的手续费余额")


if __name__ == "__main__":
    run_binance_demo()
    show_usage_examples()
