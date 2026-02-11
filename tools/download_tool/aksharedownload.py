#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015-2023 Daniel Rodriguez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


import argparse
import datetime
import io
import logging
import sys


logging.basicConfig(
    format='%(levelname)s: %(message)s',
    level=logging.INFO)


class AkShareDownload(object):
    """Download historical data from Chinese markets using AkShare library"""

    def __init__(self, symbol, fromdate, todate, period='daily', adjust='qfq', market='stock'):
        """
        Initialize AkShare downloader

        Args:
            symbol: Stock code (e.g., '000001' for 平安银行, 'sh000001' for 上证指数)
                    For foreign futures: 'GC' (COMEX Gold), 'SI' (Silver), 'CL' (Crude Oil), etc.
            fromdate: Start date
            todate: End date
            period: Data frequency - 'daily', 'weekly', 'monthly'
            adjust: Price adjustment - 'qfq' (前复权), 'hfq' (后复权), '' (不复权)
            market: Market type - 'stock' (A股), 'index' (指数), 'fund' (基金),
                    'futures' (国内期货), 'foreign_futures' (国际期货)
        """
        try:
            import akshare as ak
        except ImportError:
            msg = ('The AkShare data feed requires the akshare module. '
                   'Please install it using: pip install akshare')
            raise Exception(msg)

        self.error = None
        self.datafile = None

        # Format dates
        start_date = fromdate.strftime('%Y%m%d')
        end_date = todate.strftime('%Y%m%d')

        try:
            logging.info(f'Downloading {symbol} from {start_date} to {end_date}')

            df = None

            # Download based on market type
            if market == 'stock':
                # A股股票数据
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust
                )

            elif market == 'index':
                # 指数数据 - 使用东方财富接口
                if symbol.startswith('sh') or symbol.startswith('sz'):
                    index_symbol = symbol  # Keep the prefix
                else:
                    # Add prefix if not present
                    index_symbol = 'sh' + symbol if symbol.startswith('0') else 'sz' + symbol

                df = ak.stock_zh_index_daily_em(symbol=index_symbol)

                # Filter by date range
                if df is not None and not df.empty:
                    # The date column might be named differently
                    date_col = None
                    for col in df.columns:
                        if 'date' in col.lower() or '日期' in col:
                            date_col = col
                            break

                    if date_col:
                        df[date_col] = df[date_col].astype(str).str.replace('-', '')
                        df = df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]

            elif market == 'fund':
                # 基金数据
                df = ak.fund_open_fund_info_em(symbol=symbol, indicator="单位净值走势")

            elif market == 'futures':
                # 国内期货数据
                df = ak.futures_zh_daily_sina(symbol=symbol)

            elif market == 'foreign_futures':
                # 国际期货数据 (COMEX, NYMEX, etc.)
                logging.info(f"Downloading foreign futures {symbol}")
                df = ak.futures_foreign_hist(symbol=symbol)

            else:
                self.error = f'Unsupported market type: {market}'
                logging.error(self.error)
                return

            if df is None or df.empty:
                self.error = f'No data found for symbol {symbol}'
                logging.error(self.error)
                return

            # Standardize column names for backtrader compatibility
            # AkShare columns: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
            # Backtrader expects: Date, Open, High, Low, Close, Volume, OpenInterest

            column_mapping = {
                '日期': 'Date',
                '开盘': 'Open',
                '收盘': 'Close',
                '最高': 'High',
                '最低': 'Low',
                '成交量': 'Volume',
                '成交额': 'Amount',
                'date': 'Date',
                'open': 'Open',
                'close': 'Close',
                'high': 'High',
                'low': 'Low',
                'volume': 'Volume',
            }

            # Rename columns
            df = df.rename(columns=column_mapping)

            # Select only the columns we need
            required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            available_cols = [col for col in required_cols if col in df.columns]
            df = df[available_cols]

            # Add OpenInterest column (set to 0 for stocks)
            if 'OpenInterest' not in df.columns:
                df['OpenInterest'] = 0

            # Convert DataFrame to CSV format in memory
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)

            self.datafile = csv_buffer
            logging.info(f'Successfully downloaded {len(df)} rows of data')

        except Exception as e:
            self.error = f'Error downloading data: {str(e)}'
            logging.error(self.error)
            import traceback
            logging.error(traceback.format_exc())

    def writetofile(self, filename):
        """Write downloaded data to file"""
        if not self.datafile:
            logging.warning('No data to write')
            return

        if not hasattr(filename, 'read'):
            # It's not a file - open it
            f = io.open(filename, 'w')
        else:
            f = filename

        self.datafile.seek(0)
        for line in self.datafile:
            f.write(line)

        f.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description='Download Chinese Market Data using AkShare')

    parser.add_argument('--symbol', required=True,
                        help='Stock code (e.g., 000001 for 平安银行, sh000001 for 上证指数) or Foreign futures symbol (e.g., GC for COMEX Gold, SI for Silver, CL for Crude Oil)')

    parser.add_argument('--market', default='stock',
                        choices=['stock', 'index', 'fund', 'futures', 'foreign_futures'],
                        help='Market type: stock (A股), index (指数), fund (基金), futures (国内期货), foreign_futures (国际期货如COMEX黄金)')

    parser.add_argument('--period', default='daily',
                        choices=['daily', 'weekly', 'monthly'],
                        help='Data frequency: daily, weekly, monthly')

    parser.add_argument('--adjust', default='qfq',
                        choices=['qfq', 'hfq', ''],
                        help='Price adjustment: qfq (前复权), hfq (后复权), empty (不复权)')

    parser.add_argument('--fromdate', required=True,
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--todate', required=True,
                        help='Ending date in YYYY-MM-DD format')

    parser.add_argument('--outfile', required=True,
                        help='Output file name')

    return parser.parse_args()


if __name__ == '__main__':

    args = parse_args()

    logging.info('Processing input parameters')
    logging.info('Processing fromdate')
    try:
        fromdate = datetime.datetime.strptime(args.fromdate, '%Y-%m-%d')
    except Exception as e:
        logging.error('Converting fromdate failed')
        logging.error(str(e))
        sys.exit(1)

    logging.info('Processing todate')
    try:
        todate = datetime.datetime.strptime(args.todate, '%Y-%m-%d')
    except Exception as e:
        logging.error('Converting todate failed')
        logging.error(str(e))
        sys.exit(1)

    logging.info('Downloading from AkShare')
    try:
        akshare_down = AkShareDownload(
            symbol=args.symbol,
            fromdate=fromdate,
            todate=todate,
            period=args.period,
            adjust=args.adjust,
            market=args.market)

    except Exception as e:
        logging.error('Downloading data from AkShare failed')
        logging.error(str(e))
        sys.exit(1)

    if akshare_down.error:
        logging.error(f'Download failed: {akshare_down.error}')
        sys.exit(1)

    logging.info('Opening output file')
    try:
        ofile = io.open(args.outfile, 'w')
    except IOError as e:
        logging.error('Error opening output file')
        logging.error(str(e))
        sys.exit(1)

    logging.info('Writing downloaded data to output file')
    try:
        akshare_down.writetofile(ofile)
    except Exception as e:
        logging.error('Writing to output file failed')
        logging.error(str(e))
        sys.exit(1)

    logging.info('All operations completed successfully')
    sys.exit(0)
