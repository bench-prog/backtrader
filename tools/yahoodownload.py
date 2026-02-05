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


class YahooDownload(object):
    """Download historical data from Yahoo Finance using yfinance library"""

    retries = 3

    def __init__(self, ticker, fromdate, todate, period='d', reverse=False, proxy=None):
        try:
            import yfinance as yf
            import time
            import os
        except ImportError:
            msg = ('The Yahoo data feed requires the yfinance module. '
                   'Please install it using: pip install yfinance')
            raise Exception(msg)

        # Set proxy via environment variables if provided
        # yfinance uses curl_cffi which reads from environment variables
        original_http_proxy = os.environ.get('HTTP_PROXY')
        original_https_proxy = os.environ.get('HTTPS_PROXY')

        if proxy:
            os.environ['HTTP_PROXY'] = proxy
            os.environ['HTTPS_PROXY'] = proxy
            logging.info(f'Using proxy: {proxy}')

        # Map period to yfinance interval
        intervals = {
            'd': '1d',
            'w': '1wk',
            'm': '1mo',
        }

        interval = intervals.get(period, '1d')

        # Format dates for yfinance (YYYY-MM-DD)
        start_date = fromdate.strftime('%Y-%m-%d')
        end_date = todate.strftime('%Y-%m-%d')

        df = None
        last_error = None

        # Retry logic for rate limiting
        for attempt in range(self.retries):
            try:
                # Download data using yfinance
                logging.info(f'Downloading {ticker} from {start_date} to {end_date} (attempt {attempt + 1}/{self.retries})')

                # Let yfinance handle the session (it uses curl_cffi internally)
                ticker_obj = yf.Ticker(ticker)
                df = ticker_obj.history(start=start_date, end=end_date, interval=interval)

                if df.empty:
                    last_error = f'No data found for ticker {ticker}'
                    if attempt < self.retries - 1:
                        logging.warning(f'{last_error}, retrying...')
                        time.sleep(3 + (2 ** attempt))  # Longer wait time
                        continue
                    else:
                        self.error = last_error
                        self.datafile = None
                        logging.error(self.error)
                        return

                # Success - break out of retry loop
                break

            except Exception as e:
                last_error = str(e)
                if attempt < self.retries - 1:
                    wait_time = 5 + (2 ** attempt)  # Longer exponential backoff
                    logging.warning(f'Error: {last_error}, waiting {wait_time}s before retry...')
                    time.sleep(wait_time)
                else:
                    self.error = f'Error downloading data after {self.retries} attempts: {last_error}'
                    self.datafile = None
                    logging.error(self.error)
                    return

        if df is None or df.empty:
            self.error = last_error or 'Unknown error'
            self.datafile = None
            return

        try:
            # Convert DataFrame to CSV format in memory
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer)
            csv_buffer.seek(0)

            # Optionally reverse the data
            if reverse:
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
            logging.info(f'Successfully downloaded {len(df)} rows of data')

        except Exception as e:
            self.error = f'Error processing data: {str(e)}'
            self.datafile = None
            logging.error(self.error)

        finally:
            # Restore original proxy settings
            if proxy:
                if original_http_proxy:
                    os.environ['HTTP_PROXY'] = original_http_proxy
                else:
                    os.environ.pop('HTTP_PROXY', None)

                if original_https_proxy:
                    os.environ['HTTPS_PROXY'] = original_https_proxy
                else:
                    os.environ.pop('HTTPS_PROXY', None)

    def writetofile(self, filename):
        if not self.datafile:
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
        description='Download Yahoo CSV Finance Data')

    parser.add_argument('--ticker', required=True,
                        help='Ticker to be downloaded')

    parser.add_argument('--reverse', action='store_true', default=False,
                        help='Do reverse the downloaded files')

    parser.add_argument('--timeframe', default='d',
                        help='Timeframe: d -> day, w -> week, m -> month')

    parser.add_argument('--fromdate', required=True,
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--todate', required=True,
                        help='Ending date in YYYY-MM-DD format')

    parser.add_argument('--outfile', required=True,
                        help='Output file name')

    parser.add_argument('--proxy',
                        help='Proxy URL (e.g., http://127.0.0.1:7890)')

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

    logging.info('Do Not Reverse flag status')
    reverse = args.reverse

    logging.info('Downloading from yahoo')
    try:
        yahoodown = YahooDownload(
            ticker=args.ticker,
            fromdate=fromdate,
            todate=todate,
            period=args.timeframe,
            reverse=reverse,
            proxy=args.proxy)

    except Exception as e:
        logging.error('Downloading data from Yahoo failed')
        logging.error(str(e))
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
        yahoodown.writetofile(ofile)
    except Exception as e:
        logging.error('Writing to output file failed')
        logging.error(str(e))
        sys.exit(1)

    logging.info('All operations completed successfully')
    sys.exit(0)
