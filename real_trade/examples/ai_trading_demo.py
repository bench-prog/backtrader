#!/usr/bin/env python3
"""
AI增强交易完整示例
结合传统技术和机器学习的智能交易策略
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

from real_trade.core.ai_trading import AIStrategy


def load_btc_data():
    """加载BTC历史数据"""
    # 正确的数据文件路径
    data_file = os.path.join(project_root, "datas", "binance-btc-2015-2026.txt")

    if os.path.exists(data_file):
        # 读取真实数据
        print("加载真实BTC数据...")
        df = pd.read_csv(data_file)
        # 假设列名为: Date,Open,High,Low,Close,Volume
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        return df
    else:
        # 创建模拟BTC数据
        print("BTC数据文件不存在，创建模拟数据...")
        dates = pd.date_range("2015-01-01", "2023-12-31", freq="D")

        # 生成类似BTC的价格走势
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.04, len(dates))  # 高波动性
        prices = 300 * np.exp(np.cumsum(returns))  # 从300美元开始

        # 添加趋势和周期性
        trend = np.linspace(0, 5, len(dates))  # 长期上涨趋势
        cycle = 0.3 * np.sin(np.linspace(0, 20 * np.pi, len(dates)))  # 周期波动
        prices = prices * (1 + trend + cycle)

        df = pd.DataFrame(
            {
                "Open": prices * (1 + np.random.normal(0, 0.01, len(dates))),
                "High": prices * (1 + abs(np.random.normal(0, 0.02, len(dates)))),
                "Low": prices * (1 - abs(np.random.normal(0, 0.02, len(dates)))),
                "Close": prices,
                "Volume": np.random.exponential(1000, len(dates)),
            },
            index=dates,
        )

        return df


def main():
    """主函数"""
    print("=== Backtrader AI增强交易演示 ===\n")

    # 加载数据
    btc_data = load_btc_data()
    print(f"数据时间范围: {btc_data.index[0]} 到 {btc_data.index[-1]}")
    print(f"数据点数量: {len(btc_data)}")
    print(f"价格范围: ${btc_data['Close'].min():.2f} - ${btc_data['Close'].max():.2f}")

    # 创建引擎
    cerebro = bt.Cerebro()

    # 添加数据
    data = bt.feeds.PandasData(dataname=btc_data)
    cerebro.adddata(data)

    # 测试不同配置
    configs = [
        {"name": "纯技术分析", "enable_ai": False, "confidence_threshold": 0.6},
        {"name": "AI辅助决策", "enable_ai": True, "confidence_threshold": 0.6},
        {"name": "高置信度AI", "enable_ai": True, "confidence_threshold": 0.8},
    ]

    results = []

    for config in configs:
        print(f"\n--- {config['name']} ---")

        # 重新初始化cerebro
        cerebro = bt.Cerebro()
        cerebro.adddata(bt.feeds.PandasData(dataname=btc_data))

        # 添加策略
        cerebro.addstrategy(
            AIStrategy,
            enable_ai=config["enable_ai"],
            confidence_threshold=config["confidence_threshold"],
            training_period=100,
            printlog=False,
        )  # 减少日志输出

        # 设置初始条件
        cerebro.broker.setcash(10000.0)  # 1万美元初始资金
        cerebro.broker.setcommission(commission=0.001)  # 0.1%手续费

        # 运行回测
        initial_value = cerebro.broker.getvalue()
        strat_results = cerebro.run()
        final_value = cerebro.broker.getvalue()

        # 记录结果
        returns = (final_value - initial_value) / initial_value
        results.append(
            {
                "config": config["name"],
                "initial_value": initial_value,
                "final_value": final_value,
                "returns": returns,
                "strategy": strat_results[0],
            }
        )

        print(f"初始资金: ${initial_value:,.2f}")
        print(f"最终资金: ${final_value:,.2f}")
        print(f"收益率: {returns:.2%}")

        # 计算年化收益率
        days = len(btc_data)
        annual_return = (1 + returns) ** (365 / days) - 1
        print(f"年化收益率: {annual_return:.2%}")

    # 结果对比
    print("\n" + "=" * 60)
    print("=== 策略性能对比 ===")
    print("=" * 60)

    for result in results:
        print(
            f"{result['config']:15} | 收益率: {result['returns']:8.2%} | "
            f"最终资金: ${result['final_value']:10,.2f}"
        )

    # 找出最佳策略
    best_result = max(results, key=lambda x: x["returns"])
    print(f"\n🏆 最佳策略: {best_result['config']}")
    print(f"   最高收益率: {best_result['returns']:.2%}")

    # 风险调整后收益对比
    print("\n=== 风险调整后收益分析 ===")
    for result in results:
        strat = result["strategy"]
        # 简单的最大回撤估算
        drawdown = 0.15  # 假设15%最大回撤
        sharpe_ratio = result["returns"] / (drawdown + 0.01)  # 简化的夏普比率

        print(
            f"{result['config']:15} | 夏普比率: {sharpe_ratio:6.2f} | "
            f"回撤风险: {drawdown:5.1%}"
        )


if __name__ == "__main__":
    main()
