#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
使用配置文件的 Binance 交易示例

演示如何使用配置创建 Binance 交易引擎。

运行模式：
---------
1. 回测模式（默认）：
   - 历史数据回测
   - 本地模拟订单
   - 不需要 API 密钥

2. Demo Trading 实盘测试：
   设置 testnet=true, paper_trading=false, backtest=false
   - 连接 Demo Trading
   - 真实订单流程
   - 需要 Demo Trading API 密钥

3. 生产实盘（谨慎！）：
   设置 testnet=false, paper_trading=false, backtest=false
"""

import datetime
import os
import sys

import backtrader as bt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from real_trade.brokers import BinanceBroker
from real_trade.feeds import BinanceData
from real_trade.stores import BinanceStore
from real_trade.utils.config import GlobalConfig


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
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.ma_fast = bt.indicators.SMA(period=self.p.ma_fast)
        self.ma_slow = bt.indicators.SMA(period=self.p.ma_slow)
        self.crossover = bt.indicators.CrossOver(self.ma_fast, self.ma_slow)

        self.order = None
        self.trade_count = 0
        self.buy_count = 0
        self.sell_count = 0

        print("\n" + "=" * 60)
        print("Strategy initialized")
        print("=" * 60)
        print(f"RSI period: {self.p.rsi_period}")
        print(f"RSI range: {self.p.rsi_low} - {self.p.rsi_high}")
        print(f"MA periods: {self.p.ma_fast}/{self.p.ma_slow}")
        print(f"Trade size: {self.p.trade_size_pct * 100}%")
        print(f"Stop loss: {self.p.stop_loss_pct}%")
        print("=" * 60 + "\n")

    def log(self, txt, dt=None):
        if self.p.printlog:
            if dt is None:
                try:
                    dt = self.datas[0].datetime.datetime(0)
                except (IndexError, AttributeError):
                    dt = datetime.datetime.now()
            print(f"[{dt.strftime('%Y-%m-%d %H:%M:%S')}] {txt}")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            if order.isbuy():
                self.buy_count += 1
                self.trade_count += 1
                self.log(
                    f"BUY  #{self.trade_count}  "
                    f"Price={order.executed.price:,.2f}  "
                    f"Size={order.executed.size:.6f}  "
                    f"Value=${self.broker.getvalue():,.2f}"
                )
            else:
                self.sell_count += 1
                self.log(
                    f"SELL #{self.trade_count}  "
                    f"Price={order.executed.price:,.2f}  "
                    f"Size={-order.executed.size:.6f}  "
                    f"Value=${self.broker.getvalue():,.2f}"
                )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order {order.Status[order.status]}")

        self.order = None

    def next(self):
        if self.order:
            return
        if len(self) < self.p.ma_slow:
            return

        if not self.position:
            buy_signal_rsi = self.rsi[0] < self.p.rsi_low
            buy_signal_ma = self.crossover[0] > 0

            if buy_signal_rsi or buy_signal_ma:
                cash_to_use = self.broker.getcash() * self.p.trade_size_pct
                size = cash_to_use / self.data.close[0]
                if size > 0:
                    self.order = self.buy(size=size)
        else:
            sell_signal_rsi = self.rsi[0] > self.p.rsi_high
            sell_signal_ma = self.crossover[0] < 0
            pnl_pct = (
                (self.data.close[0] - self.position.price) / self.position.price * 100
            )
            sell_signal_stoploss = pnl_pct < -self.p.stop_loss_pct

            if sell_signal_rsi or sell_signal_ma or sell_signal_stoploss:
                self.order = self.sell(size=self.position.size)

    def stop(self):
        profit = self.broker.getvalue() - self.broker.startingcash
        profit_pct = profit / self.broker.startingcash * 100
        self.log(
            f"DONE  Trades={self.trade_count}  "
            f"Value=${self.broker.getvalue():,.2f}  "
            f"P&L=${profit:,.2f} ({profit_pct:+.2f}%)"
        )


def create_engine_from_config(cfg: GlobalConfig):
    """从配置创建交易引擎"""
    # 回测模式不需要 API 密钥
    use_testnet = cfg.testnet if not cfg.backtest else False

    store = BinanceStore.get_instance(
        apikey=cfg.apikey if not cfg.backtest else "",
        secret=cfg.secret if not cfg.backtest else "",
        testnet=use_testnet,
        proxy=cfg.proxy,
        market_type=cfg.market_type,
    )

    broker = BinanceBroker(store, paper_trading=cfg.paper_trading, cash=cfg.cash)
    if cfg.commission > 0:
        broker.setcommission(commission=cfg.commission)

    data_kwargs = {}
    if cfg.fromdate:
        data_kwargs["fromdate"] = datetime.datetime.fromisoformat(cfg.fromdate)
    if cfg.todate:
        data_kwargs["todate"] = datetime.datetime.fromisoformat(cfg.todate)
    if cfg.historical_limit != 1000:
        data_kwargs["historical_limit"] = cfg.historical_limit

    data = BinanceData.from_timeframe_string(
        cfg.timeframe,
        store,
        symbol=cfg.symbol,
        backtest=cfg.backtest,
        **data_kwargs,
    )

    return store, broker, data


def main():
    """主函数"""

    # ----- 方法1: 从字典创建配置 -----
    cfg = GlobalConfig.from_dict(
        {
            "symbol": "BTC/USDT",
            "timeframe": "15m",
            "backtest": True,
            "paper_trading": True,
            "cash": 10000.0,
            "market_type": "future",
        }
    )

    # ----- 方法2: 从 JSON 文件 -----
    # cfg = GlobalConfig.from_json("config/binance/spot_testnet.json")

    # ----- 方法3: 直接创建 GlobalConfig -----
    # cfg = GlobalConfig(symbol="ETH/USDT", backtest=True, market_type="future")

    store, broker, data = create_engine_from_config(cfg)

    cerebro = bt.Cerebro()
    cerebro.setbroker(broker)
    cerebro.adddata(data)

    # 策略参数
    cerebro.addstrategy(
        ConfigurableStrategy,
        rsi_period=7,
        rsi_low=40,
        rsi_high=60,
        ma_fast=3,
        ma_slow=10,
        trade_size_pct=0.3,
        stop_loss_pct=5.0,
    )

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    print(f"\nInitial value: ${cerebro.broker.getvalue():,.2f}")
    print("Starting backtest...\n")

    start_time = datetime.datetime.now()
    results = cerebro.run()
    strat = results[0]
    duration = (datetime.datetime.now() - start_time).total_seconds()

    # 最终结果
    print(f"\n{'=' * 60}")
    print(f"Backtest complete ({duration:.2f}s)")
    print(f"Final value: ${cerebro.broker.getvalue():,.2f}")

    trade_analysis = strat.analyzers.trades.get_analysis()
    try:
        total_trades = trade_analysis.total.get("total", 0)
    except (AttributeError, KeyError):
        total_trades = 0

    sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio")
    drawdown = strat.analyzers.drawdown.get_analysis()
    max_dd = drawdown.get("max", {}).get("drawdown", 0)

    print(
        f"Total trades: {total_trades}  Max DD: {max_dd:.2f}%  Sharpe: {sharpe:.2f}"
        if sharpe
        else f"Total trades: {total_trades}  Max DD: {max_dd:.2f}%"
    )
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
