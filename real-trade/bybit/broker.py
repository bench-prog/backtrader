#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Bybit Broker - 交易所 Broker 实现

支持模拟交易和实盘交易两种模式。
提供完整的订单管理、持仓管理和资金管理功能。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from typing import Optional, Dict, Any
import backtrader as bt

from .store import BybitStore


class BybitBroker(bt.BrokerBase):
    """
    Bybit 交易所 Broker

    功能:
    - 模拟交易模式（Paper Trading）
    - 实盘交易模式（Live Trading）
    - 订单管理（提交、取消、查询）
    - 持仓管理
    - 资金管理
    - 支持多种订单类型（市价、限价、止损）
    """

    params = (
        ("paper_trading", True),  # 是否为模拟交易
        ("base_currency", "USDT"),  # 计价币种
        ("cash", 10000.0),  # 初始资金（模拟交易用）
    )

    def __init__(self, store: BybitStore):
        """
        初始化 Broker

        Args:
            store: BybitStore 实例
        """
        super(BybitBroker, self).__init__()

        self.store = store
        self.exchange = store.exchange

        # 模拟交易状态
        self.paper_cash = self.params.cash
        self.paper_positions: Dict[str, Dict[str, float]] = {}
        self.paper_orders: Dict[str, Dict[str, Any]] = {}
        self.order_counter = 0

        # 订单跟踪
        self.open_orders: Dict[Any, str] = {}

        mode = "Paper Trading" if self.params.paper_trading else "Live Trading"
        print(f"BybitBroker initialized: mode={mode}, initial_cash={self.params.cash}")

    def getcash(self) -> float:
        """
        获取可用资金

        Returns:
            可用现金
        """
        if self.params.paper_trading:
            return self.paper_cash

        try:
            return self.store.get_balance(self.params.base_currency)
        except Exception as e:
            print(f"Error fetching cash: {e}")
            return 0.0

    def getvalue(self, datas=None) -> float:
        """
        获取账户总价值

        Args:
            datas: 数据源（兼容性参数）

        Returns:
            总价值
        """
        _ = datas  # unused

        if self.params.paper_trading:
            total_value = self.paper_cash
            # 加上所有持仓的价值
            for symbol, position in self.paper_positions.items():
                total_value += position["size"] * position["price"]
            return total_value

        try:
            return self.store.get_total_value(self.params.base_currency)
        except Exception as e:
            print(f"Error fetching portfolio value: {e}")
            return self.getcash()

    def getposition(self, data, clone=True) -> bt.Position:
        """
        获取持仓

        Args:
            data: 数据源
            clone: 兼容性参数

        Returns:
            持仓对象
        """
        _ = clone  # unused

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
            print(f"Error fetching position: {e}")
            return bt.Position(0, 0)

    def submit(self, order) -> Any:
        """
        提交订单

        Args:
            order: Backtrader 订单对象

        Returns:
            订单对象
        """
        data = order.data
        symbol = data._name if hasattr(data, "_name") else "BTC/USDT"

        side = "buy" if order.isbuy() else "sell"
        size = abs(order.created.size)
        price = order.created.price if order.exectype == bt.Order.Limit else None

        if self.params.paper_trading:
            # 模拟交易
            self._submit_paper_order(order, symbol, side, size, price)
        else:
            # 实盘交易
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

        self.open_orders[order] = order_id

        # 市价单立即执行
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
                symbol=symbol,
                type=order_type,
                side=side,
                amount=size,
                price=price,
            )

            self.open_orders[order] = ccxt_order["id"]
            order.submit()
            self.notify(order)

            print(
                f"✓ Order submitted: {ccxt_order['id']} - {side} {size} {symbol} @ {price or 'market'}"
            )

        except Exception as e:
            print(f"✗ Error submitting order: {e}")
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

        # 买入
        if side == "buy":
            cost = size * exec_price
            if cost > self.paper_cash:
                order.margin()
                self.notify(order)
                del self.paper_orders[order_id]
                if order in self.open_orders:
                    del self.open_orders[order]
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

        # 卖出
        else:
            if (
                symbol not in self.paper_positions
                or self.paper_positions[symbol]["size"] < size
            ):
                order.margin()
                self.notify(order)
                del self.paper_orders[order_id]
                if order in self.open_orders:
                    del self.open_orders[order]
                return

            proceeds = size * exec_price
            self.paper_cash += proceeds

            pos = self.paper_positions[symbol]
            pos["size"] -= size
            if pos["size"] <= 0:
                del self.paper_positions[symbol]

        # 完成订单
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
        if order in self.open_orders:
            del self.open_orders[order]

    def cancel(self, order):
        """
        取消订单

        Args:
            order: 订单对象
        """
        if order not in self.open_orders:
            return

        order_id = self.open_orders[order]

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
                print(f"✓ Order cancelled: {order_id}")
            except Exception as e:
                print(f"✗ Error cancelling order: {e}")

        if order in self.open_orders:
            del self.open_orders[order]

    def get_order_status(self, order) -> Optional[str]:
        """
        查询订单状态

        Args:
            order: 订单对象

        Returns:
            订单状态
        """
        if order not in self.open_orders:
            return None

        order_id = self.open_orders[order]

        if self.params.paper_trading:
            if order_id in self.paper_orders:
                return self.paper_orders[order_id]["status"]
            return "closed"

        try:
            symbol = order.data._name if hasattr(order.data, "_name") else "BTC/USDT"
            ccxt_order = self.exchange.fetch_order(order_id, symbol)
            return ccxt_order["status"]
        except Exception as e:
            print(f"Error fetching order status: {e}")
            return None

    def get_paper_summary(self) -> Dict[str, Any]:
        """
        获取模拟交易摘要

        Returns:
            摘要信息字典
        """
        if not self.params.paper_trading:
            return {}

        return {
            "cash": self.paper_cash,
            "positions": self.paper_positions.copy(),
            "total_value": self.getvalue(),
            "open_orders": len(self.paper_orders),
        }

    def __repr__(self):
        mode = "Paper" if self.params.paper_trading else "Live"
        return f"BybitBroker(mode={mode}, cash={self.getcash():.2f}, value={self.getvalue():.2f})"
