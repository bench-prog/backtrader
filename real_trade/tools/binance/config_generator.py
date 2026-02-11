#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
配置文件生成器

快速生成 Binance 配置文件的交互式工具。
生成的 JSON 文件可直接传给 create_binance_engine_from_config() 使用。
"""

import json
import os


def main():
    print("\n" + "=" * 60)
    print("Binance 配置文件生成器")
    print("=" * 60)
    print("快速创建自定义配置文件\n")

    # 市场类型
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

    # API
    print("\n2. API 配置:")
    print("  (回测模式可跳过 API 密钥)")
    apikey = input("  API Key [回车跳过]: ").strip()
    secret = input("  API Secret [回车跳过]: ").strip()

    use_testnet = input("  使用 Demo Trading (y/n) [默认:y]: ").strip().lower() or "y"
    testnet = use_testnet == "y"

    # 交易
    print("\n3. 交易配置:")
    paper_trading = (input("  模拟交易 (y/n) [默认:y]: ").strip().lower() or "y") == "y"
    cash = float(input("  初始资金 [默认:10000]: ").strip() or "10000")
    commission = float(
        input("  手续费率 (0.001 = 0.1%) [默认:0.001]: ").strip() or "0.001"
    )

    # 数据
    print("\n4. 数据配置:")
    symbol = input("  交易对 [默认:BTC/USDT]: ").strip() or "BTC/USDT"
    timeframe = (
        input(f"  时间周期 [默认:{timeframe_default}]: ").strip() or timeframe_default
    )
    backtest = (input("  回测模式 (y/n) [默认:y]: ").strip().lower() or "y") == "y"
    historical_limit = int(input("  历史数据数量 [默认:500]: ").strip() or "500")

    # 代理
    print("\n5. 代理配置:")
    proxy_url = input("  代理地址 (留空自动检测, 如 http://127.0.0.1:7890): ").strip()

    # 构建扁平结构配置（与 GlobalConfig 对齐）
    config = {
        "exchange": "binance",
        "apikey": apikey,
        "secret": secret,
        "testnet": testnet,
        "market_type": market_type,
        "symbol": symbol,
        "timeframe": timeframe,
        "paper_trading": paper_trading,
        "cash": cash,
        "commission": commission,
        "backtest": backtest,
        "historical_limit": historical_limit,
    }

    if proxy_url:
        config["proxy"] = proxy_url

    # 保存
    print("\n6. 保存配置:")
    filename = input("  配置文件名 [默认:my_config.json]: ").strip() or "my_config.json"
    if not filename.endswith(".json"):
        filename += ".json"

    config_dir = os.path.join(os.path.dirname(__file__), "../config")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, filename)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"Config saved: {config_path}")
    print("\nUsage:")
    print("  from real_trade.utils.config import GlobalConfig")
    print("  from real_trade.stores import BinanceStore")
    print(f'  cfg = GlobalConfig.from_json("{filename}")')
    print("  store = BinanceStore.get_instance(apikey=cfg.apikey, ...)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
