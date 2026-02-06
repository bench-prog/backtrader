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
"""
Bybit Live Trading Example using CCXT

This sample demonstrates how to connect to Bybit exchange using CCXT
and execute live trading with backtrader.

Features:
- Real-time data streaming from Bybit
- Live order execution (with paper trading mode)
- Position management
- Simple moving average crossover strategy

Requirements:
- pip install ccxt
- Bybit API credentials (API Key and Secret)

Usage:
    # proxy
    --proxy http://127.0.0.1:7890

    # Backtest mode (download historical data)
    python bybit-live-trading.py --backtest --symbol BTC/USDT --fromdate 2024-01-01

    # Paper trading mode (default, simulates orders)
    python bybit-live-trading.py --testnet --apikey YOUR_KEY --secret YOUR_SECRET

    # Paper trading with live data feed but simulated orders
    python bybit-live-trading.py --apikey YOUR_KEY --secret YOUR_SECRET --paper-trading

    # Live trading mode (REAL orders sent to exchange - use with caution!)
    python bybit-live-trading.py --apikey YOUR_KEY --secret YOUR_SECRET --no-paper-trading

    # Testnet trading (recommended for testing)
    python bybit-live-trading.py --testnet --apikey YOUR_TESTNET_KEY --secret YOUR_TESTNET_SECRET --no-paper-trading
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import datetime

import backtrader as bt


class SMACrossStrategy(bt.Strategy):
    """
    Simple Moving Average Crossover Strategy

    Buy when fast MA crosses above slow MA
    Sell when fast MA crosses below slow MA
    """

    params = (
        ("fast_period", 10),
        ("slow_period", 30),
        ("order_size", 0.01),  # Order size in base currency (e.g., 0.01 BTC)
        ("printlog", True),
    )

    def log(self, txt, dt=None):
        """Logging function"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.datetime(0)
            print(f"{dt.isoformat()} {txt}")

    def __init__(self):
        # Keep reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Add moving average indicators
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.fast_period
        )
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.slow_period
        )

        # Crossover signal
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted - no action required
            return

        # Check if an order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BUY EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}, "
                    f"Comm: {order.executed.comm:.2f}"
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(
                    f"SELL EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}, "
                    f"Comm: {order.executed.comm:.2f}"
                )

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        # Reset order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f"OPERATION PROFIT, GROSS: {trade.pnl:.2f}, NET: {trade.pnlcomm:.2f}")

    def next(self):
        # Log the closing price
        self.log(f"Close: {self.dataclose[0]:.2f}")

        # Check if an order is pending
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Not in the market, look for buy signal
            if self.crossover > 0:
                self.log(f"BUY CREATE, {self.dataclose[0]:.2f}")
                self.order = self.buy(size=self.params.order_size)

        else:
            # In the market, look for sell signal
            if self.crossover < 0:
                self.log(f"SELL CREATE, {self.dataclose[0]:.2f}")
                self.order = self.sell(size=self.params.order_size)

    def stop(self):
        self.log(
            f"(Fast MA: {self.params.fast_period}, Slow MA: {self.params.slow_period}) "
            f"Ending Value: {self.broker.getvalue():.2f}",
            dt=self.datas[0].datetime.datetime(0),
        )


