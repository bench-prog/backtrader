#!/usr/bin/env python3
"""
BTC数据诊断和策略调试
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


class DiagnosticStrategy(bt.Strategy):
    """诊断策略 - 用于分析数据和信号生成"""

    params = (
        ("print_freq", 30),  # 每30天打印一次
    )

    def __init__(self):
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.data, period=10)
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.data, period=30)
        self.rsi = bt.indicators.RSI(self.data, period=14)
        self.day_count = 0

    def next(self):
        self.day_count += 1

        # 定期打印诊断信息
        if self.day_count % self.p.print_freq == 0 or self.day_count <= 5:
            print(f"\n--- 诊断信息 (第{self.day_count}天) ---")
            print(f"日期: {self.data.datetime.date(0)}")
            print(
                f"价格: 开${self.data.open[0]:.2f}, 高${self.data.high[0]:.2f}, 低${self.data.low[0]:.2f}, 收${self.data.close[0]:.2f}"
            )
            print(f"MA10: {self.sma_fast[0]:.2f}, MA30: {self.sma_slow[0]:.2f}")
            print(f"RSI: {self.rsi[0]:.2f}")
            print(
                f"MA关系: {'金叉' if self.sma_fast[0] > self.sma_slow[0] else '死叉'}"
            )
            print(
                f"RSI状态: {'超卖' if self.rsi[0] < 30 else '超买' if self.rsi[0] > 70 else '中性'}"
            )

            # 检查交叉信号
            if len(self) > 1:
                if (
                    self.sma_fast[0] > self.sma_slow[0]
                    and self.sma_fast[-1] <= self.sma_slow[-1]
                ):
                    print("🔔 金叉信号!")
                elif (
                    self.sma_fast[0] < self.sma_slow[0]
                    and self.sma_fast[-1] >= self.sma_slow[-1]
                ):
                    print("🔔 死叉信号!")


def load_and_analyze_btc_data():
    """加载并分析BTC数据"""
    data_file = os.path.join(project_root, "datas", "binance-btc-2015-2026.txt")

    print("📊 分析BTC数据质量...")
    df = pd.read_csv(data_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)

    # 数据质量检查
    print("数据基本信息:")
    print(f"  总记录数: {len(df)}")
    print(f"  时间范围: {df.index[0]} 到 {df.index[-1]}")
    print("  缺失值:")
    print(f"    Open: {df['Open'].isna().sum()}")
    print(f"    High: {df['High'].isna().sum()}")
    print(f"    Low: {df['Low'].isna().sum()}")
    print(f"    Close: {df['Close'].isna().sum()}")
    print(f"    Volume: {df['Volume'].isna().sum()}")

    # 价格合理性检查
    print("\n价格合理性检查:")
    print(
        f"  Open-Close差异 > 50% 的天数: {((abs(df['Open'] - df['Close']) / df['Close']) > 0.5).sum()}"
    )
    print(f"  High < Low 的天数: {(df['High'] < df['Low']).sum()}")
    print(
        f"  High < Close 或 Low > Close 的天数: {((df['High'] < df['Close']) | (df['Low'] > df['Close'])).sum()}"
    )

    # 计算一些基本统计
    df["Return"] = df["Close"].pct_change()
    print("\n收益率统计:")
    print(f"  平均日收益率: {df['Return'].mean():.4%}")
    print(f"  日收益率标准差: {df['Return'].std():.4%}")
    print(f"  最大单日涨幅: {df['Return'].max():.4%}")
    print(f"  最大单日跌幅: {df['Return'].min():.4%}")

    return df


def main():
    """主函数"""
    print("🔍 BTC数据诊断工具")
    print("=" * 40)

    # 分析数据
    btc_data = load_and_analyze_btc_data()

    # 创建回测
    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(dataname=btc_data)
    cerebro.adddata(data)
    cerebro.addstrategy(DiagnosticStrategy)
    cerebro.broker.setcash(10000.0)

    print("\n🔧 运行诊断回测...")
    cerebro.run()

    print("\n✅ 诊断完成!")


if __name__ == "__main__":
    main()
