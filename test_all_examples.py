#!/usr/bin/env python3
"""
系统性测试所有real-trade示例文件
"""

import os
import subprocess
import sys
from pathlib import Path


def test_example(file_path, timeout=30):
    """测试单个示例文件"""
    print(f"\n🔍 测试: {os.path.basename(file_path)}")
    print("-" * 50)

    try:
        # 使用subprocess运行，设置超时
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(file_path),
        )

        if result.returncode == 0:
            print("✅ 运行成功")
            if result.stdout:
                # 只显示前几行输出
                lines = result.stdout.strip().split("\n")
                for line in lines[:10]:
                    print(f"   {line}")
                if len(lines) > 10:
                    print(f"   ... (共{len(lines)}行输出)")
            return True
        else:
            print("❌ 运行失败")
            print(f"   错误码: {result.returncode}")
            if result.stderr:
                error_lines = result.stderr.strip().split("\n")
                for line in error_lines[:5]:
                    print(f"   {line}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ 运行超时 ({timeout}秒)")
        return False
    except Exception as e:
        print(f"💥 运行异常: {e}")
        return False


def main():
    """主测试函数"""
    # 示例目录
    examples_dir = Path("/Users/boalyh/CLionProjects/backtrader/real_trade/examples")

    if not examples_dir.exists():
        print("❌ 示例目录不存在")
        return

    # 获取所有.py文件
    py_files = list(examples_dir.glob("*.py"))
    py_files.sort()

    print(f"🎯 发现 {len(py_files)} 个示例文件")
    print("=" * 60)

    # 分类测试
    successful = []
    failed = []
    timeout_files = []

    # 先测试确定能运行的核心示例
    core_examples = [
        "quick_start.py",
        "full_framework_demo.py",
        "ai_trading_demo.py",
        "hf_trading_demo.py",
        "multi_asset_demo.py",
        "portfolio_optimization_demo.py",
    ]

    print("🚀 优先测试核心示例:")
    for filename in core_examples:
        file_path = examples_dir / filename
        if file_path.exists():
            if test_example(str(file_path)):
                successful.append(filename)
            else:
                failed.append(filename)

    # 测试其他示例
    print("\n📋 测试其他示例:")
    for py_file in py_files:
        filename = py_file.name
        if filename in core_examples:
            continue  # 已经测试过了

        # 跳过需要特殊依赖的文件
        skip_patterns = [
            "live_trading",
            "quickstart",
            "config_example",
            "check_available_symbols",
            "query_orders",
            "testnet_futures_test",
        ]
        if any(pattern in filename for pattern in skip_patterns):
            print(f"\n⏭️  跳过: {filename} (需要特殊依赖)")
            continue

        if test_example(str(py_file)):
            successful.append(filename)
        else:
            failed.append(filename)

    # 输出总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"✅ 成功运行: {len(successful)} 个")
    print(f"❌ 运行失败: {len(failed)} 个")

    if successful:
        print("\n🟢 成功示例:")
        for filename in successful:
            print(f"   • {filename}")

    if failed:
        print("\n🔴 失败示例:")
        for filename in failed:
            print(f"   • {filename}")


if __name__ == "__main__":
    main()
