#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Grid Trading Demo for Backtrader
动态网格交易策略示例
基于backtrader框架实现的经典网格交易算法
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import datetime
import math


class GridTradingStrategy(bt.Strategy):
    """
    动态网格交易策略
    根据市场波动动态调整网格间距和仓位大小
    """
    
    params = (
        ('grid_levels', 8),           # 网格层数
        ('grid_spacing', 0.02),       # 基础网格间距(2%)
        ('atr_period', 14),           # ATR计算周期
        ('risk_percent', 0.01),       # 每笔风险1%
        ('max_positions', 3),         # 最大持仓数
        ('take_profit_ratio', 0.03),  # 止盈3%
        ('stop_loss_ratio', 0.02),    # 止损2%
        ('printlog', True),
    )

    def __init__(self):
        """初始化策略"""
        # 技术指标
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        self.sma = bt.indicators.SMA(period=20)
        
        # 网格相关变量
        self.grid_prices = []          # 网格价格点
        self.active_orders = {}        # 活跃订单字典
        self.position_prices = {}      # 持仓价格记录
        self.last_grid_update = None   # 上次网格更新时间
        
        # 风险管理变量
        self.initial_cash = self.broker.get_cash()
        self.max_drawdown = 0
        self.peak_value = self.initial_cash
        
        # 统计变量
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0
        
        if self.p.printlog:
            print("🎯 动态网格交易策略初始化完成")
            print(f"📊 参数设置: 网格层数={self.p.grid_levels}, 基础间距={self.p.grid_spacing * 100:.1f}%")

    def log(self, txt, dt=None):
        """日志记录"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.datetime(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def start(self):
        """策略开始时调用"""
        self.log("策略启动")
        self._initialize_grids()

    def _initialize_grids(self):
        """初始化网格"""
        current_price = self.data.close[0]
        
        # 计算动态网格间距（基于ATR）
        dynamic_spacing = self.p.grid_spacing * (1 + self.atr[0] / current_price)
        
        # 在当前价格上下创建网格
        half_levels = self.p.grid_levels // 2
        
        self.grid_prices = []
        for i in range(-half_levels, half_levels + 1):
            grid_price = current_price * (1 + i * dynamic_spacing)
            self.grid_prices.append(grid_price)
            
        self.grid_prices.sort()
        
        if self.p.printlog:
            self.log(f"网格初始化完成，共{len(self.grid_prices)}个网格点")
            self.log(f"价格范围: ${self.grid_prices[0]:.2f} - ${self.grid_prices[-1]:.2f}")
            self.log(f"动态间距: {dynamic_spacing * 100:.2f}%")

    def next(self):
        """主逻辑循环"""
        current_price = self.data.close[0]
        
        # 更新峰值和最大回撤
        current_value = self.broker.getvalue()
        self.peak_value = max(self.peak_value, current_value)
        self.max_drawdown = max(self.max_drawdown, (self.peak_value - current_value) / self.peak_value)
        
        # 检查现有订单
        self._check_existing_orders()
        
        # 检查是否需要更新网格
        if self._should_update_grids():
            self._update_grids()
        
        # 检查网格触发
        self._check_grid_triggers(current_price)

    def _check_existing_orders(self):
        """检查现有订单状态"""
        # 清理已完成的订单
        completed_orders = []
        for order_ref, order_info in self.active_orders.items():
            order = order_info['order']
            if order.status in [order.Completed, order.Canceled, order.Expired, order.Rejected]:
                completed_orders.append(order_ref)
                
                if order.status == order.Completed:
                    self.total_trades += 1
                    # 记录成交价格
                    if order.isbuy():
                        self.position_prices[order_ref] = order.executed.price
                        self.log(f"买单成交: 价格${order.executed.price:.2f}, 数量{order.executed.size}")
                    else:
                        # 计算盈亏
                        entry_price = self.position_prices.get(order_ref, order.executed.price)
                        pnl = (order.executed.price - entry_price) * order.executed.size
                        self.total_pnl += pnl
                        if pnl > 0:
                            self.winning_trades += 1
                        self.log(f"卖单成交: 价格${order.executed.price:.2f}, 盈亏${pnl:.2f}")
                        
                        # 清理持仓记录
                        if order_ref in self.position_prices:
                            del self.position_prices[order_ref]
        
        # 移除已完成的订单
        for order_ref in completed_orders:
            if order_ref in self.active_orders:
                del self.active_orders[order_ref]

    def _should_update_grids(self):
        """判断是否需要更新网格"""
        # 简单的时间间隔判断（每100个周期更新一次）
        if self.last_grid_update is None:
            self.last_grid_update = len(self)
            return True
            
        if len(self) - self.last_grid_update >= 100:
            self.last_grid_update = len(self)
            return True
            
        return False

    def _update_grids(self):
        """更新网格"""
        current_price = self.data.close[0]
        dynamic_spacing = self.p.grid_spacing * (1 + self.atr[0] / current_price)
        
        # 重新计算网格中心
        half_levels = self.p.grid_levels // 2
        self.grid_prices = []
        
        for i in range(-half_levels, half_levels + 1):
            grid_price = current_price * (1 + i * dynamic_spacing)
            self.grid_prices.append(grid_price)
            
        self.grid_prices.sort()
        
        if self.p.printlog:
            self.log(f"网格更新完成，新价格范围: ${self.grid_prices[0]:.2f} - ${self.grid_prices[-1]:.2f}")

    def _check_grid_triggers(self, current_price):
        """检查网格触发条件"""
        # 检查当前持仓数量
        current_positions = len([pos for pos in self.position_prices.values()])
        if current_positions >= self.p.max_positions:
            return
            
        # 检查每个网格点
        for grid_price in self.grid_prices:
            # 检查是否接近网格点（0.1%范围内）
            if abs(current_price - grid_price) / grid_price < 0.001:
                self._trigger_grid_order(grid_price)

    def _trigger_grid_order(self, grid_price):
        """触发网格订单"""
        current_price = self.data.close[0]
        current_cash = self.broker.get_cash()
        
        # 避免重复触发同一网格点
        grid_key = f"grid_{grid_price:.2f}"
        if grid_key in [order_info.get('grid_key') for order_info in self.active_orders.values()]:
            return
            
        # 计算仓位大小（基于风险百分比）
        risk_amount = current_cash * self.p.risk_percent
        position_size = int(risk_amount / (self.atr[0] * 2))  # 基于ATR的风险调整
        
        if position_size <= 0:
            position_size = 1
            
        # 根据价格关系决定买卖方向
        if current_price > grid_price:  # 价格高于网格点，做空
            order = self.sell(size=position_size)
            order_type = "SELL"
        else:  # 价格低于网格点，做多
            order = self.buy(size=position_size)
            order_type = "BUY"
            
        # 记录订单
        if order:
            self.active_orders[order.ref] = {
                'order': order,
                'grid_price': grid_price,
                'grid_key': grid_key,
                'type': order_type
            }
            
            self.log(f"网格订单触发: {order_type} {position_size}股 @ ${grid_price:.2f}")

    def notify_order(self, order):
        """订单通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            pass
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'订单{order.Status[order.status]}')

    def stop(self):
        """策略结束"""
        self.log("=== 策略结束统计 ===")
        self.log(f"总交易次数: {self.total_trades}")
        self.log(f"盈利交易: {self.winning_trades}")
        self.log(f"胜率: {self.winning_trades/self.total_trades*100:.1f}%" if self.total_trades > 0 else "胜率: 0%")
        self.log(f"总盈亏: ${self.total_pnl:.2f}")
        self.log(f"最大回撤: {self.max_drawdown:.2%}")
        self.log(f"最终账户价值: ${self.broker.getvalue():.2f}")


