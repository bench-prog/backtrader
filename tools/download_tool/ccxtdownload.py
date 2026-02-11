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
import time


logging.basicConfig(
    format='%(levelname)s: %(message)s',
    level=logging.INFO)


class CCXTDownload(object):
    """Download historical cryptocurrency data using CCXT library"""

    def __init__(self, exchange, symbol, fromdate, todate, timeframe='1d', proxies=None):
        """
        Initialize CCXT downloader

        Args:
            exchange: Exchange name (e.g., 'binance', 'okx', 'huobi', 'coinbase')
            symbol: Trading pair (e.g., 'BTC/USDT', 'ETH/USDT')
            fromdate: Start date
            todate: End date
            timeframe: Timeframe - '1m', '5m', '15m', '1h', '4h', '1d', '1w', '1M'
            proxies: Proxy settings (e.g., {'http': 'http://proxy:port', 'https': 'http://proxy:port'})
        """
        try:
            import ccxt
            import pandas as pd
        except ImportError:
            msg = ('The CCXT data feed requires the ccxt module. '
                   'Please install it using: pip install ccxt')
            raise Exception(msg)

        self.error = None
        self.datafile = None

        try:
            # Initialize exchange with proxy support
            exchange_config = {
                'enableRateLimit': True,  # Enable rate limiting
                'timeout': 30000,  # 30 seconds timeout
            }

            if proxies:
                exchange_config['proxies'] = proxies
                logging.info(f'Using proxy: {proxies}')

            exchange_class = getattr(ccxt, exchange)
            exchange_obj = exchange_class(exchange_config)

            logging.info(f'Connecting to {exchange} exchange')

            # Check if exchange supports OHLCV data
            if not exchange_obj.has['fetchOHLCV']:
                self.error = f'Exchange {exchange} does not support OHLCV data'
                logging.error(self.error)
                return

            # Convert dates to milliseconds timestamp
            since = int(fromdate.timestamp() * 1000)
            until = int(todate.timestamp() * 1000)

            logging.info(f'Downloading {symbol} from {fromdate} to {todate} with timeframe {timeframe}')

            # Fetch OHLCV data
            all_ohlcv = []
            current_since = since

            # Fetch data in chunks (most exchanges limit the number of candles per request)
            while current_since < until:
                try:
                    ohlcv = exchange_obj.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=timeframe,
                        since=current_since,
                        limit=1000  # Maximum candles per request
                    )

                    if not ohlcv:
                        break

                    # Filter data within date range
                    filtered_ohlcv = [candle for candle in ohlcv if candle[0] <= until]
                    all_ohlcv.extend(filtered_ohlcv)

                    # Update since to the last candle timestamp + 1
                    if ohlcv:
                        current_since = ohlcv[-1][0] + 1
                    else:
                        break

                    # If we got less than requested, we've reached the end
                    if len(ohlcv) < 1000:
                        break

                    # Rate limiting - sleep to avoid hitting API limits
                    time.sleep(exchange_obj.rateLimit / 1000)

                except Exception as e:
                    logging.warning(f'Error fetching data: {str(e)}')
                    break

            if not all_ohlcv:
                self.error = f'No data found for {symbol} on {exchange}'
                logging.error(self.error)
                return

            # Convert to DataFrame
            # OHLCV format: [timestamp, open, high, low, close, volume]
            df = pd.DataFrame(all_ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])

            # Convert timestamp to datetime
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')

            # Remove duplicates based on timestamp
            df = df.drop_duplicates(subset=['Timestamp'], keep='first')

            # Sort by date
            df = df.sort_values('Date')

            # Select and reorder columns for backtrader compatibility
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

            # Add OpenInterest column (set to 0 for crypto spot)
            df['OpenInterest'] = 0

            # Convert DataFrame to CSV format in memory
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)

            self.datafile = csv_buffer
            logging.info(f'Successfully downloaded {len(df)} candles')

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
        description='Download Cryptocurrency Data using CCXT')

    parser.add_argument('--exchange',
                        help='Exchange name (e.g., binance, okx, huobi, coinbase, kraken)')

    parser.add_argument('--symbol',
                        help='Trading pair (e.g., BTC/USDT, ETH/USDT, BTC/USD)')

    parser.add_argument('--timeframe', default='1d',
                        choices=['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w', '1M'],
                        help='Timeframe: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M')

    parser.add_argument('--fromdate',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--todate',
                        help='Ending date in YYYY-MM-DD format')

    parser.add_argument('--outfile',
                        help='Output file name')

    parser.add_argument('--proxy',
                        help='Proxy URL (e.g., http://127.0.0.1:7890 or socks5://127.0.0.1:1080)')

    parser.add_argument('--list-exchanges', action='store_true',
                        help='List all supported exchanges')

    args = parser.parse_args()

    # Check if list-exchanges is requested
    if args.list_exchanges:
        return args

    # Otherwise, require all other arguments
    if not all([args.exchange, args.symbol, args.fromdate, args.todate, args.outfile]):
        parser.error('--exchange, --symbol, --fromdate, --todate, and --outfile are required when not using --list-exchanges')

    return args


if __name__ == '__main__':

    args = parse_args()

    # List exchanges if requested
    if args.list_exchanges:
        try:
            import ccxt
            exchanges = ccxt.exchanges
            print(f'\nSupported exchanges ({len(exchanges)}):')
            print('=' * 60)
            for i, exchange in enumerate(sorted(exchanges), 1):
                print(f'{i:3d}. {exchange}')
            print('=' * 60)
            print('\nPopular exchanges: binance, okx, huobi, coinbase, kraken, bybit, gate')
            sys.exit(0)
        except Exception as e:
            logging.error(f'Error listing exchanges: {str(e)}')
            sys.exit(1)

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

    logging.info('Downloading from CCXT')
    try:
        # Setup proxies if provided
        proxies = None
        if args.proxy:
            proxies = {
                'http': args.proxy,
                'https': args.proxy,
            }
            logging.info(f'Using proxy: {args.proxy}')

        ccxt_down = CCXTDownload(
            exchange=args.exchange,
            symbol=args.symbol,
            fromdate=fromdate,
            todate=todate,
            timeframe=args.timeframe,
            proxies=proxies)

    except Exception as e:
        logging.error('Downloading data from CCXT failed')
        logging.error(str(e))
        sys.exit(1)

    if ccxt_down.error:
        logging.error(f'Download failed: {ccxt_down.error}')
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
        ccxt_down.writetofile(ofile)
    except Exception as e:
        logging.error('Writing to output file failed')
        logging.error(str(e))
        sys.exit(1)

    logging.info('All operations completed successfully')
    sys.exit(0)
