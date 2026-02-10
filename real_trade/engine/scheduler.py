#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Scheduler - 定时调度

支持周期性任务（如定时刷新行情、定期报告、定时重启策略）。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import threading
from typing import Callable, Dict, Optional


class _ScheduledJob:
    """一个定时任务"""

    def __init__(
        self, name: str, func: Callable, interval: float, run_immediately: bool = False
    ):
        self.name = name
        self.func = func
        self.interval = interval
        self.run_immediately = run_immediately
        self._timer: Optional[threading.Timer] = None
        self._running = False

    def start(self):
        self._running = True
        if self.run_immediately:
            self._execute()
        else:
            self._schedule_next()

    def stop(self):
        self._running = False
        if self._timer:
            self._timer.cancel()

    def _schedule_next(self):
        if not self._running:
            return
        self._timer = threading.Timer(self.interval, self._execute)
        self._timer.daemon = True
        self._timer.start()

    def _execute(self):
        if not self._running:
            return
        try:
            self.func()
        except Exception as e:
            print(f"[Scheduler] Error in job '{self.name}': {e}")
        self._schedule_next()


class Scheduler:
    """
    定时调度器

    Usage::

        sched = Scheduler()
        sched.add_job("heartbeat", lambda: print("alive"), interval=60)
        sched.add_job("report", generate_report, interval=3600)
        sched.start()
        # ...
        sched.stop()
    """

    def __init__(self):
        self._jobs: Dict[str, _ScheduledJob] = {}
        self._started = False

    def add_job(
        self, name: str, func: Callable, interval: float, run_immediately: bool = False
    ):
        """
        添加定时任务

        Args:
            name: 任务名称（唯一标识）
            func: 要执行的函数
            interval: 执行间隔（秒）
            run_immediately: 是否立即执行一次
        """
        if name in self._jobs:
            self._jobs[name].stop()

        job = _ScheduledJob(name, func, interval, run_immediately)
        self._jobs[name] = job

        if self._started:
            job.start()

    def remove_job(self, name: str):
        if name in self._jobs:
            self._jobs[name].stop()
            del self._jobs[name]

    def start(self):
        self._started = True
        for job in self._jobs.values():
            job.start()

    def stop(self):
        self._started = False
        for job in self._jobs.values():
            job.stop()

    @property
    def job_names(self):
        return list(self._jobs.keys())