class CCXTBybitData(bt.DataBase):
    """
    CCXT Bybit Data Feed

    This data feed connects to Bybit exchange using CCXT library
    and streams real-time OHLCV data.
    """

    params = (
        ("apikey", ""),
        ("secret", ""),
        ("symbol", "BTC/USDT"),
        ("timeframe", bt.TimeFrame.Minutes),
        ("compression", 1),
        ("testnet", True),
        ("backtest", False),
        ("fromdate", None),
        ("todate", None),
        ("proxy", None),
        ("ccxt_timeframe", "1m"),
    )

    def __init__(self):
        super(CCXTBybitData, self).__init__()

        try:
            import ccxt
        except ImportError:
            raise Exception("CCXT library required. Install with: pip install ccxt")

        # Initialize Bybit exchange
        exchange_config = {
            "apiKey": self.p.apikey,
            "secret": self.p.secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",  # or 'future' for derivatives
            },
        }

        # Add proxy support
        if self.p.proxy:
            exchange_config["proxies"] = {
                "http": self.p.proxy,
                "https": self.p.proxy,
            }

        if self.p.testnet:
            exchange_config["urls"] = {
                "api": {
                    "public": "https://api-testnet.bybit.com",
                    "private": "https://api-testnet.bybit.com",
                }
            }

        self.exchange = ccxt.bybit(exchange_config)
        self.symbol = self.p.symbol

        # For backtest mode
        if self.p.backtest:
            self._load_historical_data()
        else:
            self.live = True

    def _load_historical_data(self):
        """Load historical data for backtesting"""
        since = None
        if self.p.fromdate:
            since = int(self.p.fromdate.timestamp() * 1000)

        limit = 1000
        all_ohlcv = []

        print(f"Loading historical data for {self.symbol}...")

        while True:
            ohlcv = self.exchange.fetch_ohlcv(
                self.symbol, timeframe=self.p.ccxt_timeframe, since=since, limit=limit
            )

            if not ohlcv:
                break

            all_ohlcv.extend(ohlcv)

            if len(ohlcv) < limit:
                break

            since = ohlcv[-1][0] + 1

        self.historical_data = all_ohlcv
        self.historical_index = 0
        print(f"Loaded {len(self.historical_data)} candles")

    def _load(self):
        if self.p.backtest:
            return self._load_historical()
        else:
            return self._load_live()

    def _load_historical(self):
        """Load next bar from historical data"""
        if self.historical_index >= len(self.historical_data):
            return False

        ohlcv = self.historical_data[self.historical_index]
        self.historical_index += 1

        # ohlcv format: [timestamp, open, high, low, close, volume]
        self.lines.datetime[0] = bt.date2num(
            datetime.datetime.fromtimestamp(ohlcv[0] / 1000)
        )
        self.lines.open[0] = ohlcv[1]
        self.lines.high[0] = ohlcv[2]
        self.lines.low[0] = ohlcv[3]
        self.lines.close[0] = ohlcv[4]
        self.lines.volume[0] = ohlcv[5]
        self.lines.openinterest[0] = 0

        return True

    def _load_live(self):
        """Load next bar from live data"""
        try:
            # Fetch latest OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(
                self.symbol, timeframe=self.p.ccxt_timeframe, limit=1
            )

            if not ohlcv:
                return None

            bar = ohlcv[-1]

            # ohlcv format: [timestamp, open, high, low, close, volume]
            self.lines.datetime[0] = bt.date2num(
                datetime.datetime.fromtimestamp(bar[0] / 1000)
            )
            self.lines.open[0] = bar[1]
            self.lines.high[0] = bar[2]
            self.lines.low[0] = bar[3]
            self.lines.close[0] = bar[4]
            self.lines.volume[0] = bar[5]
            self.lines.openinterest[0] = 0

            return True

        except Exception as e:
            print(f"Error loading live data: {e}")
            return None


