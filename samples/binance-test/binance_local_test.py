#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Binance本地数据回测示例
使用本地BTC数据进行回测，避免网络连接问题
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import datetime
import os


class BinanceLocalTest(bt.Strategy):
    """
    Binance本地数据测试策略
    使用本地BTC数据进行回测
    """
    
    params = (
        ('sma_period', 20),
        ('trade_size', 0.001),  # BTC交易数量
        ('printlog', True),
    )

    def __init__(self):
        # 添加简单移动平均线
        self.sma = bt.indicators.SMA(self.data, period=self.p.sma_period)
        
        # 订单和持仓变量
        self.order = None
        
        if self.p.printlog:
            print("🎯 Binance本地数据测试策略初始化完成")
            print(f"📊 参数: SMA周期={self.p.sma_period}, 交易数量={self.p.trade_size} BTC")

    def log(self, txt, dt=None):
        """日志函数"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.datetime(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/已接受，等待成交
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Size: %.6f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.size,
                     order.executed.value,
                     order.executed.comm))
            else:
                self.log('SELL EXECUTED, Price: %.2f, Size: %.6f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.size,
                          order.executed.value,
                          order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        """每个周期调用"""
        # 记录收盘价和SMA
        self.log('Close, %.2f, SMA, %.2f' % (self.data.close[0], self.sma[0]))

        # 检查是否有挂起的订单
        if self.order:
            return

        # 检查是否在市场中
        if not self.position:
            # SMA向上交叉时买入
            if self.data.close[0] > self.sma[0] and self.data.close[-1] <= self.sma[-1]:
                self.log('BUY CREATE, %.2f' % self.data.close[0])
                self.order = self.buy(size=self.p.trade_size)

        else:
            # 持仓时，SMA向下交叉时卖出
            if self.data.close[0] < self.sma[0] and self.data.close[-1] >= self.sma[-1]:
                self.log('SELL CREATE, %.2f' % self.data.close[0])
                self.order = self.sell(size=self.p.trade_size)

    def stop(self):
        """策略结束"""
        self.log('(SMA Period %2d) Ending Value %.2f' %
                 (self.params.sma_period, self.broker.getvalue()), doprint=True)


def run_local_binance_test():
    """运行本地Binance测试"""
    print("=== Backtrader Binance本地数据回测演示 ===\n")
    
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 查找本地BTC数据文件
    data_files = [
        "datas/binance-btc-2015-2026.txt",
        "datas/binance-btc-1h-2017-2025.txt", 
        "datas/binance-btc-4h-2017-2025.txt",
        "datas/binance-btc-30m-2017-2025.txt"
    ]
    
    data_loaded = False
    for data_file in data_files:
        full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), data_file)
        if os.path.exists(full_path):
            print(f"📂 使用本地数据文件: {data_file}")
            
            # 根据文件名判断时间格式
            if '1h' in data_file:
                timeframe = bt.TimeFrame.Minutes
                compression = 60
            elif '4h' in data_file:
                timeframe = bt.TimeFrame.Minutes
                compression = 240
            elif '30m' in data_file:
                timeframe = bt.TimeFrame.Minutes
                compression = 30
            else:
                timeframe = bt.TimeFrame.Days
                compression = 1
            
            try:
                data = bt.feeds.GenericCSVData(
                    dataname=full_path,
                    fromdate=datetime.datetime(2023, 1, 1),
                    todate=datetime.datetime(2023, 12, 31),
                    dtformat='%Y-%m-%d',
                    datetime=0,
                    open=1,
                    high=2,
                    low=3,
                    close=4,
                    volume=5,
                    openinterest=6,
                    timeframe=timeframe,
                    compression=compression,
                    header=True  # CSV文件有标题行
                )
                
                cerebro.adddata(data)
                data_loaded = True
                print("✅ 数据加载成功")
                break
                
            except Exception as e:
                print(f"❌ 数据加载失败: {e}")
                continue
    
    if not data_loaded:
        print("❌ 未找到可用的本地数据文件")
        print("💡 请确保以下文件之一存在:")
        for f in data_files:
            print(f"   - {f}")
        return
    
    # 添加策略
    cerebro.addstrategy(BinanceLocalTest, printlog=True)
    
    # 设置初始资金（USDT）
    cerebro.broker.setcash(10000.0)
    print(f'💼 初始资金: 10,000 USDT')
    
    # 设置佣金（Binance现货交易费率约0.1%）
    cerebro.broker.setcommission(commission=0.001)
    print('💰 交易佣金: 0.1%\n')
    
    # 显示初始状态
    print(f'📈 回测开始时账户价值: {cerebro.broker.getvalue():.2f} USDT')
    
    # 运行回测
    print("🚀 开始本地数据回测...")
    results = cerebro.run()
    
    # 显示最终结果
    final_value = cerebro.broker.getvalue()
    print(f'\n💰 回测结束时账户价值: {final_value:.2f} USDT')
    print(f'📊 总收益率: {(final_value - 10000) / 10000:.2%}')
    
    # 绘制图表（可选）
    try:
        print("\n📊 生成回测图表...")
        cerebro.plot()
    except Exception as e:
        print(f"⚠️  图表生成失败: {e}")
        print("💡 可能需要安装matplotlib: pip install matplotlib")
    
    print("\n🎯 本地数据回测演示完成!")


if __name__ == '__main__':
    run_local_binance_test()