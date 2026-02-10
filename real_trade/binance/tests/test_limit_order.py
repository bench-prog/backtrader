#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
限价单测试 - Binance Futures Demo Trading

测试限价买入和限价卖出功能。
设置合理的限价，确保订单能够成交。
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from real_trade.binance import BinanceStore


def test_limit_order():
    """测试限价单"""

    print("\n" + "=" * 60)
    print("限价单测试")
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

        # 获取当前价格
        ticker = exchange.fetch_ticker("ETH/USDT:USDT")
        current_price = ticker['last']
        bid = ticker['bid']
        ask = ticker['ask']

        print(f"当前行情:")
        print(f"  最新价: ${current_price:,.2f}")
        print(f"  买一价: ${bid:,.2f}")
        print(f"  卖一价: ${ask:,.2f}")
        print()

        # 测试参数
        test_amount = 0.05  # 0.05 ETH，约 $130

        # ==========================================
        # 测试 1: 限价买入（略高于卖一价，快速成交）
        # ==========================================
        print("=" * 60)
        print("测试 1: 限价买入")
        print("=" * 60)

        # 设置限价略高于卖一价，确保能成交
        buy_price = round(ask * 1.0005, 2)  # 高于卖一价 0.05%

        print(f"下单数量: {test_amount} ETH")
        print(f"限价: ${buy_price:,.2f} (略高于卖一价，确保成交)")
        print(f"预计成本: ${test_amount * buy_price:.2f}\n")

        buy_order = exchange.create_limit_buy_order("ETH/USDT:USDT", test_amount, buy_price)

        print("✓ 买入订单已提交")
        print(f"  订单 ID: {buy_order['id']}")
        print(f"  状态: {buy_order['status']}")
        print(f"  类型: {buy_order['type']}")
        print(f"  限价: ${buy_order['price']:,.2f}")
        print()

        # 等待订单成交
        print("等待订单成交...")
        for i in range(10):
            time.sleep(2)
            order_status = exchange.fetch_order(buy_order['id'], "ETH/USDT:USDT")

            if order_status['status'] == 'closed':
                print(f"✓ 订单已成交 (等待 {(i+1)*2} 秒)")
                print(f"  成交数量: {order_status['filled']} ETH")
                print(f"  成交价格: ${order_status.get('average', 0):,.2f}")
                break
            elif order_status['status'] == 'open':
                print(f"  [{i+1}] 订单未成交，继续等待...")
            else:
                print(f"  订单状态: {order_status['status']}")
        else:
            print("⚠️ 订单等待超时，取消订单...")
            exchange.cancel_order(buy_order['id'], "ETH/USDT:USDT")
            print("✗ 测试失败：订单未能成交")
            return

        print()

        # 查看持仓
        print("查询持仓...")
        positions = exchange.fetch_positions()
        active_pos = [p for p in positions if float(p.get('contracts', 0)) != 0]

        eth_pos = None
        for pos in active_pos:
            if pos['symbol'] == 'ETH/USDT:USDT':
                eth_pos = pos
                print(f"✓ 持仓建立成功")
                print(f"  方向: {pos['side']}")
                print(f"  数量: {float(pos['contracts']):.6f} ETH")
                print(f"  开仓价: ${float(pos['entryPrice']):,.2f}")
                print()

        if not eth_pos:
            print("✗ 未找到持仓")
            return

        # ==========================================
        # 测试 2: 限价卖出（略低于买一价，快速成交）
        # ==========================================
        print("=" * 60)
        print("测试 2: 限价卖出（平仓）")
        print("=" * 60)

        # 重新获取行情
        ticker = exchange.fetch_ticker("ETH/USDT:USDT")
        bid = ticker['bid']

        # 设置限价略低于买一价，确保能成交
        sell_price = round(bid * 0.9995, 2)  # 低于买一价 0.05%

        print(f"平仓数量: {test_amount} ETH")
        print(f"限价: ${sell_price:,.2f} (略低于买一价，确保成交)\n")

        sell_order = exchange.create_limit_sell_order("ETH/USDT:USDT", test_amount, sell_price)

        print("✓ 卖出订单已提交")
        print(f"  订单 ID: {sell_order['id']}")
        print(f"  状态: {sell_order['status']}")
        print(f"  类型: {sell_order['type']}")
        print(f"  限价: ${sell_order['price']:,.2f}")
        print()

        # 等待订单成交
        print("等待订单成交...")
        for i in range(10):
            time.sleep(2)
            order_status = exchange.fetch_order(sell_order['id'], "ETH/USDT:USDT")

            if order_status['status'] == 'closed':
                print(f"✓ 订单已成交 (等待 {(i+1)*2} 秒)")
                print(f"  成交数量: {order_status['filled']} ETH")
                print(f"  成交价格: ${order_status.get('average', 0):,.2f}")
                break
            elif order_status['status'] == 'open':
                print(f"  [{i+1}] 订单未成交，继续等待...")
            else:
                print(f"  订单状态: {order_status['status']}")
        else:
            print("⚠️ 订单等待超时，取消订单...")
            exchange.cancel_order(sell_order['id'], "ETH/USDT:USDT")
            print("✗ 测试失败：订单未能成交")
            return

        print()

        # 查看平仓后的持仓
        print("查询平仓后持仓...")
        positions = exchange.fetch_positions()
        active_pos = [p for p in positions if float(p.get('contracts', 0)) != 0]

        eth_pos = [p for p in active_pos if p['symbol'] == 'ETH/USDT:USDT']
        if not eth_pos:
            print("✓ 持仓已完全平仓")
        else:
            print(f"⚠️ 剩余持仓: {float(eth_pos[0]['contracts']):.6f} ETH")
        print()

        print("=" * 60)
        print("✓ 限价单测试完成！")
        print("=" * 60)
        print("  - 限价买入订单成功")
        print("  - 订单成交成功")
        print("  - 持仓建立成功")
        print("  - 限价卖出订单成功")
        print("  - 持仓平仓成功")
        print()

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_limit_order()
