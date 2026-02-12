#!/usr/bin/env python3
"""
分析真实BTC数据特征
"""

import pandas as pd

# 检查数据特征
data_file = "datas/binance-btc-2015-2026.txt"
df = pd.read_csv(data_file)
df["Date"] = pd.to_datetime(df["Date"])
df.set_index("Date", inplace=True)

print("📊 BTC数据统计:")
print(f"数据范围: {df.index[0].date()} 到 {df.index[-1].date()}")
print(f"数据点数: {len(df)} 天")
print(f"开盘价: ${df['Open'].iloc[0]:.2f} -> ${df['Open'].iloc[-1]:.2f}")
print(f"收盘价: ${df['Close'].iloc[0]:.2f} -> ${df['Close'].iloc[-1]:.2f}")
print(f"最高价: ${df['High'].max():.2f}")
print(f"最低价: ${df['Low'].min():.2f}")

# 检查价格变化
price_change = (df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0]
print(f"总体涨幅: {price_change:.2%}")

# 检查最近的价格走势
recent = df.tail(100)
recent_change = (recent["Close"].iloc[-1] - recent["Close"].iloc[0]) / recent[
    "Close"
].iloc[0]
print("\n最近100天价格走势:")
print(f"起始: ${recent['Close'].iloc[0]:.2f}")
print(f"结束: ${recent['Close'].iloc[-1]:.2f}")
print(f"涨幅: {recent_change:.2%}")

# 检查移动平均线情况
if len(df) >= 30:
    df["MA10"] = df["Close"].rolling(10).mean()
    df["MA30"] = df["Close"].rolling(30).mean()

    last_cross = None
    for i in range(-100, -1):
        if (
            df["MA10"].iloc[i] > df["MA30"].iloc[i]
            and df["MA10"].iloc[i - 1] <= df["MA30"].iloc[i - 1]
        ):
            last_cross = "金叉"
            cross_date = df.index[i].date()
        elif (
            df["MA10"].iloc[i] < df["MA30"].iloc[i]
            and df["MA10"].iloc[i - 1] >= df["MA30"].iloc[i - 1]
        ):
            last_cross = "死叉"
            cross_date = df.index[i].date()

    if last_cross:
        print(f"\n最近交叉信号: {last_cross} at {cross_date}")
    else:
        print("\n最近100天内无交叉信号")

print("\n数据可用于回测验证!")
