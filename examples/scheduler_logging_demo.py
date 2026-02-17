#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级调度和日志功能集成示例
Enterprise Scheduler & Logging Integration Example

展示如何集成任务调度和日志增强功能：
1. 定时策略执行
2. 结构化日志记录
3. 自动订单和风控日志
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time

import backtrader as bt
from backtrader.logging import LoggingStrategyMixin, setup_logger
from backtrader.scheduler import enable_scheduler, schedule_daily_strategy


class ScheduledTradingStrategy(LoggingStrategyMixin, bt.Strategy):
    """带日志功能的定时交易策略"""

    params = (
        ("sma_period", 15),
        ("printlog", True),
    )

    def __init__(self):
        # 初始化父类
        LoggingStrategyMixin.__init__(self)
        bt.Strategy.__init__(self)

        # 技术指标
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.sma_period
        )

    def next(self):
        """策略逻辑"""
        if not self.position:
            # 价格上穿SMA时买入
            if self.data.close[0] > self.sma[0] and self.data.close[-1] <= self.sma[-1]:
                self.log(f"买入信号 @ {self.data.close[0]:.2f}")
                self.buy()
        else:
            # 价格下穿SMA时卖出
            if self.data.close[0] < self.sma[0] and self.data.close[-1] >= self.sma[-1]:
                self.log(f"卖出信号 @ {self.data.close[0]:.2f}")
                self.sell()

    def stop(self):
        """策略结束"""
        self.log(
            f"(SMA {self.params.sma_period}) 最终价值: {self.broker.getvalue():.2f}"
        )


def demonstrate_scheduler_and_logging():
    """演示调度器和日志功能"""
    print("=" * 80)
    print("企业级调度和日志功能演示")
    print("=" * 80)

    # ========== 1. 创建 Cerebro ==========
    cerebro = bt.Cerebro()

    # ========== 2. 启用企业级功能 ==========
    print("\n[1] 启用企业级功能...")

    # 2.1 启用任务调度
    scheduler = enable_scheduler(cerebro, timezone="Asia/Shanghai")
    print("✓ 任务调度已启用")

    # 2.2 启用日志增强
    logger = setup_logger(log_dir="demo_logs", retention_days=7)
    print("✓ 日志增强已启用")

    # ========== 3. 调度定时任务 ==========
    print("\n[2] 设置定时任务...")

    # 调度每日策略执行（演示用，设置为每分钟执行）
    job_id = schedule_daily_strategy(
        cerebro, hour=9, minute=30, strategy_name="morning_strategy"
    )
    print(f"✓ 策略调度已设置: {job_id}")

    # 调度间隔任务（每2分钟执行一次监控）
    def health_check():
        logger.info("执行系统健康检查")
        # 这里可以添加具体的健康检查逻辑

    interval_job = scheduler.add_task(
        name="health_check", func=health_check, trigger_type="interval", minutes=2
    )
    print(f"✓ 健康检查任务已设置: {interval_job}")

    # ========== 4. 添加数据和策略 ==========
    print("\n[3] 配置回测环境...")

    # 添加数据
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "datas",
        "2006-day-001.txt",
    )
    data = bt.feeds.GenericCSVData(
        dataname=data_path,
        dtformat="%Y-%m-%d",
        openinterest=-1,
        fromdate=datetime.datetime(2006, 1, 1),
        todate=datetime.datetime(2006, 3, 31),  # 缩短回测时间
    )
    cerebro.adddata(data)
    print("✓ 数据源已添加")

    # 添加策略
    cerebro.addstrategy(ScheduledTradingStrategy)
    print("✓ 策略已添加")

    # 设置初始资金
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    # ========== 5. 运行演示 ==========
    print("\n[4] 开始演示...")
    print(f"初始资金: {cerebro.broker.getvalue():.2f}")

    # 手动运行一次策略（演示日志功能）
    print("\n手动执行策略（演示日志记录）:")
    results = cerebro.run()

    final_value = cerebro.broker.getvalue()
    print(f"最终资金: {final_value:.2f}")
    print(f"收益率: {(final_value - 100000) / 100000:.2%}")

    # ========== 6. 展示调度任务状态 ==========
    print("\n[5] 调度任务状态:")
    tasks = scheduler.get_all_tasks()
    for task in tasks:
        print(f"  - {task['name']}:")
        print(f"    下次执行: {task['next_run']}")
        print(f"    执行次数: {task['run_count']}")
        print(f"    成功次数: {task['success_count']}")
        print(f"    失败次数: {task['error_count']}")

    # ========== 7. 演示日志功能 ==========
    print("\n[6] 日志功能演示:")

    # 记录一些示例日志
    from backtrader.logging import log_order_execution, log_risk_event

    # 模拟订单日志
    log_order_execution("BTC/USDT", "BUY", 45000.0, 0.001, "ORDER_001")
    log_order_execution("ETH/USDT", "SELL", 3000.0, 0.1, "ORDER_002")

    # 模拟风控日志
    log_risk_event("leverage_check", "PASS", {"current": 2.0, "limit": 3.0})
    log_risk_event(
        "position_check", "FAIL", {"symbol": "BTC/USDT", "size": 0.5, "limit": 0.3}
    )

    print("✓ 日志记录演示完成")

    # ========== 8. 保持调度器运行 ==========
    print("\n[7] 调度器运行中...")
    print("调度器将在后台继续运行，按 Ctrl+C 停止")

    try:
        # 保持程序运行，让调度器工作
        time.sleep(10)  # 运行10秒观察效果

        print("\n调度器即将关闭...")
        scheduler.shutdown()

    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭...")
        scheduler.shutdown()


def demonstrate_minimal_integration():
    """最简集成示例"""
    print("\n\n" + "=" * 80)
    print("最简集成示例")
    print("=" * 80)

    # 最简集成只需要3行代码
    cerebro = bt.Cerebro()

    from backtrader.logging import setup_logger
    from backtrader.scheduler import enable_scheduler

    scheduler = enable_scheduler(cerebro)  # 启用调度
    logger = setup_logger()  # 启用日志

    print("✓ 调度和日志功能已启用")
    print("✓ 后续可正常使用 Backtrader")

    # 后续正常使用
    # cerebro.adddata(data)
    # cerebro.addstrategy(MyStrategy)
    # cerebro.run()

    # 清理
    scheduler.shutdown()


if __name__ == "__main__":
    # 运行完整演示
    demonstrate_scheduler_and_logging()

    # 运行最简示例
    demonstrate_minimal_integration()

    print("\n" + "=" * 80)
    print("演示完成！")
    print("查看 demo_logs/ 目录下的日志文件")
    print("=" * 80)
