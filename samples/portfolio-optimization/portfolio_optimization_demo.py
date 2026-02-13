#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Portfolio Optimization Demo for Backtrader
基于真实数据的投资组合优化完整示例
展示均值-方差和风险平价两种优化方法
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import datetime
import os


class MultiAssetStrategy(bt.Strategy):
    """
    多资产投资组合策略
    展示投资组合优化在backtrader中的实际应用
    """
    
    params = (
        ('rebalance_frequency', 20),    # 再平衡频率（交易日）
        ('optimization_method', 'mean_variance'),  # 优化方法
        ('printlog', True),
    )

    def __init__(self):
        super(MultiAssetStrategy, self).__init__()

        # 根据参数选择优化器
        if self.p.optimization_method == 'mean_variance':
            self.optimizer = self.analyzers.mv_optimizer
        else:
            self.optimizer = self.analyzers.rp_optimizer
            
        self.rebalancer = bt.analyzers.PortfolioRebalancer(self)

        # 状态变量
        self.days_since_rebalance = 0
        self.last_optimization_result = None

    def log(self, txt, dt=None):
        """日志记录"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def next(self):
        """主逻辑循环"""
        self.days_since_rebalance += 1

        # 定期执行优化和再平衡
        if self.days_since_rebalance >= self.p.rebalance_frequency:
            self._perform_optimization_and_rebalance()
            self.days_since_rebalance = 0

    def _perform_optimization_and_rebalance(self):
        """执行优化和再平衡"""
        # 获取所有数据名称
        data_names = [data._name for data in self.datas]

        if len(data_names) < 2:
            self.log("资产数量不足，无法进行投资组合优化")
            return

        try:
            # 执行优化
            if self.p.optimization_method == 'mean_variance':
                optimization_result = self.optimizer.optimize(data_names)
            else:
                optimization_result = self.optimizer.optimize(data_names)
                
            self.last_optimization_result = optimization_result

            self.log(
                f"优化完成 - 预期收益: {optimization_result.expected_return:.2%}, "
                f"风险: {optimization_result.risk:.2%}, "
                f"夏普比率: {optimization_result.sharpe_ratio:.2f}"
            )

            # 显示权重分配
            self.log("最优权重分配:")
            for asset, weight in optimization_result.weights.items():
                self.log(f"  {asset}: {weight:.2%}")

            # 设置目标权重并执行再平衡
            self.rebalancer.set_target_weights(optimization_result.weights)
            trades = self.rebalancer.rebalance(tolerance=0.03)  # 3%容忍度

            # 执行交易
            for data_name, size_diff, price in trades:
                data = self.getdatabyname(data_name)
                if size_diff > 0:
                    self.buy(data=data, size=size_diff)
                    self.log(f"买入 {data_name}: {size_diff} 股，价格 {price:.2f}")
                elif size_diff < 0:
                    self.sell(data=data, size=abs(size_diff))
                    self.log(f"卖出 {data_name}: {abs(size_diff)} 股，价格 {price:.2f}")

        except Exception as e:
            self.log(f"优化过程出错: {e}")

    def stop(self):
        """策略结束"""
        if self.last_optimization_result:
            self.log("=== 最终投资组合统计 ===")
            self.log(
                f"预期年化收益: {self.last_optimization_result.expected_return:.2%}"
            )
            self.log(f"年化波动率: {self.last_optimization_result.risk:.2%}")
            self.log(f"夏普比率: {self.last_optimization_result.sharpe_ratio:.2f}")

            total_value = self.broker.getvalue()
            self.log(f"最终组合价值: {total_value:.2f}")


def load_sample_data():
    """加载示例数据"""
    # 使用内置的ORCL数据作为示例
    data1 = bt.feeds.YahooFinanceData(
        dataname='ORCL',
        fromdate=datetime.datetime(2000, 1, 1),
        todate=datetime.datetime(2000, 12, 31)
    )
    data1._name = 'ORCL'
    
    data2 = bt.feeds.YahooFinanceData(
        dataname='ORCL',
        fromdate=datetime.datetime(2000, 1, 1),
        todate=datetime.datetime(2000, 12, 31)
    )
    data2._name = 'ORCL_COPY'  # 模拟第二个资产
    
    return [data1, data2]


def run_mean_variance_demo():
    """运行均值-方差优化演示"""
    print("=== 均值-方差投资组合优化演示 ===\n")
    
    cerebro = bt.Cerebro()
    
    # 添加数据
    datas = load_sample_data()
    for data in datas:
        cerebro.adddata(data)
    
    # 添加策略
    cerebro.addstrategy(
        MultiAssetStrategy,
        optimization_method='mean_variance',
        rebalance_frequency=15,
        printlog=True
    )
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.MeanVarianceOptimizer, _name='mv_optimizer')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    
    # 设置初始条件
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # 运行回测
    print("开始均值-方差优化回测...")
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    strategy = results[0]
    
    final_value = cerebro.broker.getvalue()
    
    print(f"\n回测结果:")
    print(f"初始资金: ${initial_value:,.2f}")
    print(f"最终资金: ${final_value:,.2f}")
    print(f"收益率: {(final_value - initial_value) / initial_value:.2%}")
    
    # 显示分析器结果
    returns_analysis = strategy.analyzers.returns.get_analysis()
    drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
    
    print(f"总回报: {returns_analysis.get('rtot', 0):.2%}")
    print(f"最大回撤: {drawdown_analysis.get('maxdrawdown', 0):.2%}")
    
    return strategy


def run_risk_parity_demo():
    """运行风险平价优化演示"""
    print("\n" + "="*50)
    print("=== 风险平价投资组合优化演示 ===\n")
    
    cerebro = bt.Cerebro()
    
    # 添加数据
    datas = load_sample_data()
    for data in datas:
        cerebro.adddata(data)
    
    # 添加策略
    cerebro.addstrategy(
        MultiAssetStrategy,
        optimization_method='risk_parity',
        rebalance_frequency=15,
        printlog=True
    )
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.RiskParityOptimizer, _name='rp_optimizer')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    
    # 设置初始条件
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # 运行回测
    print("开始风险平价优化回测...")
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    strategy = results[0]
    
    final_value = cerebro.broker.getvalue()
    
    print(f"\n回测结果:")
    print(f"初始资金: ${initial_value:,.2f}")
    print(f"最终资金: ${final_value:,.2f}")
    print(f"收益率: {(final_value - initial_value) / initial_value:.2%}")
    
    # 显示分析器结果
    returns_analysis = strategy.analyzers.returns.get_analysis()
    drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
    
    print(f"总回报: {returns_analysis.get('rtot', 0):.2%}")
    print(f"最大回撤: {drawdown_analysis.get('maxdrawdown', 0):.2%}")
    
    return strategy


def main():
    """主函数"""
    print("Backtrader投资组合优化完整演示")
    print("展示两种现代投资组合理论的实现\n")
    
    # 运行两种优化方法
    mv_strategy = run_mean_variance_demo()
    rp_strategy = run_risk_parity_demo()
    
    print("\n" + "="*60)
    print("🎯 演示完成!")
    print("✅ 均值-方差优化器")
    print("✅ 风险平价优化器") 
    print("✅ 投资组合再平衡")
    print("✅ 绩效分析集成")
    print("✅ 策略日志记录")


if __name__ == '__main__':
    main()