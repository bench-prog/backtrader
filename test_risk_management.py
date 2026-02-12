#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Risk Management and Notification Integration Test
Based on the detailed technical implementation roadmap
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import datetime


class TestRiskStrategy(bt.Strategy):
    """测试风险管理和通知功能的策略"""
    
    params = (
        ('printlog', True),
        ('risk_percent', 0.02),  # 2%风险
        ('max_position', 0.3),   # 30%最大持仓
    )

    def log(self, txt, dt=None, doprint=False):
        """日志函数"""
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.datetime(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # 保存收盘价的引用
        self.data_close = self.datas[0].close
        self.order = None
        
        # 添加简单指标
        self.sma = bt.indicators.SimpleMovingAverage(self.datas[0], period=15)
        
        # 添加风险分析器
        self.risk_analyzer = self.analyzers.risk_analyzer
        self.market_state = self.analyzers.market_state

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Size: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.size,
                     order.executed.value,
                     order.executed.comm))
            else:
                self.log('SELL EXECUTED, Price: %.2f, Size: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.size,
                          order.executed.value,
                          order.executed.comm))

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
        """每个周期调用"""
        # 记录收盘价
        self.log('Close, %.2f' % self.data_close[0])

        # 检查是否有挂起的订单
        if self.order:
            return

        # 检查是否在市场中
        if not self.position:
            # 趋势向上时买入
            if self.data_close[0] > self.sma[0]:
                self.log('BUY CREATE, %.2f' % self.data_close[0])
                # 使用风险Sizer计算仓位
                self.order = self.buy()
        else:
            # 趋势向下时卖出
            if self.data_close[0] < self.sma[0]:
                self.log('SELL CREATE, %.2f' % self.data_close[0])
                self.order = self.sell()

    def stop(self):
        """策略结束时调用"""
        # 获取风险分析结果
        risk_results = self.analyzers.risk_analyzer.get_analysis()
        market_results = self.analyzers.market_state.get_analysis()
        
        self.log('=' * 50)
        self.log('风险分析结果:')
        self.log(f"最大回撤: {risk_results['risk_metrics'].get('max_drawdown', 0):.2%}")
        self.log(f"当前回撤: {risk_results['risk_metrics'].get('current_drawdown', 0):.2%}")
        self.log(f"持仓风险: {risk_results['risk_metrics'].get('position_risk', 0):.2%}")
        self.log(f"风险警报数量: {risk_results['performance_summary']['total_alerts']}")
        self.log(f"当前状态: {risk_results['current_status']}")
        
        self.log('\n市场状态分析:')
        self.log(f"当前市场状态: {market_results['current_state']}")
        self.log(f"状态变化次数: {len(market_results['state_changes'])}")


def run_risk_test():
    """运行风险管理和通知测试"""
    print("=== 风险管理与通知功能测试 ===\n")
    
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 创建测试数据（使用内置测试数据）
    data = bt.feeds.YahooFinanceData(
        dataname='ORCL',
        fromdate=datetime.datetime(2000, 1, 1),
        todate=datetime.datetime(2000, 12, 31),
        reverse=False
    )
    
    cerebro.adddata(data)
    
    # 设置初始资金
    cerebro.broker.setcash(10000.0)
    print("1. 设置初始资金: $10,000.00")
    
    # 设置佣金
    cerebro.broker.setcommission(commission=0.001)
    print("2. 设置交易佣金: 0.1%")
    
    # 添加风险Sizer
    cerebro.addsizer(bt.sizers.RiskBasedSizer, 
                     risk_per_trade=0.02,
                     max_position_pct=0.3)
    print("3. 添加风险管理Sizer")
    
    # 添加策略
    cerebro.addstrategy(TestRiskStrategy)
    print("4. 添加测试策略")
    
    # 添加风险分析器
    cerebro.addanalyzer(bt.analyzers.RiskAnalyzer, 
                       _name='risk_analyzer',
                       max_drawdown_limit=0.15,
                       max_position_risk=0.3)
    print("5. 添加风险分析器")
    
    # 添加市场状态分析器
    cerebro.addanalyzer(bt.analyzers.MarketStateAnalyzer, 
                       _name='market_state')
    print("6. 添加市场状态分析器")
    
    # 打印初始资金
    print(f'\n7. 回测开始时账户价值: ${cerebro.broker.getvalue():.2f}')
    
    # 运行回测
    print("8. 开始回测...")
    results = cerebro.run()
    
    # 打印最终资金
    final_value = cerebro.broker.getvalue()
    print(f'\n9. 回测结束时账户价值: ${final_value:.2f}')
    
    # 计算收益率
    initial_value = 10000.0
    profit = final_value - initial_value
    roi = (profit / initial_value) * 100
    
    print(f'\n=== 回测结果 ===')
    print(f'初始资金: ${initial_value:.2f}')
    print(f'最终资金: ${final_value:.2f}')
    print(f'盈利: ${profit:.2f}')
    print(f'收益率: {roi:.2f}%')
    
    print("\n=== 风险管理测试完成 ===")


if __name__ == '__main__':
    run_risk_test()