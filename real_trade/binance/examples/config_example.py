#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
使用配置文件的 Binance 交易示例

演示如何使用 JSON 配置文件创建 Binance 交易引擎。

运行模式：
---------
1. 回测模式（默认）：
   使用配置：futures_backtest.json
   - 历史数据回测
   - 本地模拟订单
   - 不需要 API 密钥

2. Demo Trading 实盘测试：
   使用配置：futures_live_demo.json
   - 连接 Demo Trading
   - 真实订单流程
   - 需要 Demo Trading API 密钥

3. 生产实盘（谨慎！）：
   创建自定义配置，设置：
   - testnet: false
   - paper_trading: false
   - backtest: false

切换方式：
---------
修改 main() 函数中的配置文件名：
  config_file = "futures_backtest.json"     # 回测模式
  config_file = "futures_live_demo.json"    # 实盘测试
"""

import os
import sys
import datetime

import backtrader as bt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from real_trade.binance import (
    create_binance_engine_from_config,
    get_config_value,
)


class ConfigurableStrategy(bt.Strategy):
    """可配置策略 - 从配置文件读取参数"""

    params = (
        ("rsi_period", 7),
        ("rsi_low", 40),
        ("rsi_high", 60),
        ("ma_fast", 3),
        ("ma_slow", 10),
        ("trade_size_pct", 0.3),
        ("stop_loss_pct", 5.0),
        ("printlog", True),
    )

    def __init__(self):
        # 技术指标
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.ma_fast = bt.indicators.SMA(period=self.p.ma_fast)
        self.ma_slow = bt.indicators.SMA(period=self.p.ma_slow)
        self.crossover = bt.indicators.CrossOver(self.ma_fast, self.ma_slow)

        # 统计
        self.order = None
        self.trade_count = 0
        self.buy_count = 0
        self.sell_count = 0

        print("\n" + "=" * 60)
        print("策略初始化完成（从配置文件加载参数）")
        print("=" * 60)
        print(f"RSI 周期: {self.p.rsi_period}")
        print(f"RSI 范围: {self.p.rsi_low} - {self.p.rsi_high}")
        print(f"均线周期: {self.p.ma_fast}/{self.p.ma_slow}")
        print(f"交易规模: {self.p.trade_size_pct*100}% 的可用资金")
        print(f"止损: {self.p.stop_loss_pct}%")
        print("=" * 60 + "\n")

    def log(self, txt, dt=None):
        """日志函数"""
        if self.p.printlog:
            if dt is None:
                try:
                    dt = self.datas[0].datetime.datetime(0)
                except (IndexError, AttributeError):
                    dt = datetime.datetime.now()
            print(f'[{dt.strftime("%Y-%m-%d %H:%M:%S")}] {txt}')

    def notify_order(self, order):
        """订单通知"""
        if order.status in [order.Submitted]:
            self.log(f"订单已提交: {order.getordername()}")
            return

        if order.status in [order.Accepted]:
            self.log(f"订单已接受: {order.getordername()}")
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_count += 1
                self.trade_count += 1
                self.log(
                    f"\n{'='*60}\n"
                    f"✓ 买入成交 #{self.trade_count}\n"
                    f"{'='*60}\n"
                    f"  价格: ${order.executed.price:,.2f}\n"
                    f"  数量: {order.executed.size:.6f} BTC\n"
                    f"  成本: ${order.executed.value:,.2f}\n"
                    f"  当前余额: ${self.broker.getcash():,.2f}\n"
                    f"  账户价值: ${self.broker.getvalue():,.2f}\n"
                    f"{'='*60}"
                )
            else:
                self.sell_count += 1
                self.log(
                    f"\n{'='*60}\n"
                    f"✓ 卖出成交 #{self.trade_count}\n"
                    f"{'='*60}\n"
                    f"  价格: ${order.executed.price:,.2f}\n"
                    f"  数量: {-order.executed.size:.6f} BTC\n"
                    f"  收入: ${order.executed.value:,.2f}\n"
                    f"  当前余额: ${self.broker.getcash():,.2f}\n"
                    f"  账户价值: ${self.broker.getvalue():,.2f}\n"
                    f"{'='*60}"
                )

        elif order.status in [order.Canceled]:
            self.log("✗ 订单已取消")
        elif order.status in [order.Margin]:
            self.log("✗ 订单被拒绝 - 保证金不足")
        elif order.status in [order.Rejected]:
            self.log("✗ 订单被拒绝")

        self.order = None

    def next(self):
        """策略主逻辑"""

        # 显示当前状态（每 10 根 K 线）
        if len(self) % 10 == 0:
            self.log(
                f"\n当前状态 (K线 #{len(self)}):\n"
                f"  价格: ${self.data.close[0]:,.2f}\n"
                f"  RSI: {self.rsi[0]:.2f}\n"
                f"  快速MA: ${self.ma_fast[0]:,.2f}\n"
                f"  慢速MA: ${self.ma_slow[0]:,.2f}\n"
                f"  余额: ${self.broker.getcash():,.2f}\n"
                f"  持仓: {self.position.size:.6f} BTC\n"
                f"  总价值: ${self.broker.getvalue():,.2f}\n"
                f"  总交易: {self.trade_count} (买:{self.buy_count}, 卖:{self.sell_count})"
            )

        if self.order:
            return

        if len(self) < self.p.ma_slow:
            return

        # 交易逻辑
        if not self.position:
            # 买入信号
            buy_signal_rsi = self.rsi[0] < self.p.rsi_low
            buy_signal_ma = self.crossover[0] > 0

            if buy_signal_rsi or buy_signal_ma:
                cash_to_use = self.broker.getcash() * self.p.trade_size_pct
                size = cash_to_use / self.data.close[0]

                if size > 0:
                    self.order = self.buy(size=size)

                    signal_type = []
                    if buy_signal_rsi:
                        signal_type.append(f"RSI超卖({self.rsi[0]:.2f})")
                    if buy_signal_ma:
                        signal_type.append("金叉")

                    self.log(
                        f'\n→ 买入信号触发 (K线 #{len(self)})\n'
                        f'  信号: {", ".join(signal_type)}\n'
                        f'  当前价格: ${self.data.close[0]:,.2f}\n'
                        f'  计划买入: {size:.6f} BTC (使用 ${cash_to_use:,.2f})'
                    )

        else:
            # 卖出信号
            sell_signal_rsi = self.rsi[0] > self.p.rsi_high
            sell_signal_ma = self.crossover[0] < 0

            # 止损
            pnl_pct = (
                (self.data.close[0] - self.position.price) / self.position.price * 100
            )
            sell_signal_stoploss = pnl_pct < -self.p.stop_loss_pct

            if sell_signal_rsi or sell_signal_ma or sell_signal_stoploss:
                self.order = self.sell(size=self.position.size)

                signal_type = []
                if sell_signal_rsi:
                    signal_type.append(f"RSI超买({self.rsi[0]:.2f})")
                if sell_signal_ma:
                    signal_type.append("死叉")
                if sell_signal_stoploss:
                    signal_type.append(f"止损({pnl_pct:.2f}%)")

                self.log(
                    f'\n→ 卖出信号触发 (K线 #{len(self)})\n'
                    f'  信号: {", ".join(signal_type)}\n'
                    f'  当前价格: ${self.data.close[0]:,.2f}\n'
                    f'  持仓成本: ${self.position.price:,.2f}\n'
                    f'  持仓盈亏: {pnl_pct:.2f}%\n'
                    f'  卖出数量: {self.position.size:.6f} BTC'
                )

    def stop(self):
        """策略结束"""
        self.log("\n" + "=" * 60)
        self.log("策略执行完毕")
        self.log("=" * 60)
        self.log(f"总交易次数: {self.trade_count}")
        self.log(f"买入次数: {self.buy_count}")
        self.log(f"卖出次数: {self.sell_count}")
        self.log(f"最终价值: ${self.broker.getvalue():,.2f}")
        profit = self.broker.getvalue() - self.broker.startingcash
        profit_pct = profit / self.broker.startingcash * 100
        self.log(f"盈亏: ${profit:,.2f} ({profit_pct:+.2f}%)")
        self.log("=" * 60 + "\n")


def main():
    """主函数"""

    print("\n" + "=" * 60)
    print("Binance 配置文件示例")
    print("=" * 60)
    print("使用 JSON 配置文件创建交易引擎")
    print("=" * 60 + "\n")

    # 方法1: 使用默认配置文件
    # store, broker, data, config = create_binance_engine_from_config()

    # 方法2: 使用指定配置文件
    config_file = "futures_live_demo.json"
    store, broker, data, config = create_binance_engine_from_config(config_file)

    # 方法3: 使用完整路径
    # config_path = "/path/to/my_config.json"
    # store, broker, data, config = create_binance_engine_from_config(config_path)

    # 创建 Cerebro
    cerebro = bt.Cerebro()
    cerebro.setbroker(broker)
    cerebro.adddata(data)

    # 从配置中读取策略参数
    strategy_params = {
        "rsi_period": get_config_value(config, "strategy.rsi_period", 7),
        "rsi_low": get_config_value(config, "strategy.rsi_low", 40),
        "rsi_high": get_config_value(config, "strategy.rsi_high", 60),
        "ma_fast": get_config_value(config, "strategy.ma_fast", 3),
        "ma_slow": get_config_value(config, "strategy.ma_slow", 10),
        "trade_size_pct": get_config_value(config, "strategy.trade_size_pct", 0.3),
        "stop_loss_pct": get_config_value(config, "strategy.stop_loss_pct", 5.0),
        "printlog": get_config_value(config, "strategy.printlog", True),
    }

    cerebro.addstrategy(ConfigurableStrategy, **strategy_params)

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    # 运行
    print(f"\n{'='*60}")
    print(f"初始账户价值: ${cerebro.broker.getvalue():,.2f}")
    print(f"{'='*60}\n")

    print("开始回测...\n")
    start_time = datetime.datetime.now()

    results = cerebro.run()
    strat = results[0]

    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 最终结果
    print(f"\n\n{'='*60}")
    print("回测完成 - 最终结果")
    print(f"{'='*60}")
    print(f"执行时间: {duration:.2f} 秒")
    print(f"最终账户价值: ${cerebro.broker.getvalue():,.2f}")

    initial_cash = get_config_value(config, "trading.initial_cash", 10000.0)
    profit = cerebro.broker.getvalue() - initial_cash
    print(f"总盈亏: ${profit:,.2f} ({profit/initial_cash*100:+.2f}%)")
    print(f"{'='*60}\n")

    # 交易统计
    trade_analysis = strat.analyzers.trades.get_analysis()

    try:
        total_trades = trade_analysis.total.get("total", 0)
    except (AttributeError, KeyError):
        total_trades = 0

    try:
        won_trades = trade_analysis.won.get("total", 0)
    except (AttributeError, KeyError):
        won_trades = 0

    try:
        lost_trades = trade_analysis.lost.get("total", 0)
    except (AttributeError, KeyError):
        lost_trades = 0

    print("📊 交易统计:")
    print(f"  总交易次数: {total_trades}")
    print(f"  盈利交易: {won_trades}")
    print(f"  亏损交易: {lost_trades}")
    if total_trades > 0:
        print(f"  胜率: {won_trades/total_trades*100:.1f}%")

    # 性能指标
    print("\n📈 性能指标:")

    sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio")
    if sharpe:
        print(f"  夏普比率: {sharpe:.2f}")
    else:
        print("  夏普比率: N/A")

    drawdown = strat.analyzers.drawdown.get_analysis()
    max_dd = drawdown.get("max", {}).get("drawdown", 0)
    print(f"  最大回撤: {max_dd:.2f}%")

    total_return = strat.analyzers.returns.get_analysis().get("rtot", 0) * 100
    print(f"  总收益率: {total_return:+.2f}%")

    print(f"\n{'='*60}")
    if total_trades > 5:
        print("✓ 测试成功！系统产生了足够的交易进行全面测试。")
    elif total_trades > 0:
        print("⚠ 测试部分成功，交易次数较少，但系统功能正常。")
    else:
        print("⚠ 未产生交易，可能需要调整策略参数。")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
