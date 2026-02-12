#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Data Quality Monitor - 数据质量监控器

实时监控数据流质量，提供预警和自动处理机制。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Deque, Dict, List, Optional

# 延迟导入避免循环依赖
# from ..utils import DataError, RealTradeError, get_logger
from .data_quality import DataQualityAssessor, DataQualityReport


@dataclass
class QualityMetrics:
    """质量指标"""

    timestamp: float
    quality_score: float
    completeness_rate: float
    consistency_issues: int
    outlier_count: int
    error_count: int
    processing_speed: float  # 条/秒


class QualityThreshold:
    """质量阈值配置"""

    def __init__(
        self,
        min_quality_score: float = 0.8,
        max_consistency_issues: int = 5,
        max_outliers_ratio: float = 0.05,
        max_error_rate: float = 0.1,
    ):
        self.min_quality_score = min_quality_score
        self.max_consistency_issues = max_consistency_issues
        self.max_outliers_ratio = max_outliers_ratio
        self.max_error_rate = max_error_rate


class DataStreamMonitor:
    """数据流监控器"""

    def __init__(
        self,
        stream_name: str,
        buffer_size: int = 1000,
        assessment_window: int = 100,
        threshold: QualityThreshold = None,
    ):
        self.stream_name = stream_name
        self.buffer_size = buffer_size
        self.assessment_window = assessment_window
        self.threshold = threshold or QualityThreshold()

        # 数据缓冲区
        self.data_buffer: Deque[List] = deque(maxlen=buffer_size)
        self.quality_history: Deque[QualityMetrics] = deque(maxlen=buffer_size)
        self.error_log: Deque[Dict[str, Any]] = deque(maxlen=1000)

        # 状态
        self.is_monitoring = False
        self.last_assessment_time = 0
        self.processed_count = 0
        self.error_count = 0
        self.start_time = 0

        # 回调函数
        self.alert_callbacks: List[Callable] = []
        self.quality_degradation_callbacks: List[Callable] = []
        self.recovery_callbacks: List[Callable] = []

        # 线程
        self.monitor_thread = None
        self._lock = threading.RLock()
        from .logger import get_logger

        self.logger = get_logger(f"data_monitor_{stream_name}")

        # 质量评估器
        self.quality_assessor = DataQualityAssessor()

    def start_monitoring(self):
        """开始监控"""
        with self._lock:
            if self.is_monitoring:
                return

            self.is_monitoring = True
            self.start_time = time.time()
            self.last_assessment_time = self.start_time

            # 启动监控线程
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True
            )
            self.monitor_thread.start()

            self.logger.info(f"开始监控数据流: {self.stream_name}")

    def stop_monitoring(self):
        """停止监控"""
        with self._lock:
            self.is_monitoring = False
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)
            self.logger.info(f"停止监控数据流: {self.stream_name}")

    def add_data(self, data: List[List]):
        """添加数据到监控缓冲区"""
        with self._lock:
            current_time = time.time()

            # 添加到缓冲区
            for bar in data:
                self.data_buffer.append(bar)

            # 更新处理统计
            self.processed_count += len(data)

            # 定期评估质量
            if (current_time - self.last_assessment_time) >= 1.0:  # 每秒评估一次
                self._assess_quality()
                self.last_assessment_time = current_time

    def add_error(self, error: Exception, context: str = ""):
        """记录错误"""
        with self._lock:
            self.error_count += 1
            error_info = {
                "timestamp": time.time(),
                "error": str(error),
                "type": type(error).__name__,
                "context": context,
            }
            self.error_log.append(error_info)
            self.logger.warning(f"数据流错误: {error_info}")

    def register_alert_callback(self, callback: Callable):
        """注册警报回调"""
        self.alert_callbacks.append(callback)

    def register_quality_degradation_callback(self, callback: Callable):
        """注册质量下降回调"""
        self.quality_degradation_callbacks.append(callback)

    def register_recovery_callback(self, callback: Callable):
        """注册恢复回调"""
        self.recovery_callbacks.append(callback)

    def get_current_metrics(self) -> Optional[QualityMetrics]:
        """获取当前质量指标"""
        with self._lock:
            if not self.quality_history:
                return None
            return self.quality_history[-1]

    def get_quality_report(self) -> Optional[DataQualityReport]:
        """获取详细质量报告"""
        with self._lock:
            if len(self.data_buffer) < 10:
                return None

            # 使用最近的数据进行评估
            recent_data = list(self.data_buffer)[
                -min(self.assessment_window, len(self.data_buffer)) :
            ]
            return self.quality_assessor.assess_quality(recent_data)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            runtime = time.time() - self.start_time if self.start_time > 0 else 0
            processing_speed = self.processed_count / runtime if runtime > 0 else 0

            # 计算平均质量指标
            if self.quality_history:
                avg_quality = sum(q.quality_score for q in self.quality_history) / len(
                    self.quality_history
                )
                avg_completeness = sum(
                    q.completeness_rate for q in self.quality_history
                ) / len(self.quality_history)
            else:
                avg_quality = 0
                avg_completeness = 0

            return {
                "stream_name": self.stream_name,
                "is_monitoring": self.is_monitoring,
                "runtime_seconds": runtime,
                "processed_count": self.processed_count,
                "error_count": self.error_count,
                "error_rate": self.error_count / self.processed_count
                if self.processed_count > 0
                else 0,
                "processing_speed": processing_speed,
                "average_quality_score": avg_quality,
                "average_completeness": avg_completeness,
                "buffer_size": len(self.data_buffer),
                "quality_history_count": len(self.quality_history),
            }

    def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                time.sleep(1)
                self._check_thresholds()
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")

    def _assess_quality(self):
        """评估数据质量"""
        with self._lock:
            if len(self.data_buffer) < 10:
                return

            # 获取评估窗口内的数据
            window_data = list(self.data_buffer)[
                -min(self.assessment_window, len(self.data_buffer)) :
            ]

            try:
                # 评估质量
                report = self.quality_assessor.assess_quality(window_data)

                # 计算处理速度
                current_time = time.time()
                processing_speed = len(window_data) / max(
                    current_time - self.last_assessment_time, 0.1
                )

                # 创建质量指标
                metrics = QualityMetrics(
                    timestamp=current_time,
                    quality_score=report.accuracy_score,
                    completeness_rate=report.completeness_rate,
                    consistency_issues=report.consistency_issues,
                    outlier_count=report.outlier_records,
                    error_count=self.error_count,
                    processing_speed=processing_speed,
                )

                self.quality_history.append(metrics)

            except Exception as e:
                self.logger.error(f"质量评估失败: {e}")
                self.add_error(e, "quality_assessment")

    def _check_thresholds(self):
        """检查质量阈值"""
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            return

        alerts = []
        quality_degraded = False

        # 检查质量分数
        if current_metrics.quality_score < self.threshold.min_quality_score:
            alerts.append(
                f"质量分数过低: {current_metrics.quality_score:.3f} < {self.threshold.min_quality_score}"
            )
            quality_degraded = True

        # 检查一致性问题
        if current_metrics.consistency_issues > self.threshold.max_consistency_issues:
            alerts.append(
                f"一致性问题过多: {current_metrics.consistency_issues} > {self.threshold.max_consistency_issues}"
            )
            quality_degraded = True

        # 检查异常值比例
        outlier_ratio = (
            current_metrics.outlier_count / self.processed_count
            if self.processed_count > 0
            else 0
        )
        if outlier_ratio > self.threshold.max_outliers_ratio:
            alerts.append(
                f"异常值比例过高: {outlier_ratio:.3f} > {self.threshold.max_outliers_ratio}"
            )
            quality_degraded = True

        # 检查错误率
        error_rate = (
            current_metrics.error_count / self.processed_count
            if self.processed_count > 0
            else 0
        )
        if error_rate > self.threshold.max_error_rate:
            alerts.append(
                f"错误率过高: {error_rate:.3f} > {self.threshold.max_error_rate}"
            )
            quality_degraded = True

        # 触发警报
        if alerts:
            self._trigger_alerts(alerts)

        # 检查质量退化
        if quality_degraded and len(self.quality_history) > 1:
            prev_metrics = self.quality_history[-2]
            if (
                current_metrics.quality_score < prev_metrics.quality_score * 0.9
            ):  # 下降超过10%
                self._trigger_quality_degradation(current_metrics, prev_metrics)

    def _trigger_alerts(self, alerts: List[str]):
        """触发警报"""
        alert_info = {
            "timestamp": time.time(),
            "stream_name": self.stream_name,
            "alerts": alerts,
            "current_metrics": self.get_current_metrics(),
        }

        self.logger.warning(f"数据质量警报: {alerts}")

        # 调用回调函数
        for callback in self.alert_callbacks:
            try:
                callback(alert_info)
            except Exception as e:
                self.logger.error(f"警报回调执行失败: {e}")

    def _trigger_quality_degradation(
        self, current: QualityMetrics, previous: QualityMetrics
    ):
        """触发质量退化通知"""
        degradation_info = {
            "timestamp": time.time(),
            "stream_name": self.stream_name,
            "current_metrics": current,
            "previous_metrics": previous,
            "degradation_amount": previous.quality_score - current.quality_score,
        }

        self.logger.warning(
            f"数据质量退化: {degradation_info['degradation_amount']:.3f}"
        )

        # 调用回调函数
        for callback in self.quality_degradation_callbacks:
            try:
                callback(degradation_info)
            except Exception as e:
                self.logger.error(f"质量退化回调执行失败: {e}")

    def _trigger_recovery(self, recovery_info: Dict[str, Any]):
        """触发恢复通知"""
        self.logger.info(f"数据质量恢复: {recovery_info}")

        # 调用回调函数
        for callback in self.recovery_callbacks:
            try:
                callback(recovery_info)
            except Exception as e:
                self.logger.error(f"恢复回调执行失败: {e}")


