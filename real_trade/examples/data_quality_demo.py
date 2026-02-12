#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Data Quality Examples - 数据质量保障使用示例

展示如何使用数据质量检查、监控和异常数据处理功能。
"""

import os
import random
import sys
import time
from typing import List

# 添加项目路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

try:
    from real_trade.utils import (
        DataConsistencyChecker,
        OutlierDetector,
        assess_ohlcv_quality,
        create_data_monitor,
        get_data_manager,
        validate_single_bar,
    )
except ImportError:
    # 创建模拟类
    class DataConsistencyChecker:
        def __init__(self, *args, **kwargs):
            pass

        def check_consistency(self, data):
            return {"consistent": True, "issues": []}

    class OutlierDetector:
        def __init__(self, *args, **kwargs):
            pass

        def detect_outliers(self, data):
            return []

    def assess_ohlcv_quality(data):
        return {"quality_score": 0.95, "issues": []}

    def create_data_monitor():
        return DataConsistencyChecker()

    def get_data_manager():
        return DataConsistencyChecker()

    def validate_single_bar(bar):
        return True


def generate_sample_data(count: int = 100, add_anomalies: bool = False) -> List[List]:
    """生成示例OHLCV数据"""
    data = []
    base_price = 50000.0
    base_volume = 1000.0
    timestamp = 1700000000000  # 2023-11-14

    for i in range(count):
        # 生成合理的随机价格波动
        price_change = random.uniform(-0.02, 0.02)  # ±2%波动
        open_price = base_price * (1 + price_change)

        # 高低价应该包围开盘收盘价
        high_change = random.uniform(0, 0.01)
        low_change = random.uniform(-0.01, 0)
        high = open_price * (1 + high_change)
        low = open_price * (1 + low_change)

        # 收盘价在高低价之间
        close = random.uniform(low, high)

        # 成交量
        volume = base_volume * random.uniform(0.5, 2.0)

        # 添加一些异常数据（如果需要）
        if add_anomalies and i in [10, 25, 50, 75]:
            if i == 10:  # 价格异常高
                high = open_price * 3
            elif i == 25:  # 价格关系错误
                high = low - 100
            elif i == 50:  # 成交量为负
                volume = -1000
            elif i == 75:  # 时间戳错误
                timestamp = timestamp - 60000  # 时间倒退

        bar = [timestamp, open_price, high, low, close, volume]
        data.append(bar)

        # 更新基准值
        base_price = close
        timestamp += 60000  # 1分钟间隔

    return data


def demonstrate_data_validation():
    """数据验证演示"""
    print("=== 数据验证演示 ===\n")

    # 1. 验证单条数据
    print("1. 单条数据验证:")
    valid_bar = [1700000000000, 50000.0, 50100.0, 49900.0, 50050.0, 1000.0]
    is_valid, errors = validate_single_bar(valid_bar)
    print(f"   有效数据验证结果: {is_valid}, 错误数: {len(errors)}")

    invalid_bar = [1700000000000, -50000.0, 50100.0, 49900.0, 50050.0, 1000.0]  # 负价格
    is_valid, errors = validate_single_bar(invalid_bar)
    print(f"   无效数据验证结果: {is_valid}")
    for error in errors:
        print(f"     - {error}")

    print()


def demonstrate_quality_assessment():
    """数据质量评估演示"""
    print("=== 数据质量评估演示 ===\n")

    # 1. 评估高质量数据
    print("1. 高质量数据评估:")
    clean_data = generate_sample_data(100, add_anomalies=False)
    report = assess_ohlcv_quality(clean_data)

    print(f"   质量等级: {report.quality_level.value}")
    print(f"   总记录数: {report.total_records}")
    print(f"   有效记录: {report.valid_records}")
    print(f"   完整性率: {report.completeness_rate:.3f}")
    print(f"   准确性得分: {report.accuracy_score:.3f}")
    print(f"   一致性问题: {report.consistency_issues}")
    print(f"   异常值数量: {report.outlier_records}")
    if report.issues:
        print("   主要问题 (前3个):")
        for issue in report.issues[:3]:
            print(f"     - {issue}")
    print()

    # 2. 评估低质量数据
    print("2. 低质量数据评估:")
    dirty_data = generate_sample_data(100, add_anomalies=True)
    report2 = assess_ohlcv_quality(dirty_data)

    print(f"   质量等级: {report2.quality_level.value}")
    print(f"   一致性问题: {report2.consistency_issues}")
    print(f"   异常值数量: {report2.outlier_records}")
    print(f"   准确性得分: {report2.accuracy_score:.3f}")
    if report2.issues:
        print("   主要问题 (前5个):")
        for issue in report2.issues[:5]:
            print(f"     - {issue}")
    print()

    # 3. 建议措施
    print("3. 改进建议:")
    for recommendation in report2.recommendations:
        print(f"   - {recommendation}")
    print()


def demonstrate_outlier_detection():
    """异常值检测演示"""
    print("=== 异常值检测演示 ===\n")

    # 生成包含明显异常值的数据
    data_with_outliers = []
    base_price = 50000.0
    timestamp = 1700000000000

    for i in range(50):
        if i == 25:  # 插入一个明显的异常值
            price = base_price * 3  # 价格突然变为3倍
        else:
            price = base_price * (1 + random.uniform(-0.05, 0.05))

        bar = [timestamp, price, price * 1.01, price * 0.99, price, 1000.0]
        data_with_outliers.append(bar)
        timestamp += 60000

    # 使用不同的检测方法
    detector = OutlierDetector()

    print("1. IQR方法检测收盘价异常值:")
    outliers_iqr = detector.detect_price_outliers(data_with_outliers, 4)
    print(f"   检测到 {len(outliers_iqr)} 个异常值")
    for idx, value, reason in outliers_iqr[:3]:  # 显示前3个
        print(f"     - 记录 {idx}: 价格 {value:.2f}, {reason}")
    print()

    print("2. Z-score方法检测:")
    detector.method = "zscore"
    outliers_zscore = detector.detect_price_outliers(data_with_outliers, 4)
    print(f"   检测到 {len(outliers_zscore)} 个异常值")
    if outliers_zscore:
        idx, value, reason = outliers_zscore[0]
        print(f"     - 记录 {idx}: 价格 {value:.2f}, {reason}")
    print()


def demonstrate_consistency_checking():
    """一致性检查演示"""
    print("=== 数据一致性检查演示 ===\n")

    checker = DataConsistencyChecker()

    # 1. 价格一致性检查
    print("1. 价格一致性检查:")
    inconsistent_data = [
        [
            1700000000000,
            50000.0,
            49000.0,
            51000.0,
            50500.0,
            1000.0,
        ],  # high < max(open,close)
        [
            1700000060000,
            50500.0,
            50600.0,
            50700.0,
            50650.0,
            1200.0,
        ],  # low > min(open,close)
    ]

    price_issues = checker.check_price_consistency(inconsistent_data)
    print(f"   发现 {len(price_issues)} 个价格一致性问题:")
    for issue in price_issues:
        print(f"     - {issue}")
    print()

    # 2. 时间序列检查
    print("2. 时间序列一致性检查:")
    time_inconsistent_data = [
        [1700000000000, 50000.0, 50100.0, 49900.0, 50050.0, 1000.0],
        [1700000000000, 50050.0, 50150.0, 49950.0, 50100.0, 1100.0],  # 相同时间戳
        [1699999940000, 50100.0, 50200.0, 50000.0, 50150.0, 1200.0],  # 时间倒退
    ]

    time_issues = checker.check_time_sequence(time_inconsistent_data)
    print(f"   发现 {len(time_issues)} 个时间序列问题:")
    for issue in time_issues:
        print(f"     - {issue}")
    print()


def demonstrate_real_time_monitoring():
    """实时数据监控演示"""
    print("=== 实时数据监控演示 ===\n")

    # 创建数据监控器
    monitor = create_data_monitor("BTC_USDT_1m", buffer_size=500, assessment_window=50)

    # 注册回调函数
    def alert_callback(alert_info):
        print(f"🚨 警报: {alert_info['alerts']}")

    def degradation_callback(degradation_info):
        print(f"⚠️  质量退化: 下降 {degradation_info['degradation_amount']:.3f}")

    monitor.register_alert_callback(alert_callback)
    monitor.register_quality_degradation_callback(degradation_callback)

    # 开始监控
    monitor.start_monitoring()

    try:
        print("1. 监控正常数据流:")
        # 发送正常数据
        for i in range(3):
            normal_data = generate_sample_data(20, add_anomalies=False)
            monitor.add_data(normal_data)
            time.sleep(0.5)

        stats = monitor.get_statistics()
        print(f"   处理记录数: {stats['processed_count']}")
        print(f"   处理速度: {stats['processing_speed']:.1f} 条/秒")
        print(f"   平均质量得分: {stats['average_quality_score']:.3f}")
        print()

        print("2. 模拟数据质量问题:")
        # 发送有问题的数据
        bad_data = generate_sample_data(30, add_anomalies=True)
        monitor.add_data(bad_data)
        time.sleep(1)

        # 获取质量报告
        report = monitor.get_quality_report()
        if report:
            print(f"   当前质量等级: {report.quality_level.value}")
            print(f"   一致性问题: {report.consistency_issues}")
            print(f"   异常值数量: {report.outlier_records}")
        print()

        print("3. 监控统计信息:")
        final_stats = monitor.get_statistics()
        print(f"   总处理记录: {final_stats['processed_count']}")
        print(f"   错误数量: {final_stats['error_count']}")
        print(f"   错误率: {final_stats['error_rate']:.3f}")
        print(f"   运行时间: {final_stats['runtime_seconds']:.1f}秒")

    finally:
        monitor.stop_monitoring()


def demonstrate_data_manager():
    """数据管理器演示"""
    print("=== 数据管理器演示 ===\n")

    # 获取全局数据管理器
    manager = get_data_manager()

    # 创建多个监控器
    btc_monitor = manager.create_monitor("BTC_USDT")
    eth_monitor = manager.create_monitor("ETH_USDT")

    # 注册全局回调
    def global_alert(alert_info):
        print(f"🌍 全局警报 [{alert_info['stream_name']}]: {alert_info['alerts']}")

    manager.register_global_alert_callback(global_alert)

    # 启动所有监控器
    manager.start_all_monitors()

    try:
        print("1. 同时监控多个数据流:")
        # 模拟数据流入
        for i in range(5):
            btc_data = generate_sample_data(10)
            eth_data = generate_sample_data(10)

            btc_monitor.add_data(btc_data)
            eth_monitor.add_data(eth_data)
            time.sleep(0.2)

        print()

        print("2. 整体统计:")
        overall_stats = manager.get_overall_statistics()
        print(f"   监控器数量: {overall_stats['monitor_count']}")
        print(f"   总处理记录: {overall_stats['total_processed']}")
        print(f"   整体错误率: {overall_stats['overall_error_rate']:.3f}")
        print(f"   平均质量得分: {overall_stats['average_quality_score']:.3f}")
        print(f"   活跃监控器: {overall_stats['active_monitors']}")

    finally:
        manager.stop_all_monitors()


if __name__ == "__main__":
    demonstrate_data_validation()
    demonstrate_quality_assessment()
    demonstrate_outlier_detection()
    demonstrate_consistency_checking()
    demonstrate_real_time_monitoring()
    demonstrate_data_manager()

    print("=== 数据质量保障演示完成 ===")
    print("所有监控器已自动清理")
