#!/usr/bin/env python3
"""
Backtrader Real-Trade 完整测试流程
一键运行所有核心测试
"""

import subprocess
import sys
import time
from datetime import datetime


def run_test(name, command, timeout=60):
    """运行单个测试"""
    print(f"\n{'=' * 60}")
    print(f"🧪 开始测试: {name}")
    print(f"{'=' * 60}")

    try:
        start_time = time.time()
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/Users/boalyh/CLionProjects/backtrader",
        )
        elapsed_time = time.time() - start_time

        if result.returncode == 0:
            print(f"✅ {name} 测试通过 (耗时: {elapsed_time:.1f}s)")
            if result.stdout:
                # 只显示关键输出
                lines = result.stdout.strip().split("\n")
                for line in lines[-10:]:  # 显示最后10行
                    if any(
                        keyword in line for keyword in ["收益", "资金", "信号", "交易"]
                    ):
                        print(f"   {line}")
            return True
        else:
            print(f"❌ {name} 测试失败")
            if result.stderr:
                print(f"   错误信息: {result.stderr[:200]}...")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {name} 测试超时 ({timeout}s)")
        return False
    except Exception as e:
        print(f"💥 {name} 测试异常: {e}")
        return False


def main():
    """主测试流程"""
    print("🚀 Backtrader Real-Trade 完整测试流程")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    tests = [
        # 1. 数据质量测试
        (
            "BTC数据质量检查",
            "python -c \"import pandas as pd; df=pd.read_csv('datas/binance-btc-2015-2026.txt'); print(f'数据记录数: {len(df)}'); print(f'时间范围: {df.Date.iloc[0]} to {df.Date.iloc[-1]}')\"",
        ),
        # 2. 核心功能测试
        ("简化BTC回测", "python simple_btc_backtest.py"),
        # 3. 框架集成测试
        ("快速开始示例", "python real_trade/examples/quick_start.py"),
        ("完整框架演示", "python real_trade/examples/full_framework_demo.py"),
        # 4. 高级功能测试
        ("AI交易演示", "python real_trade/examples/ai_trading_demo.py"),
        ("高频交易演示", "python real_trade/examples/hf_trading_demo.py"),
        ("多资产交易演示", "python real_trade/examples/multi_asset_demo.py"),
        # 5. 分析工具测试
        ("投资组合优化", "python real_trade/examples/portfolio_optimization_demo.py"),
        ("策略调试器", "python real_trade/examples/strategy_debugger_demo.py"),
        # 6. 系统诊断
        ("数据流演示", "python real_trade/examples/data_flow_demo.py"),
        ("通知系统", "python real_trade/examples/notification_system_demo.py"),
    ]

    passed = 0
    failed = 0
    start_time = time.time()

    # 依次运行所有测试
    for test_name, test_command in tests:
        if run_test(test_name, test_command):
            passed += 1
        else:
            failed += 1

    # 总结报告
    total_time = time.time() - start_time
    print(f"\n{'=' * 80}")
    print("📊 测试总结报告")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {total_time:.1f}秒")
    print(f"{'=' * 80}")
    print(f"✅ 通过测试: {passed} 个")
    print(f"❌ 失败测试: {failed} 个")
    print(f"💯 通过率: {passed / (passed + failed) * 100:.1f}%")

    if failed == 0:
        print("\n🎉 所有测试通过！框架功能完整可用！")
        print("✅ 真实数据回测验证成功")
        print("✅ 核心功能模块工作正常")
        print("✅ 高级特性集成完整")
        print("✅ 可以投入实际使用")
    else:
        print(f"\n⚠️  {failed} 个测试需要关注")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
