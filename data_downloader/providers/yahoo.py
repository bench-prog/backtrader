#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Yahoo Finance Data Downloader

基于 yfinance 库的数据下载器，支持全球股票、指数、期货、外汇和加密货币数据下载。
"""

import io
import logging
import os
import time
from typing import Optional

from ..core.downloader import BaseDownloader


class YahooDownloader(BaseDownloader):
    """Yahoo Finance 数据下载器"""

    def __init__(
        self,
        ticker: str,
        fromdate: str,
        todate: str,
        period: str = "d",
        reverse: bool = False,
        proxy: Optional[str] = None,
    ):
        """
        初始化 Yahoo 数据下载器

        Args:
            ticker: 股票代码或符号 (如 'AAPL', 'GC=F', '^GSPC')
            fromdate: 开始日期 (YYYY-MM-DD)
            todate: 结束日期 (YYYY-MM-DD)
            period: 时间周期 ('d'=日, 'w'=周, 'm'=月)
            reverse: 是否反转数据顺序
            proxy: 代理服务器地址 (如 'http://127.0.0.1:7890')
        """
        super().__init__()

        # 验证日期
        from_dt, to_dt = self._validate_dates(fromdate, todate)

        # 导入依赖
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError(
                "Yahoo data downloader requires yfinance module. "
                "Please install it using: pip install yfinance"
            )

        # 设置代理
        self._original_http_proxy = os.environ.get("HTTP_PROXY")
        self._original_https_proxy = os.environ.get("HTTPS_PROXY")

        if proxy:
            os.environ["HTTP_PROXY"] = proxy
            os.environ["HTTPS_PROXY"] = proxy
            logging.info(f"Using proxy: {proxy}")

        # 映射周期到 yfinance 间隔
        intervals = {
            "d": "1d",
            "w": "1wk",
            "m": "1mo",
        }
        self.interval = intervals.get(period, "1d")

        # 格式化日期
        self.start_date = from_dt.strftime("%Y-%m-%d")
        self.end_date = to_dt.strftime("%Y-%m-%d")
        self.ticker = ticker
        self.reverse = reverse
        self.yf = yf

        logging.info(
            f"Initialized YahooDownloader for {ticker} from {self.start_date} to {self.end_date}"
        )

    def download(self, output_file) -> bool:
        """
        下载数据到指定文件

        Args:
            output_file: 输出文件路径或文件对象

        Returns:
            bool: 下载是否成功
        """
        try:
            # 下载数据
            if not self._fetch_data():
                return False

            # 写入输出文件
            self._write_output(output_file)
            logging.info("Data download completed successfully")
            return True

        except Exception as e:
            self.error = f"Download failed: {str(e)}"
            logging.error(self.error)
            return False
        finally:
            # 恢复原始代理设置
            self._restore_proxy_settings()

    def _fetch_data(self) -> bool:
        """获取数据"""
        df = None
        retries = 3

        for attempt in range(retries):
            try:
                logging.info(
                    f"Downloading {self.ticker} from {self.start_date} to {self.end_date} "
                    f"(attempt {attempt + 1}/{retries})"
                )

                # 使用 yfinance 下载数据
                ticker_obj = self.yf.Ticker(self.ticker)
                df = ticker_obj.history(
                    start=self.start_date, end=self.end_date, interval=self.interval
                )

                if df.empty:
                    error_msg = f"No data found for ticker {self.ticker}"
                    if attempt < retries - 1:
                        logging.warning(f"{error_msg}, retrying...")
                        time.sleep(3 + (2**attempt))
                        continue
                    else:
                        self.error = error_msg
                        return False

                # 成功 - 跳出重试循环
                break

            except Exception as e:
                if attempt < retries - 1:
                    wait_time = 5 + (2**attempt)
                    logging.warning(
                        f"Error: {str(e)}, waiting {wait_time}s before retry..."
                    )
                    time.sleep(wait_time)
                else:
                    self.error = (
                        f"Error downloading data after {retries} attempts: {str(e)}"
                    )
                    return False

        if df is None or df.empty:
            self.error = "Failed to download data"
            return False

        try:
            # 转换 DataFrame 为 CSV 格式
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer)
            csv_buffer.seek(0)

            # 可选地反转数据
            if self.reverse:
                lines = csv_buffer.readlines()
                header = lines[0]
                data_lines = lines[1:]
                data_lines.reverse()
                csv_buffer = io.StringIO()
                csv_buffer.write(header)
                csv_buffer.writelines(data_lines)
                csv_buffer.seek(0)

            self.datafile = csv_buffer
            self.error = None
            logging.info(f"Successfully downloaded {len(df)} rows of data")
            return True

        except Exception as e:
            self.error = f"Error processing data: {str(e)}"
            return False

    def _restore_proxy_settings(self):
        """恢复原始代理设置"""
        if hasattr(self, "_original_http_proxy"):
            if self._original_http_proxy:
                os.environ["HTTP_PROXY"] = self._original_http_proxy
            else:
                os.environ.pop("HTTP_PROXY", None)

        if hasattr(self, "_original_https_proxy"):
            if self._original_https_proxy:
                os.environ["HTTPS_PROXY"] = self._original_https_proxy
            else:
                os.environ.pop("HTTPS_PROXY", None)


def download_yahoo_data(
    ticker: str,
    fromdate: str,
    todate: str,
    output_file: str,
    period: str = "d",
    reverse: bool = False,
    proxy: Optional[str] = None,
) -> bool:
    """
    便捷函数：下载 Yahoo Finance 数据

    Args:
        ticker: 股票代码
        fromdate: 开始日期
        todate: 结束日期
        output_file: 输出文件路径
        period: 时间周期
        reverse: 是否反转数据
        proxy: 代理地址

    Returns:
        bool: 下载是否成功
    """
    downloader = YahooDownloader(
        ticker=ticker,
        fromdate=fromdate,
        todate=todate,
        period=period,
        reverse=reverse,
        proxy=proxy,
    )
    return downloader.download(output_file)