class CCXTBybitBroker(bt.BrokerBase):
    """
    CCXT Bybit Broker

    This broker connects to Bybit exchange using CCXT library
    and executes orders on the exchange.

    Supports both paper trading (simulation) and live trading modes.
    """

    params = (
        ("apikey", ""),
        ("secret", ""),
        ("testnet", True),
        ("paper_trading", True),  # If True, simulate orders without sending to exchange
        ("proxy", None),
        ("base_currency", "USDT"),  # Base currency for calculating portfolio value
    )

    def __init__(self):
        super(CCXTBybitBroker, self).__init__()

        try:
            import ccxt
        except ImportError:
            raise Exception("CCXT library required. Install with: pip install ccxt")

        # Initialize Bybit exchange
        exchange_config = {
            "apiKey": self.p.apikey,
            "secret": self.p.secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
            },
        }

        if self.p.proxy:
            exchange_config["proxies"] = {
                "http": self.p.proxy,
                "https": self.p.proxy,
            }

        if self.p.testnet:
            exchange_config["urls"] = {
                "api": {
                    "public": "https://api-testnet.bybit.com",
                    "private": "https://api-testnet.bybit.com",
                }
            }

        self.exchange = ccxt.bybit(exchange_config)

        # Paper trading state
        self.paper_cash = 10000.0  # Initial cash for paper trading
        self.paper_positions = {}  # {symbol: {'size': float, 'price': float}}
        self.paper_orders = {}  # {order_id: order_info}
        self.order_counter = 0

        # Order tracking
        self.open_orders = {}  # {bt_order: ccxt_order_id}

        print(
            f"CCXTBybitBroker initialized: paper_trading={self.p.paper_trading}, testnet={self.p.testnet}"
        )

    def getcash(self):
        """Get available cash"""
        if self.p.paper_trading:
            return self.paper_cash

        try:
            balance = self.exchange.fetch_balance()
            return balance[self.p.base_currency]["free"]
        except Exception as e:
            print(f"Error fetching cash: {e}")
            return 0.0

    def getvalue(self, datas=None):
        """Get total portfolio value (datas parameter for compatibility)"""
        _ = datas  # unused, kept for API compatibility

        if self.p.paper_trading:
            # Calculate paper trading portfolio value
            total_value = self.paper_cash
            for symbol, position in self.paper_positions.items():
                total_value += position["size"] * position["price"]
            return total_value

        try:
            balance = self.exchange.fetch_balance()
            return balance["total"][self.p.base_currency]
        except Exception as e:
            print(f"Error fetching portfolio value: {e}")
            return self.getcash()

    def getposition(self, data, clone=True):
        """Get position for a data feed (clone parameter for compatibility)"""
        _ = clone  # unused, kept for API compatibility

        symbol = data._name if hasattr(data, "_name") else "BTC/USDT"

        if self.p.paper_trading:
            pos_data = self.paper_positions.get(symbol, {"size": 0, "price": 0})
            # Create a position object
            pos = bt.Position(pos_data["size"], pos_data["price"])
            return pos

        try:
            # Fetch position from exchange
            positions = self.exchange.fetch_positions([symbol])
            if positions:
                pos_info = positions[0]
                size = float(pos_info.get("contracts", 0))
                price = float(pos_info.get("entryPrice", 0))
                return bt.Position(size, price)
            return bt.Position(0, 0)
        except Exception as e:
            print(f"Error fetching position: {e}")
            return bt.Position(0, 0)

    def submit(self, order):
        """Submit an order"""
        # Get data and symbol
        data = order.data
        symbol = data._name if hasattr(data, "_name") else self.p.symbol

        # Determine order side
        side = "buy" if order.isbuy() else "sell"

        # Get order size
        size = abs(order.created.size)

        # Get order price (if limit order)
        price = order.created.price if order.exectype == bt.Order.Limit else None

        if self.p.paper_trading:
            # Paper trading: simulate order execution
            self.order_counter += 1
            order_id = f"paper_{self.order_counter}"

            # Store order info
            current_price = data.close[0]
            execution_price = price if price else current_price

            self.paper_orders[order_id] = {
                "id": order_id,
                "symbol": symbol,
                "side": side,
                "size": size,
                "price": execution_price,
                "order": order,
                "status": "open",
            }

            self.open_orders[order] = order_id

            # Immediately execute market orders in paper trading
            if order.exectype in [bt.Order.Market, None]:
                self._execute_paper_order(order_id, current_price)

            order.submit()
            self.notify(order)

        else:
            # Live trading: send order to exchange
            try:
                order_type = "market"
                if order.exectype == bt.Order.Limit:
                    order_type = "limit"
                elif order.exectype == bt.Order.Stop:
                    order_type = "stop"

                # Create order on exchange
                ccxt_order = self.exchange.create_order(
                    symbol=symbol,
                    type=order_type,
                    side=side,
                    amount=size,
                    price=price,
                )

                # Track the order
                self.open_orders[order] = ccxt_order["id"]

                order.submit()
                self.notify(order)

                print(
                    f"Order submitted to exchange: {ccxt_order['id']} - {side} {size} {symbol} @ {price}"
                )

            except Exception as e:
                print(f"Error submitting order: {e}")
                order.reject()
                self.notify(order)

        return order

    def _execute_paper_order(self, order_id, price=None):
        """Execute a paper trading order"""
        if order_id not in self.paper_orders:
            return

        order_info = self.paper_orders[order_id]
        order = order_info["order"]
        symbol = order_info["symbol"]
        side = order_info["side"]
        size = order_info["size"]
        exec_price = price if price else order_info["price"]

        # Update paper trading state
        if side == "buy":
            cost = size * exec_price
            if cost > self.paper_cash:
                # Insufficient cash
                order.margin()
                self.notify(order)
                del self.paper_orders[order_id]
                if order in self.open_orders:
                    del self.open_orders[order]
                return

            self.paper_cash -= cost

            # Update position
            if symbol not in self.paper_positions:
                self.paper_positions[symbol] = {"size": 0, "price": 0}

            pos = self.paper_positions[symbol]
            total_size = pos["size"] + size
            if total_size > 0:
                pos["price"] = (
                    pos["size"] * pos["price"] + size * exec_price
                ) / total_size
            pos["size"] = total_size

        else:  # sell
            if (
                symbol not in self.paper_positions
                or self.paper_positions[symbol]["size"] < size
            ):
                # Insufficient position
                order.margin()
                self.notify(order)
                del self.paper_orders[order_id]
                if order in self.open_orders:
                    del self.open_orders[order]
                return

            proceeds = size * exec_price
            self.paper_cash += proceeds

            # Update position
            pos = self.paper_positions[symbol]
            pos["size"] -= size
            if pos["size"] <= 0:
                del self.paper_positions[symbol]

        # Mark order as completed
        order.execute(
            dt=order.data.datetime[0],
            size=size if side == "buy" else -size,
            price=exec_price,
            closed=0,
            closedvalue=0,
            closedcomm=0,
            opened=size,
            openedvalue=size * exec_price,
            openedcomm=0,
            margin=0,
            pnl=0,
            psize=0,
            pprice=0,
        )

        order_info["status"] = "closed"
        self.notify(order)

        # Clean up
        del self.paper_orders[order_id]
        if order in self.open_orders:
            del self.open_orders[order]

    def cancel(self, order):
        """Cancel an order"""
        if order not in self.open_orders:
            return

        order_id = self.open_orders[order]

        if self.p.paper_trading:
            # Paper trading: just remove the order
            if order_id in self.paper_orders:
                del self.paper_orders[order_id]
            order.cancel()
            self.notify(order)
        else:
            # Live trading: cancel on exchange
            try:
                symbol = (
                    order.data._name if hasattr(order.data, "_name") else self.p.symbol
                )
                self.exchange.cancel_order(order_id, symbol)
                order.cancel()
                self.notify(order)
                print(f"Order cancelled: {order_id}")
            except Exception as e:
                print(f"Error cancelling order: {e}")

        if order in self.open_orders:
            del self.open_orders[order]

    def get_order_status(self, order):
        """Check order status on exchange"""
        if order not in self.open_orders:
            return None

        order_id = self.open_orders[order]

        if self.p.paper_trading:
            # Paper trading: check internal state
            if order_id in self.paper_orders:
                return self.paper_orders[order_id]["status"]
            return "closed"

        try:
            symbol = order.data._name if hasattr(order.data, "_name") else self.p.symbol
            ccxt_order = self.exchange.fetch_order(order_id, symbol)
            return ccxt_order["status"]
        except Exception as e:
            print(f"Error fetching order status: {e}")
            return None


