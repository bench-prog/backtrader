#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Utilities Module

数据下载工具的辅助函数和工具类。
"""

import logging
from typing import Dict, Optional


def validate_date_range(fromdate: str, todate: str) -> bool:
    """
    验证日期范围的有效性

    Args:
        fromdate: 开始日期 (YYYY-MM-DD)
        todate: 结束日期 (YYYY-MM-DD)

    Returns:
        bool: 日期范围是否有效
    """
    try:
        import datetime

        from_dt = datetime.datetime.strptime(fromdate, "%Y-%m-%d")
        to_dt = datetime.datetime.strptime(todate, "%Y-%m-%d")
        return from_dt <= to_dt
    except ValueError:
        return False


def format_proxy_dict(proxy_url: Optional[str]) -> Optional[Dict[str, str]]:
    """
    格式化代理URL为字典格式

    Args:
        proxy_url: 代理URL字符串

    Returns:
        Dict[str, str]: 代理字典，格式错误时返回None
    """
    if not proxy_url:
        return None

    try:
        return {"http": proxy_url, "https": proxy_url}
    except Exception:
        logging.warning(f"Invalid proxy URL format: {proxy_url}")
        return None


def get_supported_exchanges() -> Dict[str, str]:
    """
    获取支持的交易所列表

    Returns:
        Dict[str, str]: 交易所名称和描述的映射
    """
    return {
        "binance": "Binance - 全球最大的加密货币交易所",
        "okx": "OKX - 领先的数字资产交易所",
        "huobi": "Huobi - 全球数字资产交易所",
        "coinbase": "Coinbase - 美国合规交易所",
        "kraken": "Kraken - 老牌欧洲交易所",
        "bybit": "Bybit - 衍生品交易所",
        "kucoin": "KuCoin - 多元化数字资产平台",
    }


def get_common_symbols() -> Dict[str, Dict[str, str]]:
    """
    获取常用交易品种符号

    Returns:
        Dict[str, Dict[str, str]]: 按类别分类的符号字典
    """
    return {
        "yahoo": {
            "GC=F": "COMEX黄金期货",
            "CL=F": "NYMEX原油期货",
            "SI=F": "COMEX白银期货",
            "^GSPC": "标普500指数",
            "^DJI": "道琼斯工业平均指数",
            "AAPL": "苹果公司股票",
            "GOOGL": "谷歌股票",
            "BTC-USD": "比特币(美元计价)",
        },
        "akshare": {
            "000001": "平安银行",
            "600519": "贵州茅台",
            "sh000001": "上证指数",
            "sz399001": "深证成指",
            "AU0": "黄金期货主力合约",
            "CU0": "铜期货主力合约",
            "GC": "COMEX黄金",
            "SI": "COMEX白银",
            "CL": "NYMEX原油",
        },
        "ccxt": {
            "BTC/USDT": "比特币/泰达币",
            "ETH/USDT": "以太坊/泰达币",
            "BNB/USDT": "币安币/泰达币",
            "SOL/USDT": "Solana/泰达币",
            "XRP/USDT": "瑞波币/泰达币",
        },
    }


def print_data_source_info():
    """打印数据源信息"""
    print("=== Data Downloader 支持的数据源 ===\n")

    print("1. Yahoo Finance (yahoo)")
    print("   适用市场: 全球股票、指数、期货、外汇、加密货币")
    print("   常用代码:", ", ".join(list(get_common_symbols()["yahoo"].keys())[:5]))
    print()

    print("2. AkShare (akshare)")
    print("   适用市场: 中国A股、指数、基金、国内期货、国际期货")
    print("   常用代码:", ", ".join(list(get_common_symbols()["akshare"].keys())[:5]))
    print()

    print("3. CCXT (ccxt)")
    print("   适用市场: 200+ 加密货币交易所")
    print("   支持交易所:", ", ".join(list(get_supported_exchanges().keys())[:5]))
    print("   常用交易对:", ", ".join(list(get_common_symbols()["ccxt"].keys())[:3]))
    print()


# 便捷函数别名
validate_dates = validate_date_range
format_proxy = format_proxy_dict
