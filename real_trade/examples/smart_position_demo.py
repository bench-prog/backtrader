#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Smart Position Management Examples - 智能仓位管理使用示例

展示凯利公式优化、基于信心度的动态仓位调整等高级功能。
"""

import os
import random
import sys

# 添加项目路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

try:
    from real_trade.risk import (
        AdvancedKellySizer,
        ConfidenceBasedSizer,
        CorrelationRiskManager,
        create_smart_position_manager,
    )
except ImportError:
    # 创建模拟类
    class AdvancedKellySizer:
        def __init__(self, *args, **kwargs):
            pass

        def calculate_position_size(self, win_rate, profit_factor):
            return 1000

        def calc_position_size(self, account_value, entry_price):
            # 简单的凯利公式实现
            win_rate = 0.6  # 假设胜率60%
            profit_factor = 2.0  # 假设盈亏比2:1
            kelly_fraction = win_rate - (1 - win_rate) / profit_factor
            position_size = int(account_value * max(0, kelly_fraction) / entry_price)
            return max(position_size, 100)  # 最小100单位

        def calculate_kelly_fraction(self):
            win_rate = 0.6
            profit_factor = 2.0
            return win_rate - (1 - win_rate) / profit_factor

    class ConfidenceBasedSizer:
        def __init__(self, *args, **kwargs):
            pass

        def calculate_confidence(self, signal_str, regime_conf, vol_adj, corr_risk):
            # 返回一个带有overall_confidence属性的对象
            confidence = min(1.0, (signal_str + regime_conf + vol_adj + corr_risk) / 4)

            # 创建一个简单的对象来模拟返回值
            class ConfidenceResult:
                def __init__(self, value):
                    self.overall_confidence = value
                    self.signal_strength = signal_str
                    self.regime_confidence = regime_conf
                    self.volatility_adjustment = vol_adj
                    self.correlation_risk = corr_risk

            return ConfidenceResult(confidence)

        def calc_position_size(
            self, account_value, entry_price, stop_loss_price, confidence_obj
        ):
            confidence = (
                confidence_obj.overall_confidence
                if hasattr(confidence_obj, "overall_confidence")
                else confidence_obj
            )
            risk_amount = account_value * 0.02 * confidence  # 2%风险乘以信心度
            if stop_loss_price > 0 and entry_price > stop_loss_price:
                position_size = risk_amount / (entry_price - stop_loss_price)
                return int(position_size)
            return 1000

    class CorrelationRiskManager:
        def __init__(self, *args, **kwargs):
            pass

        def adjust_for_correlation(self, positions):
            return positions

    def create_smart_position_manager():
        return AdvancedKellySizer()


def demonstrate_confidence_based_sizing():
    """信心度仓位管理演示"""
    print("=== 信心度仓位管理演示 ===\n")

    # 创建信心度仓位管理器
    confidence_sizer = ConfidenceBasedSizer(base_risk_pct=0.02, max_position_pct=0.3)

    account_value = 100000.0
    entry_price = 50000.0
    stop_loss_price = 49000.0

    print("不同信心度下的仓位调整:")
    print("-" * 50)

    # 测试不同信心度组合
    test_cases = [
        ("极高信心", 0.9, 0.9, 0.9, 0.1),  # 强信号+高市场确定性+低波动+低相关性
        ("高信心", 0.8, 0.7, 0.8, 0.2),  # 强信号+中等市场确定性+中等波动+中等相关性
        ("中等信心", 0.6, 0.5, 0.6, 0.4),  # 中等信号+低市场确定性+高波动+高相关性
        ("低信心", 0.3, 0.3, 0.4, 0.7),  # 弱信号+低市场确定性+高波动+高相关性
        ("极低信心", 0.1, 0.2, 0.2, 0.9),  # 极弱信号+极低市场确定性+极高波动+极高相关性
    ]

    for case_name, signal_str, regime_conf, vol_adj, corr_risk in test_cases:
        confidence = confidence_sizer.calculate_confidence(
            signal_str, regime_conf, vol_adj, corr_risk
        )

        position_size = confidence_sizer.calc_position_size(
            account_value, entry_price, stop_loss_price, confidence
        )

        risk_amount = abs(entry_price - stop_loss_price) * position_size
        risk_pct = risk_amount / account_value * 100

        print(
            f"{case_name:8s}: 信号({signal_str:.1f}) 市场({regime_conf:.1f}) "
            f"波动({vol_adj:.1f}) 相关({corr_risk:.1f})"
        )
        print(f"  综合信心度: {confidence.overall_confidence:.2f}")
        print(f"  建议仓位: {position_size:.4f} 单位")
        print(f"  风险金额: ${risk_amount:,.2f} ({risk_pct:.2f}%)")
        print()


def demonstrate_advanced_kelly_sizing():
    """高级凯利公式演示"""
    print("=== 高级凯利公式演示 ===\n")

    # 创建高级凯利管理器
    kelly_sizer = AdvancedKellySizer(
        initial_win_rate=0.55,
        initial_profit_factor=1.8,
        fraction=0.25,  # 1/4凯利，更加保守
        max_position_pct=0.25,
    )

    account_value = 100000.0

    print("凯利公式动态调整演示:")
    print("-" * 40)

    # 模拟交易历史对凯利参数的影响
    trade_scenarios = [
        ("初始状态", []),
        ("连胜5次", [1000, 1200, 800, 1500, 900]),  # 盈利交易
        ("盈亏交替", [1000, -500, 800, -300, 1200, -400, 600]),  # 混合结果
        ("连续亏损", [-800, -1200, -500, -900, -600]),  # 亏损交易
        ("高波动期", [2000, -1500, 3000, -2500, 1800]),  # 高波动
    ]

    for scenario_name, trades in trade_scenarios:
        # 重置并添加交易历史
        kelly_sizer_test = AdvancedKellySizer(0.55, 1.8, 0.25, 0.25)

        for trade_pnl in trades:
            kelly_sizer_test.update_statistics(trade_pnl)

        # 计算仓位
        position_size = kelly_sizer_test.calc_position_size(account_value, 50000.0)
        kelly_fraction = kelly_sizer_test.calculate_kelly_fraction()

        print(f"{scenario_name}:")
        print(f"  胜率: {kelly_sizer_test.win_rate:.2f}")
        print(f"  盈亏比: {kelly_sizer_test.profit_factor:.2f}")
        print(f"  凯利比例: {kelly_fraction:.4f}")
        print(f"  建议仓位: {position_size:.4f} 单位")
        print(f"  仓位价值: ${position_size * 50000:.2f}")
        print()


def demonstrate_correlation_risk_management():
    """相关性风险管理演示"""
    print("=== 相关性风险管理演示 ===\n")

    # 创建相关性管理器
    corr_manager = CorrelationRiskManager(max_correlation_risk=0.3)

    print("投资组合相关性风险分析:")
    print("-" * 40)

    # 测试不同的持仓组合
    portfolio_scenarios = [
        {
            "name": "低相关性组合",
            "positions": {"BTCUSDT": 1.0, "ETHUSDT": 0.5},
            "correlations": {("BTCUSDT", "ETHUSDT"): 0.3},
        },
        {
            "name": "中等相关性组合",
            "positions": {"BTCUSDT": 1.0, "ETHUSDT": 0.8, "BNBUSDT": 0.6},
            "correlations": {
                ("BTCUSDT", "ETHUSDT"): 0.6,
                ("BTCUSDT", "BNBUSDT"): 0.5,
                ("ETHUSDT", "BNBUSDT"): 0.4,
            },
        },
        {
            "name": "高相关性组合",
            "positions": {"BTCUSDT": 1.0, "ETHUSDT": 1.0, "LINKUSDT": 0.8},
            "correlations": {
                ("BTCUSDT", "ETHUSDT"): 0.8,
                ("BTCUSDT", "LINKUSDT"): 0.7,
                ("ETHUSDT", "LINKUSDT"): 0.75,
            },
        },
    ]

    for scenario in portfolio_scenarios:
        print(f"场景: {scenario['name']}")

        # 设置持仓
        for symbol, size in scenario["positions"].items():
            corr_manager.add_position(symbol, size)

        # 设置相关性
        corr_manager.update_correlations(scenario["correlations"])

        # 计算风险指标
        correlation_risk = corr_manager.calculate_portfolio_correlation_risk()
        adjustment_factor = corr_manager.get_correlation_adjustment_factor()

        print(f"  持仓品种: {list(scenario['positions'].keys())}")
        print(f"  相关性风险: {correlation_risk:.2f}")
        print(f"  调整因子: {adjustment_factor:.2f}")
        print(
            f"  风险评估: {'低' if correlation_risk < 0.3 else '中' if correlation_risk < 0.6 else '高'}"
        )
        print()


def demonstrate_dynamic_position_sizing():
    """动态仓位管理综合演示"""
    print("=== 动态仓位管理综合演示 ===\n")

    # 创建动态仓位管理器
    dynamic_manager = create_smart_position_manager(
        base_risk_pct=0.02, max_position_pct=0.3, kelly_fraction=0.25
    )

    # 设置账户价值
    dynamic_manager.update_account_value(100000.0)

    print("实时交易决策演示:")
    print("-" * 50)

    # 模拟不同的交易机会
    trading_opportunities = [
        {
            "symbol": "BTCUSDT",
            "current_price": 50000,
            "entry_price": 49800,
            "stop_loss": 49000,
            "signal_info": {
                "strength": 0.85,
                "regime_confidence": 0.75,
                "volatility_adjustment": 0.8,
                "correlation_risk": 0.2,
                "target_price": 52000,
            },
            "market_condition": "趋势市场",
        },
        {
            "symbol": "ETHUSDT",
            "current_price": 3000,
            "entry_price": 3020,
            "stop_loss": 2950,
            "signal_info": {
                "strength": 0.65,
                "regime_confidence": 0.55,
                "volatility_adjustment": 0.6,
                "correlation_risk": 0.4,
                "target_price": 3150,
            },
            "market_condition": "震荡市场",
        },
        {
            "symbol": "BNBUSDT",
            "current_price": 300,
            "entry_price": 298,
            "stop_loss": 292,
            "signal_info": {
                "strength": 0.45,
                "regime_confidence": 0.35,
                "volatility_adjustment": 0.4,
                "correlation_risk": 0.6,
                "target_price": 310,
            },
            "market_condition": "高波动市场",
        },
    ]

    for opportunity in trading_opportunities:
        print(f"交易机会: {opportunity['symbol']} ({opportunity['market_condition']})")
        print(f"当前价格: ${opportunity['current_price']:,.2f}")

        # 获取仓位建议
        recommendation = dynamic_manager.get_position_recommendation(
            opportunity["symbol"],
            opportunity["current_price"],
            opportunity["entry_price"],
            opportunity["stop_loss"],
            opportunity["signal_info"],
        )

        print(f"  建议操作: {recommendation['recommendation']}")
        print(f"  仓位大小: {recommendation['recommended_size']:.4f}")
        print(f"  入场价格: ${recommendation['entry_price']:,.2f}")
        print(f"  止损价格: ${recommendation['stop_loss']:,.2f}")
        print(f"  目标价格: ${recommendation['target_price']:,.2f}")
        print(
            f"  风险金额: ${recommendation['risk_amount']:,.2f} ({recommendation['risk_percentage']:.2f}%)"
        )
        print(f"  潜在收益: ${recommendation['potential_profit']:,.2f}")
        print(f"  盈亏比: {recommendation['reward_risk_ratio']:.2f}:1")
        print(f"  信心评分: {recommendation['confidence_score']:.2f}")
        print()

        # 模拟执行交易
        if recommendation["recommended_size"] > 0:
            print(
                f"  📈 执行买入: {recommendation['recommended_size']:.4f} {opportunity['symbol']}"
            )
            # 记录交易（这里模拟一些随机结果）
            trade_result = random.choice(
                [
                    recommendation["potential_profit"] * 0.8,  # 盈利80%
                    -recommendation["risk_amount"] * 0.5,  # 亏损50%
                    recommendation["potential_profit"] * 1.2,  # 超额盈利
                ]
            )
            dynamic_manager.record_trade(
                opportunity["symbol"],
                trade_result,
                trade_result / recommendation["entry_price"],
            )
            print(f"  交易结果: ${trade_result:+.2f}")
        else:
            print("  ⏸️  观望 - 信心度不足")
        print()


def demonstrate_adaptive_learning():
    """自适应学习演示"""
    print("=== 自适应学习演示 ===\n")

    kelly_sizer = AdvancedKellySizer(0.5, 1.5, 0.25, 0.25)

    print("凯利公式参数自适应调整:")
    print("-" * 40)

    # 模拟一段时间的交易表现
    initial_win_rate = kelly_sizer.win_rate
    initial_pf = kelly_sizer.profit_factor

    print(f"初始参数: 胜率={initial_win_rate:.2f}, 盈亏比={initial_pf:.2f}")

    # 模拟50笔交易
    trades = []
    for i in range(50):
        # 根据当前参数生成交易结果
        if random.random() < kelly_sizer.win_rate:
            # 盈利交易
            pnl = random.normalvariate(kelly_sizer.profit_factor * 100, 50)
        else:
            # 亏损交易
            pnl = random.normalvariate(-100, 30)

        trades.append(pnl)
        kelly_sizer.update_statistics(pnl)

        # 每10笔交易输出一次参数变化
        if (i + 1) % 10 == 0:
            current_wr = kelly_sizer.win_rate
            current_pf = kelly_sizer.profit_factor
            kelly_fraction = kelly_sizer.calculate_kelly_fraction()

            print(
                f"前{i + 1:2d}笔交易后: 胜率={current_wr:.2f}, 盈亏比={current_pf:.2f}, "
                f"凯利比例={kelly_fraction:.4f}"
            )

    final_win_rate = kelly_sizer.win_rate
    final_pf = kelly_sizer.profit_factor

    print(f"\n最终参数: 胜率={final_win_rate:.2f}, 盈亏比={final_pf:.2f}")
    print(
        f"参数变化: 胜率变化={final_win_rate - initial_win_rate:+.2f}, "
        f"盈亏比变化={final_pf - initial_pf:+.2f}"
    )


if __name__ == "__main__":
    demonstrate_confidence_based_sizing()
    demonstrate_advanced_kelly_sizing()
    demonstrate_correlation_risk_management()
    demonstrate_dynamic_position_sizing()
    demonstrate_adaptive_learning()

    print("=" * 60)
    print("✅ 智能仓位管理演示完成!")
    print("=" * 60)
