#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级功能完整性验证脚本
Enterprise Features Integrity Verification Script
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_module_imports():
    """测试所有企业级模块导入"""
    print("🧪 模块导入测试")
    print("=" * 30)
    
    modules_to_test = [
        ('config', '配置管理'),
        ('risk', '风险控制'),
        ('monitoring', '监控告警'),
        ('scheduler', '任务调度'),
        ('logging', '日志增强'),
        ('storage', '数据存储'),
        ('messaging', '消息队列')
    ]
    
    results = {}
    
    for module_name, description in modules_to_test:
        try:
            module = getattr(__import__('backtrader'), module_name)
            print(f"✅ {description} ({module_name}): 导入成功")
            results[module_name] = True
        except Exception as e:
            print(f"❌ {description} ({module_name}): 导入失败 - {e}")
            results[module_name] = False
    
    return results

def test_core_functions():
    """测试核心功能函数"""
    print("\n🔧 核心功能测试")
    print("=" * 30)
    
    import backtrader as bt
    
    functions_to_test = [
        # 配置管理
        ('config.get_config_manager', '获取配置管理器'),
        ('config.setup_project_structure', '设置项目结构'),
        
        # 风险控制
        ('risk.enable_risk_control', '启用风险控制'),
        ('risk.PreTradeRiskEngine', '事前风控引擎'),
        
        # 监控告警
        ('monitoring.create_monitoring_service', '创建监控服务'),
        ('monitoring.MonitoringDashboard', '监控仪表板'),
        
        # 任务调度
        ('scheduler.enable_scheduler', '启用任务调度'),
        
        # 日志增强
        ('logging.setup_logger', '设置日志系统'),
    ]
    
    results = {}
    
    for func_path, description in functions_to_test:
        try:
            # 动态获取函数
            module_path, func_name = func_path.rsplit('.', 1)
            module = eval(f'bt.{module_path}')
            func = getattr(module, func_name)
            print(f"✅ {description}: 可用")
            results[func_path] = True
        except Exception as e:
            print(f"❌ {description}: 不可用 - {e}")
            results[func_path] = False
    
    return results

def test_example_execution():
    """测试示例执行"""
    print("\n🏃‍♂️ 示例执行测试")
    print("=" * 30)
    
    examples_to_test = [
        ('examples/scheduler_logging_demo.py', '任务调度和日志示例'),
        ('samples/risk-management/risk_management_demo.py', '风控管理示例'),
    ]
    
    results = {}
    
    for example_path, description in examples_to_test:
        if not os.path.exists(example_path):
            print(f"⚠️  {description}: 文件不存在")
            results[example_path] = False
            continue
            
        try:
            print(f"🧪 测试 {description}...")
            # 执行示例的前几行来验证基本功能
            with open(example_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取前50行进行测试
            test_content = '\n'.join(content.split('\n')[:50])
            
            # 创建临时测试环境
            exec_globals = {
                '__name__': '__main__',
                '__file__': example_path,
                'sys': sys,
                'os': os,
            }
            
            exec(test_content, exec_globals)
            print(f"✅ {description}: 基本执行成功")
            results[example_path] = True
            
        except Exception as e:
            print(f"❌ {description}: 执行失败 - {str(e)[:100]}...")
            results[example_path] = False
    
    return results

def main():
    """主测试函数"""
    print("🏛️  Backtrader 企业级功能完整性验证")
    print("=" * 50)
    
    # 执行各项测试
    module_results = test_module_imports()
    function_results = test_core_functions()
    example_results = test_example_execution()
    
    # 汇总结果
    print("\n📊 测试结果汇总")
    print("=" * 50)
    
    total_modules = len(module_results)
    passed_modules = sum(module_results.values())
    print(f"模块导入: {passed_modules}/{total_modules} 通过")
    
    total_functions = len(function_results)
    passed_functions = sum(function_results.values())
    print(f"功能测试: {passed_functions}/{total_functions} 通过")
    
    total_examples = len(example_results)
    passed_examples = sum(example_results.values())
    print(f"示例执行: {passed_examples}/{total_examples} 通过")
    
    overall_score = (passed_modules + passed_functions + passed_examples) / (total_modules + total_functions + total_examples)
    print(f"\n📈 总体通过率: {overall_score:.1%}")
    
    if overall_score >= 0.8:
        print("🎉 企业级功能基本完善，可以正常使用！")
    elif overall_score >= 0.6:
        print("⚠️  功能基本可用，但需要进一步完善")
    else:
        print("❌ 功能存在问题，需要修复")

if __name__ == "__main__":
    main()