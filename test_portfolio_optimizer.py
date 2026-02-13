#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Portfolio Optimizer Quick Test
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import datetime


def test_portfolio_optimizer():
    """测试投资组合优化器"""
    print("=== 投资组合优化器测试 ===")
    
    try:
        # 创建Cerebro引擎
        cerebro = bt.Cerebro()
        
        # 添加多个数据源（使用相同的ORCL数据模拟多资产）
        data1 = bt.feeds.YahooFinanceData(
            dataname='ORCL',
            fromdate=datetime.datetime(2000, 1, 1),
            todate=datetime.datetime(2000, 3, 31)
        )
        data1._name = 'ORCL'
        
        data2 = bt.feeds.YahooFinanceData(
            dataname='ORCL',
            fromdate=datetime.datetime(2000, 1, 1),
            todate=datetime.datetime(2000, 3, 31)
        )
        data2._name = 'ORCL2'  # 模拟第二个资产
        
        cerebro.adddata(data1)
        cerebro.adddata(data2)
        
        # 设置初始资金
        cerebro.broker.setcash(100000.0)
        
        # 添加简单策略
        class TestStrategy(bt.Strategy):
            def __init__(self):
                pass
            def next(self):
                pass
        
        cerebro.addstrategy(TestStrategy)
        
        # 添加均值-方差优化器
        cerebro.addanalyzer(bt.analyzers.MeanVarianceOptimizer, 
                           _name='mv_optimizer',
                           _debug=True)
        
        # 添加风险平价优化器
        cerebro.addanalyzer(bt.analyzers.RiskParityOptimizer, 
                           _name='rp_optimizer',
                           _debug=True)
        
        print("✓ 分析器添加成功")
        
        # 运行回测
        print("✓ 开始运行回测...")
        results = cerebro.run()
        
        strategy = results[0]
        
        # 获取分析结果
        mv_result = strategy.analyzers.mv_optimizer.get_analysis()
        rp_result = strategy.analyzers.rp_optimizer.get_analysis()
        
        print("✓ 均值-方差优化器运行成功")
        print(f"  - 优化次数: {mv_result.get('optimization_count', 0)}")
        print(f"  - 当前权重: {mv_result.get('current_weights', {})}")
        
        print("✓ 风险平价优化器运行成功")
        print(f"  - 优化次数: {rp_result.get('optimization_count', 0)}")
        print(f"  - 当前权重: {rp_result.get('current_weights', {})}")
        
        # 测试再平衡器
        rebalancer = bt.analyzers.PortfolioRebalancer(strategy)
        rebalancer.set_target_weights({'ORCL': 0.6, 'ORCL2': 0.4})
        trades = rebalancer.rebalance(tolerance=0.1)
        
        print("✓ 投资组合再平衡器测试成功")
        print(f"  - 待执行交易: {len(trades)} 笔")
        
        return True
        
    except Exception as e:
        print(f"✗ 投资组合优化器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dataclass():
    """测试PortfolioWeights数据类"""
    print("\n=== PortfolioWeights数据类测试 ===")
    
    try:
        from backtrader.analyzers.portfolio_optimizer import PortfolioWeights
        
        # 创建测试实例
        weights = PortfolioWeights(
            weights={'AAPL': 0.5, 'GOOGL': 0.5},
            expected_return=0.15,
            risk=0.20,
            sharpe_ratio=0.75
        )
        
        print("✓ PortfolioWeights创建成功")
        print(f"  - 权重: {weights.weights}")
        print(f"  - 预期收益: {weights.expected_return:.2%}")
        print(f"  - 风险: {weights.risk:.2%}")
        print(f"  - Sharpe比率: {weights.sharpe_ratio:.2f}")
        
        return True
    except Exception as e:
        print(f"✗ PortfolioWeights测试失败: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("=== 投资组合优化功能测试 ===\n")
    
    tests = [
        test_dataclass,
        test_portfolio_optimizer
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有投资组合优化功能测试通过！")
        print("✅ 均值-方差优化器")
        print("✅ 风险平价优化器") 
        print("✅ 投资组合再平衡器")
        print("✅ PortfolioWeights数据类")
    else:
        print("❌ 部分功能测试失败")
    
    print("=== 测试完成 ===")
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)