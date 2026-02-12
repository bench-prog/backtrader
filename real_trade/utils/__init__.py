#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Utils - 公共工具模块

提供日志、配置、校验、重试、时间工具等通用能力。
"""

from .config import GlobalConfig
from .connection_manager import (
    Connection,
    ConnectionPool,
    ConnectionState,
    ConnectionStats,
    HeartbeatMonitor,
    HTTPConnection,
    WebSocketConnection,
    get_connection_manager,
    get_heartbeat_monitor,
    shutdown_connection_managers,
)
from .data_monitor import (
    DataManager,
    DataStreamMonitor,
    QualityMetrics,
    QualityThreshold,
    create_data_monitor,
    get_data_manager,
    shutdown_data_monitors,
)
from .data_quality import (
    DataConsistencyChecker,
    DataQualityAssessor,
    DataQualityLevel,
    DataQualityReport,
    DataValidationRule,
    DataValidator,
    OutlierDetector,
    assess_ohlcv_quality,
    validate_single_bar,
)
from .exceptions import (
    BusinessError,
    ConfigError,
    ConnectionError,
    DataError,
    ErrorCode,
    NetworkError,
    RealTradeError,
    SystemError,
    TimeoutError,
    TradingError,
    exception_handler,
    handle_exception,
    safe_call,
)
from .logger import get_logger, setup_logger
from .retry import RetryConfig, retry
from .time_utils import (
    datetime_to_timestamp,
    timeframe_to_seconds,
    timestamp_to_datetime,
)
from .validators import (
    validate_api_keys,
    validate_symbol,
    validate_timeframe,
)

__all__ = [
    "setup_logger",
    "get_logger",
    "GlobalConfig",
    "validate_symbol",
    "validate_timeframe",
    "validate_api_keys",
    "retry",
    "RetryConfig",
    "timestamp_to_datetime",
    "datetime_to_timestamp",
    "timeframe_to_seconds",
    # Exceptions
    "ErrorCode",
    "RealTradeError",
    "SystemError",
    "NetworkError",
    "ConnectionError",
    "TimeoutError",
    "DataError",
    "TradingError",
    "ConfigError",
    "BusinessError",
    "handle_exception",
    "safe_call",
    "exception_handler",
    # Connection Management
    "ConnectionState",
    "ConnectionStats",
    "Connection",
    "HTTPConnection",
    "WebSocketConnection",
    "ConnectionPool",
    "HeartbeatMonitor",
    "get_connection_manager",
    "get_heartbeat_monitor",
    "shutdown_connection_managers",
    # Data Quality
    "DataQualityLevel",
    "DataQualityReport",
    "DataValidationRule",
    "DataValidator",
    "DataConsistencyChecker",
    "OutlierDetector",
    "DataQualityAssessor",
    "assess_ohlcv_quality",
    "validate_single_bar",
    # Data Monitoring
    "QualityMetrics",
    "QualityThreshold",
    "DataStreamMonitor",
    "DataManager",
    "get_data_manager",
    "create_data_monitor",
    "shutdown_data_monitors",
]
