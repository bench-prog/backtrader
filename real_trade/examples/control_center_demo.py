#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Control Center Usage Example - 控制中枢使用示例
==============================================

展示如何使用交易控制中枢来管理整个交易系统。
包括组件注册、系统监控、风险控制等功能演示。
"""

import os
import sys
import time

# 添加项目路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

# 简单的日志实现
import logging

from real_trade.core.control_center import ComponentType, get_control_center

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


class DemoDataFeed:
    """演示数据源组件"""

    def __init__(self, symbol="BTC/USDT"):
        self.symbol = symbol
        self.running = False
        self.data_count = 0

    def start(self):
        """启动数据源"""
        self.running = True
        logger.info(f"📈 数据源 {self.symbol} 启动")

    def stop(self):
        """停止数据源"""
        self.running = False
        logger.info(f"⏹️ 数据源 {self.symbol} 停止")

    def get_metrics(self):
        """获取指标"""
        return {
            "symbol": self.symbol,
            "data_points": self.data_count,
            "status": "RUNNING" if self.running else "STOPPED",
        }


class DemoStrategy:
    """演示策略组件"""

    def __init__(self, name="Demo Strategy"):
        self.name = name
        self.positions = 0
        self.pnl = 0.0

    def start(self):
        """启动策略"""
        logger.info(f"🧠 策略 {self.name} 启动")

    def stop(self):
        """停止策略"""
        logger.info(f"⏹️ 策略 {self.name} 停止")

    def get_metrics(self):
        """获取指标"""
        return {
            "name": self.name,
            "positions": self.positions,
            "pnl": self.pnl,
            "status": "ACTIVE",
        }


class DemoRiskManager:
    """演示风险管理组件"""

    def __init__(self):
        self.max_exposure = 100000
        self.current_exposure = 0

    def start(self):
        """启动风险管理"""
        logger.info("🛡️ 风险管理启动")

    def stop(self):
        """停止风险管理"""
        logger.info("⏹️ 风险管理停止")

    def get_metrics(self):
        """获取指标"""
        return {
            "max_exposure": self.max_exposure,
            "current_exposure": self.current_exposure,
            "utilization": self.current_exposure / self.max_exposure
            if self.max_exposure > 0
            else 0,
        }


def demonstrate_control_center():
    """演示控制中枢功能"""
    print("🎯 Backtrader 控制中枢演示")
    print("=" * 50)

    # 获取控制中枢实例
    control_center = get_control_center()

    # 1. 注册组件
    print("\n📋 1. 组件注册演示")
    print("-" * 30)

    # 注册数据源
    btc_feed = DemoDataFeed("BTC/USDT")
    eth_feed = DemoDataFeed("ETH/USDT")

    control_center.register_component(
        "btc_data_feed",
        btc_feed,
        ComponentType.DATA_FEED,
        {"symbol": "BTC/USDT", "timeframe": "1m"},
    )

    control_center.register_component(
        "eth_data_feed",
        eth_feed,
        ComponentType.DATA_FEED,
        {"symbol": "ETH/USDT", "timeframe": "1m"},
    )

    # 注册策略
    strategy1 = DemoStrategy("Mean Reversion Strategy")
    strategy2 = DemoStrategy("Trend Following Strategy")

    control_center.register_component(
        "mean_reversion",
        strategy1,
        ComponentType.STRATEGY,
        {"type": "mean_reversion", "lookback": 20},
    )

    control_center.register_component(
        "trend_following",
        strategy2,
        ComponentType.STRATEGY,
        {"type": "trend_following", "period": 50},
    )

    # 注册风险管理
    risk_manager = DemoRiskManager()
    control_center.register_component(
        "risk_manager",
        risk_manager,
        ComponentType.RISK_MANAGER,
        {"max_drawdown": 0.15, "position_limit": 5},
    )

    print(f"✅ 已注册 {len(control_center.components)} 个组件")

    # 2. 启动控制中枢
    print("\n🚀 2. 系统启动演示")
    print("-" * 30)

    if control_center.start():
        print("✅ 控制中枢启动成功")

        # 启动所有组件
        for component_id, component_info in control_center.components.items():
            if hasattr(component_info["instance"], "start"):
                component_info["instance"].start()
                component_info["status"] = "RUNNING"

        print("✅ 所有组件启动完成")
    else:
        print("❌ 控制中枢启动失败")
        return

    # 3. 系统状态监控
    print("\n📊 3. 状态监控演示")
    print("-" * 30)

    # 显示系统状态
    system_status = control_center.get_system_status()
    print(f"系统状态: {system_status['status']}")
    print(f"运行时间: {system_status['uptime']}")
    print(f"组件总数: {system_status['components_count']}")
    print(f"健康组件: {system_status['healthy_components']}")

    # 显示组件状态
    print("\n组件状态详情:")
    component_statuses = control_center.get_component_status()
    for component_id, status in component_statuses.items():
        print(f"  {component_id}: {status.get('health', 'UNKNOWN')}")

    # 4. 模拟运行
    print("\n🔄 4. 系统运行演示 (30秒)")
    print("-" * 30)

    start_time = time.time()
    while time.time() - start_time < 30:
        elapsed = int(time.time() - start_time)
        if elapsed % 5 == 0:  # 每5秒显示一次
            system_status = control_center.get_system_status()
            healthy_count = system_status["healthy_components"]
            total_count = system_status["components_count"]
            print(
                f"[{elapsed:2d}s] 系统运行中 - 健康组件: {healthy_count}/{total_count}"
            )

        time.sleep(1)

    # 5. 风险控制演示
    print("\n🛡️ 5. 风险控制演示")
    print("-" * 30)

    # 模拟风险事件
    print("⚠️ 模拟风险事件:")
    risk_events = ["市场剧烈波动", "组件响应延迟", "资金使用率过高", "最大回撤接近阈值"]

    for event in risk_events:
        print(f"  • 检测到风险: {event}")
        # 这里可以集成实际的风险处理逻辑

    # 6. 系统操作演示
    print("\n🎛️ 6. 系统操作演示")
    print("-" * 30)

    # 暂停系统
    print("⏸️ 暂停系统...")
    if control_center.pause():
        print("✅ 系统已暂停")
        time.sleep(3)

        # 恢复系统
        print("▶️ 恢复系统...")
        if control_center.resume():
            print("✅ 系统已恢复")

    # 7. 系统停止
    print("\n🛑 7. 系统停止演示")
    print("-" * 30)

    print("⏹️ 停止控制中枢...")
    if control_center.stop():
        print("✅ 控制中枢已停止")

    # 8. 最终状态报告
    print("\n📈 8. 最终状态报告")
    print("-" * 30)

    final_status = control_center.get_system_status()
    print(f"最终状态: {final_status['status']}")
    print(f"总运行时间: {final_status['uptime']}")
    print(f"组件注册数: {final_status['components_count']}")


def interactive_demo():
    """交互式演示"""
    print("\n🎮 交互式控制台")
    print("=" * 50)
    print("可用命令:")
    print("  start    - 启动系统")
    print("  stop     - 停止系统")
    print("  pause    - 暂停系统")
    print("  resume   - 恢复系统")
    print("  status   - 查看状态")
    print("  metrics  - 查看指标")
    print("  quit     - 退出程序")
    print()

    control_center = get_control_center()

    while True:
        try:
            command = input("请输入命令: ").strip().lower()

            if command == "quit":
                break
            elif command == "start":
                if control_center.start():
                    print("✅ 系统启动成功")
                else:
                    print("❌ 系统启动失败")
            elif command == "stop":
                if control_center.stop():
                    print("✅ 系统停止成功")
                else:
                    print("❌ 系统停止失败")
            elif command == "pause":
                if control_center.pause():
                    print("✅ 系统已暂停")
                else:
                    print("❌ 暂停失败")
            elif command == "resume":
                if control_center.resume():
                    print("✅ 系统已恢复")
                else:
                    print("❌ 恢复失败")
            elif command == "status":
                status = control_center.get_system_status()
                print(f"系统状态: {status['status']}")
                print(f"运行时间: {status['uptime']}")
                print(
                    f"健康组件: {status['healthy_components']}/{status['components_count']}"
                )
            elif command == "metrics":
                # 这里可以显示更详细的指标
                print("系统指标功能待完善...")
            else:
                print("未知命令，请重新输入")

        except KeyboardInterrupt:
            print("\n\n收到中断信号，正在退出...")
            control_center.stop()
            break
        except Exception as e:
            print(f"执行命令时出错: {e}")


if __name__ == "__main__":
    # 运行演示
    demonstrate_control_center()

    # 可选：运行交互式演示
    # interactive_demo()

    print("\n🎉 控制中枢演示完成!")
