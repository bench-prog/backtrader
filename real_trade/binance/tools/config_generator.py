#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
配置文件生成器

快速生成 Binance 配置文件的交互式工具。
"""

import json
import os
import sys


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Binance 配置文件生成器")
    print("=" * 60)
    print("快速创建自定义配置文件\n")

    # 获取市场类型
    print("1. 选择市场类型:")
    print("  [1] Futures (合约)")
    print("  [2] Spot (现货)")
    choice = input("\n请选择 (1/2) [默认:1]: ").strip() or "1"

    if choice == "2":
        market_type = "spot"
        timeframe_default = "1h"
    else:
        market_type = "future"
        timeframe_default = "15m"

    # API 配置
    print("\n2. API 配置:")
    print("  (如果使用回测模式，可以跳过 API 密钥)")
    apikey = input("  API Key [回车跳过]: ").strip()
    secret = input("  API Secret [回车跳过]: ").strip()

    use_testnet = input("  使用 Demo Trading (y/n) [默认:y]: ").strip().lower() or "y"
    testnet = use_testnet == "y"

    # 交易配置
    print("\n3. 交易配置:")
    paper_trading = (
        input("  模拟交易 (y/n) [默认:y]: ").strip().lower() or "y"
    ) == "y"
    initial_cash = float(
        input("  初始资金 [默认:10000]: ").strip() or "10000"
    )
    commission = float(
        input("  手续费率 (0.001 = 0.1%) [默认:0.001]: ").strip() or "0.001"
    )

    # 数据配置
    print("\n4. 数据配置:")
    symbol = input(f"  交易对 [默认:BTC/USDT]: ").strip() or "BTC/USDT"
    timeframe = input(f"  时间周期 [默认:{timeframe_default}]: ").strip() or timeframe_default

    backtest = (
        input("  回测模式 (y/n) [默认:y]: ").strip().lower() or "y"
    ) == "y"
    historical_limit = int(
        input("  历史数据数量 [默认:500]: ").strip() or "500"
    )

    # 代理配置
    print("\n5. 代理配置:")
    auto_detect = (
        input("  自动检测系统代理 (y/n) [默认:y]: ").strip().lower() or "y"
    ) == "y"
    proxy_url = ""
    if not auto_detect:
        proxy_url = input("  代理地址 (如 http://127.0.0.1:7890): ").strip()

    # 策略配置（可选）
    print("\n6. 策略配置（可选，回车跳过）:")
    strategy = {}

    if market_type == "future":
        rsi_period = input("  RSI 周期 [默认:7]: ").strip()
        if rsi_period:
            strategy["rsi_period"] = int(rsi_period)
            strategy["rsi_low"] = int(input("  RSI 超卖线 [默认:40]: ").strip() or "40")
            strategy["rsi_high"] = int(input("  RSI 超买线 [默认:60]: ").strip() or "60")
            strategy["ma_fast"] = int(input("  快速均线 [默认:3]: ").strip() or "3")
            strategy["ma_slow"] = int(input("  慢速均线 [默认:10]: ").strip() or "10")
            strategy["trade_size_pct"] = float(
                input("  交易规模比例 [默认:0.3]: ").strip() or "0.3"
            )
            strategy["stop_loss_pct"] = float(
                input("  止损百分比 [默认:5.0]: ").strip() or "5.0"
            )
    else:
        fast_period = input("  快速均线周期 [默认:10]: ").strip()
        if fast_period:
            strategy["fast_period"] = int(fast_period)
            strategy["slow_period"] = int(
                input("  慢速均线周期 [默认:30]: ").strip() or "30"
            )

    strategy["printlog"] = True

    # 构建配置
    config = {
        "api": {
            "apikey": apikey,
            "secret": secret,
            "testnet": testnet,
            "market_type": market_type,
        },
        "trading": {
            "paper_trading": paper_trading,
            "initial_cash": initial_cash,
            "commission": commission,
        },
        "data": {
            "symbol": symbol,
            "timeframe": timeframe,
            "backtest": backtest,
            "historical_limit": historical_limit,
        },
        "strategy": strategy,
        "proxy": {
            "auto_detect": auto_detect,
            "proxy_url": proxy_url,
        },
    }

    # 保存配置
    print("\n7. 保存配置:")
    filename = (
        input("  配置文件名 [默认:my_config.json]: ").strip() or "my_config.json"
    )

    if not filename.endswith(".json"):
        filename += ".json"

    # 确定保存路径
    config_dir = os.path.join(
        os.path.dirname(__file__), "../config"
    )
    config_path = os.path.join(config_dir, filename)

    # 确保目录存在
    os.makedirs(config_dir, exist_ok=True)

    # 保存文件
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("✓ 配置文件已生成！")
    print("=" * 60)
    print(f"文件路径: {config_path}")
    print(f"\n使用方法:")
    print(f'  from real_trade.binance import create_binance_engine_from_config')
    print(f'  store, broker, data, config = create_binance_engine_from_config("{filename}")')
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
