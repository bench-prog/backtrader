#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015-2026 Backtrader Team
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
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import datetime

# The above could be sent to an independent module
import backtrader as bt


class TestStrategy(bt.Strategy):
    params = dict(
        smaperiod=15,
        trade=False,
        stake=0.01,  # BTC数量
        exectype=bt.Order.Market,
        stopafter=0,
        valid=None,
        cancel=0,
        donotsell=False,
        stoptrail=False,
        stoptraillimit=False,
        trailamount=None,
        trailpercent=None,
        limitoffset=None,
        oco=False,
        bracket=False,
    )

    def __init__(self):
        # To control operation entries
        self.orderid = list()
        self.order = None

        self.counttostop = 0
        self.data_live = False

        # Add a Simple Moving Average indicator
        self.sma = bt.indicators.SMA(self.data, period=self.p.smaperiod)

        print("--------------------------------------------------")
        print("Strategy Created")
        print("--------------------------------------------------")

    def notify_data(self, data, status, *args, **kwargs):
        print("*" * 5, "DATA NOTIF:", data._name, data._getstatusname(status), "*" * 5)
        if status == data.LIVE:
            self.counttostop = self.p.stopafter
            self.data_live = True

    def notify_store(self, msg, *args, **kwargs):
        print("*" * 5, "STORE NOTIF:", msg, *args, **kwargs)
        # 检查是否包含错误信息
        if "error" in str(msg).lower() or "failed" in str(msg).lower():
            print("⚠️  检测到错误信息，可能需要检查API密钥配置")

    def notify_order(self, order):
        if order.status in [order.Completed, order.Cancelled, order.Rejected]:
            self.order = None

        print(
            "{}: Order ref: {} / Type {} / Status {}".format(
                self.data.datetime.date(0),
                order.ref,
                "Buy" * order.isbuy() or "Sell",
                order.getstatusname(),
            )
        )

    def notify_trade(self, trade):
        print("-" * 50)
        print("TRADE REPORT")
        print("-" * 50)
        print("Ref:", trade.ref)
        print("Status:", trade.status_names[trade.status])
        print("Dt:", trade.dt)
        print("Stake:", trade.stake)
        print("Size:", trade.size)
        print("Price:", trade.price)
        print("Value:", trade.value)
        print("Commission:", trade.commission)
        print("PnL:", trade.pnl)
        print("PnL Comm:", trade.pnlcomm)
        print("-" * 50)

    def prenext(self):
        self.next(frompre=True)

    def next(self, frompre=False):
        txt = list()
        txt.append("Data0")
        txt.append("%04d" % len(self.data0))
        dtfmt = "%Y-%m-%dT%H:%M:%S.%f"
        txt.append("{:f}".format(self.data.datetime[0]))
        txt.append("%s" % self.data.datetime.datetime(0).strftime(dtfmt))
        txt.append("{:f}".format(self.data.open[0]))
        txt.append("{:f}".format(self.data.high[0]))
        txt.append("{:f}".format(self.data.low[0]))
        txt.append("{:f}".format(self.data.close[0]))
        txt.append("{:6d}".format(int(self.data.volume[0])))
        txt.append("{:d}".format(int(self.data.openinterest[0])))
        txt.append("{:f}".format(self.sma[0]))
        print(", ".join(txt))

        if len(self.datas) > 1 and len(self.data1):
            txt = list()
            txt.append("Data1")
            txt.append("%04d" % len(self.data1))
            dtfmt = "%Y-%m-%dT%H:%M:%S.%f"
            txt.append("{}".format(self.data1.datetime[0]))
            txt.append("%s" % self.data1.datetime.datetime(0).strftime(dtfmt))
            txt.append("{}".format(self.data1.open[0]))
            txt.append("{}".format(self.data1.high[0]))
            txt.append("{}".format(self.data1.low[0]))
            txt.append("{}".format(self.data1.close[0]))
            txt.append("{}".format(self.data1.volume[0]))
            txt.append("{}".format(self.data1.openinterest[0]))
            print(", ".join(txt))

        if self.counttostop:  # stop after x live lines
            self.counttostop -= 1
            if not self.counttostop:
                self.env.runstop()
                return

        if not self.p.trade:
            return

        if self.data_live and not self.position:
            if self.order is None:
                if self.p.exectype in [bt.Order.Market, bt.Order.Limit]:
                    # Market/Limit order
                    self.order = self.buy(
                        size=self.p.stake,
                        exectype=self.p.exectype,
                        price=self.data.close[0] + self.p.limitoffset,
                        valid=self.p.valid,
                    )

                elif self.p.exectype == bt.Order.Stop:
                    # Stop order
                    self.order = self.buy(
                        size=self.p.stake,
                        exectype=self.p.exectype,
                        price=self.data.close[0] + self.p.limitoffset,
                        valid=self.p.valid,
                    )

                elif self.p.exectype == bt.Order.StopLimit:
                    # StopLimit order
                    self.order = self.buy(
                        size=self.p.stake,
                        exectype=self.p.exectype,
                        price=self.data.close[0] + self.p.limitoffset,
                        plimit=self.data.close[0] + self.p.limitoffset,
                        valid=self.p.valid,
                    )

                elif self.p.exectype == bt.Order.StopTrail:
                    # StopTrail order
                    self.order = self.buy(
                        size=self.p.stake,
                        exectype=self.p.exectype,
                        trailamount=self.p.trailamount,
                        trailpercent=self.p.trailpercent,
                    )

                elif self.p.exectype == bt.Order.StopTrailLimit:
                    # StopTrailLimit order
                    self.order = self.buy(
                        size=self.p.stake,
                        exectype=self.p.exectype,
                        price=self.data.close[0] + self.p.limitoffset,
                        plimit=self.data.close[0] + self.p.limitoffset,
                        trailamount=self.p.trailamount,
                        trailpercent=self.p.trailpercent,
                    )

                elif self.p.oco:
                    # OCO order
                    self.order = self.buy(
                        size=self.p.stake,
                        exectype=bt.Order.Limit,
                        price=self.data.close[0] + self.p.limitoffset,
                        oco=self.order,
                    )

                elif self.p.bracket:
                    # Bracket order
                    self.order, _, _ = self.buy_bracket(
                        size=self.p.stake,
                        exectype=bt.Order.Market,
                        price=self.data.close[0],
                        limitprice=self.data.close[0] + self.p.limitoffset,
                        stopprice=self.data.close[0] - self.p.limitoffset,
                        valid=self.p.valid,
                    )

        elif self.position and not self.p.donotsell:
            if self.order is None:
                if self.p.exectype in [bt.Order.Market, bt.Order.Limit]:
                    # Market/Limit order
                    self.order = self.sell(
                        size=self.p.stake,
                        exectype=self.p.exectype,
                        price=self.data.close[0] - self.p.limitoffset,
                        valid=self.p.valid,
                    )

                elif self.p.exectype == bt.Order.Stop:
                    # Stop order
                    self.order = self.sell(
                        size=self.p.stake,
                        exectype=self.p.exectype,
                        price=self.data.close[0] - self.p.limitoffset,
                        valid=self.p.valid,
                    )

                elif self.p.exectype == bt.Order.StopLimit:
                    # StopLimit order
                    self.order = self.sell(
                        size=self.p.stake,
                        exectype=self.p.exectype,
                        price=self.data.close[0] - self.p.limitoffset,
                        plimit=self.data.close[0] - self.p.limitoffset,
                        valid=self.p.valid,
                    )

                elif self.p.exectype == bt.Order.StopTrail:
                    # StopTrail order
                    self.order = self.sell(
                        size=self.p.stake,
                        exectype=self.p.exectype,
                        trailamount=self.p.trailamount,
                        trailpercent=self.p.trailpercent,
                    )

                elif self.p.exectype == bt.Order.StopTrailLimit:
                    # StopTrailLimit order
                    self.order = self.sell(
                        size=self.p.stake,
                        exectype=self.p.exectype,
                        price=self.data.close[0] - self.p.limitoffset,
                        plimit=self.data.close[0] - self.p.limitoffset,
                        trailamount=self.p.trailamount,
                        trailpercent=self.p.trailpercent,
                    )

                elif self.p.oco:
                    # OCO order
                    self.order = self.sell(
                        size=self.p.stake,
                        exectype=bt.Order.Limit,
                        price=self.data.close[0] - self.p.limitoffset,
                        oco=self.order,
                    )

                elif self.p.bracket:
                    # Bracket order
                    _, _, self.order = self.sell_bracket(
                        size=self.p.stake,
                        exectype=bt.Order.Market,
                        price=self.data.close[0],
                        limitprice=self.data.close[0] - self.p.limitoffset,
                        stopprice=self.data.close[0] + self.p.limitoffset,
                        valid=self.p.valid,
                    )

        if self.p.cancel:
            if self.data_live and not self.position and len(self.orderid):
                self.cancel(self.orderid[0])


