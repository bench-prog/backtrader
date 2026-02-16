#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级任务调度系统 (Enterprise Task Scheduler)
基于APScheduler的任务调度解决方案

核心功能：
1. 定时策略执行
2. 异步任务队列
3. 任务状态追踪
4. Cron表达式支持
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import threading
import time
from typing import Callable, Dict, List, Optional

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import backtrader as bt


class TaskSchedulerError(Exception):
    """任务调度异常"""

    pass


class ScheduledTask:
    """
    调度任务封装类
    """

    def __init__(self, name: str, func: Callable, trigger, **trigger_args):
        self.name = name
        self.func = func
        self.trigger = trigger
        self.trigger_args = trigger_args
        self.job_id = None
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self.success_count = 0
        self.error_count = 0

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "job_id": self.job_id,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
        }


class TradingTaskScheduler:
    """
    交易任务调度器
    """

    def __init__(self, timezone: str = "Asia/Shanghai"):
        self.scheduler = BackgroundScheduler(timezone=timezone)
        self.tasks = {}
        self._running = False
        self._lock = threading.RLock()

        # 注册事件监听器
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)

    def start(self):
        """启动调度器"""
        with self._lock:
            if not self._running:
                self.scheduler.start()
                self._running = True
                print("✅ 任务调度器已启动")

    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        with self._lock:
            if self._running:
                self.scheduler.shutdown(wait=wait)
                self._running = False
                print("🛑 任务调度器已关闭")

    def is_running(self) -> bool:
        """检查调度器是否运行"""
        return self._running and self.scheduler.running

    def add_task(
        self, name: str, func: Callable, trigger_type: str = "cron", **trigger_params
    ) -> str:
        """
        添加调度任务

        Args:
            name: 任务名称
            func: 执行函数
            trigger_type: 触发器类型 ('cron', 'interval', 'date')
            **trigger_params: 触发器参数

        Returns:
            job_id: 任务ID
        """
        with self._lock:
            if name in self.tasks:
                raise TaskSchedulerError(f"任务 '{name}' 已存在")

            # 创建触发器
            if trigger_type == "cron":
                trigger = CronTrigger(**trigger_params)
            elif trigger_type == "interval":
                trigger = IntervalTrigger(**trigger_params)
            else:
                raise TaskSchedulerError(f"不支持的触发器类型: {trigger_type}")

            # 添加任务
            job = self.scheduler.add_job(func, trigger, id=name)

            # 记录任务信息
            task = ScheduledTask(name, func, trigger, **trigger_params)
            task.job_id = job.id
            task.next_run = job.next_run_time
            self.tasks[name] = task

            print(f"✅ 任务已添加: {name} -> {trigger}")
            return job.id

    def remove_task(self, name: str) -> bool:
        """移除任务"""
        with self._lock:
            if name in self.tasks:
                self.scheduler.remove_job(name)
                del self.tasks[name]
                print(f"🗑️  任务已移除: {name}")
                return True
            return False

    def pause_task(self, name: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(name)
            print(f"⏸️  任务已暂停: {name}")
            return True
        except Exception as e:
            print(f"❌ 暂停任务失败: {e}")
            return False

    def resume_task(self, name: str) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(name)
            print(f"▶️  任务已恢复: {name}")
            return True
        except Exception as e:
            print(f"❌ 恢复任务失败: {e}")
            return False

    def get_task_info(self, name: str) -> Optional[Dict]:
        """获取任务信息"""
        with self._lock:
            if name in self.tasks:
                return self.tasks[name].to_dict()
            return None

    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务信息"""
        with self._lock:
            return [task.to_dict() for task in self.tasks.values()]

    def _job_executed_listener(self, event):
        """任务执行完成监听器"""
        with self._lock:
            if event.job_id in self.tasks:
                task = self.tasks[event.job_id]
                task.last_run = datetime.datetime.now()
                task.next_run = event.jobstore.get_next_run_time(event.job_id)
                task.run_count += 1
                task.success_count += 1

    def _job_error_listener(self, event):
        """任务执行错误监听器"""
        with self._lock:
            if event.job_id in self.tasks:
                task = self.tasks[event.job_id]
                task.error_count += 1
                print(f"❌ 任务执行失败: {event.job_id} - {event.exception}")


# 便捷函数
def enable_scheduler(
    cerebro, timezone: str = "Asia/Shanghai", start_immediately: bool = True
) -> TradingTaskScheduler:
    """
    启用任务调度功能（符合P0集成规范）

    Args:
        cerebro: Cerebro实例
        timezone: 时区
        start_immediately: 是否立即启动调度器

    Returns:
        TradingTaskScheduler: 调度器实例
    """
    scheduler = TradingTaskScheduler(timezone=timezone)

    if start_immediately:
        scheduler.start()

    # 将调度器附加到cerebro以便访问
    cerebro._scheduler = scheduler

    print("✅ 任务调度功能已启用")
    return scheduler


def schedule_daily_strategy(
    cerebro, hour: int = 9, minute: int = 30, strategy_name: str = "daily_strategy"
) -> str:
    """
    调度每日策略执行

    Args:
        cerebro: Cerebro实例
        hour: 执行小时 (默认9点)
        minute: 执行分钟 (默认30分)
        strategy_name: 策略任务名称

    Returns:
        job_id: 任务ID
    """
    if not hasattr(cerebro, "_scheduler"):
        raise TaskSchedulerError("请先调用 enable_scheduler() 启用调度功能")

    def run_strategy():
        print(f"⏰ 执行定时策略: {strategy_name}")
        try:
            cerebro.run()
            print(f"✅ 策略执行完成: {strategy_name}")
        except Exception as e:
            print(f"❌ 策略执行失败: {e}")

    scheduler = cerebro._scheduler
    job_id = scheduler.add_task(
        name=strategy_name,
        func=run_strategy,
        trigger_type="cron",
        hour=hour,
        minute=minute,
    )

    print(f"📅 策略调度已设置: 每天 {hour:02d}:{minute:02d}")
    return job_id


def schedule_interval_task(
    cerebro, func: Callable, minutes: int = 60, task_name: str = "interval_task"
) -> str:
    """
    调度间隔任务

    Args:
        cerebro: Cerebro实例
        func: 执行函数
        minutes: 间隔分钟数
        task_name: 任务名称

    Returns:
        job_id: 任务ID
    """
    if not hasattr(cerebro, "_scheduler"):
        raise TaskSchedulerError("请先调用 enable_scheduler() 启用调度功能")

    scheduler = cerebro._scheduler
    job_id = scheduler.add_task(
        name=task_name, func=func, trigger_type="interval", minutes=minutes
    )

    print(f"⏱️  间隔任务已设置: 每 {minutes} 分钟执行一次")
    return job_id


# 使用示例
if __name__ == "__main__":
    # 创建Cerebro实例
    cerebro = bt.Cerebro()

    # 启用调度功能
    scheduler = enable_scheduler(cerebro)

    # 调度每日策略
    schedule_daily_strategy(cerebro, hour=9, minute=30)

    # 调度间隔任务
    def sample_task():
        print("🔧 执行间隔任务")

    schedule_interval_task(cerebro, sample_task, minutes=30)

    # 查看所有任务
    tasks = scheduler.get_all_tasks()
    print("\n📋 当前调度任务:")
    for task in tasks:
        print(f"  - {task['name']}: {task['next_run']}")

    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 正在关闭调度器...")
        scheduler.shutdown()
