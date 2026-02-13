#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
AkShare Data Downloader

基于 AkShare 库的数据下载器，支持中国A股、指数、基金、期货等市场数据下载。
"""

import io
import logging

from ..core.downloader import BaseDownloader


class AkShareDownloader(BaseDownloader):
    """AkShare 数据下载器"""

    def __init__(
        self,
        symbol: str,
        fromdate: str,
        todate: str,
        period: str = "daily",
        adjust: str = "qfq",
        market: str = "stock",
    ):
        """
        初始化 AkShare 数据下载器

        Args:
            symbol: 股票代码或符号
            fromdate: 开始日期 (YYYY-MM-DD)
            todate: 结束日期 (YYYY-MM-DD)
            period: 数据频率 ('daily', 'weekly', 'monthly')
            adjust: 价格调整方式 ('qfq'=前复权, 'hfq'=后复权, ''=不复权)
            market: 市场类型 ('stock', 'index', 'fund', 'futures', 'foreign_futures')
        """
        super().__init__()

        # 验证日期
        from_dt, to_dt = self._validate_dates(fromdate, todate)

        # 导入依赖
        try:
            import akshare as ak
        except ImportError:
            raise ImportError(
                "AkShare data downloader requires akshare module. "
                "Please install it using: pip install akshare"
            )

        self.symbol = symbol
        self.fromdate = from_dt
        self.todate = to_dt
        self.period = period
        self.adjust = adjust
        self.market = market
        self.ak = ak

        logging.info(
            f"Initialized AkShareDownloader for {symbol} ({market}) from {fromdate} to {todate}"
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
            df = None

            if self.market == "stock":
                # A股数据
                df = self.ak.stock_zh_a_hist(
                    symbol=self.symbol,
                    period=self.period,
                    start_date=self.fromdate.strftime("%Y%m%d"),
                    end_date=self.todate.strftime("%Y%m%d"),
                    adjust=self.adjust,
                )

            elif self.market == "index":
                # 指数数据
                if self.symbol.startswith(("sh", "sz")):
                    # 国内指数
                    df = self.ak.index_zh_a_hist(
                        symbol=self.symbol,
                        period=self.period,
                        start_date=self.fromdate.strftime("%Y%m%d"),
                        end_date=self.todate.strftime("%Y%m%d"),
                    )
                else:
                    # 其他指数处理
                    df = self.ak.index_us_stock_sina(symbol=self.symbol)

            elif self.market == "fund":
                # 基金数据
                df = self.ak.fund_open_fund_info_em(
                    symbol=self.symbol, indicator="单位净值走势"
                )

            elif self.market == "futures":
                # 国内期货数据
                df = self.ak.futures_zh_daily_sina(symbol=self.symbol)

            elif self.market == "foreign_futures":
                # 国际期货数据
                logging.info(f"Downloading foreign futures {self.symbol}")
                df = self.ak.futures_foreign_hist(symbol=self.symbol)

            else:
                self.error = f"Unsupported market type: {self.market}"
                return False

            if df is None or df.empty:
                self.error = f"No data found for symbol {self.symbol}"
                return False

            # 标准化列名以兼容 backtrader
            column_mapping = {
                "日期": "Date",
                "开盘": "Open",
                "收盘": "Close",
                "最高": "High",
                "最低": "Low",
                "成交量": "Volume",
                "成交额": "Amount",
                "date": "Date",
                "open": "Open",
                "close": "Close",
                "high": "High",
                "low": "Low",
                "volume": "Volume",
            }

            # 重命名列
            df = df.rename(columns=column_mapping)

            # 选择需要的列
            required_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
            available_cols = [col for col in required_cols if col in df.columns]
            df = df[available_cols]

            # 添加 OpenInterest 列
            if "OpenInterest" not in df.columns:
                df["OpenInterest"] = 0

            # 转换 DataFrame 为 CSV 格式
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)

            self.datafile = csv_buffer
            self.error = None
            logging.info(f"Successfully downloaded {len(df)} rows of data")
            return True

        except Exception as e:
            self.error = f"Error downloading data: {str(e)}"
            logging.error(self.error)
            import traceback

            logging.error(traceback.format_exc())
            return False


def download_akshare_data(
    symbol: str,
    fromdate: str,
    todate: str,
    output_file: str,
    period: str = "daily",
    adjust: str = "qfq",
    market: str = "stock",
) -> bool:
    """
    便捷函数：下载 AkShare 数据

    Args:
        symbol: 股票代码
        fromdate: 开始日期
        todate: 结束日期
        output_file: 输出文件路径
        period: 数据频率
        adjust: 价格调整方式
        market: 市场类型

    Returns:
        bool: 下载是否成功
    """
    downloader = AkShareDownloader(
        symbol=symbol,
        fromdate=fromdate,
        todate=todate,
        period=period,
        adjust=adjust,
        market=market,
    )
    return downloader.download(output_file)
