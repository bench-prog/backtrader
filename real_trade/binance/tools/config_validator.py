#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
配置文件验证工具

验证 Binance 配置文件的正确性。
"""

import json
import os
import sys


def validate_config(config_file):
    """验证配置文件"""

    print("\n" + "=" * 60)
    print("配置文件验证工具")
    print("=" * 60)
    print(f"验证文件: {config_file}\n")

    # 确定配置文件路径
    if os.path.isabs(config_file):
        config_path = config_file
    else:
        config_dir = os.path.join(os.path.dirname(__file__), "../config")
        config_path = os.path.join(config_dir, config_file)

    # 检查文件是否存在
    if not os.path.exists(config_path):
        print(f"✗ 错误: 配置文件不存在")
        print(f"  路径: {config_path}")
        return False

    print(f"✓ 文件存在: {config_path}\n")

    # 尝试加载 JSON
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        print("✓ JSON 格式正确\n")
    except json.JSONDecodeError as e:
        print(f"✗ JSON 格式错误:")
        print(f"  {e}")
        return False
    except Exception as e:
        print(f"✗ 读取文件失败:")
        print(f"  {e}")
        return False

    # 验证必需字段
    errors = []
    warnings = []

    # 检查 API 配置
    if "api" not in config:
        errors.append("缺少 'api' 配置")
    else:
        api = config["api"]

        if "market_type" in api:
            if api["market_type"] not in ["spot", "future", "swap"]:
                errors.append(
                    f"'api.market_type' 无效: {api['market_type']} (应为 spot/future/swap)"
                )
        else:
            warnings.append("缺少 'api.market_type'，将使用默认值 'spot'")

        # 检查 API 密钥
        if config.get("data", {}).get("backtest", False):
            if api.get("apikey"):
                warnings.append("回测模式下不需要 API 密钥")
        else:
            if not api.get("apikey"):
                warnings.append("未设置 API Key，仅支持公共数据和回测模式")

    # 检查交易配置
    if "trading" not in config:
        warnings.append("缺少 'trading' 配置，将使用默认值")
    else:
        trading = config["trading"]

        if "initial_cash" in trading:
            if trading["initial_cash"] <= 0:
                errors.append("'trading.initial_cash' 必须大于 0")

        if "commission" in trading:
            if trading["commission"] < 0 or trading["commission"] > 0.1:
                warnings.append(
                    f"'trading.commission' 异常: {trading['commission']} (通常为 0.0001-0.01)"
                )

    # 检查数据配置
    if "data" not in config:
        warnings.append("缺少 'data' 配置，将使用默认值")
    else:
        data = config["data"]

        if "symbol" in data:
            if "/" not in data["symbol"]:
                warnings.append(
                    f"'data.symbol' 格式可能不正确: {data['symbol']} (建议格式: BTC/USDT)"
                )

        if "timeframe" in data:
            valid_timeframes = [
                "1m",
                "3m",
                "5m",
                "15m",
                "30m",
                "1h",
                "2h",
                "4h",
                "6h",
                "8h",
                "12h",
                "1d",
                "3d",
                "1w",
                "1M",
            ]
            if data["timeframe"] not in valid_timeframes:
                warnings.append(
                    f"'data.timeframe' 可能不受支持: {data['timeframe']}"
                )

        if "historical_limit" in data:
            if data["historical_limit"] > 1000:
                warnings.append(
                    f"'data.historical_limit' 过大: {data['historical_limit']} (建议 ≤1000)"
                )

    # 检查代理配置
    if "proxy" not in config:
        warnings.append("缺少 'proxy' 配置，将使用默认值")

    # 打印结果
    print("验证结果:")
    print("-" * 60)

    if errors:
        print(f"\n❌ 发现 {len(errors)} 个错误:\n")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")

    if warnings:
        print(f"\n⚠️  发现 {len(warnings)} 个警告:\n")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")

    if not errors and not warnings:
        print("\n✓ 配置文件完全正确，无错误和警告！")

    print("\n" + "=" * 60)

    # 打印配置摘要
    print("配置摘要:")
    print("-" * 60)
    print(f"  市场类型: {config.get('api', {}).get('market_type', 'spot').upper()}")
    print(
        f"  测试网: {'是' if config.get('api', {}).get('testnet', True) else '否'}"
    )
    print(
        f"  模拟交易: {'是' if config.get('trading', {}).get('paper_trading', True) else '否'}"
    )
    print(
        f"  回测模式: {'是' if config.get('data', {}).get('backtest', False) else '否'}"
    )
    print(f"  交易对: {config.get('data', {}).get('symbol', 'BTC/USDT')}")
    print(f"  时间周期: {config.get('data', {}).get('timeframe', '1h')}")
    print(
        f"  初始资金: ${config.get('trading', {}).get('initial_cash', 10000.0):,.2f}"
    )
    print("=" * 60 + "\n")

    return len(errors) == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python config_validator.py <配置文件名>")
        print("示例: python config_validator.py futures_testnet.json")
        sys.exit(1)

    config_file = sys.argv[1]
    success = validate_config(config_file)

    sys.exit(0 if success else 1)
