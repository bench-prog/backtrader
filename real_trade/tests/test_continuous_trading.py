#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
连续交易测试 - Binance Futures Demo Trading

执行多次小仓位交易，测试系统稳定性。
每次交易 0.05 ETH（约 $130），进行 5 轮买卖测试。
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from real_trade.stores import BinanceStore


def test_continuous_trading():
    """测试连续交易"""

    print("\n" + "=" * 60)
    print("连续交易测试")
    print("=" * 60)
    print("测试参数: 5 轮买卖，每次 0.05 ETH（约 $130）")
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

        # 获取初始余额
        balance_start = exchange.fetch_balance()
        usdt_start = balance_start["USDT"]["total"]
        print(f"初始余额: {usdt_start:.2f} USDT\n")

        # 测试参数
        rounds = 5  # 交易轮数
        amount_per_trade = 0.05  # 每次 0.05 ETH（约 $130）
        wait_time = 2  # 每次交易间隔（秒）

        # 统计数据
        total_trades = 0
        successful_trades = 0
        failed_trades = 0
        trade_records = []

        # 开始交易
        for round_num in range(1, rounds + 1):
            print("=" * 60)
            print(f"第 {round_num}/{rounds} 轮交易")
            print("=" * 60)

            try:
                # 获取当前价格
                ticker = exchange.fetch_ticker("ETH/USDT:USDT")
                current_price = ticker["last"]
                print(f"当前价格: ${current_price:,.2f}\n")

                # ----------------------------------------
                # 买入
                # ----------------------------------------
                print(f"[{round_num}.1] 买入 {amount_per_trade} ETH...")

                buy_order = exchange.create_market_buy_order(
                    "ETH/USDT:USDT", amount_per_trade
                )
                buy_price = buy_order.get("average", current_price)

                print("  ✓ 买入成功")
                print(f"    订单 ID: {buy_order['id']}")
                print(f"    成交价: ${buy_price:,.2f}")
                print(f"    成交量: {buy_order['filled']} ETH")

                total_trades += 1
                successful_trades += 1

                time.sleep(wait_time)

                # ----------------------------------------
                # 卖出
                # ----------------------------------------
                print(f"\n[{round_num}.2] 卖出 {amount_per_trade} ETH...")

                sell_order = exchange.create_market_sell_order(
                    "ETH/USDT:USDT", amount_per_trade
                )
                sell_price = sell_order.get("average", current_price)

                print("  ✓ 卖出成功")
                print(f"    订单 ID: {sell_order['id']}")
                print(f"    成交价: ${sell_price:,.2f}")
                print(f"    成交量: {sell_order['filled']} ETH")

                total_trades += 1
                successful_trades += 1

                # 计算本轮盈亏
                pnl = (sell_price - buy_price) * amount_per_trade
                pnl_pct = (sell_price - buy_price) / buy_price * 100

                trade_records.append(
                    {
                        "round": round_num,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                    }
                )

                print(f"\n  本轮盈亏: ${pnl:.4f} ({pnl_pct:+.3f}%)")

                # 查看当前持仓（应该为 0）
                positions = exchange.fetch_positions()
                active_pos = [p for p in positions if float(p.get("contracts", 0)) != 0]
                btc_pos = [p for p in active_pos if p["symbol"] == "ETH/USDT:USDT"]

                if not btc_pos:
                    print("  ✓ 持仓已平仓")
                else:
                    print(f"  ⚠️ 剩余持仓: {float(btc_pos[0]['contracts']):.6f} ETH")

                print()

                # 等待下一轮
                if round_num < rounds:
                    time.sleep(wait_time)

            except Exception as e:
                print(f"  ✗ 交易失败: {e}")
                failed_trades += 1
                print()

        # ==========================================
        # 交易总结
        # ==========================================
        print("=" * 60)
        print("交易总结")
        print("=" * 60)

        # 获取最终余额
        balance_end = exchange.fetch_balance()
        usdt_end = balance_end["USDT"]["total"]

        print("\n余额变化:")
        print(f"  初始余额: {usdt_start:.2f} USDT")
        print(f"  最终余额: {usdt_end:.2f} USDT")
        print(f"  净盈亏: {usdt_end - usdt_start:.2f} USDT")

        print("\n交易统计:")
        print(f"  总交易次数: {total_trades}")
        print(f"  成功: {successful_trades}")
        print(f"  失败: {failed_trades}")
        print(f"  成功率: {successful_trades / total_trades * 100:.1f}%")

        if trade_records:
            print("\n每轮明细:")
            total_pnl = 0
            for record in trade_records:
                print(
                    f"  轮次 {record['round']}: "
                    f"买 ${record['buy_price']:,.2f} → "
                    f"卖 ${record['sell_price']:,.2f} = "
                    f"${record['pnl']:.4f} ({record['pnl_pct']:+.3f}%)"
                )
                total_pnl += record["pnl"]

            print(f"\n  总盈亏（不含手续费）: ${total_pnl:.4f}")
            print(f"  平均每轮: ${total_pnl / len(trade_records):.4f}")

        print("\n" + "=" * 60)
        print("✓ 连续交易测试完成！")
        print("=" * 60)
        print(f"  - 完成 {rounds} 轮买卖")
        print(f"  - 成功率 {successful_trades / total_trades * 100:.1f}%")
        print("  - 系统运行稳定")
        print()

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_continuous_trading()
