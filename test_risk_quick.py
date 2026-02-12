#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Quick Risk Management Unit Tests
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import datetime


def test_risk_sizer():
    """测试风险管理Sizer"""
    print("=== 风险管理Sizer测试 ===")
    
    try:
        # 测试基本功能
        sizer = bt.sizers.RiskBasedSizer(
            risk_per_trade=0.02,
            max_position_pct=0.3,
            _debug=True
        )
        
        print("✓ RiskBasedSizer创建成功")
        print(f"✓ 风险参数: {sizer.p.risk_per_trade}")
        print(f"✓ 最大持仓: {sizer.p.max_position_pct}")
        print(f"✓ ATR倍数: {sizer.p.atr_multiplier}")
        
        # 测试方法存在性
        print(f"✓ _getsizing方法: {hasattr(sizer, '_getsizing')}")
        print(f"✓ _calculate_atr方法: {hasattr(sizer, '_calculate_atr')}")
        
        return True
    except Exception as e:
        print(f"✗ RiskBasedSizer测试失败: {e}")
        return False


def test_risk_analyzer():
    """测试风险分析器"""
    print("\n=== 风险分析器测试 ===")
    
    try:
        # 创建Cerebro环境来测试Analyzer
        cerebro = bt.Cerebro()
        
        # 添加虚拟数据
        data = bt.feeds.YahooFinanceData(
            dataname='ORCL',
            fromdate=datetime.datetime(2000, 1, 1),
            todate=datetime.datetime(2000, 1, 10)
        )
        cerebro.adddata(data)
        
        # 添加策略
        class TestStrategy(bt.Strategy):
            def __init__(self):
                pass
            def next(self):
                pass
        
        cerebro.addstrategy(TestStrategy)
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.RiskAnalyzer, 
                           _name='risk_test',
                           max_drawdown_limit=0.15,
                           max_position_risk=0.3,
                           _debug=True)
        
        # 运行简短测试
        results = cerebro.run()
        strategy = results[0]
        analyzer = strategy.analyzers.risk_test
        
        print("✓ RiskAnalyzer创建成功")
        print(f"✓ 回撤限制: {analyzer.p.max_drawdown_limit}")
        print(f"✓ 持仓风险限制: {analyzer.p.max_position_risk}")
        
        # 测试方法存在性
        print(f"✓ next方法: {hasattr(analyzer, 'next')}")
        print(f"✓ get_analysis方法: {hasattr(analyzer, 'get_analysis')}")
        print(f"✓ _check_position_risk方法: {hasattr(analyzer, '_check_position_risk')}")
        
        # 测试基本功能调用
        analyzer.start()
        print("✓ start方法执行成功")
        
        return True
    except Exception as e:
        print(f"✗ RiskAnalyzer测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_market_state_analyzer():
    """测试市场状态分析器"""
    print("\n=== 市场状态分析器测试 ===")
    
    try:
        # 创建Cerebro环境来测试Analyzer
        cerebro = bt.Cerebro()
        
        # 添加虚拟数据
        data = bt.feeds.YahooFinanceData(
            dataname='ORCL',
            fromdate=datetime.datetime(2000, 1, 1),
            todate=datetime.datetime(2000, 1, 10)
        )
        cerebro.adddata(data)
        
        # 添加策略
        class TestStrategy(bt.Strategy):
            def __init__(self):
                pass
            def next(self):
                pass
        
        cerebro.addstrategy(TestStrategy)
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.MarketStateAnalyzer, 
                           _name='market_test',
                           _debug=True)
        
        # 运行简短测试
        results = cerebro.run()
        strategy = results[0]
        analyzer = strategy.analyzers.market_test
        
        print("✓ MarketStateAnalyzer创建成功")
        print(f"✓ 趋势周期: {analyzer.p.trend_period}")
        print(f"✓ 波动率阈值: {analyzer.p.volatility_threshold}")
        
        # 测试方法存在性
        print(f"✓ next方法: {hasattr(analyzer, 'next')}")
        print(f"✓ get_analysis方法: {hasattr(analyzer, 'get_analysis')}")
        print(f"✓ _analyze_trend方法: {hasattr(analyzer, '_analyze_trend')}")
        
        return True
    except Exception as e:
        print(f"✗ MarketStateAnalyzer测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("=== 风险管理与通知功能单元测试 ===\n")
    
    tests = [
        test_risk_sizer,
        test_risk_analyzer,
        test_market_state_analyzer
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    print("=== 测试完成 ===")
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)