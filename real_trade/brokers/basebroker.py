#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Base Broker - 通用的 Broker 基类

提供模拟交易和实盘交易的通用逻辑。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
from typing import Any, Dict, Optional

import backtrader as bt


class BaseBroker(bt.BrokerBase):
    """
    Broker 基类

    提供模拟交易和实盘交易的通用实现。
    """

    params = (
        ("paper_trading", True),
        ("base_currency", "USDT"),
        ("cash", 10000.0),
    )

    def __init__(self, store, **kwargs):
        super(BaseBroker, self).__init__()

        # 应用 kwargs 到 params（paper_trading, cash 等）
        for key, value in kwargs.items():
            if hasattr(self.params, key):
                setattr(self.params, key, value)

        self.store = store
        self.exchange = store.exchange

        # 模拟交易状态
        self.paper_cash = self.params.cash
        self.startingcash = self.params.cash  # Backtrader 报告需要
        self.paper_positions: Dict[str, Dict[str, float]] = {}
        self.paper_orders: Dict[str, Dict[str, Any]] = {}
        self.order_counter = 0

        # 订单跟踪 - 使用 order.ref 作为键
        self.open_orders: Dict[int, str] = {}  # {order.ref: exchange_order_id}

        # 订单通知队列
        self.notifs = collections.deque()

        # 佣金信息 - 使用默认佣金
        self.comminfo = {}

        mode = "Paper Trading" if self.params.paper_trading else "Live Trading"
        print(
            f"[Broker] {self.__class__.__name__} initialized: mode={mode}, cash={self.params.cash}"
        )

    def getcash(self) -> float:
        """获取可用资金"""
        if self.params.paper_trading:
            return self.paper_cash

        try:
            return self.store.get_balance(self.params.base_currency)
        except Exception as e:
            print(f"[Broker] Error fetching cash: {e}")
            return 0.0

    def setcash(self, cash: float):
        """设置初始资金"""
        self.paper_cash = cash
        self.startingcash = cash

    def getvalue(self, datas=None) -> float:
        """获取账户总价值"""
        _ = datas

        if self.params.paper_trading:
            total_value = self.paper_cash
            for symbol, position in self.paper_positions.items():
                total_value += position["size"] * position["price"]
            return total_value

        try:
            return self.store.get_total_value(self.params.base_currency)
        except Exception as e:
            print(f"[Broker] Error fetching portfolio value: {e}")
            return self.getcash()

    def getposition(self, data, clone=True) -> bt.Position:
        """获取持仓"""
        _ = clone

        symbol = data._name if hasattr(data, "_name") else "BTC/USDT"

        if self.params.paper_trading:
            pos_data = self.paper_positions.get(symbol, {"size": 0, "price": 0})
            return bt.Position(pos_data["size"], pos_data["price"])

        try:
            positions = self.store.get_positions([symbol])
            if positions:
                pos_info = positions[0]
                size = float(pos_info.get("contracts", 0))
                price = float(pos_info.get("entryPrice", 0))
                return bt.Position(size, price)
            return bt.Position(0, 0)
        except Exception as e:
            print(f"[Broker] Error fetching position: {e}")
            return bt.Position(0, 0)

    def buy(
        self,
        owner,
        data,
        size,
        price=None,
        plimit=None,
        exectype=None,
        valid=None,
        tradeid=0,
        oco=None,
        trailamount=None,
        trailpercent=None,
        parent=None,
        transmit=True,
        **kwargs,
    ):
        """创建买单"""
        order = bt.BuyOrder(
            owner=owner,
            data=data,
            size=size,
            price=price,
            pricelimit=plimit,
            exectype=exectype,
            valid=valid,
            tradeid=tradeid,
            oco=oco,
            trailamount=trailamount,
            trailpercent=trailpercent,
            parent=parent,
            transmit=transmit,
        )

        return self.submit(order)

    def sell(
        self,
        owner,
        data,
        size,
        price=None,
        plimit=None,
        exectype=None,
        valid=None,
        tradeid=0,
        oco=None,
        trailamount=None,
        trailpercent=None,
        parent=None,
        transmit=True,
        **kwargs,
    ):
        """创建卖单"""
        order = bt.SellOrder(
            owner=owner,
            data=data,
            size=size,
            price=price,
            pricelimit=plimit,
            exectype=exectype,
            valid=valid,
            tradeid=tradeid,
            oco=oco,
            trailamount=trailamount,
            trailpercent=trailpercent,
            parent=parent,
            transmit=transmit,
        )

        return self.submit(order)

    def submit(self, order) -> Any:
        """提交订单"""
        data = order.data
        symbol = data._name if hasattr(data, "_name") else "BTC/USDT"

        # 设置订单的佣金信息
        order.addcomminfo(self.getcommissioninfo(data))

        side = "buy" if order.isbuy() else "sell"
        size = abs(order.created.size)
        price = order.created.price if order.exectype == bt.Order.Limit else None

        if self.params.paper_trading:
            self._submit_paper_order(order, symbol, side, size, price)
        else:
            self._submit_live_order(order, symbol, side, size, price)

        return order

    def _submit_paper_order(
        self, order, symbol: str, side: str, size: float, price: Optional[float]
    ):
        """提交模拟订单"""
        self.order_counter += 1
        order_id = f"paper_{self.order_counter}"

        current_price = order.data.close[0]
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

        self.open_orders[order.ref] = order_id

        if order.exectype in [bt.Order.Market, None]:
            self._execute_paper_order(order_id, current_price)

        order.submit()
        self.notify(order)

    def _submit_live_order(
        self, order, symbol: str, side: str, size: float, price: Optional[float]
    ):
        """提交实盘订单"""
        try:
            order_type = "market"
            if order.exectype == bt.Order.Limit:
                order_type = "limit"
            elif order.exectype == bt.Order.Stop:
                order_type = "stop"

            ccxt_order = self.exchange.create_order(
                symbol=symbol, type=order_type, side=side, amount=size, price=price
            )

            self.open_orders[order.ref] = ccxt_order["id"]
            order.submit()
            self.notify(order)

            print(
                f"[Broker] Order submitted: {ccxt_order['id']} - {side} {size} {symbol} @ {price or 'market'}"
            )

        except Exception as e:
            print(f"[Broker] Error submitting order: {e}")
            order.reject()
            self.notify(order)

    def _execute_paper_order(self, order_id: str, price: Optional[float] = None):
        """执行模拟订单"""
        if order_id not in self.paper_orders:
            return

        order_info = self.paper_orders[order_id]
        order = order_info["order"]
        symbol = order_info["symbol"]
        side = order_info["side"]
        size = order_info["size"]
        exec_price = price if price else order_info["price"]

        if side == "buy":
            cost = size * exec_price
            if cost > self.paper_cash:
                order.margin()
                self.notify(order)
                del self.paper_orders[order_id]
                if order.ref in self.open_orders:
                    del self.open_orders[order.ref]
                return

            self.paper_cash -= cost

            if symbol not in self.paper_positions:
                self.paper_positions[symbol] = {"size": 0, "price": 0}

            pos = self.paper_positions[symbol]
            total_size = pos["size"] + size
            if total_size > 0:
                pos["price"] = (
                    pos["size"] * pos["price"] + size * exec_price
                ) / total_size
            pos["size"] = total_size

        else:
            if (
                symbol not in self.paper_positions
                or self.paper_positions[symbol]["size"] < size
            ):
                order.margin()
                self.notify(order)
                del self.paper_orders[order_id]
                if order.ref in self.open_orders:
                    del self.open_orders[order.ref]
                return

            proceeds = size * exec_price
            self.paper_cash += proceeds

            pos = self.paper_positions[symbol]
            pos["size"] -= size
            if pos["size"] <= 0:
                del self.paper_positions[symbol]

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

        del self.paper_orders[order_id]
        if order.ref in self.open_orders:
            del self.open_orders[order.ref]

    def cancel(self, order):
        """取消订单"""
        if order.ref not in self.open_orders:
            return

        order_id = self.open_orders[order.ref]

        if self.params.paper_trading:
            if order_id in self.paper_orders:
                del self.paper_orders[order_id]
            order.cancel()
            self.notify(order)
        else:
            try:
                symbol = (
                    order.data._name if hasattr(order.data, "_name") else "BTC/USDT"
                )
                self.exchange.cancel_order(order_id, symbol)
                order.cancel()
                self.notify(order)
                print(f"[Broker] Order cancelled: {order_id}")
            except Exception as e:
                print(f"[Broker] Error cancelling order: {e}")

        if order.ref in self.open_orders:
            del self.open_orders[order.ref]

    def get_paper_summary(self) -> Dict[str, Any]:
        """获取模拟交易摘要"""
        if not self.params.paper_trading:
            return {}

        return {
            "cash": self.paper_cash,
            "positions": self.paper_positions.copy(),
            "total_value": self.getvalue(),
            "open_orders": len(self.paper_orders),
        }

    def notify(self, order):
        """将订单通知添加到通知队列"""
        self.notifs.append(order.clone())

    def get_notification(self):
        """获取下一个订单通知"""
        try:
            return self.notifs.popleft()
        except IndexError:
            return None

    def getcommissioninfo(self, data):
        """获取佣金信息"""
        # 首先尝试查找特定于 data 的佣金信息
        if data in self.comminfo:
            return self.comminfo[data]

        # 然后尝试查找默认佣金信息（None 键）
        if None in self.comminfo:
            return self.comminfo[None]

        # 如果都没有设置，创建并使用默认的 CommissionInfo
        comm = bt.CommInfoBase(commission=0.001, mult=1.0, margin=None)
        self.comminfo[None] = comm
        return comm

    def addcommissioninfo(self, comminfo, name=None):
        """添加佣金信息"""
        if name is not None:
            self.comminfo[name] = comminfo
        else:
            self.comminfo[None] = comminfo

    def setcommission(
        self,
        commission=0.0,
        margin=None,
        mult=1.0,
        commtype=None,
        percabs=True,
        stocklike=False,
        interest=0.0,
        interest_long=False,
        leverage=1.0,
        automargin=False,
        name=None,
    ):
        """设置佣金"""
        comm = bt.CommInfoBase(
            commission=commission,
            mult=mult,
            margin=margin,
            commtype=commtype,
            stocklike=stocklike,
            percabs=percabs,
            interest=interest,
            interest_long=interest_long,
            leverage=leverage,
            automargin=automargin,
        )
        self.addcommissioninfo(comm, name=name)

    def __repr__(self):
        mode = "Paper" if self.params.paper_trading else "Live"
        return f"{self.__class__.__name__}(mode={mode}, cash={self.getcash():.2f})"
