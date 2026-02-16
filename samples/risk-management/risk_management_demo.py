#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级风控系统完整示例
Demonstration of Enterprise Risk Management System

展示如何使用新添加的风控功能：
1. 事前风控引擎集成
2. 实时风险监控
3. 动态风控配置
4. 风控规则管理
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class RiskManagedStrategy(bt.Strategy):
    """
    风控管理策略示例
    """
    
    params = (
        ('sma_period', 15),
        ('printlog', True),
    )

    def __init__(self):
        # 技术指标
        self.sma = bt.indicators.SMA(self.data, period=self.p.sma_period)
        
        # 订单和持仓管理
        self.order = None
        self.entry_price = None
        
        # 风控相关
        self.risk_monitor = None
        
        if self.p.printlog:
            print("🎯 风控管理策略初始化完成")
            print(f"📊 参数: SMA周期={self.p.sma_period}")

    def log(self, txt, dt=None):
        """日志函数"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.datetime(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Size: %.6f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price, order.executed.size,
                     order.executed.value, order.executed.comm))
                self.entry_price = order.executed.price
            else:
                self.log('SELL EXECUTED, Price: %.2f, Size: %.6f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price, order.executed.size,
                          order.executed.value, order.executed.comm))
                self.entry_price = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        """每个周期执行"""
        # 基本交易逻辑
        if not self.position:
            # SMA向上交叉时买入
            if self.data.close[0] > self.sma[0] and self.data.close[-1] <= self.sma[-1]:
                self.log('BUY CREATE, %.2f' % self.data.close[0])
                self.order = self.buy(size=0.001)  # 固定小仓位测试风控
                
        else:
            # 持仓时的风险管理
            current_price = self.data.close[0]
            
            # 简单的止损逻辑
            if self.entry_price and current_price < self.entry_price * 0.95:  # 5%止损
                self.log('STOP LOSS, %.2f' % current_price)
                self.order = self.sell(size=self.position.size)
            
            # SMA向下交叉时卖出
            elif self.data.close[0] < self.sma[0] and self.data.close[-1] >= self.sma[-1]:
                self.log('SELL CREATE, %.2f' % self.data.close[0])
                self.order = self.sell(size=self.position.size)

    def stop(self):
        """策略结束"""
        self.log('(SMA Period %2d) Ending Value %.2f' %
                 (self.params.sma_period, self.broker.getvalue()))


def demonstrate_pre_trade_risk():
    """演示事前风控引擎"""
    print("\n" + "="*60)
    print("🛡️  事前风控引擎演示")
    print("="*60)
    
    # 创建Cerebro
    cerebro = bt.Cerebro()
    
    # 集成事前风控引擎
    risk_engine = bt.risk.integrate_pre_trade_risk_engine(
        cerebro,
        max_leverage=2.0,
        max_position_concentration=0.3,
        max_daily_loss_limit=0.05,
        max_order_size_ratio=0.1,
        market_impact_threshold=0.02
    )
    
    # 添加数据
    data = bt.feeds.YahooFinanceData(
        dataname='AAPL',
        fromdate=datetime.datetime(2020, 1, 1),
        todate=datetime.datetime(2020, 12, 31)
    )
    cerebro.adddata(data)
    
    # 添加策略
    cerebro.addstrategy(RiskManagedStrategy)
    
    # 设置初始资金
    initial_cash = 10000.0
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)
    
    print(f'初始资金: ${initial_cash:,.2f}')
    
    # 运行回测
    results = cerebro.run()
    
    # 显示风控统计
    print("\n📊 事前风控统计:")
    stats = risk_engine.get_statistics()
    print(f"  总检查次数: {stats['total_checks']}")
    print(f"  通过次数: {stats['passed']}")
    print(f"  拒绝次数: {stats['failed']}")
    print(f"  通过率: {stats['pass_rate']:.2%}")
    print(f"  当前杠杆: {stats['current_leverage']:.2f}x")
    
    final_value = cerebro.broker.getvalue()
    print(f'最终资金: ${final_value:,.2f}')
    print(f'收益率: {(final_value - initial_cash) / initial_cash:.2%}')


def demonstrate_real_time_monitoring():
    """演示实时风险监控"""
    print("\n" + "="*60)
    print("📈 实时风险监控演示")
    print("="*60)
    
    # 创建Cerebro
    cerebro = bt.Cerebro()
    
    # 添加实时风险监控
    risk_monitor = bt.risk.add_real_time_risk_monitoring(
        cerebro,
        var_confidence_level=0.95,
        circuit_breaker_threshold=0.1,
        risk_budget_limit=0.02,
        enable_var_monitoring=True,
        enable_cvar_monitoring=True
    )
    
    # 添加数据
    data = bt.feeds.YahooFinanceData(
        dataname='GOOGL',
        fromdate=datetime.datetime(2020, 1, 1),
        todate=datetime.datetime(2020, 12, 31)
    )
    cerebro.adddata(data)
    
    # 添加策略（带风控混入）
    class MonitoredStrategy(RiskManagedStrategy, bt.risk.RiskControlMixin):
        def __init__(self):
            RiskManagedStrategy.__init__(self)
            bt.risk.RiskControlMixin.__init__(self)
            self.set_risk_monitor(risk_monitor)
    
    cerebro.addstrategy(MonitoredStrategy)
    
    # 设置初始资金
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # 运行回测
    results = cerebro.run()
    
    # 显示风险监控结果
    print("\n📊 实时风险监控结果:")
    analysis = risk_monitor.get_analysis()
    
    print(f"  当前VaR (95%): {analysis['current_var']:.2%}")
    print(f"  当前CVaR (95%): {analysis['current_cvar']:.2%}")
    print(f"  当前回撤: {analysis['current_drawdown']:.2%}")
    print(f"  风险预算使用: {analysis['risk_budget_used']:.2%}")
    print(f"  VaR违规次数: {analysis['var_violations']}")
    print(f"  CVaR违规次数: {analysis['cvar_violations']}")
    print(f"  回撤违规次数: {analysis['drawdown_violations']}")
    print(f"  熔断触发: {'是' if analysis['circuit_breaker_triggered'] else '否'}")
    
    # 显示警报
    alerts = risk_monitor.get_alerts()
    if alerts:
        print(f"\n🚨 风险警报 ({len(alerts)}条):")
        for i, alert in enumerate(alerts[-3:], 1):  # 显示最近3条
            print(f"  {i}. [{alert['type']}] {alert['message']}")


def demonstrate_risk_configuration():
    """演示风控配置管理"""
    print("\n" + "="*60)
    print("⚙️  风控配置管理演示")
    print("="*60)
    
    # 创建风控配置管理器
    config_manager = bt.risk.create_default_risk_config("demo_account")
    
    # 自定义规则参数
    config_manager.rules['leverage_limit'].max_leverage = 1.5
    config_manager.rules['position_concentration'].max_concentration = 0.25
    
    # 添加自定义规则
    class CustomRiskRule(bt.risk.RiskRule):
        def __init__(self, max_daily_trades=10):
            super().__init__("daily_trade_limit", "日交易次数限制")
            self.max_daily_trades = max_daily_trades
            self.daily_trades = 0
            self.current_date = None
        
        def check(self, context):
            current_date = context.get('current_date')
            if current_date != self.current_date:
                self.daily_trades = 0
                self.current_date = current_date
            
            self.daily_trades += 1
            if self.daily_trades > self.max_daily_trades:
                return False, f"日交易次数超限: {self.daily_trades} > {self.max_daily_trades}"
            return True, ""
    
    config_manager.add_rule(CustomRiskRule(max_daily_trades=5), ['pre_trade'])
    
    # 模拟风控检查
    print("🧪 模拟风控检查:")
    
    test_context = {
        'current_leverage': 1.8,
        'position_concentration': 0.3,
        'daily_loss': 0.03,
        'market_impact': 0.015,
        'current_date': datetime.date.today()
    }
    
    results = config_manager.check_rules(test_context)
    
    for rule_name, (passed, message) in results.items():
        status = "✅ 通过" if passed else "❌ 拒绝"
        print(f"  {status} {rule_name}: {message}")
    
    # 显示统计信息
    print("\n📊 规则统计:")
    stats = config_manager.get_rule_statistics()
    for rule_name, rule_stats in stats.items():
        print(f"  {rule_name}: 违规{rule_stats['violation_count']}次, "
              f"{'启用' if rule_stats['enabled'] else '禁用'}")


def main():
    """主函数"""
    print("🏛️  Backtrader企业级风控系统演示")
    print("Enterprise Risk Management System Demonstration")
    print("="*60)
    
    try:
        # 演示各个风控功能
        demonstrate_pre_trade_risk()
        demonstrate_real_time_monitoring()
        demonstrate_risk_configuration()
        
        print("\n" + "="*60)
        print("🎉 所有风控功能演示完成!")
        print("="*60)
        print("\n📋 新增风控功能总结:")
        print("  ✅ 事前风控引擎 - 订单提交前的全面风险检查")
        print("  ✅ 实时风险监控 - 持续跟踪VaR、CVaR、回撤等指标")
        print("  ✅ 动态风控配置 - 灵活的规则管理和参数调整")
        print("  ✅ 多层风控体系 - 事前、事中、事后全覆盖")
        print("  ✅ 熔断机制 - 紧急风险控制")
        print("  ✅ 风控报告 - 详细的风控统计和警报")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()