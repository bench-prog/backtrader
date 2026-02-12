#!/usr/bin/env python3
"""
高频交易框架完整示例
展示低延迟订单执行和套利策略的实现
"""

import os
import sys
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import backtrader as bt

# 添加项目路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from real_trade.core.hf_trading import ExecutionMode, HFTradingStrategy


class MeanReversionHFStrategy(HFTradingStrategy):
    """
    均值回归高频交易策略
    利用价格短期偏离均值的机会进行快速交易
    """

    params = (
        ("lookback_period", 20),
        ("entry_threshold", 2.0),  # 进入场标准差倍数
        ("exit_threshold", 0.5),  # 出场标准差倍数
        ("max_position", 100),
    )

    def __init__(self):
        super().__init__()

        # 计算技术指标
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data, period=self.p.lookback_period
        )
        self.std = bt.indicators.StandardDeviation(
            self.data, period=self.p.lookback_period
        )

        # 状态变量
        self.in_position = False
        self.entry_price = 0.0
        self.position_size = 0

    def generate_hf_signals(self):
        """生成高频交易信号"""
        if len(self.data) < self.p.lookback_period:
            return

        current_price = self.data.close[0]
        sma_value = self.sma[0]
        std_value = self.std[0]

        # 计算标准化偏离
        z_score = (current_price - sma_value) / std_value

        # 均值回归信号
        if not self.in_position:
            # 开仓信号
            if z_score > self.p.entry_threshold:
                # 价格过高，做空
                size = min(
                    self.p.max_position, int(self.broker.getcash() / current_price)
                )
                if size > 0:
                    order_id = self.hf_sell(self.data, size)
                    self.in_position = True
                    self.entry_price = current_price
                    self.position_size = size
                    self.log(
                        f"做空开仓: 价格={current_price:.2f}, Z-score={z_score:.2f}"
                    )

            elif z_score < -self.p.entry_threshold:
                # 价格过低，做多
                size = min(
                    self.p.max_position, int(self.broker.getcash() / current_price)
                )
                if size > 0:
                    order_id = self.hf_buy(self.data, size)
                    self.in_position = True
                    self.entry_price = current_price
                    self.position_size = size
                    self.log(
                        f"做多开仓: 价格={current_price:.2f}, Z-score={z_score:.2f}"
                    )

        else:
            # 平仓信号
            if self.position_size > 0:  # 多头仓位
                if z_score > -self.p.exit_threshold:  # 接近均值
                    order_id = self.hf_sell(self.data, self.position_size)
                    profit = (current_price - self.entry_price) * self.position_size
                    self.log(f"多头平仓: 价格={current_price:.2f}, 收益={profit:.2f}")
                    self.in_position = False
                    self.position_size = 0

            elif self.position_size < 0:  # 空头仓位
                if z_score < self.p.exit_threshold:  # 接近均值
                    order_id = self.hf_buy(self.data, abs(self.position_size))
                    profit = (self.entry_price - current_price) * abs(
                        self.position_size
                    )
                    self.log(f"空头平仓: 价格={current_price:.2f}, 收益={profit:.2f}")
                    self.in_position = False
                    self.position_size = 0


class StatisticalArbitrageStrategy(HFTradingStrategy):
    """
    统计套利策略
    利用相关资产间的价格差异进行套利
    """

    params = (
        ("correlation_threshold", 0.8),
        ("spread_threshold", 2.0),  # 标准差倍数
        ("max_position", 50),
    )

    def __init__(self):
        super().__init__()
        # 设置执行模式
        self.order_executor.mode = ExecutionMode.ARBITRAGE
        self.p.enable_arbitrage = True

        # 确保至少有两个数据源
        if len(self.datas) < 2:
            raise ValueError("统计套利需要至少两个相关资产")

        # 计算相关性和价差
        self.correlations = {}
        self.spreads = {}

    def execute_arbitrage(self, opportunity: dict):
        """执行套利交易"""
        data1_name, data2_name = opportunity["pair"]
        direction = opportunity["direction"]
        deviation = opportunity["deviation"]

        try:
            data1 = self.getdatabyname(data1_name)
            data2 = self.getdatabyname(data2_name)
        except:
            return

        # 计算套利仓位
        cash = self.broker.getcash()
        size1 = min(self.p.max_position, int(cash * 0.4 / data1.close[0]))
        size2 = min(self.p.max_position, int(cash * 0.4 / data2.close[0]))

        if size1 <= 0 or size2 <= 0:
            return

        if direction == "long_first":
            # 做多第一个资产，做空第二个资产
            self.hf_buy(data1, size1)
            self.hf_sell(data2, size2)
            self.log(
                f"套利交易: 买入{data1_name} {size1}手，卖出{data2_name} {size2}手"
            )
        else:
            # 做空第一个资产，做多第二个资产
            self.hf_sell(data1, size1)
            self.hf_buy(data2, size2)
            self.log(
                f"套利交易: 卖出{data1_name} {size1}手，买入{data2_name} {size2}手"
            )


