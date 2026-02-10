#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
检查 Binance Futures Demo Trading 可用交易对

诊断为什么 ETH/USDT 订单显示成功但官网看不到记录。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from real_trade.binance import BinanceStore


def check_available_symbols():
    """检查可用交易对"""

    print("\n" + "=" * 60)
    print("检查 Binance Futures Demo Trading 可用交易对")
    print("=" * 60 + "\n")

    # API 密钥
    API_KEY = "ER6I4vNFBvA4A6G7EoXraXeOEWKzGNlYS66myQ2429eWFqNTz5QyUoNmZsh0I7NR"
    API_SECRET = "KKMSQtZeBVnpeTYLELY4Z5VLxcTPcJtHibr5HSj4gpeNIKVmP3OlPXrEQtpkLpkG"

    try:
        # 连接
        print("正在连接 Binance Futures Demo Trading...")
        store = BinanceStore.get_instance(
            apikey=API_KEY,
            secret=API_SECRET,
            testnet=True,
            market_type="future",
        )
        exchange = store.exchange
        print("✓ 连接成功\n")

        # 1. 加载市场信息
        print("=" * 60)
        print("1. 加载市场信息")
        print("=" * 60)

        markets = exchange.load_markets()
        print(f"✓ 找到 {len(markets)} 个交易对\n")

        # 2. 查找 ETH 相关交易对
        print("=" * 60)
        print("2. ETH 相关的永续合约")
        print("=" * 60)

        eth_markets = {k: v for k, v in markets.items() if 'ETH' in k and v.get('type') == 'swap'}

        if eth_markets:
            print(f"找到 {len(eth_markets)} 个 ETH 永续合约：\n")
            for symbol, market in eth_markets.items():
                print(f"Symbol: {symbol}")
                print(f"  ID: {market['id']}")
                print(f"  Base: {market['base']}")
                print(f"  Quote: {market['quote']}")
                print(f"  Settle: {market.get('settle', 'N/A')}")
                print(f"  Type: {market['type']}")
                print(f"  Active: {market.get('active', False)}")

                # 检查最小订单大小
                limits = market.get('limits', {})
                amount_limits = limits.get('amount', {})
                cost_limits = limits.get('cost', {})

                print(f"  最小数量: {amount_limits.get('min', 'N/A')}")
                print(f"  最小金额: {cost_limits.get('min', 'N/A')}")
                print()
        else:
            print("⚠️ 未找到 ETH 永续合约\n")

        # 3. 查找常用的永续合约
        print("=" * 60)
        print("3. 常用永续合约（USDT 结算）")
        print("=" * 60)

        common_symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT', 'SOL/USDT:USDT']

        for symbol in common_symbols:
            if symbol in markets:
                market = markets[symbol]
                print(f"✓ {symbol}")
                print(f"  ID: {market['id']}")
                print(f"  Active: {market.get('active', False)}")

                limits = market.get('limits', {})
                cost_limits = limits.get('cost', {})
                print(f"  最小订单金额: {cost_limits.get('min', 'N/A')} USDT")
                print()
            else:
                print(f"✗ {symbol} - 不可用\n")

        # 4. 测试获取 ETH 行情
        print("=" * 60)
        print("4. 测试获取 ETH 行情")
        print("=" * 60)

        test_symbols = ['ETH/USDT', 'ETH/USDT:USDT', 'ETHUSDT']

        for symbol in test_symbols:
            try:
                ticker = exchange.fetch_ticker(symbol)
                print(f"✓ {symbol} - 行情获取成功")
                print(f"  最新价: ${ticker['last']:,.2f}")
                print()
            except Exception as e:
                print(f"✗ {symbol} - 行情获取失败: {e}\n")

        # 5. 检查最近的订单历史
        print("=" * 60)
        print("5. 最近的订单历史")
        print("=" * 60)

        try:
            # 不指定 symbol，获取所有订单
            orders = exchange.fetch_orders(limit=10)

            if orders:
                print(f"✓ 找到 {len(orders)} 个订单\n")
                for order in orders:
                    print(f"订单 ID: {order['id']}")
                    print(f"  Symbol: {order['symbol']}")
                    print(f"  Side: {order['side']}")
                    print(f"  Amount: {order['amount']}")
                    print(f"  Status: {order['status']}")
                    print(f"  Timestamp: {order.get('datetime', 'N/A')}")
                    print()
            else:
                print("⚠️ 没有找到订单历史\n")
        except Exception as e:
            print(f"✗ 获取订单历史失败: {e}\n")

        # 6. 建议
        print("=" * 60)
        print("📋 诊断建议")
        print("=" * 60)
        print()
        print("如果 ETH/USDT:USDT 存在且 active=True：")
        print("  → 应该使用 'ETH/USDT:USDT' 作为交易对")
        print()
        print("如果只有 ETH/USDT 但订单历史为空：")
        print("  → 可能 CCXT 返回了假数据，订单实际未提交")
        print()
        print("建议使用最小订单金额 ≥ $100 的交易对")
        print("  → BTC/USDT:USDT 最小订单通常 $100")
        print("  → ETH/USDT:USDT 最小订单通常 $10-$100")
        print()

    except Exception as e:
        print(f"\n✗ 检查失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_available_symbols()
