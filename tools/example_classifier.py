#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backtrader 示例分类整理方案
Backtrader Examples Classification and Organization Plan

根据功能类型对企业级示例进行分组和分类
"""

EXAMPLE_CATEGORIES = {
    "企业级核心功能": {
        "描述": "新添加的企业级基础设施功能示例",
        "示例文件": [
            "examples/scheduler_logging_demo.py",  # 任务调度和日志增强
            "samples/risk-management/risk_management_demo.py",  # 风险管理
            "samples/monitoring-alerting/monitoring_alerting_demo.py",  # 监控告警
            "samples/configuration-management/config_management_demo.py",  # 配置管理
        ],
        "运行命令": [
            "python examples/scheduler_logging_demo.py",
            "python samples/risk-management/risk_management_demo.py",
            "python samples/monitoring-alerting/monitoring_alerting_demo.py",
            "python samples/configuration-management/config_management_demo.py",
        ],
    },
    "数据集成示例": {
        "描述": "各种数据源接入和处理示例",
        "示例文件": [
            "samples/data-pandas/data-pandas.py",
            "samples/data-multitimeframe/data-multitimeframe.py",
            "samples/data-resample/data-resample.py",
            "samples/data-replay/data-replay.py",
            "samples/yahoo-test/yahoo-test.py",
        ],
    },
    "策略开发示例": {
        "描述": "策略编写和信号生成示例",
        "示例文件": [
            "samples/sigsmacross/sigsmacross.py",
            "samples/macd-settings/macd-settings.py",
            "samples/rsi/rsi-test.py",
            "samples/signals-strategy/signals-strategy.py",
        ],
    },
    "风控交易示例": {
        "描述": "风险控制和订单管理示例",
        "示例文件": [
            "samples/order-execution/order-execution.py",
            "samples/stop-trading/stop-loss-approaches.py",
            "samples/stoptrail/trail.py",
            "samples/bracket/bracket.py",
            "samples/oco/oco.py",
        ],
    },
    "性能分析示例": {
        "描述": "回测分析和绩效评估示例",
        "示例文件": [
            "samples/analyzer-annualreturn/analyzer-annualreturn.py",
            "samples/sharpe-timereturn/sharpe-timereturn.py",
            "samples/calmar/calmar-test.py",
            "samples/observer-benchmark/observer-benchmark.py",
        ],
    },
    "实盘交易示例": {
        "描述": "实盘交易对接示例",
        "示例文件": [
            "samples/binance-test/binance_test.py",
            "samples/ibtest/ibtest.py",
            "samples/oandatest/oandatest.py",
        ],
    },
}


def print_classification_plan():
    """打印分类整理方案"""
    print("🏛️  Backtrader 示例分类整理方案")
    print("=" * 60)

    for category, info in EXAMPLE_CATEGORIES.items():
        print(f"\n📁 {category}")
        print(f"📝 描述: {info['描述']}")
        print(f"📄 示例数量: {len(info.get('示例文件', []))}")

        if "示例文件" in info:
            print("📋 示例文件:")
            for i, example in enumerate(info["示例文件"], 1):
                print(f"  {i}. {example}")

        if "运行命令" in info:
            print("⚡ 运行命令:")
            for cmd in info["运行命令"]:
                print(f"  $ {cmd}")


if __name__ == "__main__":
    print_classification_plan()