def create_hf_test_data():
    """创建高频交易测试数据"""
    np.random.seed(42)

    # 创建高频率数据（每分钟）
    start_date = datetime(2023, 1, 1)
    periods = 1000  # 约17小时的分钟数据
    dates = [start_date + timedelta(minutes=i) for i in range(periods)]

    # 主要资产价格（带有均值回归特性）
    base_returns = np.random.normal(0, 0.001, periods)  # 0.1%波动
    price_series = 100 + np.cumsum(base_returns * 100)

    # 添加均值回归效应
    for i in range(20, len(price_series)):
        mean_price = np.mean(price_series[i - 20 : i])
        adjustment = (mean_price - price_series[i - 1]) * 0.05  # 5%回归力度
        price_series[i] = price_series[i - 1] + base_returns[i] * 100 + adjustment

    # 创建DataFrame
    df = pd.DataFrame(
        {
            "open": price_series * (1 + np.random.normal(0, 0.0005, periods)),
            "high": price_series * (1 + abs(np.random.normal(0, 0.001, periods))),
            "low": price_series * (1 - abs(np.random.normal(0, 0.001, periods))),
            "close": price_series,
            "volume": np.random.randint(1000, 10000, periods),
        },
        index=dates,
    )

    # 创建相关资产数据
    correlated_returns = base_returns + np.random.normal(0, 0.0005, periods)
    corr_price_series = 50 + np.cumsum(correlated_returns * 50)

    for i in range(20, len(corr_price_series)):
        mean_price = np.mean(corr_price_series[i - 20 : i])
        adjustment = (mean_price - corr_price_series[i - 1]) * 0.03
        corr_price_series[i] = (
            corr_price_series[i - 1] + correlated_returns[i] * 50 + adjustment
        )

    corr_df = pd.DataFrame(
        {
            "open": corr_price_series * (1 + np.random.normal(0, 0.0005, periods)),
            "high": corr_price_series * (1 + abs(np.random.normal(0, 0.001, periods))),
            "low": corr_price_series * (1 - abs(np.random.normal(0, 0.001, periods))),
            "close": corr_price_series,
            "volume": np.random.randint(500, 5000, periods),
        },
        index=dates,
    )

    return df, corr_df


def main():
    """主函数"""
    print("=== Backtrader高频交易框架演示 ===\n")

    # 创建引擎
    cerebro = bt.Cerebro()

    # 创建高频数据
    main_df, corr_df = create_hf_test_data()

    # 添加数据源
    data = bt.feeds.PandasData(dataname=main_df, name="MAIN_ASSET")
    cerebro.adddata(data)

    corr_data = bt.feeds.PandasData(dataname=corr_df, name="CORRELATED_ASSET")
    cerebro.adddata(corr_data)

    # 测试两种策略
    print("1. 均值回归高频策略:")
    cerebro.addstrategy(
        MeanReversionHFStrategy,
        execution_mode=ExecutionMode.HIGH_FREQUENCY,
        printlog=True,
        latency_threshold=10.0,
    )

    # 设置初始条件
    cerebro.broker.setcash(50000.0)
    cerebro.broker.setcommission(commission=0.0001)  # 0.01% 低佣金

    # 运行回测
    print("开始均值回归高频策略回测...")
    start_time = time.time()
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    strategy1 = results[0]
    end_time = time.time()

    execution_time = end_time - start_time
    final_value = cerebro.broker.getvalue()

    print("\n均值回归策略结果:")
    print(f"执行时间: {execution_time:.4f} 秒")
    print(f"初始资金: {initial_value:.2f}")
    print(f"最终资金: {final_value:.2f}")
    print(f"收益率: {(final_value - initial_value) / initial_value:.2%}")

    print("\n" + "=" * 50 + "\n")

    # 重新初始化进行套利策略测试
    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=main_df, name="ASSET1"))
    cerebro.adddata(bt.feeds.PandasData(dataname=corr_df, name="ASSET2"))

    print("2. 统计套利策略:")
    cerebro.addstrategy(
        StatisticalArbitrageStrategy,
        printlog=True,
        correlation_threshold=0.7,
        spread_threshold=1.5,
    )

    cerebro.broker.setcash(50000.0)
    cerebro.broker.setcommission(commission=0.0001)

    print("开始统计套利策略回测...")
    start_time = time.time()
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    strategy2 = results[0]
    end_time = time.time()

    execution_time = end_time - start_time
    final_value = cerebro.broker.getvalue()

    print("\n统计套利策略结果:")
    print(f"执行时间: {execution_time:.4f} 秒")
    print(f"初始资金: {initial_value:.2f}")
    print(f"最终资金: {final_value:.2f}")
    print(f"收益率: {(final_value - initial_value) / initial_value:.2%}")


if __name__ == "__main__":
    main()
