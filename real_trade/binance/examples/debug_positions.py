#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Binance Futures 持仓调试工具

诊断为什么能看到订单历史但看不到持仓。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from real_trade.binance import BinanceStore


def debug_positions():
    """调试持仓信息"""

    print("\n" + "=" * 60)
    print("Binance Futures 持仓调试")
    print("=" * 60 + "\n")

    # 使用你的 API 密钥
    API_KEY = "ER6I4vNFBvA4A6G7EoXraXeOEWKzGNlYS66myQ2429eWFqNTz5QyUoNmZsh0I7NR"
    API_SECRET = "KKMSQtZeBVnpeTYLELY4Z5VLxcTPcJtHibr5HSj4gpeNIKVmP3OlPXrEQtpkLpkG"

    try:
        # 创建 Store
        print("正在连接 Binance Futures Demo Trading...")
        store = BinanceStore.get_instance(
            apikey=API_KEY,
            secret=API_SECRET,
            testnet=True,
            market_type="future",
        )
        print("✓ 连接成功\n")

        exchange = store.exchange

        # 1. 获取账户信息
        print("=" * 60)
        print("1. 账户信息")
        print("-" * 60)
        try:
            balance = exchange.fetch_balance()
            print(f"✓ USDT 总余额: {balance['USDT']['total']:.2f}")
            print(f"  可用余额: {balance['USDT']['free']:.2f}")
            print(f"  冻结余额: {balance['USDT']['used']:.2f}")
        except Exception as e:
            print(f"✗ 获取余额失败: {e}")

        # 2. 获取订单历史
        print("\n" + "=" * 60)
        print("2. 最近的订单历史")
        print("-" * 60)
        try:
            orders = exchange.fetch_orders("BTC/USDT", limit=10)
            print(f"✓ 找到 {len(orders)} 个订单\n")
            for order in orders[-5:]:  # 显示最近 5 个
                status = order['status']
                side = order['side']
                order_type = order['type']
                amount = order['amount']
                filled = order['filled']
                price = order.get('average') or order.get('price', 0)

                print(f"订单 ID: {order['id']}")
                print(f"  状态: {status}")
                print(f"  方向: {side}")
                print(f"  类型: {order_type}")
                print(f"  数量: {amount:.6f} BTC")
                print(f"  成交: {filled:.6f} BTC")
                print(f"  价格: ${price:,.2f}")
                print()
        except Exception as e:
            print(f"✗ 获取订单失败: {e}")

        # 3. 获取持仓（方法 1：fetch_positions）
        print("=" * 60)
        print("3. 持仓查询（方法 1：fetch_positions）")
        print("-" * 60)
        try:
            # 不传参数，获取所有持仓
            positions = exchange.fetch_positions()
            print(f"✓ 返回 {len(positions)} 个持仓记录\n")

            active_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]

            if active_positions:
                print(f"找到 {len(active_positions)} 个活跃持仓：\n")
                for pos in active_positions:
                    symbol = pos['symbol']
                    contracts = float(pos.get('contracts', 0))
                    side = pos.get('side', 'unknown')
                    entry_price = float(pos.get('entryPrice', 0))
                    unrealized_pnl = float(pos.get('unrealizedPnl', 0))

                    print(f"交易对: {symbol}")
                    print(f"  方向: {side}")
                    print(f"  数量: {contracts:.6f}")
                    print(f"  开仓价: ${entry_price:,.2f}")
                    print(f"  未实现盈亏: ${unrealized_pnl:.2f}")
                    print()
            else:
                print("⚠️ 没有活跃持仓（所有持仓数量为 0）")
                print("\n可能原因：")
                print("1. 订单是限价单，尚未成交")
                print("2. 订单已成交并立即平仓")
                print("3. 订单被拒绝或取消")
                print("4. Demo Trading 数据延迟")

        except Exception as e:
            print(f"✗ fetch_positions 失败: {e}")
            import traceback
            traceback.print_exc()

        # 4. 获取持仓（方法 2：通过余额推断）
        print("\n" + "=" * 60)
        print("4. 持仓查询（方法 2：通过余额）")
        print("-" * 60)
        try:
            balance = exchange.fetch_balance()
            print("所有资产：")
            for currency, info in balance.items():
                if isinstance(info, dict) and info.get('total', 0) != 0:
                    print(f"  {currency}: {info['total']}")
        except Exception as e:
            print(f"✗ 获取余额失败: {e}")

        # 5. 获取未成交订单
        print("\n" + "=" * 60)
        print("5. 未成交订单")
        print("-" * 60)
        try:
            open_orders = exchange.fetch_open_orders("BTC/USDT")
            if open_orders:
                print(f"✓ 找到 {len(open_orders)} 个未成交订单\n")
                for order in open_orders:
                    print(f"订单 ID: {order['id']}")
                    print(f"  方向: {order['side']}")
                    print(f"  类型: {order['type']}")
                    print(f"  数量: {order['amount']:.6f} BTC")
                    print(f"  价格: ${order['price']:,.2f}")
                    print()
            else:
                print("✓ 没有未成交订单")
        except Exception as e:
            print(f"✗ 获取未成交订单失败: {e}")

        # 6. 获取持仓模式
        print("\n" + "=" * 60)
        print("6. 持仓模式检查")
        print("-" * 60)
        try:
            # Binance Futures 有两种持仓模式
            # 单向持仓（One-way）和 双向持仓（Hedge）
            position_mode = exchange.fapiPrivateGetPositionSideDual()
            dual_side = position_mode.get('dualSidePosition', False)

            if dual_side:
                print("✓ 当前模式: 双向持仓模式（Hedge Mode）")
                print("  可以同时持有多空仓位")
            else:
                print("✓ 当前模式: 单向持仓模式（One-way Mode）")
                print("  只能持有单向仓位")
        except Exception as e:
            print(f"⚠️ 无法获取持仓模式: {e}")

        print("\n" + "=" * 60)
        print("调试完成")
        print("=" * 60 + "\n")

        print("📋 诊断建议：")
        print("1. 检查订单状态是否为 'closed' 或 'filled'")
        print("2. 如果订单是限价单，可能未成交")
        print("3. 如果是市价单，检查是否立即被平仓")
        print("4. Demo Trading 可能有数据延迟，稍后再查询")
        print("5. 检查持仓模式是否正确")
        print()

    except Exception as e:
        print(f"\n✗ 连接失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_positions()
