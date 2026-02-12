#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Simple Grid Trading Demo - 简化版网格交易演示
============================================

一个更加简洁明了的网格交易示例，便于理解和学习。
使用真实BTC数据进行回测验证。
"""

import math
import os
import sys

import numpy as np
import pandas as pd

import backtrader as bt

# 添加项目路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)


class SimpleGridStrategy(bt.Strategy):
    """简化版网格交易策略"""

    params = (
        ("grid_levels", 8),  # 网格层数
        ("grid_spacing", 0.025),  # 网格间距2.5%
        ("position_size", 0.1),  # 每次交易仓位10%
    )

    def __init__(self):
        self.grid_lines = []  # 网格线价格
        self.active_orders = {}  # 已下未成交订单
        self.active_positions = {}  # 当前持仓

    def start(self):
        """初始化网格"""
        price = self.data.close[0]

        # 在当前价格上下创建对称网格
        for i in range(-self.p.grid_levels // 2, self.p.grid_levels // 2 + 1):
            grid_price = price * (1 + self.p.grid_spacing) ** i
            self.grid_lines.append(grid_price)

        print("🎯 网格策略启动")
        print(f"💰 当前价格: ${price:.2f}")
        print(
            f"📊 网格线: {[f'${p:.2f}' for p in sorted(self.grid_lines)[:3]]} ... {[f'${p:.2f}' for p in sorted(self.grid_lines)[-3:]]}"
        )

    def next(self):
        """每个K线周期执行"""
        current_price = self.data.close[0]

        # 检查网格触发
        for grid_price in self.grid_lines:
            grid_id = f"grid_{grid_price:.2f}"

            # 价格向下穿过网格线（买入信号）
            if (
                len(self.data.close) > 1
                and self.data.close[-1] > grid_price >= current_price
                and grid_id not in self.active_orders
                and grid_id not in self.active_positions
            ):
                self._buy_at_grid(grid_price, grid_id)

            # 价格向上穿过网格线（卖出信号）
            elif (
                grid_id in self.active_positions and current_price >= grid_price * 1.01
            ):  # 1%利润就卖出
                self._sell_at_grid(grid_price, grid_id)

    def _buy_at_grid(self, price, grid_id):
        """在网格线买入"""
        # 计算仓位大小
        cash = self.broker.get_cash()
        size = (cash * self.p.position_size) / price
        size = math.floor(size * 10000) / 10000  # 4位小数精度

        if size > 0:
            order = self.buy(size=size, price=price, exectype=bt.Order.Limit)
            self.active_orders[grid_id] = {"order": order, "price": price, "size": size}
            print(f"📈 买单: ${price:.2f} × {size:.4f}")

    def _sell_at_grid(self, buy_price, grid_id):
        """在网格线卖出"""
        if grid_id in self.active_positions:
            position = self.active_positions[grid_id]
            sell_price = self.data.close[0]
            pnl = (sell_price - position["price"]) * position["size"]

            order = self.sell(size=position["size"])
            print(
                f"📉 卖单: ${position['price']:.2f} → ${sell_price:.2f}, 收益${pnl:.2f}"
            )

            del self.active_positions[grid_id]

    def notify_order(self, order):
        """订单状态通知"""
        if order.status == order.Completed:
            if order.isbuy():
                # 找到对应的网格订单
                for grid_id, order_info in self.active_orders.items():
                    if order_info["order"] == order:
                        self.active_positions[grid_id] = {
                            "price": order.executed.price,
                            "size": order.executed.size,
                        }
                        del self.active_orders[grid_id]
                        break
            # 卖单完成不需要特殊处理


def create_sample_data():
    """创建示例BTC数据（如果没有真实数据）"""
    print("📝 创建模拟BTC数据...")

    dates = pd.date_range("2023-01-01", periods=365, freq="D")
    # 模拟BTC价格走势：长期上涨+短期波动
    trend = np.linspace(16000, 45000, len(dates))
    noise = np.random.normal(0, 0.03, len(dates))  # 3%日波动
    prices = trend * (1 + np.cumsum(noise))

    df = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.005, len(dates))),
            "high": prices * (1 + abs(np.random.normal(0, 0.01, len(dates)))),
            "low": prices * (1 - abs(np.random.normal(0, 0.01, len(dates)))),
            "close": prices,
            "volume": np.random.exponential(1000, len(dates)),
        },
        index=dates,
    )

    return df


def load_real_data():
    """尝试加载真实数据"""
    try:
        data_file = os.path.join(project_root, "datas", "binance-btc-2015-2026.txt")
        if os.path.exists(data_file):
            print("📂 加载真实BTC数据...")
            df = pd.read_csv(data_file)
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
            # 只选择需要的列
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.columns = ["open", "high", "low", "close", "volume"]
            print(f"✅ 加载完成: {len(df)} 条数据")
            return df
    except Exception as e:
        print(f"⚠️ 真实数据加载失败: {e}")

    return None


def main():
    """主函数"""
    print("🤖 Binance简化网格交易演示")
    print("=" * 40)

    # 加载数据
    data = load_real_data()
    if data is None:
        data = create_sample_data()

    # 创建回测引擎
    cerebro = bt.Cerebro()
    cerebro.addstrategy(SimpleGridStrategy)
    cerebro.adddata(bt.feeds.PandasData(dataname=data))
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)

    # 运行回测
    print(f"\n🚀 初始资金: ${cerebro.broker.get_cash():,.2f}")
    cerebro.run()
    print(f"🏁 最终资金: ${cerebro.broker.get_value():,.2f}")
    print(f"📈 收益率: {(cerebro.broker.get_value() / 10000 - 1) * 100:.2f}%")


if __name__ == "__main__":
    main()
