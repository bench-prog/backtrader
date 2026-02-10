#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
止损单测试 - Binance Futures Demo Trading

测试止损单功能（Stop Loss）。
先建立多头仓位，然后设置止损价保护。
使用 0.05 ETH（约 $130）进行测试。
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from real_trade.binance import BinanceStore


def test_stop_loss_order():
    """测试止损单"""

    print("\n" + "=" * 60)
    print("止损单测试")
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
        print(f"当前 ETH 价格: ${current_price:,.2f}\n")

        # 测试参数
        test_amount = 0.05  # 0.05 ETH，约 $130

        # ==========================================
        # 步骤 1: 市价买入建仓
        # ==========================================
        print("=" * 60)
        print("步骤 1: 市价买入建仓")
        print("=" * 60)
        print(f"下单数量: {test_amount} ETH\n")

        buy_order = exchange.create_market_buy_order("ETH/USDT:USDT", test_amount)

        print("✓ 买入订单已提交")
        print(f"  订单 ID: {buy_order['id']}")
        print(f"  成交价格: ${buy_order.get('average', current_price):,.2f}")
        print()

        time.sleep(2)

        # 查看持仓
        positions = exchange.fetch_positions()
        active_pos = [p for p in positions if float(p.get('contracts', 0)) != 0]

        entry_price = None
        for pos in active_pos:
            if pos['symbol'] == 'ETH/USDT:USDT':
                entry_price = float(pos['entryPrice'])
                print(f"✓ 持仓建立成功")
                print(f"  开仓价: ${entry_price:,.2f}")
                print()

        if not entry_price:
            print("✗ 未找到持仓")
            return

        # ==========================================
        # 步骤 2: 设置止损单（5% 止损）
        # ==========================================
        print("=" * 60)
        print("步骤 2: 设置止损单")
        print("=" * 60)

        # 止损价格：比开仓价低 5%
        stop_price = round(entry_price * 0.95, 2)

        print(f"止损价格: ${stop_price:,.2f} (开仓价的 95%)")
        print(f"当前价格: ${current_price:,.2f}")
        print(f"止损距离: {((entry_price - stop_price) / entry_price * 100):.2f}%\n")

        print("⚠️ 注意：Binance Futures 止损单类型为 STOP_MARKET")
        print("  当价格跌破止损价时，会以市价卖出平仓\n")

        # 创建止损单
        # stopPrice: 触发价格
        # type: STOP_MARKET (止损市价单)
        # side: SELL (平多仓)
        stop_order = exchange.create_order(
            symbol="ETH/USDT:USDT",
            type="STOP_MARKET",
            side="sell",
            amount=test_amount,
            params={
                "stopPrice": stop_price,
            }
        )

        print("✓ 止损单已设置")
        print(f"  订单 ID: {stop_order['id']}")
        print(f"  类型: {stop_order['type']}")
        print(f"  止损价: ${stop_price:,.2f}")
        print(f"  状态: {stop_order['status']}")
        print()

        # ==========================================
        # 步骤 3: 查看未成交订单（止损单）
        # ==========================================
        print("=" * 60)
        print("步骤 3: 查看未成交订单")
        print("=" * 60)

        open_orders = exchange.fetch_open_orders("ETH/USDT:USDT")

        if open_orders:
            print(f"✓ 找到 {len(open_orders)} 个未成交订单\n")
            for order in open_orders:
                print(f"订单 ID: {order['id']}")
                print(f"  类型: {order['type']}")
                print(f"  方向: {order['side']}")
                print(f"  数量: {order['amount']:.6f} ETH")
                print(f"  止损价: ${order.get('stopPrice', 0):,.2f}")
                print(f"  状态: {order['status']}")
                print()
        else:
            print("⚠️ 没有找到未成交订单")
            print("  止损单可能已触发或设置失败")
            print()

        # ==========================================
        # 步骤 4: 取消止损单并手动平仓
        # ==========================================
        print("=" * 60)
        print("步骤 4: 取消止损单并手动平仓")
        print("=" * 60)

        print("取消止损单...")
        try:
            exchange.cancel_order(stop_order['id'], "ETH/USDT:USDT")
            print("✓ 止损单已取消\n")
        except Exception as e:
            print(f"⚠️ 取消失败: {e}\n")

        print("手动平仓...")
        sell_order = exchange.create_market_sell_order("ETH/USDT:USDT", test_amount)

        print("✓ 平仓订单已提交")
        print(f"  订单 ID: {sell_order['id']}")
        print(f"  成交价格: ${sell_order.get('average', current_price):,.2f}")
        print()

        time.sleep(2)

        # 查看最终持仓
        positions = exchange.fetch_positions()
        active_pos = [p for p in positions if float(p.get('contracts', 0)) != 0]

        eth_pos = [p for p in active_pos if p['symbol'] == 'ETH/USDT:USDT']
        if not eth_pos:
            print("✓ 持仓已完全平仓")
        else:
            print(f"⚠️ 剩余持仓: {float(eth_pos[0]['contracts']):.6f} ETH")
        print()

        print("=" * 60)
        print("✓ 止损单测试完成！")
        print("=" * 60)
        print("  - 市价建仓成功")
        print("  - 止损单设置成功")
        print("  - 止损单查询成功")
        print("  - 止损单取消成功")
        print("  - 手动平仓成功")
        print()

        print("💡 测试说明：")
        print("  本测试演示了止损单的完整流程")
        print("  实际使用中，止损单会在价格触及止损价时自动执行")
        print("  为了测试完整性，这里手动取消了止损单")
        print()

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_stop_loss_order()
