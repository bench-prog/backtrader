#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Data Downloader CLI

统一的命令行接口，支持所有数据源的数据下载。
"""

import argparse
import logging
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

# 使用绝对导入
from data_downloader.providers.akshare import AkShareDownloader
from data_downloader.providers.ccxt import CCXTDownloader
from data_downloader.providers.yahoo import YahooDownloader


def setup_logging(level: str = "INFO"):
    """设置日志级别"""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s", level=numeric_level
    )


def download_command(args) -> int:
    """处理下载命令"""
    try:
        if args.source == "yahoo":
            downloader = YahooDownloader(
                ticker=args.ticker,
                fromdate=args.fromdate,
                todate=args.todate,
                period=args.timeframe,
                reverse=args.reverse,
                proxy=args.proxy,
            )
        elif args.source == "akshare":
            downloader = AkShareDownloader(
                symbol=args.symbol,
                fromdate=args.fromdate,
                todate=args.todate,
                period=args.period,
                adjust=args.adjust,
                market=args.market,
            )
        elif args.source == "ccxt":
            proxies = None
            if args.proxy:
                proxies = {"http": args.proxy, "https": args.proxy}

            downloader = CCXTDownloader(
                exchange=args.exchange,
                symbol=args.symbol,
                fromdate=args.fromdate,
                todate=args.todate,
                timeframe=args.timeframe,
                proxies=proxies,
            )
        else:
            logging.error(f"Unsupported data source: {args.source}")
            return 1

        success = downloader.download(args.outfile)
        if success:
            logging.info(f"Data successfully downloaded to {args.outfile}")
            return 0
        else:
            error = downloader.get_error()
            logging.error(f"Download failed: {error}")
            return 1

    except Exception as e:
        logging.error(f"Error during download: {str(e)}")
        return 1


def list_sources_command(args) -> int:
    """列出支持的数据源"""
    print("Supported Data Sources:")
    print("  yahoo    - Yahoo Finance (Global stocks, indices, futures, forex, crypto)")
    print("  akshare  - AkShare (Chinese A-shares, indices, funds, futures)")
    print("  ccxt     - CCXT (200+ cryptocurrency exchanges)")
    print()
    print("Use 'download-tool --help' for detailed usage information.")
    return 0


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Unified Data Downloader for Backtrader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download gold data from Yahoo Finance
  download-tool yahoo --ticker GC=F --fromdate 2020-01-01 --todate 2024-01-01 --outfile gold.txt
  
  # Download Chinese stock data
  download-tool akshare --symbol 000001 --market stock --fromdate 2020-01-01 --todate 2024-01-01 --outfile pingan.txt
  
  # Download cryptocurrency data
  download-tool ccxt --exchange binance --symbol BTC/USDT --fromdate 2020-01-01 --todate 2024-01-01 --outfile btc.txt
  
  # List all supported data sources
  download-tool list-sources
        """,
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list-sources 命令
    subparsers.add_parser("list-sources", help="List supported data sources")

    # yahoo 子命令
    yahoo_parser = subparsers.add_parser("yahoo", help="Download from Yahoo Finance")
    yahoo_parser.add_argument("--ticker", required=True, help="Ticker symbol")
    yahoo_parser.add_argument(
        "--fromdate", required=True, help="Start date (YYYY-MM-DD)"
    )
    yahoo_parser.add_argument("--todate", required=True, help="End date (YYYY-MM-DD)")
    yahoo_parser.add_argument(
        "--timeframe",
        default="d",
        choices=["d", "w", "m"],
        help="Timeframe: d=day, w=week, m=month",
    )
    yahoo_parser.add_argument(
        "--reverse", action="store_true", default=False, help="Reverse data order"
    )
    yahoo_parser.add_argument("--proxy", help="Proxy URL")
    yahoo_parser.add_argument("--outfile", required=True, help="Output file path")

    # akshare 子命令
    akshare_parser = subparsers.add_parser("akshare", help="Download from AkShare")
    akshare_parser.add_argument("--symbol", required=True, help="Symbol code")
    akshare_parser.add_argument(
        "--fromdate", required=True, help="Start date (YYYY-MM-DD)"
    )
    akshare_parser.add_argument("--todate", required=True, help="End date (YYYY-MM-DD)")
    akshare_parser.add_argument(
        "--market",
        default="stock",
        choices=["stock", "index", "fund", "futures", "foreign_futures"],
        help="Market type",
    )
    akshare_parser.add_argument(
        "--period",
        default="daily",
        choices=["daily", "weekly", "monthly"],
        help="Data frequency",
    )
    akshare_parser.add_argument(
        "--adjust",
        default="qfq",
        choices=["qfq", "hfq", ""],
        help="Price adjustment: qfq=前复权, hfq=后复权, empty=不复权",
    )
    akshare_parser.add_argument("--outfile", required=True, help="Output file path")

    # ccxt 子命令
    ccxt_parser = subparsers.add_parser("ccxt", help="Download from CCXT")
    ccxt_parser.add_argument("--exchange", required=True, help="Exchange name")
    ccxt_parser.add_argument("--symbol", required=True, help="Trading pair")
    ccxt_parser.add_argument(
        "--fromdate", required=True, help="Start date (YYYY-MM-DD)"
    )
    ccxt_parser.add_argument("--todate", required=True, help="End date (YYYY-MM-DD)")
    ccxt_parser.add_argument(
        "--timeframe", default="1d", help="Timeframe (e.g., 1m, 5m, 1h, 1d)"
    )
    ccxt_parser.add_argument("--proxy", help="Proxy URL")
    ccxt_parser.add_argument("--outfile", required=True, help="Output file path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    setup_logging(args.log_level)

    if args.command == "list-sources":
        return list_sources_command(args)
    else:
        return download_command(args)


if __name__ == "__main__":
    sys.exit(main())
