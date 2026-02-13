#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
CCXT Data Downloader

基于 CCXT 库的数据下载器，支持 200+ 加密货币交易所数据下载。
"""

import datetime
import io
import logging
from typing import Dict, Optional

from ..core.downloader import BaseDownloader


class CCXTDownloader(BaseDownloader):
    """CCXT 加密货币数据下载器"""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        fromdate: str,
        todate: str,
        timeframe: str = "1d",
        proxies: Optional[Dict[str, str]] = None,
    ):
        """
        初始化 CCXT 数据下载器

        Args:
            exchange: 交易所名称 (如 'binance', 'okx', 'huobi', 'coinbase')
            symbol: 交易对 (如 'BTC/USDT', 'ETH/USDT')
            fromdate: 开始日期 (YYYY-MM-DD)
            todate: 结束日期 (YYYY-MM-DD)
            timeframe: 时间周期 (如 '1m', '5m', '1h', '1d')
            proxies: 代理设置 {'http': 'proxy_url', 'https': 'proxy_url'}
        """
        super().__init__()

        # 验证日期
        from_dt, to_dt = self._validate_dates(fromdate, todate)

        # 导入依赖
        try:
            import ccxt
        except ImportError:
            raise ImportError(
                "CCXT data downloader requires ccxt module. "
                "Please install it using: pip install ccxt"
            )

        self.exchange_name = exchange
        self.symbol = symbol
        self.fromdate = from_dt
        self.todate = to_dt
        self.timeframe = timeframe
        self.proxies = proxies

        # 创建交易所实例
        try:
            exchange_class = getattr(ccxt, exchange)
            self.exchange = (
                exchange_class({"enableRateLimit": True, "proxies": proxies})
                if proxies
                else exchange_class({"enableRateLimit": True})
            )

            # 检查交易所是否支持 OHLCV
            if not self.exchange.has["fetchOHLCV"]:
                raise ValueError(f"Exchange {exchange} does not support OHLCV data")

        except Exception as e:
            raise ValueError(f"Failed to initialize exchange {exchange}: {str(e)}")

        logging.info(
            f"Initialized CCXTDownloader for {symbol} on {exchange} from {fromdate} to {todate}"
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

    def _fetch_data(self) -> bool:
        """获取数据"""
        try:
            # 转换日期为毫秒时间戳
            since = int(self.fromdate.timestamp() * 1000)
            to_timestamp = int(self.todate.timestamp() * 1000)

            all_ohlcv = []
            limit = 1000  # CCXT 通常限制每次请求的数量

            logging.info(f"Downloading {self.symbol} data from {self.exchange_name}")

            while since < to_timestamp:
                # 获取 OHLCV 数据
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    since=since,
                    limit=limit,
                )

                if not ohlcv:
                    break

                # 过滤时间范围内的数据
                filtered_ohlcv = [
                    candle for candle in ohlcv if candle[0] <= to_timestamp
                ]
                all_ohlcv.extend(filtered_ohlcv)

                # 更新 since 为最后一条数据的时间 + 1
                since = ohlcv[-1][0] + 1

                # 如果返回的数据少于限制，说明已经到达最新数据
                if len(ohlcv) < limit:
                    break

            if not all_ohlcv:
                self.error = f"No data found for {self.symbol}"
                return False

            # 转换为 pandas DataFrame 进行处理
            try:
                import pandas as pd
            except ImportError:
                # 如果没有 pandas，手动处理
                return self._process_without_pandas(all_ohlcv)

            # 使用 pandas 处理数据
            df = pd.DataFrame(
                all_ohlcv,
                columns=["timestamp", "Open", "High", "Low", "Close", "Volume"],
            )
            df["Date"] = pd.to_datetime(df["timestamp"], unit="ms")
            df["Date"] = df["Date"].dt.strftime("%Y-%m-%d %H:%M:%S")

            # 重新排序列
            df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]

            # 添加 OpenInterest 列
            df["OpenInterest"] = 0

            # 转换为 CSV 格式
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)

            self.datafile = csv_buffer
            self.error = None
            logging.info(f"Successfully downloaded {len(df)} candles")
            return True

        except Exception as e:
            self.error = f"Error downloading data: {str(e)}"
            logging.error(self.error)
            import traceback

            logging.error(traceback.format_exc())
            return False

    def _process_without_pandas(self, ohlcv_data) -> bool:
        """不使用 pandas 处理数据"""
        try:
            # 手动格式化数据
            lines = ["Date,Open,High,Low,Close,Volume,OpenInterest\n"]

            for candle in ohlcv_data:
                timestamp, open_price, high_price, low_price, close_price, volume = (
                    candle[:6]
                )

                # 转换时间戳为日期字符串
                dt = datetime.datetime.fromtimestamp(timestamp / 1000)
                date_str = dt.strftime("%Y-%m-%d %H:%M:%S")

                line = f"{date_str},{open_price},{high_price},{low_price},{close_price},{volume},0\n"
                lines.append(line)

            csv_buffer = io.StringIO()
            csv_buffer.writelines(lines)
            csv_buffer.seek(0)

            self.datafile = csv_buffer
            self.error = None
            logging.info(f"Successfully downloaded {len(ohlcv_data)} candles")
            return True

        except Exception as e:
            self.error = f"Error processing data without pandas: {str(e)}"
            return False


def download_ccxt_data(
    exchange: str,
    symbol: str,
    fromdate: str,
    todate: str,
    output_file: str,
    timeframe: str = "1d",
    proxies: Optional[Dict[str, str]] = None,
) -> bool:
    """
    便捷函数：下载 CCXT 数据

    Args:
        exchange: 交易所名称
        symbol: 交易对
        fromdate: 开始日期
        todate: 结束日期
        output_file: 输出文件路径
        timeframe: 时间周期
        proxies: 代理设置

    Returns:
        bool: 下载是否成功
    """
    downloader = CCXTDownloader(
        exchange=exchange,
        symbol=symbol,
        fromdate=fromdate,
        todate=todate,
        timeframe=timeframe,
        proxies=proxies,
    )
    return downloader.download(output_file)
