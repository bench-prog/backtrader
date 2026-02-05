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

import collections
from datetime import date, datetime
import io
import itertools

from ..utils.py3 import (urlopen, urlquote, ProxyHandler, build_opener,
                         install_opener)

import backtrader as bt
from .. import feed
from ..utils import date2num


class YahooFinanceCSVData(feed.CSVDataBase):
    '''
    Parses pre-downloaded Yahoo CSV Data Feeds (or locally generated if they
    comply to the Yahoo format)

    Specific parameters:

      - ``dataname``: The filename to parse or a file-like object

      - ``reverse`` (default: ``False``)

        It is assumed that locally stored files have already been reversed
        during the download process

      - ``adjclose`` (default: ``True``)

        Whether to use the dividend/split adjusted close and adjust all
        values according to it.

      - ``adjvolume`` (default: ``True``)

        Do also adjust ``volume`` if ``adjclose`` is also ``True``

      - ``round`` (default: ``True``)

        Whether to round the values to a specific number of decimals after
        having adjusted the close

      - ``roundvolume`` (default: ``0``)

        Round the resulting volume to the given number of decimals after having
        adjusted it

      - ``decimals`` (default: ``2``)

        Number of decimals to round to

      - ``swapcloses`` (default: ``False``)

        [2018-11-16] It would seem that the order of *close* and *adjusted
        close* is now fixed. The parameter is retained, in case the need to
        swap the columns again arose.

    '''
    lines = ('adjclose',)

    params = (
        ('reverse', False),
        ('adjclose', True),
        ('adjvolume', True),
        ('round', True),
        ('decimals', 2),
        ('roundvolume', False),
        ('swapcloses', False),
    )

    def start(self):
        super(YahooFinanceCSVData, self).start()

        if not self.params.reverse:
            return

        # Yahoo sends data in reverse order and the file is still unreversed
        dq = collections.deque()
        for line in self.f:
            dq.appendleft(line)

        f = io.StringIO(newline=None)
        f.writelines(dq)
        f.seek(0)
        self.f.close()
        self.f = f

    def _loadline(self, linetokens):
        while True:
            nullseen = False
            for tok in linetokens[1:]:
                if tok == 'null':
                    nullseen = True
                    linetokens = self._getnextline()  # refetch tokens
                    if not linetokens:
                        return False  # cannot fetch, go away

                    # out of for to carry on wiwth while True logic
                    break

            if not nullseen:
                break  # can proceed

        i = itertools.count(0)

        dttxt = linetokens[next(i)]
        dt = date(int(dttxt[0:4]), int(dttxt[5:7]), int(dttxt[8:10]))
        dtnum = date2num(datetime.combine(dt, self.p.sessionend))

        self.lines.datetime[0] = dtnum
        o = float(linetokens[next(i)])
        h = float(linetokens[next(i)])
        l = float(linetokens[next(i)])
        c = float(linetokens[next(i)])
        self.lines.openinterest[0] = 0.0

        # 2018-11-16 ... Adjusted Close seems to always be delivered after
        # the close and before the volume columns
        adjustedclose = float(linetokens[next(i)])
        try:
            v = float(linetokens[next(i)])
        except:  # cover the case in which volume is "null"
            v = 0.0

        if self.p.swapcloses:  # swap closing prices if requested
            c, adjustedclose = adjustedclose, c

        adjfactor = c / adjustedclose

        # in v7 "adjusted prices" seem to be given, scale back for non adj
        if self.params.adjclose:
            o /= adjfactor
            h /= adjfactor
            l /= adjfactor
            c = adjustedclose
            # If the price goes down, volume must go up and viceversa
            if self.p.adjvolume:
                v *= adjfactor

        if self.p.round:
            decimals = self.p.decimals
            o = round(o, decimals)
            h = round(h, decimals)
            l = round(l, decimals)
            c = round(c, decimals)

        v = round(v, self.p.roundvolume)

        self.lines.open[0] = o
        self.lines.high[0] = h
        self.lines.low[0] = l
        self.lines.close[0] = c
        self.lines.volume[0] = v
        self.lines.adjclose[0] = adjustedclose

        return True


class YahooLegacyCSV(YahooFinanceCSVData):
    '''
    This is intended to load files which were downloaded before Yahoo
    discontinued the original service in May-2017

    '''
    params = (
        ('version', ''),
    )


class YahooFinanceCSV(feed.CSVFeedBase):
    DataCls = YahooFinanceCSVData


