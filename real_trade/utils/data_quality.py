#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Data Quality & Consistency - 数据质量和一致性保障

提供数据校验、异常数据检测、数据完整性检查等功能。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# 延迟导入避免循环依赖
# from ..utils import DataError, RealTradeError, get_logger


class DataQualityLevel(Enum):
    """数据质量等级"""

    EXCELLENT = "excellent"  # 优秀 - 完整无异常
    GOOD = "good"  # 良好 - 轻微缺失或异常
    FAIR = "fair"  # 一般 - 存在明显问题但可使用
    POOR = "poor"  # 较差 - 严重质量问题
    UNUSABLE = "unusable"  # 不可用 - 数据无法使用


@dataclass
class DataQualityReport:
    """数据质量报告"""

    quality_level: DataQualityLevel
    total_records: int
    valid_records: int
    missing_records: int
    duplicate_records: int
    outlier_records: int
    consistency_issues: int
    completeness_rate: float
    accuracy_score: float
    issues: List[str]
    recommendations: List[str]


@dataclass
class DataValidationRule:
    """数据验证规则"""

    field: str
    required: bool = True
    data_type: type = float
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allow_null: bool = False
    custom_validator: Optional[callable] = None


class DataValidator:
    """数据验证器"""

    def __init__(self, rules: List[DataValidationRule] = None):
        self.rules = rules or []
        from .logger import get_logger

        self.logger = get_logger("data_validator")

    def add_rule(self, rule: DataValidationRule):
        """添加验证规则"""
        self.rules.append(rule)

    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证单条记录"""
        errors = []

        for rule in self.rules:
            field_value = record.get(rule.field)

            # 必填字段检查
            if rule.required and field_value is None:
                errors.append(f"字段 '{rule.field}' 为必填项")
                continue

            # 空值检查
            if field_value is None:
                if not rule.allow_null:
                    errors.append(f"字段 '{rule.field}' 不允许为空")
                continue

            # 数据类型检查
            if not isinstance(field_value, rule.data_type):
                errors.append(
                    f"字段 '{rule.field}' 类型错误，期望 {rule.data_type.__name__}，实际 {type(field_value).__name__}"
                )
                continue

            # 数值范围检查
            if rule.data_type in (int, float) and isinstance(field_value, (int, float)):
                if rule.min_value is not None and field_value < rule.min_value:
                    errors.append(
                        f"字段 '{rule.field}' 值 {field_value} 小于最小值 {rule.min_value}"
                    )

                if rule.max_value is not None and field_value > rule.max_value:
                    errors.append(
                        f"字段 '{rule.field}' 值 {field_value} 大于最大值 {rule.max_value}"
                    )

            # 自定义验证
            if rule.custom_validator:
                try:
                    if not rule.custom_validator(field_value):
                        errors.append(f"字段 '{rule.field}' 未通过自定义验证")
                except Exception as e:
                    errors.append(f"字段 '{rule.field}' 自定义验证异常: {e}")

        return len(errors) == 0, errors

    def validate_dataset(
        self, dataset: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[str]]:
        """验证数据集"""
        valid_count = 0
        invalid_count = 0
        all_errors = []

        for i, record in enumerate(dataset):
            is_valid, errors = self.validate_record(record)
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                for error in errors:
                    all_errors.append(f"记录 {i}: {error}")

        return valid_count, invalid_count, all_errors


class DataConsistencyChecker:
    """数据一致性检查器"""

    def __init__(self):
        from .logger import get_logger

        self.logger = get_logger("consistency_checker")

    def check_price_consistency(self, ohlcv_data: List[List]) -> List[str]:
        """检查价格一致性 (open, high, low, close)"""
        issues = []

        for i, bar in enumerate(ohlcv_data):
            timestamp, open_price, high, low, close, volume = bar

            # 基本价格关系检查
            if high < max(open_price, close):
                issues.append(
                    f"记录 {i}: 最高价 {high} 小于开盘价 {open_price} 或收盘价 {close}"
                )

            if low > min(open_price, close):
                issues.append(
                    f"记录 {i}: 最低价 {low} 大于开盘价 {open_price} 或收盘价 {close}"
                )

            if high < low:
                issues.append(f"记录 {i}: 最高价 {high} 小于最低价 {low}")

        return issues

    def check_volume_consistency(self, ohlcv_data: List[List]) -> List[str]:
        """检查成交量一致性"""
        issues = []

        for i, bar in enumerate(ohlcv_data):
            timestamp, open_price, high, low, close, volume = bar

            # 成交量不能为负数
            if volume < 0:
                issues.append(f"记录 {i}: 成交量 {volume} 为负数")

            # 成交量为0但价格有变动的情况
            if i > 0:
                prev_bar = ohlcv_data[i - 1]
                prev_close = prev_bar[4]
                if volume == 0 and prev_close != close:
                    issues.append(
                        f"记录 {i}: 成交量为0但价格发生变动 ({prev_close} -> {close})"
                    )

        return issues

    def check_time_sequence(self, ohlcv_data: List[List]) -> List[str]:
        """检查时间序列一致性"""
        issues = []

        for i in range(1, len(ohlcv_data)):
            prev_timestamp = ohlcv_data[i - 1][0]
            curr_timestamp = ohlcv_data[i][0]

            # 时间应该是递增的
            if curr_timestamp <= prev_timestamp:
                issues.append(
                    f"记录 {i}: 时间戳 {curr_timestamp} 不大于前一条记录 {prev_timestamp}"
                )

        return issues

    def check_data_gaps(
        self, ohlcv_data: List[List], expected_interval: int
    ) -> List[str]:
        """检查数据缺口"""
        issues = []

        for i in range(1, len(ohlcv_data)):
            prev_timestamp = ohlcv_data[i - 1][0]
            curr_timestamp = ohlcv_data[i][0]
            gap = curr_timestamp - prev_timestamp

            # 检查时间间隔是否符合预期
            if gap > expected_interval * 1.5:  # 允许50%的误差
                gap_minutes = gap / 60000  # 转换为分钟
                expected_minutes = expected_interval / 60000
                issues.append(
                    f"记录 {i}: 发现数据缺口，间隔 {gap_minutes:.1f}分钟，期望约 {expected_minutes:.1f}分钟"
                )

        return issues


class OutlierDetector:
    """异常值检测器"""

    def __init__(self, method: str = "iqr"):
        self.method = method
        from .logger import get_logger

        self.logger = get_logger("outlier_detector")

    def detect_price_outliers(
        self, ohlcv_data: List[List], field_index: int = 4
    ) -> List[Tuple[int, float, str]]:
        """检测价格异常值"""
        prices = [bar[field_index] for bar in ohlcv_data]
        outliers = []

        if self.method == "iqr":
            outliers = self._detect_iqr_outliers(ohlcv_data, prices, field_index)
        elif self.method == "zscore":
            outliers = self._detect_zscore_outliers(ohlcv_data, prices, field_index)
        elif self.method == "modified_zscore":
            outliers = self._detect_modified_zscore_outliers(
                ohlcv_data, prices, field_index
            )

        return outliers

    def _detect_iqr_outliers(
        self, ohlcv_data: List[List], values: List[float], field_index: int
    ) -> List[Tuple[int, float, str]]:
        """使用四分位距方法检测异常值"""
        if len(values) < 4:
            return []

        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = []
        for i, (bar, value) in enumerate(zip(ohlcv_data, values)):
            if value < lower_bound or value > upper_bound:
                reason = "低于下界" if value < lower_bound else "高于上界"
                outliers.append(
                    (
                        i,
                        value,
                        f"IQR方法: {reason} (边界: {lower_bound:.2f}-{upper_bound:.2f})",
                    )
                )

        return outliers

    def _detect_zscore_outliers(
        self, ohlcv_data: List[List], values: List[float], field_index: int
    ) -> List[Tuple[int, float, str]]:
        """使用Z-score方法检测异常值"""
        if len(values) < 3:
            return []

        mean_val = np.mean(values)
        std_val = np.std(values)

        if std_val == 0:
            return []

        outliers = []
        for i, (bar, value) in enumerate(zip(ohlcv_data, values)):
            z_score = abs((value - mean_val) / std_val)
            if z_score > 3:  # 3σ准则
                outliers.append((i, value, f"Z-score方法: Z-score={z_score:.2f} > 3"))

        return outliers

    def _detect_modified_zscore_outliers(
        self, ohlcv_data: List[List], values: List[float], field_index: int
    ) -> List[Tuple[int, float, str]]:
        """使用修正Z-score方法检测异常值（对异常值更鲁棒）"""
        if len(values) < 3:
            return []

        median_val = np.median(values)
        mad = np.median([abs(x - median_val) for x in values])

        if mad == 0:
            return []

        outliers = []
        for i, (bar, value) in enumerate(zip(ohlcv_data, values)):
            modified_z_score = 0.6745 * (value - median_val) / mad
            if abs(modified_z_score) > 3.5:
                outliers.append(
                    (
                        i,
                        value,
                        f"修正Z-score方法: |Z|={abs(modified_z_score):.2f} > 3.5",
                    )
                )

        return outliers


class DataQualityAssessor:
    """数据质量评估器"""

    def __init__(self):
        self.validator = DataValidator()
        self.consistency_checker = DataConsistencyChecker()
        self.outlier_detector = OutlierDetector()
        from .logger import get_logger

        self.logger = get_logger("quality_assessor")

        # 添加默认验证规则
        self._setup_default_rules()

    def _setup_default_rules(self):
        """设置默认验证规则"""
        rules = [
            DataValidationRule(
                "timestamp", required=True, data_type=(int, float), min_value=0
            ),
            DataValidationRule("open", required=True, data_type=float, min_value=0),
            DataValidationRule("high", required=True, data_type=float, min_value=0),
            DataValidationRule("low", required=True, data_type=float, min_value=0),
            DataValidationRule("close", required=True, data_type=float, min_value=0),
            DataValidationRule("volume", required=True, data_type=float, min_value=0),
        ]

        for rule in rules:
            self.validator.add_rule(rule)

    def assess_quality(
        self, ohlcv_data: List[List], timeframe_minutes: int = 1
    ) -> DataQualityReport:
        """评估数据质量"""
        if not ohlcv_data:
            return DataQualityReport(
                quality_level=DataQualityLevel.UNUSABLE,
                total_records=0,
                valid_records=0,
                missing_records=0,
                duplicate_records=0,
                outlier_records=0,
                consistency_issues=0,
                completeness_rate=0.0,
                accuracy_score=0.0,
                issues=["数据集为空"],
                recommendations=["提供有效的数据"],
            )

        # 1. 基本统计
        total_records = len(ohlcv_data)

        # 2. 数据验证
        dataset_dicts = [
            {
                "timestamp": bar[0],
                "open": bar[1],
                "high": bar[2],
                "low": bar[3],
                "close": bar[4],
                "volume": bar[5],
            }
            for bar in ohlcv_data
        ]

        valid_count, invalid_count, validation_errors = self.validator.validate_dataset(
            dataset_dicts
        )

        # 3. 一致性检查
        consistency_issues = []
        consistency_issues.extend(
            self.consistency_checker.check_price_consistency(ohlcv_data)
        )
        consistency_issues.extend(
            self.consistency_checker.check_volume_consistency(ohlcv_data)
        )
        consistency_issues.extend(
            self.consistency_checker.check_time_sequence(ohlcv_data)
        )
        consistency_issues.extend(
            self.consistency_checker.check_data_gaps(
                ohlcv_data, timeframe_minutes * 60000
            )
        )

        # 4. 异常值检测
        close_outliers = self.outlier_detector.detect_price_outliers(
            ohlcv_data, 4
        )  # close price
        high_outliers = self.outlier_detector.detect_price_outliers(
            ohlcv_data, 2
        )  # high price
        low_outliers = self.outlier_detector.detect_price_outliers(
            ohlcv_data, 3
        )  # low price
        volume_outliers = self.outlier_detector.detect_price_outliers(
            ohlcv_data, 5
        )  # volume

        total_outliers = (
            len(close_outliers)
            + len(high_outliers)
            + len(low_outliers)
            + len(volume_outliers)
        )

        # 5. 重复数据检查
        timestamps = [bar[0] for bar in ohlcv_data]
        duplicate_count = len(timestamps) - len(set(timestamps))

        # 6. 质量评分
        completeness_rate = valid_count / total_records if total_records > 0 else 0
        consistency_score = (
            1.0 - (len(consistency_issues) / total_records) if total_records > 0 else 0
        )
        outlier_score = (
            1.0 - (total_outliers / total_records) if total_records > 0 else 1.0
        )
        duplicate_score = (
            1.0 - (duplicate_count / total_records) if total_records > 0 else 1.0
        )

        accuracy_score = (
            completeness_rate + consistency_score + outlier_score + duplicate_score
        ) / 4

        # 7. 确定质量等级
        quality_level = self._determine_quality_level(
            completeness_rate, consistency_score, outlier_score, duplicate_score
        )

        # 8. 生成建议
        recommendations = self._generate_recommendations(
            quality_level,
            validation_errors,
            consistency_issues,
            close_outliers,
            duplicate_count,
        )

        # 9. 汇总所有问题
        all_issues = []
        all_issues.extend(validation_errors)
        all_issues.extend(consistency_issues)
        all_issues.extend(
            [
                f"收盘价异常值 (记录{i}): {value} - {reason}"
                for i, value, reason in close_outliers
            ]
        )
        all_issues.extend(
            [
                f"最高价异常值 (记录{i}): {value} - {reason}"
                for i, value, reason in high_outliers
            ]
        )
        all_issues.extend(
            [
                f"最低价异常值 (记录{i}): {value} - {reason}"
                for i, value, reason in low_outliers
            ]
        )
        all_issues.extend(
            [
                f"成交量异常值 (记录{i}): {value} - {reason}"
                for i, value, reason in volume_outliers
            ]
        )

        if duplicate_count > 0:
            all_issues.append(f"发现 {duplicate_count} 条重复记录")

        return DataQualityReport(
            quality_level=quality_level,
            total_records=total_records,
            valid_records=valid_count,
            missing_records=invalid_count,
            duplicate_records=duplicate_count,
            outlier_records=total_outliers,
            consistency_issues=len(consistency_issues),
            completeness_rate=completeness_rate,
            accuracy_score=accuracy_score,
            issues=all_issues[:20],  # 限制显示前20个问题
            recommendations=recommendations,
        )

    def _determine_quality_level(
        self,
        completeness: float,
        consistency: float,
        outlier_score: float,
        duplicate_score: float,
    ) -> DataQualityLevel:
        """确定数据质量等级"""
        avg_score = (completeness + consistency + outlier_score + duplicate_score) / 4

        if avg_score >= 0.95:
            return DataQualityLevel.EXCELLENT
        elif avg_score >= 0.85:
            return DataQualityLevel.GOOD
        elif avg_score >= 0.70:
            return DataQualityLevel.FAIR
        elif avg_score >= 0.50:
            return DataQualityLevel.POOR
        else:
            return DataQualityLevel.UNUSABLE

    def _generate_recommendations(
        self,
        quality_level: DataQualityLevel,
        validation_errors: List[str],
        consistency_issues: List[str],
        outliers: List[Tuple[int, float, str]],
        duplicate_count: int,
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if quality_level == DataQualityLevel.EXCELLENT:
            recommendations.append("数据质量优秀，可直接使用")
            return recommendations

        if validation_errors:
            recommendations.append("修复数据格式和类型错误")

        if consistency_issues:
            recommendations.append("检查并修正价格和时间序列不一致问题")

        if outliers:
            recommendations.append("审查异常值，确认是否为真实数据或需要清洗")

        if duplicate_count > 0:
            recommendations.append("去除重复记录")

        if quality_level in [
            DataQualityLevel.FAIR,
            DataQualityLevel.POOR,
            DataQualityLevel.UNUSABLE,
        ]:
            recommendations.append("考虑使用数据清洗工具进行预处理")
            recommendations.append("验证数据源的可靠性和完整性")

        return recommendations


# 便利函数
def assess_ohlcv_quality(
    ohlcv_data: List[List], timeframe_minutes: int = 1
) -> DataQualityReport:
    """便利函数：评估OHLCV数据质量"""
    assessor = DataQualityAssessor()
    return assessor.assess_quality(ohlcv_data, timeframe_minutes)


def validate_single_bar(bar: List) -> Tuple[bool, List[str]]:
    """便利函数：验证单根K线数据"""
    validator = DataValidator()

    # 设置验证规则
    rules = [
        DataValidationRule(
            "timestamp", required=True, data_type=(int, float), min_value=0
        ),
        DataValidationRule("open", required=True, data_type=float, min_value=0),
        DataValidationRule("high", required=True, data_type=float, min_value=0),
        DataValidationRule("low", required=True, data_type=float, min_value=0),
        DataValidationRule("close", required=True, data_type=float, min_value=0),
        DataValidationRule("volume", required=True, data_type=float, min_value=0),
    ]

    for rule in rules:
        validator.add_rule(rule)

    record = {
        "timestamp": bar[0],
        "open": bar[1],
        "high": bar[2],
        "low": bar[3],
        "close": bar[4],
        "volume": bar[5],
    }

    return validator.validate_record(record)


__all__ = [
    "DataQualityLevel",
    "DataQualityReport",
    "DataValidationRule",
    "DataValidator",
    "DataConsistencyChecker",
    "OutlierDetector",
    "DataQualityAssessor",
    "assess_ohlcv_quality",
    "validate_single_bar",
]
