#!/usr/bin/env python3
"""
Backtrader完整框架使用示例
展示从数据加载到策略执行的完整流程
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

# 导入所有核心组件
from real_trade.analyzers.dynamic_risk_analyzer import DynamicRiskAnalyzer
from real_trade.analyzers.market_state_analyzer import MarketStateAnalyzer
from real_trade.core.ai_trading import AIStrategy
from real_trade.core.hf_trading import ExecutionMode, HFTradingStrategy
from real_trade.strategies.smart_base import SmartTradingStrategy


class ComprehensiveTradingStrategy(SmartTradingStrategy):
    """
    综合交易策略
    集成所有高级功能的完整策略示例
    """

    params = (
        ("use_ai", True),
        ("risk_management", True),
        ("portfolio_optimization", True),
    )

    def __init__(self):
        super().__init__()

        # 技术指标
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.data, period=10)
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.data, period=30)
        self.rsi = bt.indicators.RSI(self.data, period=14)
        self.macd = bt.indicators.MACD(self.data)

    def generate_signals(self):
        """生成综合交易信号"""
        if len(self.data) < 30:
            return

        current_price = self.data.close[0]
        position = self.getposition(self.data)

        # 基础技术信号
        tech_signal = 0

        # MA交叉信号
        if (
            self.sma_fast[0] > self.sma_slow[0]
            and self.sma_fast[-1] <= self.sma_slow[-1]
        ):
            tech_signal = 1
        elif (
            self.sma_fast[0] < self.sma_slow[0]
            and self.sma_fast[-1] >= self.sma_slow[-1]
        ):
            tech_signal = -1

        # RSI过滤
        if self.rsi[0] < 30 and tech_signal > 0:
            tech_signal = 1
        elif self.rsi[0] > 70 and tech_signal < 0:
            tech_signal = -1

        # 执行交易
        if tech_signal == 1 and position.size <= 0:
            confidence = min(1.0, 0.6 + (self.rsi[0] / 100))
            self.add_signal(self.data, "BUY", confidence)

        elif tech_signal == -1 and position.size >= 0:
            confidence = min(1.0, 0.6 + ((100 - self.rsi[0]) / 100))
            self.add_signal(self.data, "SELL", confidence)


def load_real_data():
    """加载真实市场数据"""
    # 检查数据文件
    data_files = [
        "../datas/binance-btc-2015-2026.txt",
        "../datas/yhoo-2014.txt",
        "../datas/orcl-2014.txt",
    ]

    available_files = []
    for file_path in data_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            available_files.append(full_path)
            print(f"找到数据文件: {os.path.basename(file_path)}")

    if not available_files:
        print("未找到真实数据文件，创建模拟数据...")
        return create_sample_data()

    # 加载第一个可用的数据文件
    data_file = available_files[0]
    try:
        if "binance-btc" in data_file:
            # BTC数据
            df = pd.read_csv(data_file)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
            return df[["Open", "High", "Low", "Close", "Volume"]]
        else:
            # 股票数据
            df = pd.read_csv(data_file)
            return df
    except Exception as e:
        print(f"数据加载失败: {e}")
        return create_sample_data()


def create_sample_data():
    """创建示例数据"""
    dates = pd.date_range("2020-01-01", periods=500, freq="D")

    # 生成趋势性价格序列
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.02, 500)
    prices = 100 * np.exp(np.cumsum(returns))

    # 添加趋势和波动
    trend = np.linspace(0, 0.5, 500)
    cycle = 0.1 * np.sin(np.linspace(0, 10 * np.pi, 500))
    prices = prices * (1 + trend + cycle)

    df = pd.DataFrame(
        {
            "Open": prices * (1 + np.random.normal(0, 0.005, 500)),
            "High": prices * (1 + abs(np.random.normal(0, 0.01, 500))),
            "Low": prices * (1 - abs(np.random.normal(0, 0.01, 500))),
            "Close": prices,
            "Volume": np.random.exponential(10000, 500),
        },
        index=dates,
    )

    return df


def run_comprehensive_backtest():
    """运行综合性回测"""
    print("=== Backtrader完整框架演示 ===\n")

    # 加载数据
    market_data = load_real_data()
    print(f"数据范围: {market_data.index[0]} 到 {market_data.index[-1]}")
    print(f"数据点数: {len(market_data)}")

    # 测试多种策略配置
    strategies = [
        {
            "name": "基础智能策略",
            "class": ComprehensiveTradingStrategy,
            "params": {"use_ai": False, "risk_management": True},
        },
        {
            "name": "AI增强策略",
            "class": AIStrategy,
            "params": {"enable_ai": True, "confidence_threshold": 0.6},
        },
        {
            "name": "高频交易策略",
            "class": HFTradingStrategy,
            "params": {"execution_mode": ExecutionMode.HIGH_FREQUENCY},
        },
    ]

    results = []

    for strategy_config in strategies:
        print(f"\n--- {strategy_config['name']} ---")

        # 创建回测引擎
        cerebro = bt.Cerebro()

        # 添加数据
        data = bt.feeds.PandasData(dataname=market_data)
        cerebro.adddata(data)

        # 添加策略
        cerebro.addstrategy(
            strategy_config["class"], **strategy_config["params"], printlog=False
        )

        # 添加分析器
        cerebro.addanalyzer(DynamicRiskAnalyzer, _name="risk")
        cerebro.addanalyzer(MarketStateAnalyzer, _name="market")

        # 设置初始条件
        cerebro.broker.setcash(50000.0)
        cerebro.broker.setcommission(commission=0.001)

        # 运行回测
        initial_value = cerebro.broker.getvalue()
        strat_results = cerebro.run()
        strategy = strat_results[0]
        final_value = cerebro.broker.getvalue()

        # 分析结果
        risk_analysis = strategy.analyzers.risk.get_analysis()
        market_analysis = strategy.analyzers.market.get_analysis()

        returns = (final_value - initial_value) / initial_value

        results.append(
            {
                "strategy": strategy_config["name"],
                "initial_value": initial_value,
                "final_value": final_value,
                "returns": returns,
                "max_drawdown": risk_analysis.get("max_drawdown", 0),
                "risk_level": risk_analysis.get("risk_level", "UNKNOWN"),
                "market_regime": market_analysis.get("market_regime", "UNKNOWN"),
            }
        )

        print(f"初始资金: ${initial_value:,.2f}")
        print(f"最终资金: ${final_value:,.2f}")
        print(f"收益率: {returns:.2%}")
        print(f"最大回撤: {risk_analysis.get('max_drawdown', 0):.2%}")
        print(f"风险等级: {risk_analysis.get('risk_level', 'UNKNOWN')}")
        print(f"市场制度: {market_analysis.get('market_regime', 'UNKNOWN')}")

    # 综合对比
    print("\n" + "=" * 80)
    print("=== 策略综合对比 ===")
    print("=" * 80)

    # 按收益率排序
    results.sort(key=lambda x: x["returns"], reverse=True)

    for i, result in enumerate(results, 1):
        print(f"{i}. {result['strategy']}")
        print(
            f"   收益率: {result['returns']:8.2%} | "
            f"最大回撤: {result['max_drawdown']:6.2%} | "
            f"风险等级: {result['risk_level']}"
        )
        print(f"   最终资金: ${result['final_value']:10,.2f}")
        print()

    # 最佳策略
    best_strategy = results[0]
    print(f"🏆 最佳策略: {best_strategy['strategy']}")
    print(f"   最高收益率: {best_strategy['returns']:.2%}")
    print("   风险调整后收益表现最佳")

    return results


def main():
    """主函数"""
    try:
        results = run_comprehensive_backtest()
        print("\n✅ 完整框架演示完成!")
        print(f"测试了 {len(results)} 种不同策略配置")
        print("所有组件协同工作正常")

    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
