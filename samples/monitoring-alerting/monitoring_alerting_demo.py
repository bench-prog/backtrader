#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级监控告警系统完整示例
Enterprise Monitoring & Alerting System Demonstration

展示如何使用新添加的监控告警功能：
1. 实时系统资源监控
2. 业务指标监控
3. 多渠道告警通知
4. 可视化监控面板
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import os
import sys
import time

import backtrader as bt

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class MonitoredTradingStrategy(bt.Strategy):
    """
    被监控的交易策略示例
    """

    params = (
        ("sma_period", 20),
        ("printlog", True),
    )

    def __init__(self):
        # 技术指标
        self.sma = bt.indicators.SMA(self.data, period=self.p.sma_period)

        # 订单和持仓管理
        self.order = None
        self.entry_price = None

        # 监控相关
        self.dashboard = None

        if self.p.printlog:
            print("🎯 被监控的交易策略初始化完成")
            print(f"📊 参数: SMA周期={self.p.sma_period}")

    def log(self, txt, dt=None):
        """日志函数"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.datetime(0)
            print("%s, %s" % (dt.isoformat(), txt))

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
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
                self.entry_price = order.executed.price
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
                self.entry_price = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        self.order = None

    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return

        self.log("OPERATION PROFIT, GROSS %.2f, NET %.2f" % (trade.pnl, trade.pnlcomm))

    def next(self):
        """每个周期执行"""
        # 基本交易逻辑
        if not self.position:
            # SMA向上交叉时买入
            if self.data.close[0] > self.sma[0] and self.data.close[-1] <= self.sma[-1]:
                self.log("BUY CREATE, %.2f" % self.data.close[0])
                self.order = self.buy(size=0.001)

        else:
            # 简单的止损逻辑
            current_price = self.data.close[0]
            if self.entry_price and current_price < self.entry_price * 0.95:
                self.log("STOP LOSS, %.2f" % current_price)
                self.order = self.sell(size=self.position.size)

            # SMA向下交叉时卖出
            elif (
                self.data.close[0] < self.sma[0] and self.data.close[-1] >= self.sma[-1]
            ):
                self.log("SELL CREATE, %.2f" % self.data.close[0])
                self.order = self.sell(size=self.position.size)

    def stop(self):
        """策略结束"""
        self.log(
            "(SMA Period %2d) Ending Value %.2f"
            % (self.params.sma_period, self.broker.getvalue())
        )


def demonstrate_system_monitoring():
    """演示系统监控功能"""
    print("\n" + "=" * 60)
    print("🖥️  系统资源监控演示")
    print("=" * 60)

    # 创建监控服务
    monitor_service = bt.monitoring.create_monitoring_service(check_interval=5.0)

    # 添加系统资源告警规则
    cpu_alert = bt.monitoring.SystemResourceAlertRule("cpu_percent", 70, ">")
    memory_alert = bt.monitoring.SystemResourceAlertRule("memory_percent", 75, ">")

    monitor_service.alert_manager.add_rule(cpu_alert)
    monitor_service.alert_manager.add_rule(memory_alert)

    # 启动监控
    monitor_service.start()

    try:
        print("开始监控系统资源...")
        time.sleep(10)  # 监控10秒钟

        # 查看监控数据
        system_metrics = monitor_service.get_system_metrics()
        print("\n📊 当前系统指标:")
        for key, value in system_metrics.items():
            print(f"  {key}: {value}")

        # 查看告警统计
        alert_stats = monitor_service.get_alert_statistics()
        print("\n🔔 告警统计:")
        print(f"  总告警数: {alert_stats['total_alerts']}")
        print(f"  活动告警: {alert_stats['active_alerts']}")
        print(f"  严重程度分布: {alert_stats['severity_distribution']}")

    finally:
        monitor_service.stop()


def demonstrate_business_monitoring():
    """演示业务监控功能"""
    print("\n" + "=" * 60)
    print("💼 业务监控演示")
    print("=" * 60)

    # 创建Cerebro
    cerebro = bt.Cerebro()

    # 创建监控仪表板
    dashboard = bt.monitoring.create_monitoring_dashboard(host="localhost", port=5001)

    # 集成监控到策略
    class MonitoredStrategy(
        MonitoredTradingStrategy, bt.monitoring.StrategyMonitorMixin
    ):
        def __init__(self):
            MonitoredTradingStrategy.__init__(self)
            bt.monitoring.StrategyMonitorMixin.__init__(self)
            self.set_dashboard(dashboard)

    # 添加数据
    data = bt.feeds.YahooFinanceData(
        dataname="MSFT",
        fromdate=datetime.datetime(2020, 1, 1),
        todate=datetime.datetime(2020, 3, 31),  # 缩短回测时间
    )
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(MonitoredStrategy)

    # 设置初始资金
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)

    # 集成监控
    bt.monitoring.integrate_monitoring_dashboard(cerebro, dashboard)

    print("初始资金: $10,000.00")
    print("📊 监控仪表板已启动 - 访问 http://localhost:5001")

    # 运行回测（短时间）
    print("开始回测并监控业务指标...")
    try:
        results = cerebro.run()

        # 查看最终结果
        final_value = cerebro.broker.getvalue()
        print(f"\n最终资金: ${final_value:,.2f}")
        print(f"收益率: {(final_value - 10000) / 10000:.2%}")

        # 查看监控统计
        time.sleep(2)  # 等待数据更新
        alert_stats = dashboard.dashboard.alert_manager.get_alert_statistics()
        print("\n🔔 业务告警统计:")
        print(f"  总告警数: {alert_stats['total_alerts']}")
        print(f"  活动告警: {len(dashboard.dashboard.get_active_alerts())}")

    finally:
        dashboard.stop()


def demonstrate_multi_channel_alerting():
    """演示多渠道告警"""
    print("\n" + "=" * 60)
    print("📢 多渠道告警演示")
    print("=" * 60)

    # 创建告警管理器
    alert_manager = bt.monitoring.AlertManager()

    # 添加不同类型的告警规则
    # 业务告警规则
    loss_alert = bt.monitoring.BusinessAlertRule("daily_loss", -100, "<")
    position_alert = bt.monitoring.BusinessAlertRule("position_size", 10, ">")

    alert_manager.add_rule(loss_alert)
    alert_manager.add_rule(position_alert)

    # 模拟告警场景
    print("🧪 模拟告警场景:")

    # 场景1: 模拟亏损过大
    context1 = {
        "daily_loss": -150,  # 亏损150美元
        "position_size": 5,
    }

    alert_manager.check_alerts(context1)

    # 场景2: 模拟仓位过大
    context2 = {
        "daily_loss": -50,
        "position_size": 15,  # 仓位过大
    }

    alert_manager.check_alerts(context2)

    # 显示告警结果
    active_alerts = alert_manager.get_active_alerts()
    print(f"\n🚨 触发的告警 ({len(active_alerts)}条):")
    for alert in active_alerts:
        print(f"  [{alert.severity}] {alert.rule_name}: {alert.message}")

    # 显示统计信息
    stats = alert_manager.get_alert_statistics()
    print("\n📊 告警统计:")
    print(f"  总告警数: {stats['total_alerts']}")
    print(f"  活动告警: {stats['active_alerts']}")
    print(f"  规则分布: {stats['rule_distribution']}")


def demonstrate_custom_alert_rules():
    """演示自定义告警规则"""
    print("\n" + "=" * 60)
    print("🔧 自定义告警规则演示")
    print("=" * 60)

    # 创建自定义告警规则
    class DrawdownAlertRule(bt.monitoring.AlertRule):
        """回撤告警规则"""

        def __init__(self, max_drawdown=0.1):
            super().__init__("drawdown_alert", "最大回撤告警")
            self.max_drawdown = max_drawdown
            self.peak_value = None

        def check(self, context):
            current_time = datetime.datetime.now()
            if not self.should_check(current_time):
                return False, ""

            current_value = context.get("portfolio_value", 0)
            if not self.peak_value:
                self.peak_value = current_value
                return False, ""

            # 更新峰值
            if current_value > self.peak_value:
                self.peak_value = current_value

            # 计算回撤
            drawdown = (self.peak_value - current_value) / self.peak_value

            if drawdown > self.max_drawdown:
                message = f"回撤过大: {drawdown:.2%} > {self.max_drawdown:.2%}"
                alert = self.trigger(message)
                self.set_cooldown(30)  # 30分钟冷却
                return True, message

            return False, ""

        def get_severity(self):
            return "CRITICAL"

    # 创建自定义通知渠道
    class ConsoleNotificationChannel(bt.monitoring.NotificationChannel):
        """控制台通知渠道"""

        def __init__(self):
            super().__init__("console")

        def send(self, alert):
            if not self.enabled:
                return False

            print(f"\n🚨 告警通知 [{alert.severity}]:")
            print(f"   规则: {alert.rule_name}")
            print(f"   消息: {alert.message}")
            print(f"   时间: {alert.timestamp}")
            return True

    # 测试自定义规则
    alert_manager = bt.monitoring.AlertManager()

    # 添加自定义规则和渠道
    drawdown_rule = DrawdownAlertRule(max_drawdown=0.05)
    console_channel = ConsoleNotificationChannel()

    alert_manager.add_rule(drawdown_rule)
    alert_manager.add_channel(console_channel)

    # 模拟回撤场景
    print("🧪 测试回撤告警:")

    # 模拟投资组合价值变化
    portfolio_values = [10000, 10500, 10800, 10200, 9800, 9300]  # 逐步下跌

    for i, value in enumerate(portfolio_values):
        context = {"portfolio_value": value}
        alert_manager.check_alerts(context)
        time.sleep(0.1)  # 小间隔

    # 显示结果
    active_alerts = alert_manager.get_active_alerts()
    print(f"\n触发的回撤告警: {len(active_alerts)}条")


def main():
    """主函数"""
    print("🏛️  Backtrader企业级监控告警系统演示")
    print("Enterprise Monitoring & Alerting System Demonstration")
    print("=" * 60)

    try:
        # 演示各个监控功能
        demonstrate_system_monitoring()
        demonstrate_business_monitoring()
        demonstrate_multi_channel_alerting()
        demonstrate_custom_alert_rules()

        print("\n" + "=" * 60)
        print("🎉 所有监控告警功能演示完成!")
        print("=" * 60)
        print("\n📋 新增监控告警功能总结:")
        print("  ✅ 实时系统资源监控 - CPU/内存/磁盘使用率")
        print("  ✅ 业务指标监控 - 订单/仓位/资金状况")
        print("  ✅ 多渠道告警通知 - 邮件/Webhook/控制台")
        print("  ✅ 可视化监控面板 - Web实时监控大盘")
        print("  ✅ 告警规则引擎 - 灵活的告警规则配置")
        print("  ✅ 告警去重聚合 - 智能告警管理")
        print("  ✅ 自定义扩展 - 支持自定义规则和渠道")

        print("\n🚀 使用建议:")
        print("  1. 在生产环境中配置邮件/Webhook通知渠道")
        print("  2. 根据策略特点设置合适的告警阈值")
        print("  3. 定期查看监控仪表板了解系统状态")
        print("  4. 利用告警历史进行问题分析和优化")

    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
