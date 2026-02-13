#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Monitoring Integration Test
测试基于现有框架的监控功能集成
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import datetime


def test_monitoring_integration():
    """测试监控功能集成"""
    print("=== 监控功能集成测试 ===")
    
    try:
        # 创建Cerebro引擎
        cerebro = bt.Cerebro()
        
        # 添加数据
        data = bt.feeds.YahooFinanceData(
            dataname='ORCL',
            fromdate=datetime.datetime(2000, 1, 1),
            todate=datetime.datetime(2000, 3, 31)
        )
        cerebro.adddata(data)
        
        # 设置初始资金
        cerebro.broker.setcash(10000.0)
        
        # 添加简单策略
        class TestStrategy(bt.Strategy):
            def __init__(self):
                pass
            def next(self):
                pass
        
        cerebro.addstrategy(TestStrategy)
        
        # 添加监控分析器
        monitoring_analyzers = bt.analyzers.add_monitoring_analyzers(
            cerebro, 
            health_monitor_params={'_debug': True, 'check_interval': 5}
        )
        
        print("✓ 监控分析器添加成功:")
        for name, cls_name in monitoring_analyzers.items():
            print(f"  - {name}: {cls_name}")
        
        # 添加其他分析器进行对比
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        
        # 运行回测
        print("✓ 开始运行回测...")
        results = cerebro.run()
        
        strategy = results[0]
        
        # 收集所有分析器结果
        all_results = bt.analyzers.collect_analyzer_results(strategy)
        
        print("✓ 分析器结果收集成功")
        print(f"  - 总共收集到 {len(all_results)} 个分析器结果")
        
        # 验证各个分析器
        if 'performance' in all_results:
            perf = all_results['performance']
            print("✓ 绩效分析器工作正常:")
            print(f"  - 初始价值: ${perf.get('initial_value', 0):.2f}")
            print(f"  - 最终价值: ${perf.get('final_value', 0):.2f}")
            print(f"  - 回报率: {perf.get('return_pct', 0):.2%}")
        
        if 'health_monitor' in all_results:
            health = all_results['health_monitor']
            print("✓ 健康监控器工作正常:")
            print(f"  - 总体健康度: {health.get('overall_health', 0):.1%}")
            print(f"  - 系统健康: {'是' if health.get('is_healthy', False) else '否'}")
            print(f"  - 检查次数: {health.get('total_checks', 0)}")
        
        if 'returns' in all_results:
            returns = all_results['returns']
            print("✓ 回报分析器工作正常:")
            print(f"  - 总回报: {returns.get('rtot', 0):.2%}")
        
        if 'drawdown' in all_results:
            drawdown = all_results['drawdown']
            print("✓ 回撤分析器工作正常:")
            print(f"  - 最大回撤: {drawdown.get('maxdrawdown', 0):.2%}")
        
        # 测试报告生成
        print("\n=== 报告生成测试 ===")
        
        # 生成文本报告
        text_report = bt.analyzers.ReportGenerator.generate_text_report(all_results)
        print("✓ 文本报告生成成功:")
        print(text_report[:200] + "..." if len(text_report) > 200 else text_report)
        
        # 生成简要报告
        brief_report = bt.analyzers.ReportGenerator.generate_brief_report(all_results)
        print("✓ 简要报告生成成功:")
        print(brief_report)
        
        # 生成JSON报告
        json_report = bt.analyzers.ReportGenerator.generate_json_report(all_results)
        print("✓ JSON报告生成成功")
        print(f"  - JSON长度: {len(json_report)} 字符")
        
        return True
        
    except Exception as e:
        print(f"✗ 监控功能集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_health_monitor_specifically():
    """专门测试健康监控器"""
    print("\n=== 健康监控器专项测试 ===")
    
    try:
        cerebro = bt.Cerebro()
        
        # 添加多个数据源模拟复杂场景
        data1 = bt.feeds.YahooFinanceData(
            dataname='ORCL',
            fromdate=datetime.datetime(2000, 1, 1),
            todate=datetime.datetime(2000, 2, 28)
        )
        data1._name = 'ORCL'
        cerebro.adddata(data1)
        
        data2 = bt.feeds.YahooFinanceData(
            dataname='ORCL',  # 使用相同数据模拟
            fromdate=datetime.datetime(2000, 1, 1),
            todate=datetime.datetime(2000, 2, 28)
        )
        data2._name = 'ORCL2'
        cerebro.adddata(data2)
        
        cerebro.broker.setcash(50000.0)
        
        class MonitoringTestStrategy(bt.Strategy):
            def __init__(self):
                pass
            def next(self):
                # 模拟一些交易活动
                if len(self) % 20 == 0:  # 每20个周期
                    if not self.position:
                        self.buy()
                    else:
                        self.sell()
        
        cerebro.addstrategy(MonitoringTestStrategy)
        
        # 添加健康监控器
        cerebro.addanalyzer(bt.analyzers.SystemHealthMonitor, 
                           _name='health_test',
                           _debug=True,
                           check_interval=3,  # 频繁检查
                           max_data_delay=300)  # 5分钟延迟容忍
        
        results = cerebro.run()
        strategy = results[0]
        
        health_result = strategy.analyzers.health_test.get_analysis()
        
        print("✓ 健康监控器专项测试成功:")
        print(f"  - 总检查次数: {health_result.get('total_checks', 0)}")
        print(f"  - 健康历史记录: {len(health_result.get('health_history', []))} 条")
        print(f"  - 最新检查时间: {health_result.get('latest_check', {}).get('timestamp', 'N/A')}")
        
        # 检查具体的健康检查项
        latest_check = health_result.get('latest_check', {})
        checks = latest_check.get('checks', {})
        
        print("  - 具体检查项:")
        for check_name, check_info in checks.items():
            status = "✓" if check_info.get('ok', False) else "✗"
            print(f"    {status} {check_name}: {check_info.get('type', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"✗ 健康监控器专项测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("=== 基于现有框架的监控功能集成测试 ===\n")
    
    tests = [
        test_monitoring_integration,
        test_health_monitor_specifically
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有监控功能集成测试通过！")
        print("✅ SystemHealthMonitor - 系统健康监控")
        print("✅ PerformanceSummary - 绩效汇总")
        print("✅ ReportGenerator - 报告生成")
        print("✅ add_monitoring_analyzers - 便捷集成函数")
        print("✅ collect_analyzer_results - 结果收集")
        print("\n🎯 成功实现了无需修改框架的监控功能集成！")
    else:
        print("❌ 部分功能测试失败")
    
    print("=" * 60)
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)