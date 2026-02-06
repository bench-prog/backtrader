#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
模块导入测试

验证所有模块可以正常导入。
"""

import sys
import os

# 添加项目根目录和bybit模块目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
bybit_module = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, bybit_module)

def test_imports():
    """测试所有模块导入"""
    print("Testing module imports...")
    print("=" * 60)

    try:
        # 测试核心组件（直接导入）
        print("✓ Importing core components...")
        from store import BybitStore
        from broker import BybitBroker
        from datafeed import BybitData
        print("  - BybitStore")
        print("  - BybitBroker")
        print("  - BybitData")

        # 测试工具模块
        print("\n✓ Importing utilities...")
        from utils import Config, setup_logger, validate_symbol
        print("  - Config")
        print("  - setup_logger")
        print("  - validate_symbol")

        # 测试策略模块
        print("\n✓ Importing strategies...")
        from strategies import BybitStrategyBase, SimpleMAStrategy
        print("  - BybitStrategyBase")
        print("  - SimpleMAStrategy")

        print("\n" + "=" * 60)
        print("✓ All imports successful!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validators():
    """测试验证器"""
    print("\nTesting validators...")
    print("=" * 60)

    from utils import validate_symbol, validate_timeframe, validate_api_keys

    # 测试交易对验证
    valid, msg = validate_symbol("BTC/USDT")
    assert valid, f"BTC/USDT should be valid: {msg}"
    print("✓ validate_symbol('BTC/USDT') passed")

    valid, msg = validate_symbol("INVALID")
    assert not valid, "INVALID should be invalid"
    print("✓ validate_symbol('INVALID') correctly rejected")

    # 测试时间周期验证
    valid, msg = validate_timeframe("1h")
    assert valid, f"1h should be valid: {msg}"
    print("✓ validate_timeframe('1h') passed")

    valid, msg = validate_timeframe("invalid")
    assert not valid, "invalid should be invalid"
    print("✓ validate_timeframe('invalid') correctly rejected")

    print("=" * 60)
    print("✓ All validator tests passed!")
    print("=" * 60)


def test_config():
    """测试配置"""
    print("\nTesting configuration...")
    print("=" * 60)

    from utils import Config

    # 创建配置
    config = Config(
        symbol="BTC/USDT",
        timeframe="1h",
        testnet=True,
        paper_trading=True
    )

    print(f"✓ Config created: {config.symbol}, {config.timeframe}")

    # 测试字典转换
    config_dict = config.to_dict()
    assert config_dict["symbol"] == "BTC/USDT"
    print("✓ Config.to_dict() works")

    # 测试 JSON 转换
    config_json = config.to_json()
    assert "BTC/USDT" in config_json
    print("✓ Config.to_json() works")

    print("=" * 60)
    print("✓ All configuration tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    print("\n")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║       Real Trade Bybit Module - Import Test Suite           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # 运行测试
    success = True
    success = test_imports() and success
    success = test_validators() and success
    success = test_config() and success

    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