class DataManager:
    """数据管理器 - 管理多个数据流监控器"""

    def __init__(self):
        self.monitors: Dict[str, DataStreamMonitor] = {}
        self.global_alert_callbacks: List[Callable] = []
        from .logger import get_logger

        self.logger = get_logger("data_manager")

    def create_monitor(self, stream_name: str, **kwargs) -> DataStreamMonitor:
        """创建数据流监控器"""
        if stream_name in self.monitors:
            raise ValueError(f"监控器已存在: {stream_name}")

        monitor = DataStreamMonitor(stream_name, **kwargs)

        # 注册全局回调
        for callback in self.global_alert_callbacks:
            monitor.register_alert_callback(callback)

        self.monitors[stream_name] = monitor
        return monitor

    def get_monitor(self, stream_name: str) -> Optional[DataStreamMonitor]:
        """获取监控器"""
        return self.monitors.get(stream_name)

    def remove_monitor(self, stream_name: str):
        """移除监控器"""
        monitor = self.monitors.pop(stream_name, None)
        if monitor:
            monitor.stop_monitoring()

    def start_all_monitors(self):
        """启动所有监控器"""
        for monitor in self.monitors.values():
            monitor.start_monitoring()

    def stop_all_monitors(self):
        """停止所有监控器"""
        for monitor in self.monitors.values():
            monitor.stop_monitoring()

    def register_global_alert_callback(self, callback: Callable):
        """注册全局警报回调"""
        self.global_alert_callbacks.append(callback)
        # 为现有监控器注册回调
        for monitor in self.monitors.values():
            monitor.register_alert_callback(callback)

    def get_overall_statistics(self) -> Dict[str, Any]:
        """获取整体统计数据"""
        total_processed = 0
        total_errors = 0
        avg_quality = 0
        monitor_count = len(self.monitors)

        for monitor in self.monitors.values():
            stats = monitor.get_statistics()
            total_processed += stats["processed_count"]
            total_errors += stats["error_count"]

            if stats["average_quality_score"] > 0:
                avg_quality += stats["average_quality_score"]

        avg_quality = avg_quality / monitor_count if monitor_count > 0 else 0
        error_rate = total_errors / total_processed if total_processed > 0 else 0

        return {
            "monitor_count": monitor_count,
            "total_processed": total_processed,
            "total_errors": total_errors,
            "overall_error_rate": error_rate,
            "average_quality_score": avg_quality,
            "active_monitors": [
                name for name, monitor in self.monitors.items() if monitor.is_monitoring
            ],
        }


# 全局数据管理器实例
_global_data_manager = None


def get_data_manager() -> DataManager:
    """获取全局数据管理器"""
    global _global_data_manager
    if _global_data_manager is None:
        _global_data_manager = DataManager()
    return _global_data_manager


def create_data_monitor(stream_name: str, **kwargs) -> DataStreamMonitor:
    """便利函数：创建数据监控器"""
    manager = get_data_manager()
    return manager.create_monitor(stream_name, **kwargs)


def shutdown_data_monitors():
    """关闭所有数据监控器"""
    global _global_data_manager
    if _global_data_manager:
        _global_data_manager.stop_all_monitors()
        _global_data_manager = None


__all__ = [
    "QualityMetrics",
    "QualityThreshold",
    "DataStreamMonitor",
    "DataManager",
    "get_data_manager",
    "create_data_monitor",
    "shutdown_data_monitors",
]
