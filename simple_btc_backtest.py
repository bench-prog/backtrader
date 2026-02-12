#!/usr/bin/env python3
"""
简化版BTC真实数据回测
验证信号生成和交易执行
"""

import os
import sys

import pandas as pd

import backtrader as bt

# 添加项目路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)


class SimpleBTCTrading(bt.Strategy):
    """简化BTC交易策略"""

    def __init__(self):
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.data, period=10)
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.data, period=30)
        self.trade_count = 0

    def next(self):
        # 简单的MA交叉策略
        if len(self.data) < 30:
            return

        # 买入信号：金叉且没有持仓
        if (
            self.sma_fast[0] > self.sma_slow[0]
            and self.sma_fast[-1] <= self.sma_slow[-1]
            and self.position.size <= 0
        ):
            size = int(self.broker.getcash() * 0.9 / self.data.close[0])
            if size > 0:
                self.buy(size=size)
                self.trade_count += 1
                print(
                    f"🔔 买入: {self.data.datetime.date(0)}, 价格=${self.data.close[0]:.2f}, 数量={size}"
                )

        # 卖出信号：死叉且有持仓
        elif (
            self.sma_fast[0] < self.sma_slow[0]
            and self.sma_fast[-1] >= self.sma_slow[-1]
            and self.position.size > 0
        ):
            self.sell(size=self.position.size)
            self.trade_count += 1
            print(
                f"🔔 卖出: {self.data.datetime.date(0)}, 价格=${self.data.close[0]:.2f}, 数量={self.position.size}"
            )

    def stop(self):
        print("\n🏁 策略执行完成")
        print(f"总交易次数: {self.trade_count}")


def main():
    """主函数"""
    print("🚀 简化版BTC真实数据回测")
    print("=" * 40)

    # 加载数据
    df = pd.read_csv("datas/binance-btc-2015-2026.txt")
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)

    print(f"📊 数据: {df.index[0].date()} 到 {df.index[-1].date()}")
    print(f"📊 记录数: {len(df)}")

    # 创建回测
    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    cerebro.addstrategy(SimpleBTCTrading)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)

    initial = cerebro.broker.getvalue()
    print(f"\n💰 初始资金: ${initial:,.2f}")

    # 运行回测
    results = cerebro.run()
    final = cerebro.broker.getvalue()

    returns = (final - initial) / initial

    print("\n🎯 回测结果:")
    print(f"💵 最终资金: ${final:,.2f}")
    print(f"📈 总收益率: {returns:.2%}")

    # 与持有BTC对比
    buy_hold = (df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0]
    print("⚖️  对比:")
    print(f"   BTC持有收益: {buy_hold:.2%}")
    print(f"   策略收益: {returns:.2%}")
    print(f"   差异: {returns - buy_hold:.2%}")


if __name__ == "__main__":
    main()
