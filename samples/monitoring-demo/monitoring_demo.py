#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Monitoring Demo for Backtrader
系统监控和报告生成功能演示
展示如何在backtrader中集成健康监控和绩效报告
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

import backtrader as bt


class MonitoringDemoStrategy(bt.Strategy):
    """
    监控演示策略
    展示系统健康监控和绩效跟踪功能
    """

    params = (
        ("printlog", True),
        ("sma_period", 15),
    )

    def __init__(self):
        # 保存收盘价的引用
        self.data_close = self.datas[0].close

        # 添加技术指标
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.p.sma_period
        )

        # 订单和持仓变量
        self.order = None
        self.bar_executed = None

    def log(self, txt, dt=None, doprint=False):
        """日志函数"""
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.datetime(0)
            print("%s, %s" % (dt.isoformat(), txt))

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    "BUY EXECUTED, Price: %.2f, Size: %.2f, Cost: %.2f, Comm %.2f"
                    % (
                        order.executed.price,
                        order.executed.size,
                        order.executed.value,
                        order.executed.comm,
                    )
                )
            else:
                self.log(
                    "SELL EXECUTED, Price: %.2f, Size: %.2f, Cost: %.2f, Comm %.2f"
                    % (
                        order.executed.price,
                        order.executed.size,
                        order.executed.value,
                        order.executed.comm,
                    )
                )

            self.bar_executed = len(self)

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
        # 记录收盘价
        self.log("Close, %.2f" % self.data_close[0])

        # 检查是否有挂起的订单
        if self.order:
            return

        # 检查是否在市场中
        if not self.position:
            # SMA向上交叉时买入
            if self.data_close[0] > self.sma[0]:
                if self.data_close[-1] <= self.sma[-1]:  # 交叉确认
                    self.log("BUY CREATE, %.2f" % self.data_close[0])
                    self.order = self.buy()

        else:
            # 持仓时，SMA向下交叉时卖出
            if self.data_close[0] < self.sma[0]:
                if self.data_close[-1] >= self.sma[-1]:  # 交叉确认
                    self.log("SELL CREATE, %.2f" % self.data_close[0])
                    self.order = self.sell()

    def stop(self):
        """策略结束时调用"""
        self.log(
            "(SMA Period %2d) Ending Value %.2f"
            % (self.params.sma_period, self.broker.getvalue()),
            doprint=True,
        )


def run_monitoring_demo():
    """运行监控演示"""
    print("=== Backtrader监控功能演示 ===\n")

    # 创建Cerebro引擎
    cerebro = bt.Cerebro()

    # 添加数据
    data = bt.feeds.YahooFinanceData(
        dataname="ORCL",
        fromdate=datetime.datetime(2000, 1, 1),
        todate=datetime.datetime(2000, 12, 31),
        reverse=False,
    )
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(MonitoringDemoStrategy)

    # 添加全套监控分析器
    monitoring_added = bt.analyzers.add_monitoring_analyzers(
        cerebro,
        health_monitor_params={
            "_debug": True,
            "check_interval": 20,
            "max_data_delay": 300,
        },
    )

    # 添加其他常用分析器
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    # 设置初始资金
    initial_cash = 10000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)

    print("📊 监控分析器添加完成:")
    for name, cls_name in monitoring_added.items():
        print(f"  - {name}: {cls_name}")

    print(f"\n📈 回测开始时账户价值: ${cerebro.broker.getvalue():.2f}")

    # 运行回测
    print("🚀 开始回测...")
    results = cerebro.run()
    strategy = results[0]

    # 获取最终资金
    final_value = cerebro.broker.getvalue()
    print(f"\n💰 回测结束时账户价值: ${final_value:.2f}")

    # 收集所有分析器结果
    print("\n📋 收集分析器结果...")
    all_results = bt.analyzers.collect_analyzer_results(strategy)
    print(f"  - 共收集到 {len(all_results)} 个分析器结果")

    # 生成详细报告
    print("\n📄 生成详细报告...")
    detailed_report = bt.analyzers.ReportGenerator.generate_text_report(all_results)
    print(detailed_report)

    # 生成简要报告
    print("\n📱 生成简要报告:")
    brief_report = bt.analyzers.ReportGenerator.generate_brief_report(all_results)
    print(brief_report)

    # 生成JSON报告
    print("\n💾 生成JSON报告:")
    json_report = bt.analyzers.ReportGenerator.generate_json_report(all_results)
    print(f"  - JSON报告大小: {len(json_report)} 字符")

    # 显示具体的分析结果
    print("\n🔍 详细分析结果:")

    if "performance" in all_results:
        perf = all_results["performance"]
        print("  绩效分析:")
        print(f"    初始价值: ${perf.get('initial_value', 0):,.2f}")
        print(f"    最终价值: ${perf.get('final_value', 0):,.2f}")
        print(f"    净利润: ${perf.get('net_pnl', 0):,.2f}")
        print(f"    回报率: {perf.get('return_pct', 0):.2%}")

    if "health_monitor" in all_results:
        health = all_results["health_monitor"]
        print("  健康监控:")
        print(f"    总体健康度: {health.get('overall_health', 0):.1%}")
        print(f"    系统健康: {'是' if health.get('is_healthy', False) else '否'}")
        print(f"    检查次数: {health.get('total_checks', 0)}")

    if "returns" in all_results:
        returns = all_results["returns"]
        print("  回报分析:")
        print(f"    总回报: {returns.get('rtot', 0):.2%}")
        print(f"    年化回报: {returns.get('ravg', 0) * 252:.2%}")

    if "drawdown" in all_results:
        drawdown = all_results["drawdown"]
        print("  回撤分析:")
        print(f"    最大回撤: {drawdown.get('maxdrawdown', 0):.2%}")

    if "sharpe" in all_results:
        sharpe = all_results["sharpe"]
        print("  夏普比率:")
        print(f"    Sharpe Ratio: {sharpe.get('sharperatio', 0):.2f}")

    print("\n🎯 监控演示完成!")
    print("✅ 系统健康监控")
    print("✅ 绩效跟踪分析")
    print("✅ 多格式报告生成")
    print("✅ 实时状态检查")


def main():
    """主函数"""
    run_monitoring_demo()


if __name__ == "__main__":
    main()
