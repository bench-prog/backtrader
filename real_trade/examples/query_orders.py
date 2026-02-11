#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
查询指定订单 ID

帮助用户在官网查找特定订单。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from real_trade.stores import BinanceStore


def query_specific_order():
    """查询特定订单"""

    print("\n" + "=" * 60)
    print("查询最近的订单")
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

        symbol = "ETH/USDT:USDT"

        # 获取所有订单（不限制数量）
        print("=" * 60)
        print("获取所有 ETH 订单历史")
        print("=" * 60)

        try:
            # 尝试获取更多订单
            all_orders = exchange.fetch_orders(symbol, limit=50)

            print(f"✓ 找到 {len(all_orders)} 个订单\n")

            if all_orders:
                print("最近 10 个订单：")
                print("-" * 60)

                for i, order in enumerate(all_orders[:10], 1):
                    order_id = order["id"]
                    timestamp = order.get("timestamp", 0)
                    datetime_str = order.get("datetime", "N/A")
                    side = order["side"]
                    amount = order["amount"]
                    status = order["status"]
                    price = order.get("average") or order.get("price", "N/A")

                    print(f"{i}. 订单 ID: {order_id}")
                    print(f"   时间: {datetime_str}")
                    print(f"   方向: {side.upper()}")
                    print(f"   数量: {amount} ETH")
                    print(
                        f"   价格: ${price:,.2f}"
                        if isinstance(price, (int, float))
                        else f"   价格: {price}"
                    )
                    print(f"   状态: {status}")
                    print()

                print("=" * 60)
                print("📋 如何在官网查找")
                print("=" * 60)
                print()
                print("1. 访问 Demo Trading Futures:")
                print("   https://testnet.binancefuture.com")
                print()
                print("2. 登录后，点击:")
                print("   Orders → Order History")
                print()
                print("3. 搜索以下订单 ID（任选其一）:")
                for order in all_orders[:3]:
                    print(
                        f"   - {order['id']} ({order['side'].upper()}, {order['datetime']})"
                    )
                print()
                print("4. 确保设置:")
                print("   - 交易对: ETHUSDT")
                print("   - 时间范围: 全部或最近 7 天")
                print("   - 订单状态: 全部")
                print()

        except Exception as e:
            print(f"✗ 获取订单失败: {e}\n")

        # 查看当前持仓
        print("=" * 60)
        print("当前持仓")
        print("=" * 60)

        positions = exchange.fetch_positions()
        active_pos = [p for p in positions if float(p.get("contracts", 0)) != 0]

        if active_pos:
            print(f"✓ 找到 {len(active_pos)} 个活跃持仓\n")
            for pos in active_pos:
                print(f"Symbol: {pos['symbol']}")
                print(f"  Side: {pos['side']}")
                print(f"  Contracts: {pos['contracts']}")
                print(f"  Entry Price: ${float(pos['entryPrice']):,.2f}")
                print(f"  Unrealized PnL: ${float(pos.get('unrealizedPnl', 0)):.2f}")
                print()
        else:
            print("⚠️ 没有活跃持仓\n")

    except Exception as e:
        print(f"\n✗ 查询失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    query_specific_order()
