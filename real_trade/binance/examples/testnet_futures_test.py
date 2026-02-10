#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Binance Futures Testnet 连接测试

测试连接到 Binance Futures Testnet 并验证 API 功能。

获取 Testnet API 密钥的步骤：
1. 访问 https://testnet.binancefuture.com/
2. 使用 GitHub 账号登录
3. 点击 [API Key] 生成 API Key 和 Secret
4. 将生成的密钥填入下面的配置中

注意：Testnet 密钥与生产环境完全独立，不会影响真实资金。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from real_trade.binance import BinanceStore


def test_connection():
    """测试 Binance Futures Testnet 连接"""

    print("\n" + "=" * 60)
    print("Binance Futures Testnet 连接测试")
    print("=" * 60 + "\n")

    # 配置 Testnet API 密钥
    # 请替换为你从 https://testnet.binancefuture.com/ 获取的密钥
    API_KEY = "ER6I4vNFBvA4A6G7EoXraXeOEWKzGNlYS66myQ2429eWFqNTz5QyUoNmZsh0I7NR"
    API_SECRET = "KKMSQtZeBVnpeTYLELY4Z5VLxcTPcJtHibr5HSj4gpeNIKVmP3OlPXrEQtpkLpkG"

    if API_KEY == "YOUR_TESTNET_API_KEY":
        print("⚠ 请先配置 Testnet API 密钥！")
        print("\n获取步骤：")
        print("1. 访问 https://testnet.binancefuture.com/")
        print("2. 使用 GitHub 账号登录")
        print("3. 点击 [API Key] 生成密钥")
        print("4. 将密钥填入本文件的 API_KEY 和 API_SECRET 变量中")
        print("\n" + "=" * 60 + "\n")
        return

    try:
        # 创建 Binance Store（Futures 市场）
        print("正在连接 Binance Futures Testnet...")
        store = BinanceStore.get_instance(
            apikey=API_KEY,
            secret=API_SECRET,
            testnet=True,
            market_type="future",  # 使用 futures 市场
        )

        print("✓ Store 创建成功\n")

        # 测试 1: 获取账户余额
        print("测试 1: 获取账户余额")
        print("-" * 60)
        try:
            balance = store.get_balance("USDT")
            print(f"✓ USDT 余额: {balance:.2f}")
        except Exception as e:
            print(f"✗ 获取余额失败: {e}")

        # 测试 2: 获取市场数据
        print("\n测试 2: 获取 BTC/USDT 最新价格")
        print("-" * 60)
        try:
            exchange = store.exchange
            ticker = exchange.fetch_ticker("BTC/USDT")
            print(f"✓ 最新价格: ${ticker['last']:,.2f}")

            # 某些字段在 Futures 市场可能为 None，需要安全处理
            if ticker.get('bid') is not None:
                print(f"  买一价: ${ticker['bid']:,.2f}")
            if ticker.get('ask') is not None:
                print(f"  卖一价: ${ticker['ask']:,.2f}")
            if ticker.get('baseVolume') is not None:
                print(f"  24h 成交量: {ticker['baseVolume']:,.2f} BTC")
        except Exception as e:
            print(f"✗ 获取市场数据失败: {e}")

        # 测试 3: 获取持仓信息
        print("\n测试 3: 获取持仓信息")
        print("-" * 60)
        try:
            # Binance Futures: 不传参数获取所有持仓
            # 注意：Futures 符号格式是 BTC/USDT:USDT，不是 BTC/USDT
            positions = store.get_positions()

            # 过滤出有持仓的
            active_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]

            if active_positions:
                print(f"✓ 找到 {len(active_positions)} 个持仓\n")
                for pos in active_positions:
                    symbol = pos.get('symbol', 'unknown')
                    contracts = float(pos.get('contracts', 0))
                    side = pos.get('side', 'unknown')
                    entry_price = float(pos.get('entryPrice', 0))
                    unrealized_pnl = float(pos.get('unrealizedPnl', 0))

                    print(f"  交易对: {symbol}")
                    print(f"  方向: {side}")
                    print(f"  数量: {contracts:.6f}")
                    print(f"  开仓价: ${entry_price:,.2f}")
                    print(f"  未实现盈亏: ${unrealized_pnl:.2f}")
                    print()
            else:
                print("✓ 当前无持仓")
        except Exception as e:
            print(f"✗ 获取持仓失败: {e}")

        # 测试 4: 获取历史K线数据
        print("\n测试 4: 获取历史 K 线数据")
        print("-" * 60)
        try:
            ohlcv = exchange.fetch_ohlcv("BTC/USDT", "1h", limit=5)
            print(f"✓ 成功获取 {len(ohlcv)} 根 K 线")
            if ohlcv:
                latest = ohlcv[-1]
                print("  最新 K 线:")
                print(f"    开盘: ${latest[1]:,.2f}")
                print(f"    最高: ${latest[2]:,.2f}")
                print(f"    最低: ${latest[3]:,.2f}")
                print(f"    收盘: ${latest[4]:,.2f}")
        except Exception as e:
            print(f"✗ 获取 K 线数据失败: {e}")

        print("\n" + "=" * 60)
        print("✓ 所有测试完成！Testnet 连接正常。")
        print("=" * 60 + "\n")

        print("下一步：")
        print("1. 运行 testnet_live_trading.py 进行实时交易测试")
        print("2. 或者运行带有 backtest=True 的回测模式测试")
        print()

    except Exception as e:
        print(f"\n✗ 连接失败: {e}")
        import traceback

        traceback.print_exc()
        print("\n可能的原因：")
        print("1. API 密钥不正确")
        print("2. 网络连接问题（需要 VPN）")
        print("3. Testnet 服务暂时不可用")
        print()


if __name__ == "__main__":
    test_connection()
