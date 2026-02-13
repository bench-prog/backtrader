#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Data Downloader Module

统一的数据下载工具模块，支持多种数据源的市场数据获取。

模块结构:
    core/           核心下载器基类和通用功能
    providers/      各种数据提供商的具体实现
    utils/          工具函数和辅助类
    cli/            命令行接口

支持的数据源:
    - Yahoo Finance: 全球股票、指数、期货、外汇、加密货币
    - AkShare: 中国A股、指数、基金、国内期货、国际期货
    - CCXT: 加密货币交易所 (200+)

使用示例:
    from data_downloader import YahooDownloader, AkShareDownloader, CCXTDownloader

    # 下载黄金数据
    downloader = YahooDownloader(ticker='GC=F', fromdate='2015-01-01', todate='2026-01-01')
    downloader.download('gold.txt')
"""

__version__ = "1.0.0"

# 便捷导入
from .cli.main import main as download_main
from .core.downloader import BaseDownloader
from .providers.akshare import AkShareDownloader
from .providers.ccxt import CCXTDownloader
from .providers.yahoo import YahooDownloader

__all__ = [
    "BaseDownloader",
    "YahooDownloader",
    "AkShareDownloader",
    "CCXTDownloader",
    "download_main",
]
