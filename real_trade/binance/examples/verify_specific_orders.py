#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
验证特定订单是否真的存在于交易所

逐个查询订单ID，验证哪些是真实的，哪些可能是本地缓存。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from real_trade.binance import BinanceStore


def verify_specific_orders():
    """验证特定订单"""

    print("\n" + "=" * 60)
    print("验证订单是否真实存在于交易所")
    print("=" * 60 + "\n")

    # API 密钥
    API_KEY = "ER6I4vNFBvA4A6G7EoXraXeOEWKzGNlYS66myQ2429eWFqNTz5QyUoNmZsh0I7NR"
    API_SECRET = "KKMSQtZeBVnpeTYLELY4Z5VLxcTPcJtHibr5HSj4gpeNIKVmP3OlPXrEQtpkLpkG"

    # 之前查询到的所有订单ID
    order_ids = [
        ("8272388913", "BUY", "09:54:31", "用户找到了 ✓"),
        ("8272389123", "SELL", "09:54:35", "用户找到了 ✓"),
        ("8272399246", "BUY", "09:59:05", "用户没找到"),
        ("8272399278", "SELL", "09:59:09", "用户没找到"),
        ("8272408380", "BUY", "10:03:19", "用户没找到"),
        ("8272408567", "SELL", "10:03:23", "用户没找到"),
        ("8272414989", "BUY", "10:05:36", "用户没找到"),
        ("8272415245", "SELL", "10:05:41", "用户没找到"),
        ("8272415736", "BUY", "10:05:53", "用户没找到"),
        ("8272416165", "SELL", "10:05:58", "用户没找到"),
    ]

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

        # 逐个验证订单
        print("=" * 60)
        print("逐个验证订单（通过 fetch_order）")
        print("=" * 60)
        print()

        verified_count = 0
        failed_count = 0

        for order_id, expected_side, expected_time, user_status in order_ids:
            print(f"订单 {order_id} ({expected_side}, {expected_time})")
            print(f"  用户状态: {user_status}")

            try:
                # 尝试通过订单ID查询
                order = exchange.fetch_order(order_id, symbol)

                print(f"  ✓ API 返回订单详情:")
                print(f"    订单 ID: {order['id']}")
                print(f"    状态: {order['status']}")
                print(f"    方向: {order['side']}")
                print(f"    数量: {order['amount']}")
                print(f"    成交: {order['filled']}")
                print(f"    时间: {order.get('datetime', 'N/A')}")

                # 检查订单是否真的成交
                if order['status'] == 'closed' and order['filled'] > 0:
                    print(f"    → 订单真实存在且已成交 ✓")
                    verified_count += 1
                else:
                    print(f"    → 订单存在但状态异常: {order['status']}")

            except Exception as e:
                print(f"  ✗ API 查询失败: {e}")
                print(f"    → 订单可能不存在于交易所！")
                failed_count += 1

            print()

        # 总结
        print("=" * 60)
        print("验证总结")
        print("=" * 60)
        print(f"总订单数: {len(order_ids)}")
        print(f"API 验证成功: {verified_count}")
        print(f"API 验证失败: {failed_count}")
        print()

        if failed_count > 0:
            print("⚠️ 发现问题：")
            print(f"  {failed_count} 个订单无法通过 API 查询到")
            print("  可能原因：")
            print("  1. fetch_orders() 返回的是缓存数据")
            print("  2. 这些订单实际未提交到交易所")
            print("  3. 订单ID是本地生成的，非交易所返回")
            print()

        # 再次使用 fetch_orders 查询
        print("=" * 60)
        print("使用 fetch_orders 重新查询")
        print("=" * 60)
        print()

        try:
            all_orders = exchange.fetch_orders(symbol, limit=100)
            print(f"✓ fetch_orders 返回 {len(all_orders)} 个订单")
            print()

            # 检查哪些订单在列表中
            returned_ids = [str(order['id']) for order in all_orders]

            print("检查订单是否在 fetch_orders 返回的列表中：")
            for order_id, _, _, user_status in order_ids:
                in_list = order_id in returned_ids
                status = "在列表中 ✓" if in_list else "不在列表中 ✗"
                print(f"  {order_id}: {status} ({user_status})")

        except Exception as e:
            print(f"✗ fetch_orders 失败: {e}")

        print()
        print("=" * 60)
        print("📋 诊断建议")
        print("=" * 60)
        print()
        print("如果有订单无法通过 fetch_order 查询到：")
        print("  → 说明这些订单可能只是 CCXT 本地缓存")
        print("  → 未真正提交到交易所")
        print()
        print("如果只有前2个订单能找到：")
        print("  → 可能官网有数据延迟")
        print("  → 或者只有这2个订单真正提交了")
        print()

    except Exception as e:
        print(f"\n✗ 验证失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    verify_specific_orders()
