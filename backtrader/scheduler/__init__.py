#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级任务调度系统
Enterprise Task Scheduler for Backtrader

模块结构:
├── task_scheduler.py    # 任务调度核心实现
└── __init__.py          # 模块初始化和便捷接口
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# 核心组件
from .task_scheduler import (
    TaskSchedulerError,
    ScheduledTask,
    TradingTaskScheduler,
    enable_scheduler,
    schedule_daily_strategy,
    schedule_interval_task
)

__all__ = [
    'TaskSchedulerError',
    'ScheduledTask',
    'TradingTaskScheduler',
    'enable_scheduler',
    'schedule_daily_strategy',
    'schedule_interval_task',
]

__version__ = '1.0.0'
__author__ = 'Backtrader Scheduler Team'


# 保持与您示例一致的API接口
def enable_scheduler(cerebro, timezone='Asia/Shanghai', start_immediately=True):
    """
    启用任务调度功能（P0标准接口）
    
    示例:
        scheduler = enable_scheduler(cerebro)
        scheduler.add_job(lambda: cerebro.run(), CronTrigger(hour=9, minute=30))
    """
    from .task_scheduler import enable_scheduler as _enable_scheduler
    return _enable_scheduler(cerebro, timezone, start_immediately)