#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级示例批量测试脚本
Batch Test Script for Enterprise Examples
"""

import subprocess
import sys
import os
from pathlib import Path

def run_example(example_path, timeout=30):
    """运行单个示例并返回结果"""
    try:
        # 构建完整的文件路径
        full_path = Path(example_path).resolve()
        
        # 构建命令
        cmd = [sys.executable, str(full_path)]
        
        print(f"🏃‍♂️ 正在运行: {example_path}")
        
        # 运行命令
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=full_path.parent
        )
        
        if result.returncode == 0:
            print(f"✅ 成功: {example_path}")
            return True, result.stdout
        else:
            print(f"❌ 失败: {example_path}")
            print(f"错误输出: {result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        print(f"⏰ 超时: {example_path}")
        return False, "Timeout"
    except Exception as e:
        print(f"💥 异常: {example_path} - {str(e)}")
        return False, str(e)

def test_enterprise_examples():
    """测试所有企业级示例"""
    print("🧪 Backtrader 企业级示例批量测试")
    print("=" * 50)
    
    # 企业级示例列表
    enterprise_examples = [
        "examples/scheduler_logging_demo.py",
        "samples/risk-management/risk_management_demo.py",
        "samples/monitoring-alerting/monitoring_alerting_demo.py",
        "samples/configuration-management/config_management_demo.py"
    ]
    
    results = {}
    
    for example in enterprise_examples:
        success, output = run_example(example, timeout=60)
        results[example] = {
            'success': success,
            'output': output
        }
        print("-" * 30)
    
    # 输出汇总
    print("\n📊 测试结果汇总:")
    print("=" * 50)
    
    success_count = 0
    for example, result in results.items():
        status = "✅ 通过" if result['success'] else "❌ 失败"
        print(f"{status} {example}")
        if result['success']:
            success_count += 1
    
    print(f"\n📈 总体统计: {success_count}/{len(enterprise_examples)} 个示例通过测试")
    
    return results

if __name__ == "__main__":
    test_results = test_enterprise_examples()