def runstrategy():
    args = parse_args()

    # Create a cerebro entity
    cerebro = bt.Cerebro(stdstats=False)

    storekwargs = dict(
        apikey=args.apikey,
        secret=args.secret,
        testnet=not args.live,
    )

    if args.account:
        storekwargs["account"] = args.account

    # Add the store
    store = bt.stores.BinanceStore(**storekwargs)

    # Add data
    kwargs = dict()
    if args.fromdate:
        kwargs["fromdate"] = datetime.datetime.strptime(args.fromdate, "%Y-%m-%d")
    if args.todate:
        kwargs["todate"] = datetime.datetime.strptime(args.todate, "%Y-%m-%d")

    data = store.getdata(dataname=args.data, **kwargs)
    cerebro.adddata(data)

    # Add strategy
    cerebro.addstrategy(
        TestStrategy,
        smaperiod=args.smaperiod,
        trade=args.trade,
        stake=args.stake,
        exectype=bt.Order.ExecType[args.exectype],
        stopafter=args.stopafter,
        valid=args.valid,
        cancel=args.cancel,
        donotsell=args.donotsell,
        stoptrail=args.stoptrail,
        stoptraillimit=args.stoptraillimit,
        trailamount=args.trailamount,
        trailpercent=args.trailpercent,
        limitoffset=args.limitoffset,
        oco=args.oco,
        bracket=args.bracket,
    )

    # Live data ... avoid long data accumulation by switching to "exactbars"
    cerebro.run(exactbars=args.exactbars)

    if args.plot and args.exactbars < 1:  # plot if possible
        cerebro.plot()


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=("Binance Test Script - 展示如何使用backtrader进行Binance实盘交易"),
    )

    parser.add_argument(
        "--exactbars",
        default=1,
        type=int,
        required=False,
        help="exactbars level, use 0/-1/-2 to enable plotting",
    )

    parser.add_argument(
        "--plot", required=False, action="store_true", help="Plot if possible"
    )

    parser.add_argument(
        "--stopafter",
        default=0,
        type=int,
        required=False,
        help="Stop after x lines of LIVE data",
    )

    parser.add_argument(
        "--debug",
        required=False,
        action="store_true",
        help="Display all info received from source",
    )

    parser.add_argument(
        "--apikey", default="", required=True, help="API Key needed to operate"
    )

    parser.add_argument(
        "--secret", default="", required=True, help="API Secret needed to operate"
    )

    parser.add_argument(
        "--account", default="", required=False, help="Account Number when needed"
    )

    parser.add_argument(
        "--live", default=False, action="store_true", help='Use the "LIVE" environment'
    )

    parser.add_argument(
        "--data", default="BTCUSDT", required=False, help="Binance symbol to use"
    )

    parser.add_argument(
        "--smaperiod",
        default=15,
        type=int,
        required=False,
        help="Period to apply to the Simple Moving Average",
    )

    pgroup = parser.add_mutually_exclusive_group(required=False)

    pgroup.add_argument(
        "--replay",
        required=False,
        action="store_true",
        help="replay to chosen timeframe",
    )

    pgroup.add_argument(
        "--resample",
        required=False,
        action="store_true",
        help="resample to chosen timeframe",
    )

    parser.add_argument(
        "--timeframe",
        default="Minutes",
        choices=["Ticks", "Seconds", "Minutes", "Daily", "Weekly", "Monthly"],
        required=False,
        help="TimeFrame for ReSample/RePlay",
    )

    parser.add_argument(
        "--compression",
        default=1,
        type=int,
        required=False,
        help="Compression for ReSample/RePlay",
    )

    parser.add_argument(
        "--timeframe1",
        default=None,
        choices=["Ticks", "Seconds", "Minutes", "Daily", "Weekly", "Monthly"],
        required=False,
        help="TimeFrame for ReSample/RePlay - Data1",
    )

    parser.add_argument(
        "--compression1",
        default=None,
        type=int,
        required=False,
        help="Compression for ReSample/RePlay - Data1",
    )

    parser.add_argument(
        "--csv",
        required=False,
        action="store_true",
        help="Write a CSV copy of the input data",
    )

    parser.add_argument(
        "--trim",
        required=False,
        type=int,
        help="Trim the given number of characters from the start of each line",
    )

    parser.add_argument(
        "--verbose", required=False, action="store_true", help="Turn on verbose output"
    )

    parser.add_argument(
        "--no-defaults", action="store_true", help="Do not use default values"
    )

    parser.add_argument(
        "--fromdate", required=False, help="Starting date in YYYY-MM-DD format"
    )

    parser.add_argument(
        "--todate", required=False, help="Ending date in YYYY-MM-DD format"
    )

    parser.add_argument(
        "--stake", default=0.01, required=False, help="Stake to use in each operation"
    )

    parser.add_argument(
        "--trade",
        required=False,
        action="store_true",
        help="Do Sample Buy/Sell operations",
    )

    parser.add_argument(
        "--exectype",
        default="Market",
        choices=[
            "Market",
            "Close",
            "Limit",
            "Stop",
            "StopLimit",
            "StopTrail",
            "StopTrailLimit",
            "Historical",
        ],
        required=False,
        help="Execution to Use when opening position",
    )

    parser.add_argument(
        "--valid",
        default=None,
        required=False,
        help="Seconds to keep the order alive before cancelling",
    )

    parser.add_argument(
        "--cancel",
        default=0,
        type=int,
        required=False,
        help=(
            "Cancel a buy order after n bars in operation,"
            " to be combined with orders like Limit"
        ),
    )

    # Plot options
    parser.add_argument(
        "--plot",
        "-p",
        nargs="?",
        required=False,
        metavar="kwargs",
        const=True,
        help=(
            "Plot the read data applying any kwargs passed\n"
            "\n"
            "For example:\n"
            "\n"
            '  --plot style="candle" (to plot candles)\n'
        ),
    )

    group = parser.add_mutually_exclusive_group(required=False)

    group.add_argument(
        "--donotsell",
        required=False,
        action="store_true",
        help="Do not sell after a buy",
    )

    group.add_argument(
        "--stoptrail",
        required=False,
        action="store_true",
        help="Issue a stoptraillimit after buy( do not sell",
    )

    group.add_argument(
        "--stoptraillimit",
        required=False,
        action="store_true",
        help="Issue a stoptrail after buy (do not sell",
    )

    parser.add_argument(
        "--trailamount",
        default=None,
        type=float,
        required=False,
        help="Amount for stoptrai",
    )

    parser.add_argument(
        "--trailpercent",
        default=None,
        type=float,
        required=False,
        help="Percentage for stoptrail",
    )

    parser.add_argument(
        "--limitoffset",
        default=None,
        type=float,
        required=False,
        help="Offset for stoplimit/sto",
    )

    group1 = parser.add_mutually_exclusive_group(required=False)

    group1.add_argument(
        "--oco", required=False, action="store_true", help="oco to the buy order"
    )

    group1.add_argument(
        "--bracket",
        required=False,
        action="store_true",
        help="bracket to the buy order",
    )

    return parser.parse_args()


if __name__ == "__main__":
    runstrategy()
