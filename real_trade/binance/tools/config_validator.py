#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
配置文件验证工具

验证 Binance 配置文件的正确性，支持扁平和嵌套两种 JSON 格式。
"""

import json
import os
import sys

VALID_TIMEFRAMES = {
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
}


def _resolve_path(config_file: str) -> str:
    """解析配置文件路径"""
    if os.path.isabs(config_file):
        return config_file
    if os.path.exists(config_file):
        return config_file
    config_dir = os.path.join(os.path.dirname(__file__), "../config")
    return os.path.join(config_dir, config_file)


def _extract_flat(config: dict) -> dict:
    """
    将嵌套/扁平 JSON 统一提取为扁平 key-value。
    返回标准化后的字典。
    """
    nested_keys = {"api", "trading", "data"}
    if not (nested_keys & set(config.keys())):
        # 已经是扁平结构
        return config

    flat = {}
    api = config.get("api", {})
    for k in ("apikey", "secret", "testnet", "market_type"):
        if k in api:
            flat[k] = api[k]

    trading = config.get("trading", {})
    if "paper_trading" in trading:
        flat["paper_trading"] = trading["paper_trading"]
    if "initial_cash" in trading:
        flat["cash"] = trading["initial_cash"]
    if "cash" in trading:
        flat["cash"] = trading["cash"]
    if "commission" in trading:
        flat["commission"] = trading["commission"]

    data_cfg = config.get("data", {})
    for k in ("symbol", "timeframe", "backtest", "historical_limit"):
        if k in data_cfg:
            flat[k] = data_cfg[k]

    proxy_cfg = config.get("proxy", {})
    proxy_url = proxy_cfg.get("proxy_url", "")
    if proxy_url:
        flat["proxy"] = proxy_url

    return flat


def validate_config(config_file: str) -> bool:
    """验证配置文件"""

    print(f"\n{'=' * 60}")
    print("配置文件验证工具")
    print(f"{'=' * 60}")
    print(f"验证文件: {config_file}\n")

    config_path = _resolve_path(config_file)

    if not os.path.exists(config_path):
        print(f"错误: 文件不存在 — {config_path}")
        return False

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        print("JSON 格式正确\n")
    except json.JSONDecodeError as e:
        print(f"JSON 格式错误: {e}")
        return False

    flat = _extract_flat(raw)

    errors = []
    warnings = []

    # symbol
    symbol = flat.get("symbol", "BTC/USDT")
    if "/" not in str(symbol):
        errors.append(f"symbol 格式无效: '{symbol}' (应为 BASE/QUOTE 如 BTC/USDT)")

    # timeframe
    tf = flat.get("timeframe", "1h")
    if tf not in VALID_TIMEFRAMES:
        warnings.append(f"timeframe '{tf}' 可能不受支持")

    # market_type
    mt = flat.get("market_type", "spot")
    if mt not in ("spot", "future", "delivery", "swap"):
        errors.append(f"market_type 无效: '{mt}' (应为 spot/future/delivery)")

    # cash
    cash = flat.get("cash", 10000.0)
    if not isinstance(cash, (int, float)) or cash <= 0:
        errors.append(f"cash 必须为正数, 当前: {cash}")

    # commission
    comm = flat.get("commission", 0.001)
    if isinstance(comm, (int, float)) and (comm < 0 or comm > 0.1):
        warnings.append(f"commission 异常: {comm} (通常为 0.0001 ~ 0.01)")

    # historical_limit
    hl = flat.get("historical_limit", 500)
    if isinstance(hl, int) and hl > 1500:
        warnings.append(f"historical_limit 过大: {hl}")

    # API key vs backtest
    backtest = flat.get("backtest", False)
    if backtest and flat.get("apikey"):
        warnings.append("回测模式下不需要 API 密钥")
    if not backtest and not flat.get("apikey"):
        warnings.append("非回测模式下未设置 API Key")

    # 输出结果
    print("验证结果:")
    print("-" * 60)

    if errors:
        print(f"\n错误 ({len(errors)}):")
        for i, e in enumerate(errors, 1):
            print(f"  {i}. {e}")

    if warnings:
        print(f"\n警告 ({len(warnings)}):")
        for i, w in enumerate(warnings, 1):
            print(f"  {i}. {w}")

    if not errors and not warnings:
        print("\n配置完全正确")

    # 摘要
    print(f"\n{'=' * 60}")
    print("配置摘要:")
    print(f"  交易对: {flat.get('symbol', 'BTC/USDT')}")
    print(f"  时间周期: {flat.get('timeframe', '1h')}")
    print(f"  市场类型: {flat.get('market_type', 'spot')}")
    print(f"  测试网: {'是' if flat.get('testnet', True) else '否'}")
    print(f"  模拟交易: {'是' if flat.get('paper_trading', True) else '否'}")
    print(f"  回测模式: {'是' if backtest else '否'}")
    print(f"  初始资金: ${flat.get('cash', 10000.0):,.2f}")
    print(f"{'=' * 60}\n")

    return len(errors) == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python config_validator.py <配置文件名>")
        print("示例: python config_validator.py my_config.json")
        sys.exit(1)

    success = validate_config(sys.argv[1])
    sys.exit(0 if success else 1)