def run_grid_trading_demo():
    """运行网格交易演示"""
    print("=== Backtrader网格交易策略演示 ===\n")
    
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 添加数据（使用ORCL一年数据）
    data = bt.feeds.YahooFinanceData(
        dataname='ORCL',
        fromdate=datetime.datetime(2000, 1, 1),
        todate=datetime.datetime(2000, 12, 31)
    )
    cerebro.adddata(data)
    
    # 添加策略
    cerebro.addstrategy(GridTradingStrategy, printlog=True)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # 设置初始资金和佣金
    cerebro.broker.setcash(50000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # 显示初始状态
    print(f"初始账户资金: ${cerebro.broker.getvalue():.2f}")
    
    # 运行回测
    print("开始网格交易回测...")
    results = cerebro.run()
    strategy = results[0]
    
    # 显示最终结果
    final_value = cerebro.broker.getvalue()
    print(f"\n最终账户资金: ${final_value:.2f}")
    print(f"总收益率: {(final_value - 50000) / 50000:.2%}")
    
    # 显示分析器结果
    returns_analysis = strategy.analyzers.returns.get_analysis()
    drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
    trades_analysis = strategy.analyzers.trades.get_analysis()
    
    print(f"\n绩效分析:")
    print(f"  总回报: {returns_analysis.get('rtot', 0):.2%}")
    print(f"  年化回报: {returns_analysis.get('ravg', 0)*252:.2%}")
    print(f"  最大回撤: {drawdown_analysis.get('maxdrawdown', 0):.2%}")
    
    if hasattr(trades_analysis, 'won') and trades_analysis.won.total > 0:
        print(f"  总交易数: {trades_analysis.total.total}")
        print(f"  盈利交易: {trades_analysis.won.total}")
        print(f"  胜率: {trades_analysis.won.total/trades_analysis.total.total*100:.1f}%")


if __name__ == '__main__':
    run_grid_trading_demo()