#!/usr/bin/env python3
"""
投资组合优化完整示例
展示如何使用Mean-Variance和Risk Parity优化器
"""

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

from real_trade.analyzers.portfolio_optimizer import (
    MeanVarianceOptimizer,
    PortfolioRebalancer,
    RiskParityOptimizer,
)


class MultiAssetStrategy(bt.Strategy):
    """
    多资产投资组合策略
    展示投资组合优化的实际应用
    """

    params = (
        ("rebalance_frequency", 20),  # 再平衡频率（交易日）
        ("optimization_method", "mean_variance"),  # 优化方法
        ("printlog", True),
    )

    def __init__(self):
        super().__init__()

        # 初始化优化器
        if self.p.optimization_method == "mean_variance":
            self.optimizer = MeanVarianceOptimizer()
        else:
            self.optimizer = RiskParityOptimizer()

        self.rebalancer = PortfolioRebalancer(self)

        # 状态变量
        self.days_since_rebalance = 0
        self.last_optimization_result = None

    def log(self, txt, level="INFO"):
        """日志记录"""
        if self.p.printlog:
            timestamp = self.datetime.datetime().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} | {level} | {txt}")

    def next(self):
        """主逻辑循环"""
        self.days_since_rebalance += 1

        # 定期执行优化和再平衡
        if self.days_since_rebalance >= self.p.rebalance_frequency:
            self._perform_optimization_and_rebalance()
            self.days_since_rebalance = 0

    def _perform_optimization_and_rebalance(self):
        """执行优化和再平衡"""
        # 获取所有数据名称
        data_names = [data._name for data in self.datas]

        if len(data_names) < 2:
            self.log("资产数量不足，无法进行投资组合优化")
            return

        try:
            # 执行优化
            optimization_result = self.optimizer.optimize(data_names)
            self.last_optimization_result = optimization_result

            self.log(
                f"优化完成 - 预期收益: {optimization_result.expected_return:.2%}, "
                f"风险: {optimization_result.risk:.2%}, "
                f"夏普比率: {optimization_result.sharpe_ratio:.2f}"
            )

            # 显示权重分配
            self.log("最优权重分配:")
            for asset, weight in optimization_result.weights.items():
                self.log(f"  {asset}: {weight:.2%}")

            # 设置目标权重并执行再平衡
            self.rebalancer.set_target_weights(optimization_result.weights)
            trades = self.rebalancer.rebalance(tolerance=0.03)  # 3%容忍度

            # 执行交易
            for data_name, size_diff, price in trades:
                data = self.getdatabyname(data_name)
                if size_diff > 0:
                    self.buy(data=data, size=size_diff)
                    self.log(f"买入 {data_name}: {size_diff} 股，价格 {price:.2f}")
                elif size_diff < 0:
                    self.sell(data=data, size=abs(size_diff))
                    self.log(f"卖出 {data_name}: {abs(size_diff)} 股，价格 {price:.2f}")

        except Exception as e:
            self.log(f"优化过程出错: {e}", "ERROR")

    def stop(self):
        """策略结束"""
        if self.last_optimization_result:
            self.log("=== 最终投资组合统计 ===")
            self.log(
                f"预期年化收益: {self.last_optimization_result.expected_return:.2%}"
            )
            self.log(f"年化波动率: {self.last_optimization_result.risk:.2%}")
            self.log(f"夏普比率: {self.last_optimization_result.sharpe_ratio:.2f}")

            total_value = self.broker.getvalue()
            self.log(f"最终组合价值: {total_value:.2f}")


def create_multi_asset_data():
    """创建多资产测试数据"""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=252, freq="D")

    # 创建不同相关性的资产
    assets = {}

    # 资产A - 稳定增长
    returns_a = np.random.normal(0.0008, 0.015, 252)  # 日收益率
    prices_a = 100 * np.exp(np.cumsum(returns_a))
    assets["STOCK_A"] = prices_a

    # 资产B - 高波动性
    returns_b = np.random.normal(0.0012, 0.025, 252)
    prices_b = 50 * np.exp(np.cumsum(returns_b))
    assets["STOCK_B"] = prices_b

    # 资产C - 负相关
    returns_c = -0.3 * returns_a + np.random.normal(0, 0.01, 252)
    prices_c = 75 * np.exp(np.cumsum(returns_c))
    assets["STOCK_C"] = prices_c

    # 资产D - 低风险债券
    returns_d = np.random.normal(0.0003, 0.008, 252)
    prices_d = 1000 * np.exp(np.cumsum(returns_d))
    assets["BOND_D"] = prices_d

    # 构建DataFrame
    df_dict = {}
    for name, prices in assets.items():
        df_dict[f"{name}_Open"] = prices * (1 + np.random.normal(0, 0.002, 252))
        df_dict[f"{name}_High"] = prices * (1 + abs(np.random.normal(0, 0.005, 252)))
        df_dict[f"{name}_Low"] = prices * (1 - abs(np.random.normal(0, 0.005, 252)))
        df_dict[f"{name}_Close"] = prices
        df_dict[f"{name}_Volume"] = np.random.randint(1000, 10000, 252)

    return pd.DataFrame(df_dict, index=dates)


