#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Strategy Debugger Examples - 策略调试器使用示例

展示如何使用策略可视化调试器进行实时监控和调试。
"""

import os
import random
import sys
import time

# 添加正确的导入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from tools.debugger import StrategyVisualDebugger, create_debugger
except ImportError:
    # 如果导入失败，创建简化版本
    class StrategyVisualDebugger:
        def __init__(self, *args, **kwargs):
            pass

        def start_monitoring(self):
            print("调试器: 开始监控")

        def stop_monitoring(self):
            print("调试器: 停止监控")

    def create_debugger(*args, **kwargs):
        return StrategyVisualDebugger()


def simulate_simple_strategy():
    """简单策略模拟"""
    print("=== 简单策略调试演示 ===\n")

    # 创建调试器（禁用图形界面以便在终端运行）
    debugger = create_debugger(
        update_interval=1.0, history_size=500, enable_plotting=False
    )

    # 开始监控
    debugger.start_monitoring()

    # 初始化策略状态
    current_price = 50000.0
    cash = 100000.0
    equity = 100000.0
    position_size = 0.0
    entry_price = 0.0

    print("开始模拟交易...")
    print("-" * 50)

    # 模拟50个时间步
    for step in range(50):
        # 模拟价格波动
        price_change = random.normalvariate(0, 0.01)  # 1%日波动率
        current_price *= 1 + price_change

        # 记录价格
        debugger.record_price(current_price)

        # 简单的移动平均策略
        if step >= 10:
            # 计算简单移动平均
            recent_prices = [price for _, price in list(debugger.price_history)[-10:]]
            if len(recent_prices) >= 10:
                ma_10 = sum(recent_prices) / len(recent_prices)

                # 生成交易信号
                if (
                    current_price > ma_10 * 1.01 and position_size == 0
                ):  # 价格高于均线1%且无持仓
                    # 买入信号
                    signal_strength = min((current_price / ma_10 - 1) * 100, 1.0)
                    debugger.record_signal(
                        "buy", current_price, signal_strength, "价格突破均线"
                    )

                    # 模拟下单
                    position_size = (cash * 0.9) / current_price  # 使用90%资金
                    entry_price = current_price
                    cash -= position_size * current_price
                    equity = cash + position_size * current_price

                    debugger.update_position(
                        "BTCUSDT", "long", position_size, entry_price
                    )
                    print(
                        f"第{step + 1:2d}步: 📈 买入 {position_size:.4f} BTC @ ${current_price:,.2f}"
                    )

                elif (
                    current_price < ma_10 * 0.99 and position_size > 0
                ):  # 价格低于均线1%且有持仓
                    # 卖出信号
                    signal_strength = min((1 - current_price / ma_10) * 100, 1.0)
                    debugger.record_signal(
                        "sell", current_price, signal_strength, "价格跌破均线"
                    )

                    # 模拟平仓
                    pnl = (current_price - entry_price) * position_size
                    cash += position_size * current_price
                    equity = cash
                    position_size = 0

                    debugger.update_position(
                        "BTCUSDT", "long", position_size, entry_price, current_price
                    )
                    print(
                        f"第{step + 1:2d}步: 📉 卖出 {position_size:.4f} BTC @ ${current_price:,.2f} (收益: ${pnl:+.2f})"
                    )

        # 更新策略指标
        positions_value = position_size * current_price if position_size > 0 else 0
        total_value = cash + positions_value

        # 计算简单指标
        win_rate = 0.65  # 假设胜率65%
        profit_factor = 1.8  # 假设盈亏比1.8
        sharpe_ratio = 1.2  # 假设夏普比率1.2

        debugger.update_metrics(
            equity=equity,
            cash=cash,
            positions_value=positions_value,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
        )

        # 每5步输出一次摘要
        if step % 5 == 4:
            print(
                f"第{step + 1:2d}步: 价格 ${current_price:,.2f} | 总资产 ${total_value:,.2f} | "
                f"现金 ${cash:,.2f} | 持仓 ${positions_value:,.2f}"
            )

        time.sleep(0.2)  # 模拟时间间隔

    # 输出最终仪表板
    debugger.print_dashboard()

    # 导出数据
    debugger.export_data("strategy_debug_data.json")

    # 停止监控
    debugger.stop_monitoring()
    print("\n策略模拟完成!")


def demonstrate_advanced_debugging():
    """高级调试功能演示"""
    print("=== 高级调试功能演示 ===\n")

    debugger = StrategyVisualDebugger(enable_plotting=False)
    debugger.start_monitoring()

    # 模拟多品种策略
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    prices = {symbol: 50000.0 + i * 10000 for i, symbol in enumerate(symbols)}
    positions = {symbol: 0.0 for symbol in symbols}
    cash = 100000.0

    print("多品种策略监控:")
    print("-" * 40)

    for step in range(30):
        total_value = cash

        for symbol in symbols:
            # 价格波动
            price_change = random.normalvariate(0, 0.015)
            prices[symbol] *= 1 + price_change
            debugger.record_price(prices[symbol])

            # 随机生成信号
            if random.random() < 0.1:  # 10%概率产生信号
                signal_type = random.choice(["buy", "sell"])
                strength = random.uniform(0.5, 1.0)
                reason = f"{symbol} 技术信号"

                debugger.record_signal(
                    signal_type, prices[symbol], strength, reason, symbol
                )

                if signal_type == "buy" and positions[symbol] == 0:
                    # 模拟买入
                    size = (cash * 0.2) / prices[symbol]  # 使用20%可用资金
                    positions[symbol] = size
                    cash -= size * prices[symbol]
                    debugger.update_position(symbol, "long", size, prices[symbol])
                    print(f"  {symbol}: 📈 买入 {size:.4f} @ ${prices[symbol]:,.2f}")

                elif signal_type == "sell" and positions[symbol] > 0:
                    # 模拟卖出
                    size = positions[symbol]
                    pnl = (prices[symbol] - 50000) * size  # 简化的收益计算
                    cash += size * prices[symbol]
                    debugger.update_position(
                        symbol, "long", size, 50000, prices[symbol]
                    )
                    positions[symbol] = 0
                    print(
                        f"  {symbol}: 📉 卖出 {size:.4f} @ ${prices[symbol]:,.2f} (收益: ${pnl:+.2f})"
                    )

            total_value += positions[symbol] * prices[symbol]

        # 更新指标
        debugger.update_metrics(
            equity=total_value,
            cash=cash,
            positions_value=total_value - cash,
            sharpe_ratio=random.uniform(0.8, 2.0),
            win_rate=random.uniform(0.5, 0.8),
            profit_factor=random.uniform(1.2, 3.0),
        )

        if step % 10 == 9:
            print(f"第{step + 1:2d}步: 总资产 ${total_value:,.2f} | 现金 ${cash:,.2f}")

        time.sleep(0.1)

    debugger.print_dashboard()
    debugger.stop_monitoring()


def demonstrate_signal_analysis():
    """信号分析演示"""
    print("=== 信号分析演示 ===\n")

    debugger = StrategyVisualDebugger(enable_plotting=False)

    # 生成测试信号
    test_signals = [
        ("buy", 49000, 0.8, "RSI超卖"),
        ("hold", 49500, 0.3, "观望"),
        ("buy", 50000, 0.9, "突破阻力位"),
        ("sell", 51000, 0.7, "MACD死叉"),
        ("hold", 50500, 0.2, "震荡整理"),
        ("buy", 49800, 0.6, "支撑位反弹"),
        ("sell", 49200, 0.8, "跌破支撑"),
    ]

    current_price = 50000.0

    print("信号分析:")
    print("-" * 30)

    for i, (signal_type, price, strength, reason) in enumerate(test_signals):
        debugger.record_signal(signal_type, price, strength, reason, "TestStrategy")
        current_price = price

        # 分析信号
        if signal_type == "buy":
            action = (
                "🟢 强烈建议买入"
                if strength > 0.7
                else "🟡 建议买入"
                if strength > 0.5
                else "🔴 弱买入信号"
            )
        elif signal_type == "sell":
            action = (
                "🔴 强烈建议卖出"
                if strength > 0.7
                else "🟡 建议卖出"
                if strength > 0.5
                else "🟢 弱卖出信号"
            )
        else:
            action = "⏸️  观望"

        print(f"信号 {i + 1}: {action}")
        print(f"  类型: {signal_type.upper()}")
        print(f"  价格: ${price:,.2f}")
        print(f"  强度: {strength:.1f}/1.0")
        print(f"  原因: {reason}")
        print()

    # 显示信号统计
    dashboard = debugger.get_dashboard_data()
    perf = dashboard["performance"]

    print("信号统计:")
    print(f"  总信号数: {perf['total_signals']}")
    print(f"  买入信号: {perf['buy_signals']}")
    print(f"  卖出信号: {perf['sell_signals']}")
    print(
        f"  观望信号: {perf['total_signals'] - perf['buy_signals'] - perf['sell_signals']}"
    )


def demonstrate_performance_monitoring():
    """性能监控演示"""
    print("=== 性能监控演示 ===\n")

    debugger = StrategyVisualDebugger(enable_plotting=False)
    debugger.start_monitoring()

    # 模拟策略性能变化
    equity = 100000.0
    cash = 100000.0
    sharpe_history = []
    win_rate_history = []

    print("实时性能监控:")
    print("-" * 40)

    for day in range(20):
        # 模拟每日收益
        daily_return = random.normalvariate(0.001, 0.02)  # 0.1%期望收益，2%波动
        equity *= 1 + daily_return

        # 模拟交易
        if random.random() < 0.3:  # 30%概率有交易
            trade_pnl = random.normalvariate(0, 1000)
            cash += trade_pnl
            equity += trade_pnl

        # 计算动态指标
        sharpe_ratio = max(0, random.normalvariate(1.0, 0.3))  # 夏普比率围绕1.0波动
        win_rate = max(0.4, min(0.9, random.normalvariate(0.65, 0.1)))  # 胜率40%-90%
        profit_factor = max(0.5, random.normalvariate(1.5, 0.4))  # 盈亏比0.5-3.0

        sharpe_history.append(sharpe_ratio)
        win_rate_history.append(win_rate)

        debugger.update_metrics(
            equity=equity,
            cash=cash,
            positions_value=0,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
        )

        if day % 5 == 4:
            latest_metrics = debugger.metrics_history[-1]
            print(
                f"第{day + 1:2d}天: 资产 ${equity:,.2f} | "
                f"夏普 {sharpe_ratio:.2f} | "
                f"胜率 {win_rate * 100:.1f}% | "
                f"盈亏比 {profit_factor:.2f}"
            )

        time.sleep(0.1)

    # 输出最终性能报告
    print("\n性能分析报告:")
    print("-" * 30)
    if sharpe_history:
        print(f"平均夏普比率: {sum(sharpe_history) / len(sharpe_history):.2f}")
        print(f"夏普比率范围: {min(sharpe_history):.2f} - {max(sharpe_history):.2f}")
    if win_rate_history:
        avg_win_rate = sum(win_rate_history) / len(win_rate_history)
        print(f"平均胜率: {avg_win_rate * 100:.1f}%")
        print(
            f"胜率稳定性: {'良好' if max(win_rate_history) - min(win_rate_history) < 0.2 else '一般'}"
        )

    debugger.print_dashboard()
    debugger.stop_monitoring()


if __name__ == "__main__":
    # 运行所有演示
    simulate_simple_strategy()
    print("\n" + "=" * 60 + "\n")

    demonstrate_advanced_debugging()
    print("\n" + "=" * 60 + "\n")

    demonstrate_signal_analysis()
    print("\n" + "=" * 60 + "\n")

    demonstrate_performance_monitoring()

    print("\n" + "=" * 60)
    print("✅ 策略可视化调试器演示完成!")
    print("=" * 60)
