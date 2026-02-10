#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
验证订单是否真正提交到 Demo Trading

诊断为什么订单显示成功但官网看不到记录。
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from real_trade.binance import BinanceStore


def verify_order_submission():
    """验证订单提交"""

    print("\n" + "=" * 60)
    print("验证订单是否真正提交到 Demo Trading")
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

        # 检查 exchange 对象属性
        print("=" * 60)
        print("1. 检查 Exchange 配置")
        print("=" * 60)
        print(f"Exchange ID: {exchange.id}")
        print(f"Exchange Name: {exchange.name}")
        print(f"URLs:")
        for key, value in exchange.urls.items():
            print(f"  {key}: {value}")
        print()

        # 测试参数
        symbol = "ETH/USDT:USDT"
        test_amount = 0.05

        # 步骤 1: 获取提交前的订单历史
        print("=" * 60)
        print("2. 提交订单前的订单历史")
        print("=" * 60)

        try:
            orders_before = exchange.fetch_orders(symbol, limit=5)
            print(f"✓ 找到 {len(orders_before)} 个历史订单")
            if orders_before:
                print("  最近订单：")
                for order in orders_before[:3]:
                    print(f"    - ID: {order['id']}, Side: {order['side']}, Amount: {order['amount']}")
            print()
        except Exception as e:
            print(f"⚠️ 无法获取订单历史: {e}\n")
            orders_before = []

        # 步骤 2: 提交市价买单
        print("=" * 60)
        print("3. 提交测试订单")
        print("=" * 60)
        print(f"交易对: {symbol}")
        print(f"数量: {test_amount} ETH")
        print(f"类型: 市价买单\n")

        buy_order = exchange.create_market_buy_order(symbol, test_amount)

        print("✓ 订单已提交（本地返回）")
        print(f"  订单 ID: {buy_order['id']}")
        print(f"  订单类型: {buy_order.get('type', 'N/A')}")
        print(f"  订单状态: {buy_order.get('status', 'N/A')}")
        print(f"  成交数量: {buy_order.get('filled', 'N/A')}")
        print(f"  成交价格: {buy_order.get('average', 'N/A')}")
        print(f"  时间戳: {buy_order.get('timestamp', 'N/A')}")
        print()

        # 保存订单 ID
        order_id = buy_order['id']

        # 等待
        print("等待 3 秒...")
        time.sleep(3)
        print()

        # 步骤 3: 通过订单 ID 查询订单
        print("=" * 60)
        print("4. 通过订单 ID 查询订单")
        print("=" * 60)
        print(f"查询订单 ID: {order_id}\n")

        try:
            order_detail = exchange.fetch_order(order_id, symbol)
            print("✓ 成功从 API 查询到订单")
            print(f"  订单 ID: {order_detail['id']}")
            print(f"  订单状态: {order_detail['status']}")
            print(f"  订单类型: {order_detail['type']}")
            print(f"  方向: {order_detail['side']}")
            print(f"  数量: {order_detail['amount']}")
            print(f"  成交: {order_detail['filled']}")
            print(f"  价格: {order_detail.get('average', 'N/A')}")
            print()
        except Exception as e:
            print(f"✗ 无法查询订单: {e}")
            print("  → 这表明订单可能未真正提交到交易所！\n")

        # 步骤 4: 获取提交后的订单历史
        print("=" * 60)
        print("5. 提交订单后的订单历史")
        print("=" * 60)

        try:
            orders_after = exchange.fetch_orders(symbol, limit=5)
            print(f"✓ 找到 {len(orders_after)} 个历史订单")

            if len(orders_after) > len(orders_before):
                print(f"  → 新增了 {len(orders_after) - len(orders_before)} 个订单")
                print("  最新订单：")
                for order in orders_after[:3]:
                    is_new = order['id'] == order_id
                    marker = " ← 刚提交的订单" if is_new else ""
                    print(f"    - ID: {order['id']}, Side: {order['side']}, Amount: {order['amount']}{marker}")
            else:
                print("  ⚠️ 订单数量没有变化！")
                print("  → 订单可能未真正提交到交易所")
            print()
        except Exception as e:
            print(f"✗ 无法获取订单历史: {e}\n")

        # 步骤 5: 查看持仓
        print("=" * 60)
        print("6. 查看持仓")
        print("=" * 60)

        positions = exchange.fetch_positions()
        active_pos = [p for p in positions if float(p.get('contracts', 0)) != 0]

        if active_pos:
            print(f"✓ 找到 {len(active_pos)} 个活跃持仓")
            for pos in active_pos:
                if 'ETH' in pos['symbol']:
                    print(f"  Symbol: {pos['symbol']}")
                    print(f"  Side: {pos['side']}")
                    print(f"  Contracts: {pos['contracts']}")
                    print(f"  Entry Price: {pos.get('entryPrice', 'N/A')}")
                    print()
        else:
            print("⚠️ 没有活跃持仓")
            print("  → 如果订单成功，应该有持仓\n")

        # 步骤 6: 平仓
        print("=" * 60)
        print("7. 平仓测试")
        print("=" * 60)

        # 检查是否有 ETH 持仓
        eth_positions = [p for p in active_pos if p['symbol'] == 'ETH/USDT:USDT']

        if eth_positions:
            contracts = float(eth_positions[0]['contracts'])
            print(f"发现持仓: {contracts} ETH")
            print("执行平仓...\n")

            sell_order = exchange.create_market_sell_order(symbol, abs(contracts))

            print("✓ 平仓订单已提交")
            print(f"  订单 ID: {sell_order['id']}")
            print(f"  平仓数量: {sell_order['filled']}")
            print()
        else:
            print("⚠️ 没有 ETH 持仓需要平仓\n")

        # 诊断结论
        print("=" * 60)
        print("📋 诊断结论")
        print("=" * 60)
        print()
        print("如果订单真正提交到交易所，应该满足：")
        print("  1. ✓ 能通过订单 ID 查询到订单详情")
        print("  2. ✓ 订单历史数量增加")
        print("  3. ✓ 能看到持仓")
        print()
        print("如果以上都失败，可能原因：")
        print("  - 订单只在 CCXT 本地模拟，未发送到交易所")
        print("  - API 配置问题（密钥、权限、环境）")
        print("  - Demo Trading 环境问题")
        print()
        print("建议：")
        print("  - 检查官网 Futures → Orders 界面")
        print("  - 确认使用的是 Futures (不是 Spot)")
        print("  - 确认 API 密钥是 Futures Demo Trading 的密钥")
        print()

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    verify_order_submission()
