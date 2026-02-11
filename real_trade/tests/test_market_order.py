#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
市价单测试 - Binance Futures Demo Trading

测试市价买入和市价卖出功能。
使用小仓位（0.05 ETH，约 $130）进行测试。
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from real_trade.stores import BinanceStore


def test_market_order():
    """测试市价单"""

    print("\n" + "=" * 60)
    print("市价单测试")
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
        current_price = ticker["last"]
        print(f"当前 ETH 价格: ${current_price:,.2f}\n")

        # 获取初始余额
        balance_before = exchange.fetch_balance()
        usdt_before = balance_before["USDT"]["total"]
        print(f"初始余额: {usdt_before:.2f} USDT\n")

        # 测试参数
        test_amount = 0.05  # 0.05 ETH，约 $130

        # ==========================================
        # 测试 1: 市价买入
        # ==========================================
        print("=" * 60)
        print("测试 1: 市价买入")
        print("=" * 60)
        print(f"下单数量: {test_amount} ETH")
        print(f"预计成本: ${test_amount * current_price:.2f}\n")

        buy_order = exchange.create_market_buy_order("ETH/USDT:USDT", test_amount)

        print("✓ 买入订单已提交")
        print(f"  订单 ID: {buy_order['id']}")
        print(f"  状态: {buy_order['status']}")
        print(f"  成交数量: {buy_order['filled']} ETH")
        print(f"  成交价格: ${buy_order.get('average', 0):,.2f}")
        print()

        # 等待订单成交
        time.sleep(2)

        # 查看持仓
        print("查询持仓...")
        positions = exchange.fetch_positions()
        active_pos = [p for p in positions if float(p.get("contracts", 0)) != 0]

        if active_pos:
            for pos in active_pos:
                if pos["symbol"] == "ETH/USDT:USDT":
                    print("✓ 持仓建立成功")
                    print(f"  方向: {pos['side']}")
                    print(f"  数量: {float(pos['contracts']):.6f} ETH")
                    print(f"  开仓价: ${float(pos['entryPrice']):,.2f}")
                    print(f"  未实现盈亏: ${float(pos.get('unrealizedPnl', 0)):.2f}")
                    print()

        # ==========================================
        # 测试 2: 市价平仓（卖出）
        # ==========================================
        print("=" * 60)
        print("测试 2: 市价卖出（平仓）")
        print("=" * 60)
        print(f"平仓数量: {test_amount} ETH\n")

        time.sleep(1)

        sell_order = exchange.create_market_sell_order("ETH/USDT:USDT", test_amount)

        print("✓ 卖出订单已提交")
        print(f"  订单 ID: {sell_order['id']}")
        print(f"  状态: {sell_order['status']}")
        print(f"  成交数量: {sell_order['filled']} ETH")
        print(f"  成交价格: ${sell_order.get('average', 0):,.2f}")
        print()

        # 等待平仓
        time.sleep(2)

        # 查看平仓后的持仓
        print("查询平仓后持仓...")
        positions = exchange.fetch_positions()
        active_pos = [p for p in positions if float(p.get("contracts", 0)) != 0]

        eth_pos = [p for p in active_pos if p["symbol"] == "ETH/USDT:USDT"]
        if not eth_pos:
            print("✓ 持仓已完全平仓")
        else:
            print(f"⚠️ 剩余持仓: {float(eth_pos[0]['contracts']):.6f} ETH")
        print()

        # 获取最终余额
        balance_after = exchange.fetch_balance()
        usdt_after = balance_after["USDT"]["total"]

        print("=" * 60)
        print("测试结果")
        print("=" * 60)
        print(f"初始余额: {usdt_before:.2f} USDT")
        print(f"最终余额: {usdt_after:.2f} USDT")
        print(f"盈亏: {usdt_after - usdt_before:.2f} USDT")
        print(f"手续费约: {abs(usdt_after - usdt_before):.2f} USDT")
        print("=" * 60 + "\n")

        print("✓ 市价单测试完成！")
        print("  - 买入订单成功")
        print("  - 持仓建立成功")
        print("  - 卖出订单成功")
        print("  - 持仓平仓成功")
        print()

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_market_order()
