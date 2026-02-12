#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Binance Broker Implementation
Based on IBBroker design pattern
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import threading
from collections import defaultdict

from backtrader import BrokerBase, Order, Position
from backtrader.comminfo import CommInfoBase
from backtrader.utils.py3 import with_metaclass


class MetaBinanceBroker(BrokerBase.__class__):
    def __init__(cls, name, bases, dct):
        """Class has already been created ... register"""
        # Initialize the class
        super(MetaBinanceBroker, cls).__init__(name, bases, dct)
        # Register the class in the store
        from ..stores.binance import BinanceStore

        BinanceStore.BrokerCls = cls


class BinanceBroker(with_metaclass(MetaBinanceBroker, BrokerBase)):
    """
    Binance Broker实现（参考IBBroker设计模式）

    此类将Binance的订单/持仓映射到backtrader的内部API

    注意事项：
      - tradeid不被真正支持，因为利润和亏损直接从Binance获取
      - 由于Binance按FIFO方式计算，tradeid的盈亏不准确
      - 如果在操作开始时资产有未平仓头寸，或通过其他方式下达的订单改变了头寸，
        在cerebro中计算的交易将不能反映现实情况
    """

    params = (
        ("paper_trading", True),  # 是否模拟交易
        ("testnet", True),  # 是否测试网
        ("commission", 0.001),  # 交易手续费率 (0.1%)
        ("margin", None),  # 保证金要求
        ("slippage", 0.0),  # 滑点
        ("fill_strategy", "partial"),  # 成交策略: partial, full
        ("_debug", False),  # 调试模式
    )

    def __init__(self, store):
        super(BinanceBroker, self).__init__()

        self.store = store
        self.startingcash = self.cash = 0.0
        self.startingvalue = self.value = 0.0

        # 订单和执行管理
        self._lock_orders = threading.Lock()  # 控制访问
        self.orderbyid = dict()  # 按订单ID存储订单
        self.executions = dict()  # 已通知的执行
        self.ordstatus = defaultdict(dict)
        self.notifs = collections.deque()  # 存储被通知的订单
        self.tonotify = collections.deque()  # 存储待通知的订单ID

        # 位置管理
        self.positions = collections.defaultdict(Position)

    def start(self):
        super(BinanceBroker, self).start()

        # 初始化账户信息
        if self.store.is_connected:
            try:
                balance = self.store.get_balance()
                # 假设主要使用USDT作为计价货币
                self.startingcash = self.cash = balance.get("USDT", 0.0)
                self.startingvalue = self.value = self._get_account_value()
                if self.p._debug:
                    print(f"BinanceBroker: 账户初始化完成，现金: {self.cash}")
            except Exception as e:
                if self.p._debug:
                    print(f"BinanceBroker: 账户初始化失败 - {e}")
                self.startingcash = self.cash = 0.0
                self.startingvalue = self.value = 0.0
        else:
            self.startingcash = self.cash = 0.0
            self.startingvalue = self.value = 0.0

    def stop(self):
        super(BinanceBroker, self).stop()
        # 清理资源
        self.orderbyid.clear()
        self.executions.clear()
        self.ordstatus.clear()
        self.positions.clear()

    def getcash(self):
        # 从Binance获取实时现金余额
        try:
            balance = self.store.get_balance()
            self.cash = balance.get("USDT", 0.0)
        except Exception as e:
            if self.p._debug:
                print(f"BinanceBroker: 获取现金余额失败 - {e}")
        return self.cash

    def getvalue(self, datas=None):
        # 获取账户总价值
        self.value = self._get_account_value(datas)
        return self.value

    def _get_account_value(self, datas=None):
        """计算账户总价值"""
        try:
            total_value = self.getcash()

            # 添加持仓价值
            if datas:
                # 如果指定了数据源，只计算相关持仓
                for data in datas:
                    position = self.getposition(data, clone=False)
                    if position.size != 0:
                        total_value += position.size * data.close[0]
            else:
                # 计算所有持仓价值
                balance = self.store.get_balance()
                # 这里简化处理，实际应该获取所有资产的实时价值
                for currency, amount in balance.items():
                    if currency != "USDT" and amount > 0:
                        # 需要获取对应交易对的价格来计算价值
                        pass

            return total_value
        except Exception as e:
            if self.p._debug:
                print(f"BinanceBroker: 计算账户价值失败 - {e}")
            return self.cash

    def getposition(self, data, clone=True):
        """获取指定数据的持仓"""
        # 使用交易对符号作为键
        symbol = getattr(data, "_symbol", data._name)
        pos = self.positions[symbol]
        return pos.clone() if clone else pos

    def submit(self, order, chksubmit=True):
        """提交订单"""
        with self._lock_orders:
            # 检查是否应该提交订单
            if chksubmit and not self._submit_validation(order):
                return order

            # 设置订单初始状态
            order.submit(self)

            # 分配订单ID
            order._brokerid = self.store.nextReqId()

            # 存储订单引用
            self.orderbyid[order._brokerid] = order

            # 添加到通知队列
            self.notifs.append(order)

            if self.p._debug:
                print(f"BinanceBroker: 订单已提交 - {order._brokerid}")

        return order

    def _submit_validation(self, order):
        """验证订单是否可以提交"""
        # 基本验证
        if order.exectype not in [
            Order.Market,
            Order.Limit,
            Order.Stop,
            Order.StopLimit,
        ]:
            return False

        # 资金验证（如果是实盘交易）
        if not self.p.paper_trading:
            required_cash = self._get_required_cash(order)
            if required_cash > self.cash:
                if self.p._debug:
                    print(
                        f"BinanceBroker: 资金不足，需要: {required_cash}, 可用: {self.cash}"
                    )
                return False

        return True

    def _get_required_cash(self, order):
        """计算订单所需资金"""
        if order.isbuy():
            if order.exectype == Order.Market:
                price = order.data.close[0]
            else:
                price = order.price
            return order.size * price * (1 + self.p.commission)
        else:
            # 卖出订单不需要额外资金
            return 0.0

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
        **kwargs,
    ):
        """买入订单"""
        order = BuyOrder(
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
            **kwargs,
        )

        order.addinfo(**kwargs)
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
        **kwargs,
    ):
        """卖出订单"""
        order = SellOrder(
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
            **kwargs,
        )

        order.addinfo(**kwargs)
        return self.submit(order)

    def cancel(self, order):
        """取消订单"""
        with self._lock_orders:
            if order._brokerid not in self.orderbyid:
                return False  # 订单不存在

            try:
                # 调用Binance API取消订单
                if not self.p.paper_trading:
                    result = self.store.cancel_order(
                        order._brokerid,
                        getattr(order.data, "_symbol", order.data._name),
                    )
                    if not result:
                        return False

                # 更新订单状态
                order.cancel()
                self.notifs.append(order)

                # 从跟踪中移除
                del self.orderbyid[order._brokerid]

                if self.p._debug:
                    print(f"BinanceBroker: 订单已取消 - {order._brokerid}")
                return True

            except Exception as e:
                if self.p._debug:
                    print(f"BinanceBroker: 取消订单失败 - {e}")
                return False

    def notify(self, order):
        """通知订单状态变化"""
        with self._lock_orders:
            self.notifs.append(order)

    def get_notification(self):
        """获取下一个通知"""
        try:
            return self.notifs.popleft()
        except IndexError:
            return None

    def next(self):
        """每周期检查订单状态"""
        # 处理待通知的订单
        with self._lock_orders:
            while self.tonotify:
                oid = self.tonotify.popleft()
                if oid in self.orderbyid:
                    order = self.orderbyid[oid]
                    self.notify(order)

    # 佣金信息设置
    def setcommission(
        self,
        commission=0.001,
        margin=None,
        mult=1.0,
        percabs=True,
        stocklike=False,
        interest=0.0,
        interest_long=False,
        **kwargs,
    ):
        """设置佣金信息"""
        # 使用默认的佣金信息类
        comminfo = CommInfoBase(
            commission=commission,
            margin=margin,
            mult=mult,
            percabs=percabs,
            stocklike=stocklike,
            interest=interest,
            interest_long=interest_long,
            **kwargs,
        )

        # 为所有数据设置佣金信息
        for data in self.cerebro.datas:
            self.comminfo[data] = comminfo


# 订单类定义
class BinanceOrder(Order):
    """Binance订单基类"""

    def __str__(self):
        basetxt = super(BinanceOrder, self).__str__()
        tojoin = [basetxt]
        tojoin.append("Binance Ref: {}".format(self.ref))
        tojoin.append("Binance orderId: {}".format(getattr(self, "_brokerid", "N/A")))
        return "\n".join(tojoin)


class BuyOrder(BinanceOrder):
    ordtype = Order.Buy


class SellOrder(BinanceOrder):
    ordtype = Order.Sell