def main():
    """主函数"""
    print("=== Backtrader投资组合优化演示 ===\n")

    # 创建引擎
    cerebro = bt.Cerebro()

    # 添加多资产数据
    multi_data = create_multi_asset_data()

    # 为每个资产创建数据源
    stock_a_data = bt.feeds.PandasData(
        dataname=multi_data[
            [
                "STOCK_A_Open",
                "STOCK_A_High",
                "STOCK_A_Low",
                "STOCK_A_Close",
                "STOCK_A_Volume",
            ]
        ].copy(),
        name="STOCK_A",
    )
    cerebro.adddata(stock_a_data)

    stock_b_data = bt.feeds.PandasData(
        dataname=multi_data[
            [
                "STOCK_B_Open",
                "STOCK_B_High",
                "STOCK_B_Low",
                "STOCK_B_Close",
                "STOCK_B_Volume",
            ]
        ].copy(),
        name="STOCK_B",
    )
    cerebro.adddata(stock_b_data)

    stock_c_data = bt.feeds.PandasData(
        dataname=multi_data[
            [
                "STOCK_C_Open",
                "STOCK_C_High",
                "STOCK_C_Low",
                "STOCK_C_Close",
                "STOCK_C_Volume",
            ]
        ].copy(),
        name="STOCK_C",
    )
    cerebro.adddata(stock_c_data)

    bond_d_data = bt.feeds.PandasData(
        dataname=multi_data[
            [
                "BOND_D_Open",
                "BOND_D_High",
                "BOND_D_Low",
                "BOND_D_Close",
                "BOND_D_Volume",
            ]
        ].copy(),
        name="BOND_D",
    )
    cerebro.adddata(bond_d_data)

    # 测试两种优化方法
    print("1. 均值-方差优化:")
    cerebro.addstrategy(
        MultiAssetStrategy,
        optimization_method="mean_variance",
        rebalance_frequency=20,
        printlog=True,
    )

    # 添加分析器
    cerebro.addanalyzer(MeanVarianceOptimizer, _name="mv_optimizer")
    cerebro.addanalyzer(RiskParityOptimizer, _name="rp_optimizer")

    # 设置初始条件
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    # 运行回测
    print("开始均值-方差优化回测...")
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    mv_strategy = results[0]

    mv_final_value = cerebro.broker.getvalue()
    print("\n均值-方差优化结果:")
    print(f"初始资金: {initial_value:.2f}")
    print(f"最终资金: {mv_final_value:.2f}")
    print(f"收益率: {(mv_final_value - initial_value) / initial_value:.2%}")

    print("\n" + "=" * 50 + "\n")

    # 重新初始化进行风险平价测试
    cerebro = bt.Cerebro()

    # 重新添加数据
    cerebro.adddata(stock_a_data)
    cerebro.adddata(stock_b_data)
    cerebro.adddata(stock_c_data)
    cerebro.adddata(bond_d_data)

    print("2. 风险平价优化:")
    cerebro.addstrategy(
        MultiAssetStrategy,
        optimization_method="risk_parity",
        rebalance_frequency=20,
        printlog=True,
    )

    cerebro.addanalyzer(RiskParityOptimizer, _name="rp_optimizer")
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    print("开始风险平价优化回测...")
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    rp_strategy = results[0]

    rp_final_value = cerebro.broker.getvalue()
    print("\n风险平价优化结果:")
    print(f"初始资金: {initial_value:.2f}")
    print(f"最终资金: {rp_final_value:.2f}")
    print(f"收益率: {(rp_final_value - initial_value) / initial_value:.2%}")


if __name__ == "__main__":
    main()