class YahooFinanceData(YahooFinanceCSVData):
    '''
    Executes a direct download of data from Yahoo servers for the given time
    range.

    Specific parameters (or specific meaning):

      - ``dataname``

        The ticker to download ('YHOO' for Yahoo own stock quotes)

      - ``proxies``

        A dict indicating which proxy to go through for the download as in
        {'http': 'http://myproxy.com'} or {'http': 'http://127.0.0.1:8080'}

      - ``period``

        The timeframe to download data in. Pass 'w' for weekly and 'm' for
        monthly.

      - ``reverse``

        [2018-11-16] The latest incarnation of Yahoo online downloads returns
        the data in the proper order. The default value of ``reverse`` for the
        online download is therefore set to ``False``

      - ``adjclose``

        Whether to use the dividend/split adjusted close and adjust all values
        according to it.

      - ``urlhist``

        The url of the historical quotes in Yahoo Finance used to gather a
        ``crumb`` authorization cookie for the download

      - ``urldown``

        The url of the actual download server

      - ``retries``

        Number of times (each) to try to get a ``crumb`` cookie and download
        the data

      '''

    params = (
        ('proxies', {}),
        ('period', 'd'),
        ('reverse', False),
        ('urlhist', 'https://finance.yahoo.com/quote/{}/history'),
        ('urldown', 'https://query1.finance.yahoo.com/v7/finance/download'),
        ('retries', 3),
    )

    def start_v7(self):
        try:
            import yfinance as yf
            import os
            import time
        except ImportError:
            msg = ('The Yahoo data feed requires to have the yfinance '
                   'module installed. Please use pip install yfinance')
            raise Exception(msg)

        self.error = None

        # Set proxy via environment variables if provided
        original_http_proxy = os.environ.get('HTTP_PROXY')
        original_https_proxy = os.environ.get('HTTPS_PROXY')

        if self.p.proxies:
            proxy = self.p.proxies.get('http') or self.p.proxies.get('https')
            if proxy:
                os.environ['HTTP_PROXY'] = proxy
                os.environ['HTTPS_PROXY'] = proxy

        retries = 3
        df = None
        last_error = None

        try:
            # Map timeframe to yfinance interval
            intervals = {
                bt.TimeFrame.Days: '1d',
                bt.TimeFrame.Weeks: '1wk',
                bt.TimeFrame.Months: '1mo',
            }
            interval = intervals.get(self.p.timeframe, '1d')

            # Format dates for yfinance
            start_date = self.p.fromdate.strftime('%Y-%m-%d') if self.p.fromdate else None
            end_date = self.p.todate.strftime('%Y-%m-%d') if self.p.todate else None

            # Retry logic for rate limiting
            for attempt in range(retries):
                try:
                    # Download data using yfinance
                    ticker_obj = yf.Ticker(self.p.dataname)
                    df = ticker_obj.history(start=start_date, end=end_date, interval=interval)

                    if df.empty:
                        last_error = 'No data found for ticker {}'.format(self.p.dataname)
                        if attempt < retries - 1:
                            time.sleep(3 + (2 ** attempt))
                            continue
                        else:
                            self.error = last_error
                            self.f = None
                            return

                    # Success - break out of retry loop
                    break

                except Exception as e:
                    last_error = str(e)
                    if attempt < retries - 1:
                        wait_time = 5 + (2 ** attempt)
                        time.sleep(wait_time)
                    else:
                        self.error = 'Error downloading data after {} attempts: {}'.format(retries, last_error)
                        self.f = None
                        return

            if df is None or df.empty:
                self.error = last_error or 'Unknown error'
                self.f = None
                return

            # Convert DataFrame to CSV format in memory
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer)
            csv_buffer.seek(0)

            self.f = csv_buffer

        except Exception as e:
            self.error = 'Error downloading data: {}'.format(str(e))
            self.f = None

        finally:
            # Restore original proxy settings
            if self.p.proxies:
                if original_http_proxy:
                    os.environ['HTTP_PROXY'] = original_http_proxy
                else:
                    os.environ.pop('HTTP_PROXY', None)

                if original_https_proxy:
                    os.environ['HTTPS_PROXY'] = original_https_proxy
                else:
                    os.environ.pop('HTTPS_PROXY', None)

    def start(self):
        self.start_v7()

        # Check if download was successful
        if self.f is None:
            if self.error:
                raise Exception('Yahoo Finance download failed: {}'.format(self.error))
            else:
                raise Exception('Yahoo Finance download failed: Unknown error')

        # Handle reverse if needed (Yahoo used to send data in reverse order)
        if self.params.reverse:
            dq = collections.deque()
            for line in self.f:
                dq.appendleft(line)

            f = io.StringIO(newline=None)
            f.writelines(dq)
            f.seek(0)
            self.f.close()
            self.f = f

        # Skip YahooFinanceCSVData.start() and call grandparent's start()
        # to avoid trying to open self.p.dataname as a file
        super(YahooFinanceCSVData, self).start()


class YahooFinance(feed.CSVFeedBase):
    DataCls = YahooFinanceData

    params = DataCls.params._gettuple()