def runstrat(args=None):
    args = parse_args(args)

    cerebro = bt.Cerebro()

    # Add strategy
    cerebro.addstrategy(
        SMACrossStrategy,
        fast_period=args.fast_period,
        slow_period=args.slow_period,
        order_size=args.order_size,
        printlog=args.verbose,
    )

    # Add data feed
    if args.backtest:
        # Backtest mode - use historical data
        fromdate = (
            datetime.datetime.strptime(args.fromdate, "%Y-%m-%d")
            if args.fromdate
            else None
        )
        todate = (
            datetime.datetime.strptime(args.todate, "%Y-%m-%d") if args.todate else None
        )

        # Map timeframe string to backtrader TimeFrame
        timeframe_map = {
            "1m": (bt.TimeFrame.Minutes, 1),
            "5m": (bt.TimeFrame.Minutes, 5),
            "15m": (bt.TimeFrame.Minutes, 15),
            "30m": (bt.TimeFrame.Minutes, 30),
            "1h": (bt.TimeFrame.Minutes, 60),
            "4h": (bt.TimeFrame.Minutes, 240),
            "1d": (bt.TimeFrame.Days, 1),
        }

        tf, comp = timeframe_map.get(args.timeframe, (bt.TimeFrame.Minutes, 1))

        data = CCXTBybitData(
            symbol=args.symbol,
            timeframe=tf,
            compression=comp,
            ccxt_timeframe=args.timeframe,
            backtest=True,
            fromdate=fromdate,
            todate=todate,
            testnet=args.testnet,
            proxy=args.proxy,
        )
    else:
        # Live trading mode
        if not args.apikey or not args.secret:
            print("Error: API key and secret required for live trading")
            print("Use --apikey and --secret arguments")
            return

        # Map timeframe string to backtrader TimeFrame
        timeframe_map = {
            "1m": (bt.TimeFrame.Minutes, 1),
            "5m": (bt.TimeFrame.Minutes, 5),
            "15m": (bt.TimeFrame.Minutes, 15),
            "30m": (bt.TimeFrame.Minutes, 30),
            "1h": (bt.TimeFrame.Minutes, 60),
            "4h": (bt.TimeFrame.Minutes, 240),
            "1d": (bt.TimeFrame.Days, 1),
        }

        tf, comp = timeframe_map.get(args.timeframe, (bt.TimeFrame.Minutes, 1))

        data = CCXTBybitData(
            apikey=args.apikey,
            secret=args.secret,
            symbol=args.symbol,
            timeframe=tf,
            compression=comp,
            ccxt_timeframe=args.timeframe,
            testnet=args.testnet,
            backtest=False,
            proxy=args.proxy,
        )

    # Set data name for broker to identify symbol
    data._name = args.symbol

    cerebro.adddata(data)

    # Set up broker
    if args.backtest:
        # Backtest mode: use default BackBroker
        cerebro.broker.setcash(args.cash)
        cerebro.broker.setcommission(commission=args.commission)
    else:
        # Live/Paper trading mode: use CCXTBybitBroker
        if args.paper_trading:
            print("Using Paper Trading Mode (simulated orders)")
        else:
            print(
                "WARNING: Using LIVE TRADING Mode - real orders will be sent to exchange!"
            )

        broker = CCXTBybitBroker(
            apikey=args.apikey,
            secret=args.secret,
            testnet=args.testnet,
            paper_trading=args.paper_trading,
            proxy=args.proxy,
        )
        broker.paper_cash = args.cash
        cerebro.setbroker(broker)

    # Print starting conditions
    print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())

    # Run strategy
    cerebro.run()

    # Print final conditions
    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    # Plot if requested
    if args.plot:
        cerebro.plot()


