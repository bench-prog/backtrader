#!/usr/bin/env python3
"""
多资产交易完整示例
展示如何同时交易股票、期货、加密货币等不同资产类别
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

from real_trade.core.multi_asset import (
    AssetType,
    MultiAssetCommissionInfo,
    MultiAssetData,
    MultiAssetSizer,
    MultiAssetStrategy,
    create_future_info,
    create_stock_info,
)


class DiversifiedPortfolioStrategy(MultiAssetStrategy):
    """
    分散化投资组合策略
    同时交易多种资产类别以降低风险
    """

    params = (
        ("stock_weight", 0.4),  # 股票占比
        ("future_weight", 0.3),  # 期货占比
        ("crypto_weight", 0.2),  # 加密货币占比
        ("bond_weight", 0.1),  # 债券占比
        ("rebalance_frequency", 5),  # 再平衡频率（天）
    )

    def __init__(self):
        super().__init__()

        # 初始化多资产仓位管理器
        self.sizer = MultiAssetSizer()

        # 为不同资产类型设置不同的风险参数
        self.sizer.set_asset_config(
            AssetType.STOCK,
            {
                "risk_per_trade": 0.015,  # 股票风险稍低
                "max_position_value": 0.15,
            },
        )

        self.sizer.set_asset_config(
            AssetType.FUTURE,
            {
                "risk_per_trade": 0.025,  # 期货风险较高
                "max_position_value": 0.20,
            },
        )

        self.sizer.set_asset_config(
            AssetType.CRYPTO,
            {
                "risk_per_trade": 0.03,  # 加密货币风险最高
                "max_position_value": 0.10,
            },
        )

        # 技术指标
        self.indicators = {}
        for data in self.datas:
            asset_info = self.get_asset_info(data)
            if asset_info:
                # 为每种资产创建相应的技术指标
                self.indicators[data._name] = {
                    "sma_fast": bt.indicators.SimpleMovingAverage(data, period=10),
                    "sma_slow": bt.indicators.SimpleMovingAverage(data, period=30),
                    "rsi": bt.indicators.RSI(data, period=14),
                }

        self.days_passed = 0

    def next(self):
        """主逻辑循环"""
        super().next()

        self.days_passed += 1

        # 定期再平衡
        if self.days_passed % self.p.rebalance_frequency == 0:
            self._rebalance_portfolio()

        # 为每种资产生成信号
        for data in self.datas:
            self._generate_asset_signal(data)

    def _generate_asset_signal(self, data):
        """为特定资产生成交易信号"""
        asset_info = self.get_asset_info(data)
        if not asset_info or data._name not in self.indicators:
            return

        indicators = self.indicators[data._name]

        # 基于移动平均线交叉的信号
        cross_up = (
            indicators["sma_fast"][0] > indicators["sma_slow"][0]
            and indicators["sma_fast"][-1] <= indicators["sma_slow"][-1]
        )
        cross_down = (
            indicators["sma_fast"][0] < indicators["sma_slow"][0]
            and indicators["sma_fast"][-1] >= indicators["sma_slow"][-1]
        )

        # 结合RSI过滤
        rsi = indicators["rsi"][0]
        rsi_confirm = (rsi < 30) if cross_up else (rsi > 70) if cross_down else False

        # 根据资产类型调整信号强度
        base_confidence = 0.6
        asset_multiplier = {
            AssetType.STOCK: 1.0,
            AssetType.FUTURE: 1.2,  # 期货信号权重更高
            AssetType.CRYPTO: 0.8,  # 加密货币信号权重较低
            AssetType.BOND: 0.5,  # 债券信号权重最低
        }.get(asset_info.asset_type, 1.0)

        confidence = base_confidence * asset_multiplier
        if rsi_confirm:
            confidence += 0.1

        # 执行交易
        current_position = self.getposition(data)

        if cross_up and current_position.size <= 0 and confidence > 0.7:
            # 买入信号
            size = self.sizer._getsizing(
                self.broker.getcommissioninfo(data), self.broker.getcash(), data, True
            )
            if size > 0:
                self.buy(data=data, size=size)
                self.log(
                    f"买入 {data._name}: {size} 手，价格 {data.close[0]:.2f}，置信度 {confidence:.2f}"
                )

        elif cross_down and current_position.size >= 0 and confidence > 0.7:
            # 卖出信号
            if current_position.size > 0:
                self.sell(data=data, size=current_position.size)
                self.log(
                    f"卖出 {data._name}: {current_position.size} 手，价格 {data.close[0]:.2f}，置信度 {confidence:.2f}"
                )

    def _rebalance_portfolio(self):
        """投资组合再平衡"""
        total_value = self.broker.getvalue()
        target_allocations = {
            AssetType.STOCK: self.p.stock_weight,
            AssetType.FUTURE: self.p.future_weight,
            AssetType.CRYPTO: self.p.crypto_weight,
            AssetType.BOND: self.p.bond_weight,
        }

        self.log("执行投资组合再平衡")

        # 计算当前各类资产的价值
        current_allocations = {}
        for data in self.datas:
            asset_info = self.get_asset_info(data)
            if asset_info:
                position = self.getposition(data)
                if position.size != 0:
                    value = abs(position.size * data.close[0])
                    asset_type = asset_info.asset_type

                    if asset_type not in current_allocations:
                        current_allocations[asset_type] = 0
                    current_allocations[asset_type] += value

        # 调整仓位以匹配目标配置
        for asset_type, target_weight in target_allocations.items():
            current_value = current_allocations.get(asset_type, 0)
            target_value = total_value * target_weight
            deviation = (current_value - target_value) / total_value

            if abs(deviation) > 0.05:  # 5%偏差才调整
                self.log(f"{asset_type.value} 类资产偏离目标 {deviation:.2%}，需要调整")

    def stop(self):
        """策略结束"""
        self.log("=== 最终投资组合统计 ===")
        self.log(f"最终资产价值: {self.broker.getvalue():.2f}")
        self.log(
            f"总投资收益: {(self.broker.getvalue() - self.broker.startingcash) / self.broker.startingcash:.2%}"
        )

        # 显示各资产持仓情况
        self.log("最终持仓:")
        for asset_name, pos_info in self.asset_positions.items():
            self.log(
                f"  {asset_name}: {pos_info['size']} 手，价值 {pos_info['value']:.2f}"
            )


def create_sample_multi_asset_data():
    """创建多资产示例数据"""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=200, freq="D")

    # 股票数据 (AAPL)
    stock_returns = np.random.normal(0.001, 0.02, 200)
    stock_prices = 150 * np.exp(np.cumsum(stock_returns))
    stock_df = pd.DataFrame(
        {
            "open": stock_prices * (1 + np.random.normal(0, 0.005, 200)),
            "high": stock_prices * (1 + abs(np.random.normal(0, 0.01, 200))),
            "low": stock_prices * (1 - abs(np.random.normal(0, 0.01, 200))),
            "close": stock_prices,
            "volume": np.random.randint(1000000, 5000000, 200),
        },
        index=dates,
    )

    # 期货数据 (ES期货)
    future_returns = np.random.normal(0.0008, 0.015, 200)
    future_prices = 4000 + np.cumsum(future_returns * 4000)
    future_df = pd.DataFrame(
        {
            "open": future_prices * (1 + np.random.normal(0, 0.002, 200)),
            "high": future_prices * (1 + abs(np.random.normal(0, 0.005, 200))),
            "low": future_prices * (1 - abs(np.random.normal(0, 0.005, 200))),
            "close": future_prices,
            "volume": np.random.randint(5000, 20000, 200),
        },
        index=dates,
    )

    # 加密货币数据 (BTC)
    crypto_returns = np.random.normal(0.002, 0.04, 200)  # 更高波动性
    crypto_prices = 20000 * np.exp(np.cumsum(crypto_returns))
    crypto_df = pd.DataFrame(
        {
            "open": crypto_prices * (1 + np.random.normal(0, 0.01, 200)),
            "high": crypto_prices * (1 + abs(np.random.normal(0, 0.02, 200))),
            "low": crypto_prices * (1 - abs(np.random.normal(0, 0.02, 200))),
            "close": crypto_prices,
            "volume": np.random.randint(1000, 10000, 200),
        },
        index=dates,
    )

    # 债券数据 (TLT)
    bond_returns = np.random.normal(0.0002, 0.008, 200)  # 低波动性
    bond_prices = 120 + np.cumsum(bond_returns * 120)
    bond_df = pd.DataFrame(
        {
            "open": bond_prices * (1 + np.random.normal(0, 0.001, 200)),
            "high": bond_prices * (1 + abs(np.random.normal(0, 0.002, 200))),
            "low": bond_prices * (1 - abs(np.random.normal(0, 0.002, 200))),
            "close": bond_prices,
            "volume": np.random.randint(10000, 50000, 200),
        },
        index=dates,
    )

    return {
        "AAPL": (stock_df, create_stock_info("AAPL", "NASDAQ")),
        "ES_FUTURE": (future_df, create_future_info("ES", "CME", contract_size=50)),
        "BTC_USD": (crypto_df, create_stock_info("BTC", "CRYPTO", currency="USD")),
        "TLT_BOND": (bond_df, create_stock_info("TLT", "NASDAQ", currency="USD")),
    }


def main():
    """主函数"""
    print("=== Backtrader多资产交易演示 ===\n")

    # 创建引擎
    cerebro = bt.Cerebro()

    # 创建多资产数据
    asset_data = create_sample_multi_asset_data()

    # 添加数据源
    for asset_name, (df, asset_info) in asset_data.items():
        data = MultiAssetData(dataname=df, name=asset_name, asset_info=asset_info)
        cerebro.adddata(data)

        # 为每种资产设置相应的佣金
        commission_info = MultiAssetCommissionInfo(asset_info)
        cerebro.broker.addcommissioninfo(commission_info, data)

    # 添加策略
    cerebro.addstrategy(
        DiversifiedPortfolioStrategy,
        printlog=True,
        diversification_limit=0.3,
        stock_weight=0.4,
        future_weight=0.3,
        crypto_weight=0.2,
        bond_weight=0.1,
    )

    # 设置仓位管理器
    cerebro.addsizer(MultiAssetSizer, risk_per_trade=0.02, max_position_value=0.2)

    # 设置初始条件
    cerebro.broker.setcash(100000.0)

    # 添加观察器
    cerebro.addobserver(bt.observers.Broker)
    cerebro.addobserver(bt.observers.Trades)
    cerebro.addobserver(bt.observers.DrawDown)

    # 运行回测
    print("开始多资产回测...")
    initial_value = cerebro.broker.getvalue()
    results = cerebro.run()
    strategy = results[0]

    final_value = cerebro.broker.getvalue()
    print(f"\n初始资金: {initial_value:.2f}")
    print(f"最终资金: {final_value:.2f}")
    print(f"总收益率: {(final_value - initial_value) / initial_value:.2%}")

    # 计算一些基本统计
    returns = (final_value - initial_value) / initial_value
    annual_return = (1 + returns) ** (252 / 200) - 1  # 年化收益率
    print(f"年化收益率: {annual_return:.2%}")


if __name__ == "__main__":
    main()