def parse_args(pargs=None):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Bybit Live Trading with CCXT and Backtrader",
    )

    # Exchange settings
    parser.add_argument("--apikey", default="", help="Bybit API Key")

    parser.add_argument("--secret", default="", help="Bybit API Secret")

    parser.add_argument("--symbol", default="BTC/USDT", help="Trading pair symbol")

    parser.add_argument(
        "--timeframe",
        default="1m",
        choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
        help="Timeframe for OHLCV data",
    )

    parser.add_argument(
        "--testnet", action="store_true", help="Use Bybit testnet (paper trading)"
    )

    parser.add_argument(
        "--live", action="store_true", help="Enable live trading (use with caution!)"
    )

    parser.add_argument(
        "--paper-trading",
        action="store_true",
        default=True,
        help="Use paper trading (simulated orders, default). Use --no-paper-trading for real orders",
    )

    parser.add_argument(
        "--no-paper-trading",
        dest="paper_trading",
        action="store_false",
        help="Disable paper trading - send REAL orders to exchange",
    )

    # Backtest settings
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run in backtest mode with historical data",
    )

    parser.add_argument(
        "--fromdate",
        default="2024-01-01",
        help="Starting date for backtest (YYYY-MM-DD)",
    )

    parser.add_argument(
        "--todate", default=None, help="Ending date for backtest (YYYY-MM-DD)"
    )

    # Strategy parameters
    parser.add_argument(
        "--fast-period", type=int, default=10, help="Fast moving average period"
    )

    parser.add_argument(
        "--slow-period", type=int, default=30, help="Slow moving average period"
    )

    parser.add_argument(
        "--order-size", type=float, default=0.01, help="Order size in base currency"
    )

    # Broker settings
    parser.add_argument("--cash", type=float, default=10000.0, help="Starting cash")

    parser.add_argument(
        "--commission",
        type=float,
        default=0.001,
        help="Commission rate (0.001 = 0.1 percent)",
    )

    # Output settings
    parser.add_argument("--verbose", action="store_true", help="Print detailed logs")

    parser.add_argument("--plot", action="store_true", help="Plot the results")

    parser.add_argument("--proxy", help="Proxy URL (e.g., http://127.0.0.1:7890)")

    return parser.parse_args(pargs)


if __name__ == "__main__":
    runstrat()
