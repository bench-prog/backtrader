# Backtrader 实战示例集

本文档包含多个经典量化策略的完整实现，可直接运行或作为模板修改。

---

## 目录

1. [双均线交叉策略](#1-双均线交叉策略)
2. [RSI 超买超卖策略](#2-rsi-超买超卖策略)
3. [MACD 策略](#3-macd-策略)
4. [布林带策略](#4-布林带策略)
5. [海龟交易法](#5-海龟交易法)
6. [多时间框架策略](#6-多时间框架策略)
7. [网格交易策略](#7-网格交易策略)
8. [止损止盈策略](#8-止损止盈策略)
9. [凯利公式仓位管理](#9-凯利公式仓位管理)
10. [回测组合与分析](#10-回测组合与分析)

---

## 1. 双均线交叉策略

最经典的技术分析策略，快线上穿慢线买入，快线下穿慢线卖出。

```python
import backtrader as bt

class SmaCrossStrategy(bt.Strategy):
    """双均线交叉策略"""

    params = (
        ('fast_period', 10),   # 快线周期
        ('slow_period', 30),   # 慢线周期
        ('printlog', True),    # 是否打印日志
    )

    def __init__(self):
        # 快速均线
        self.fast_sma = bt.indicators.SMA(
            self.data.close,
            period=self.params.fast_period
        )

        # 慢速均线
        self.slow_sma = bt.indicators.SMA(
            self.data.close,
            period=self.params.slow_period
        )

        # 交叉信号
        self.crossover = bt.indicators.CrossOver(
            self.fast_sma,
            self.slow_sma
        )

        # 记录订单
        self.order = None

    def log(self, txt, dt=None):
        """日志函数"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行: 价格={order.executed.price:.2f}, '
                        f'成本={order.executed.value:.2f}, '
                        f'手续费={order.executed.comm:.2f}')
            elif order.issell():
                self.log(f'卖出执行: 价格={order.executed.price:.2f}, '
                        f'成本={order.executed.value:.2f}, '
                        f'手续费={order.executed.comm:.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

        self.order = None

    def notify_trade(self, trade):
        """交易完成通知"""
        if not trade.isclosed:
            return

        self.log(f'交易盈亏: 毛利={trade.pnl:.2f}, 净利={trade.pnlcomm:.2f}')

    def next(self):
        """主逻辑"""
        # 如果有未完成的订单，不操作
        if self.order:
            return

        # 如果没有持仓
        if not self.position:
            # 金叉：买入
            if self.crossover > 0:
                self.log(f'买入信号: 价格={self.data.close[0]:.2f}')
                self.order = self.buy()

        # 如果有持仓
        else:
            # 死叉：卖出
            if self.crossover < 0:
                self.log(f'卖出信号: 价格={self.data.close[0]:.2f}')
                self.order = self.sell()

    def stop(self):
        """回测结束"""
        self.log(f'最终收益: {self.broker.getvalue():.2f}')


# 运行回测
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(SmaCrossStrategy)

    # 添加数据（这里需要替换为你的数据）
    # data = bt.feeds.GenericCSVData(dataname='your_data.csv')
    # cerebro.adddata(data)

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.run()
    cerebro.plot()
```

---

## 2. RSI 超买超卖策略

利用 RSI 指标判断超买超卖区域，低买高卖。

```python
import backtrader as bt

class RsiStrategy(bt.Strategy):
    """RSI 超买超卖策略"""

    params = (
        ('rsi_period', 14),      # RSI 周期
        ('rsi_upper', 70),       # 超买阈值
        ('rsi_lower', 30),       # 超卖阈值
        ('printlog', False),
    )

    def __init__(self):
        # RSI 指标
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.rsi_period
        )

        self.order = None

    def log(self, txt, dt=None):
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入: {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'卖出: {order.executed.price:.2f}')
        self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(f'盈亏: {trade.pnlcomm:.2f}')

    def next(self):
        if self.order:
            return

        # 没有持仓
        if not self.position:
            # RSI 低于 30，超卖，买入
            if self.rsi < self.params.rsi_lower:
                self.log(f'买入信号: RSI={self.rsi[0]:.2f}')
                self.order = self.buy()

        # 有持仓
        else:
            # RSI 高于 70，超买，卖出
            if self.rsi > self.params.rsi_upper:
                self.log(f'卖出信号: RSI={self.rsi[0]:.2f}')
                self.order = self.sell()


# 参数优化示例
if __name__ == '__main__':
    cerebro = bt.Cerebro()

    # 优化 RSI 参数
    cerebro.optstrategy(
        RsiStrategy,
        rsi_period=range(10, 20, 2),      # RSI 周期: 10, 12, 14, 16, 18
        rsi_upper=range(65, 80, 5),       # 超买阈值: 65, 70, 75
        rsi_lower=range(20, 35, 5),       # 超卖阈值: 20, 25, 30
    )

    # data = bt.feeds.GenericCSVData(dataname='your_data.csv')
    # cerebro.adddata(data)

    cerebro.broker.setcash(100000.0)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')

    results = cerebro.run()

    # 找出最佳参数
    for result in results:
        for strat in result:
            sharpe = strat.analyzers.sharpe.get_analysis()['sharperatio']
            print(f'RSI={strat.params.rsi_period}, '
                  f'Upper={strat.params.rsi_upper}, '
                  f'Lower={strat.params.rsi_lower}, '
                  f'Sharpe={sharpe:.2f if sharpe else 0}')
```

---

## 3. MACD 策略

使用 MACD 指标的金叉死叉进行交易。

```python
import backtrader as bt

class MacdStrategy(bt.Strategy):
    """MACD 策略"""

    params = (
        ('fast_period', 12),     # 快线周期
        ('slow_period', 26),     # 慢线周期
        ('signal_period', 9),    # 信号线周期
    )

    def __init__(self):
        # MACD 指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )

        # MACD 线与信号线的交叉
        self.crossover = bt.indicators.CrossOver(
            self.macd.macd,
            self.macd.signal
        )

    def next(self):
        if not self.position:
            # MACD 线上穿信号线（金叉），买入
            if self.crossover > 0:
                self.buy()

        else:
            # MACD 线下穿信号线（死叉），卖出
            if self.crossover < 0:
                self.sell()


# 增强版 MACD 策略：结合柱状图
class MacdEnhancedStrategy(bt.Strategy):
    """增强版 MACD 策略"""

    params = (
        ('fast_period', 12),
        ('slow_period', 26),
        ('signal_period', 9),
    )

    def __init__(self):
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )

    def next(self):
        # 当前柱状图和前一个柱状图
        hist = self.macd.histo[0]
        hist_prev = self.macd.histo[-1]

        if not self.position:
            # 柱状图由负转正（金叉确认），买入
            if hist > 0 and hist_prev < 0:
                self.buy()

        else:
            # 柱状图由正转负（死叉确认），卖出
            if hist < 0 and hist_prev > 0:
                self.sell()
```

---

## 4. 布林带策略

价格触及下轨买入，触及上轨卖出。

```python
import backtrader as bt

class BollingerBandsStrategy(bt.Strategy):
    """布林带策略"""

    params = (
        ('period', 20),          # 均线周期
        ('devfactor', 2.0),      # 标准差倍数
    )

    def __init__(self):
        # 布林带指标
        self.boll = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.devfactor
        )

        # 价格与布林带的关系
        self.buy_signal = self.data.close < self.boll.lines.bot
        self.sell_signal = self.data.close > self.boll.lines.top

    def next(self):
        if not self.position:
            # 价格跌破下轨，买入
            if self.buy_signal:
                self.buy()

        else:
            # 价格突破上轨，卖出
            if self.sell_signal:
                self.sell()


# 增强版：结合均线回归
class BollingerMeanReversionStrategy(bt.Strategy):
    """布林带均值回归策略"""

    params = (
        ('period', 20),
        ('devfactor', 2.0),
    )

    def __init__(self):
        self.boll = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.devfactor
        )

    def next(self):
        # 布林带宽度（波动率）
        bb_width = (self.boll.top[0] - self.boll.bot[0]) / self.boll.mid[0]

        # 只在高波动时交易
        if bb_width < 0.05:  # 波动率过低，不交易
            return

        if not self.position:
            # 价格接近下轨（相对位置 < 0.2），买入
            if self.data.close < self.boll.bot + 0.2 * (self.boll.top - self.boll.bot):
                self.buy()

        else:
            # 价格回归到中轨附近，平仓
            if self.data.close > self.boll.mid:
                self.sell()
```

---

## 5. 海龟交易法

经典的趋势跟踪策略。

```python
import backtrader as bt

class TurtleStrategy(bt.Strategy):
    """海龟交易法"""

    params = (
        ('entry_period', 20),    # 入场周期（突破 20 日高点）
        ('exit_period', 10),     # 出场周期（跌破 10 日低点）
        ('atr_period', 20),      # ATR 周期
        ('risk_percent', 0.02),  # 每次交易风险（账户的 2%）
    )

    def __init__(self):
        # 最高价和最低价
        self.highest = bt.indicators.Highest(
            self.data.high,
            period=self.params.entry_period
        )
        self.lowest = bt.indicators.Lowest(
            self.data.low,
            period=self.params.exit_period
        )

        # ATR（用于计算仓位）
        self.atr = bt.indicators.ATR(
            self.data,
            period=self.params.atr_period
        )

    def next(self):
        if not self.position:
            # 突破最高点，买入
            if self.data.close[0] > self.highest[-1]:
                # 根据 ATR 计算仓位大小
                # 风险金额 = 账户价值 * 风险百分比
                risk_amount = self.broker.getvalue() * self.params.risk_percent

                # 每手风险 = ATR * 2（止损设在 2 倍 ATR）
                per_share_risk = self.atr[0] * 2

                # 仓位大小 = 风险金额 / 每手风险
                size = int(risk_amount / per_share_risk)

                self.buy(size=size)

        else:
            # 跌破最低点，卖出
            if self.data.close[0] < self.lowest[-1]:
                self.sell()


# 增强版：加入金字塔加仓
class TurtleEnhancedStrategy(bt.Strategy):
    """海龟交易法（加仓版）"""

    params = (
        ('entry_period', 20),
        ('exit_period', 10),
        ('atr_period', 20),
        ('risk_percent', 0.02),
        ('max_units', 4),        # 最多加仓 4 次
    )

    def __init__(self):
        self.highest = bt.indicators.Highest(self.data.high, period=self.params.entry_period)
        self.lowest = bt.indicators.Lowest(self.data.low, period=self.params.exit_period)
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)

        self.units = 0           # 当前持仓单位数
        self.last_buy_price = 0  # 上次买入价格

    def next(self):
        if self.units == 0:
            # 首次入场
            if self.data.close[0] > self.highest[-1]:
                size = self._calculate_size()
                self.buy(size=size)
                self.units = 1
                self.last_buy_price = self.data.close[0]

        elif self.units < self.params.max_units:
            # 加仓：价格上涨了 0.5 个 ATR
            if self.data.close[0] > self.last_buy_price + 0.5 * self.atr[0]:
                size = self._calculate_size()
                self.buy(size=size)
                self.units += 1
                self.last_buy_price = self.data.close[0]

        # 出场
        if self.position:
            if self.data.close[0] < self.lowest[-1]:
                self.sell(size=self.position.size)
                self.units = 0

    def _calculate_size(self):
        """计算仓位大小"""
        risk_amount = self.broker.getvalue() * self.params.risk_percent
        per_share_risk = self.atr[0] * 2
        return int(risk_amount / per_share_risk)
```

---

## 6. 多时间框架策略

在多个时间周期上分析数据。

```python
import backtrader as bt

class MultiTimeframeStrategy(bt.Strategy):
    """多时间框架策略"""

    params = (
        ('fast_period', 10),
        ('slow_period', 30),
    )

    def __init__(self):
        # 日线数据（self.data0）
        self.daily_fast_sma = bt.indicators.SMA(
            self.data0.close,
            period=self.params.fast_period
        )
        self.daily_slow_sma = bt.indicators.SMA(
            self.data0.close,
            period=self.params.slow_period
        )

        # 周线数据（self.data1）
        self.weekly_fast_sma = bt.indicators.SMA(
            self.data1.close,
            period=self.params.fast_period
        )
        self.weekly_slow_sma = bt.indicators.SMA(
            self.data1.close,
            period=self.params.slow_period
        )

    def next(self):
        # 只有当两个时间框架都对齐时才交易
        daily_bullish = self.daily_fast_sma > self.daily_slow_sma
        weekly_bullish = self.weekly_fast_sma > self.weekly_slow_sma

        if not self.position:
            # 日线和周线都是多头趋势，买入
            if daily_bullish and weekly_bullish:
                self.buy()

        else:
            # 日线转为空头，卖出
            if not daily_bullish:
                self.sell()


# 使用示例
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MultiTimeframeStrategy)

    # 添加日线数据
    # daily_data = bt.feeds.GenericCSVData(dataname='daily.csv')
    # cerebro.adddata(daily_data)

    # 添加周线数据（需要从日线重采样）
    # weekly_data = cerebro.resampledata(daily_data, timeframe=bt.TimeFrame.Weeks)

    cerebro.run()
```

---

## 7. 网格交易策略

在价格区间内设置网格，低买高卖。

```python
import backtrader as bt

class GridTradingStrategy(bt.Strategy):
    """网格交易策略"""

    params = (
        ('grid_num', 10),        # 网格数量
        ('price_low', 90),       # 价格下限
        ('price_high', 110),     # 价格上限
        ('initial_cash', 100000), # 初始资金
    )

    def __init__(self):
        # 计算网格间距
        self.grid_step = (self.params.price_high - self.params.price_low) / self.params.grid_num

        # 计算每个网格的投资金额
        self.amount_per_grid = self.params.initial_cash / self.params.grid_num

        # 创建网格价格列表
        self.grid_prices = [
            self.params.price_low + i * self.grid_step
            for i in range(self.params.grid_num + 1)
        ]

        # 记录每个网格的订单
        self.grid_orders = {}

    def start(self):
        """回测开始时，在所有网格价格挂单"""
        for price in self.grid_prices:
            # 计算该价格下能买多少股
            size = int(self.amount_per_grid / price)

            # 挂限价买单
            order = self.buy(size=size, price=price, exectype=bt.Order.Limit)
            self.grid_orders[price] = order

    def notify_order(self, order):
        if order.status not in [order.Completed]:
            return

        if order.isbuy():
            # 买单成交，挂对应的卖单
            buy_price = order.executed.price
            sell_price = buy_price + self.grid_step

            # 挂限价卖单
            self.sell(size=order.executed.size, price=sell_price, exectype=bt.Order.Limit)

        elif order.issell():
            # 卖单成交，重新挂买单
            sell_price = order.executed.price
            buy_price = sell_price - self.grid_step

            size = int(self.amount_per_grid / buy_price)
            self.buy(size=size, price=buy_price, exectype=bt.Order.Limit)


# 更简单的版本：只维护当前持仓
class SimpleGridStrategy(bt.Strategy):
    """简单网格策略"""

    params = (
        ('base_price', 100),     # 基准价格
        ('grid_step', 2),        # 网格间距（%）
        ('grid_size', 100),      # 每格交易股数
    )

    def next(self):
        current_price = self.data.close[0]

        # 计算价格与基准价格的偏离百分比
        deviation = (current_price - self.params.base_price) / self.params.base_price * 100

        # 价格每下跌一个网格，买入
        if deviation < 0 and abs(deviation) % self.params.grid_step < 0.5:
            if not self.position or self.position.size < 1000:  # 限制最大持仓
                self.buy(size=self.params.grid_size)

        # 价格每上涨一个网格，卖出
        elif deviation > 0 and deviation % self.params.grid_step < 0.5:
            if self.position and self.position.size >= self.params.grid_size:
                self.sell(size=self.params.grid_size)
```

---

## 8. 止损止盈策略

实现动态止损和目标止盈。

```python
import backtrader as bt

class StopLossTakeProfitStrategy(bt.Strategy):
    """止损止盈策略"""

    params = (
        ('stop_loss', 0.02),     # 止损比例（2%）
        ('take_profit', 0.05),   # 止盈比例（5%）
        ('sma_period', 20),      # 均线周期
    )

    def __init__(self):
        self.sma = bt.indicators.SMA(period=self.params.sma_period)
        self.order = None
        self.buy_price = None

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                print(f'买入: {self.buy_price:.2f}')
            elif order.issell():
                print(f'卖出: {order.executed.price:.2f}')
                self.buy_price = None

        self.order = None

    def next(self):
        if self.order:
            return

        # 没有持仓
        if not self.position:
            # 价格上穿均线，买入
            if self.data.close[0] > self.sma[0] and self.data.close[-1] <= self.sma[-1]:
                self.order = self.buy()

        # 有持仓
        else:
            # 计算止损价和止盈价
            stop_price = self.buy_price * (1 - self.params.stop_loss)
            profit_price = self.buy_price * (1 + self.params.take_profit)

            # 触发止损
            if self.data.close[0] <= stop_price:
                print(f'止损: 买入价={self.buy_price:.2f}, 当前价={self.data.close[0]:.2f}')
                self.order = self.sell()

            # 触发止盈
            elif self.data.close[0] >= profit_price:
                print(f'止盈: 买入价={self.buy_price:.2f}, 当前价={self.data.close[0]:.2f}')
                self.order = self.sell()


# 移动止损（Trailing Stop）
class TrailingStopStrategy(bt.Strategy):
    """移动止损策略"""

    params = (
        ('trailing_percent', 0.05),  # 移动止损比例（5%）
        ('atr_period', 14),           # ATR 周期
    )

    def __init__(self):
        self.atr = bt.indicators.ATR(period=self.params.atr_period)
        self.order = None
        self.highest_price = 0  # 持仓期间的最高价

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.highest_price = order.executed.price
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # 简单的买入信号（可以替换为你的逻辑）
            if self.data.close[0] > self.data.close[-1]:
                self.order = self.buy()

        else:
            # 更新最高价
            if self.data.close[0] > self.highest_price:
                self.highest_price = self.data.close[0]

            # 移动止损：从最高价回撤 5%
            trailing_stop = self.highest_price * (1 - self.params.trailing_percent)

            if self.data.close[0] <= trailing_stop:
                print(f'移动止损触发: 最高价={self.highest_price:.2f}, '
                      f'止损价={trailing_stop:.2f}, 当前价={self.data.close[0]:.2f}')
                self.order = self.sell()


# ATR 止损
class AtrStopStrategy(bt.Strategy):
    """基于 ATR 的止损策略"""

    params = (
        ('atr_period', 14),
        ('atr_multiplier', 2.0),  # ATR 倍数
    )

    def __init__(self):
        self.atr = bt.indicators.ATR(period=self.params.atr_period)
        self.order = None
        self.buy_price = None

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # 买入信号
            if self.data.close[0] > self.data.close[-1]:
                self.order = self.buy()

        else:
            # ATR 止损：从买入价下跌 2 倍 ATR
            stop_price = self.buy_price - self.params.atr_multiplier * self.atr[0]

            if self.data.close[0] <= stop_price:
                print(f'ATR 止损: ATR={self.atr[0]:.2f}, 止损价={stop_price:.2f}')
                self.order = self.sell()
```

---

## 9. 凯利公式仓位管理

根据胜率和盈亏比动态调整仓位。

```python
import backtrader as bt

class KellySizer(bt.Sizer):
    """凯利公式仓位管理"""

    params = (
        ('win_rate', 0.6),       # 胜率
        ('avg_win', 0.05),       # 平均盈利（%）
        ('avg_loss', 0.03),      # 平均亏损（%）
        ('max_position', 0.5),   # 最大仓位（账户的 50%）
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            # 凯利公式：f = (p * b - q) / b
            # p = 胜率, q = 1 - p, b = 盈亏比
            p = self.params.win_rate
            q = 1 - p
            b = self.params.avg_win / self.params.avg_loss

            kelly_percent = (p * b - q) / b

            # 通常使用半凯利或 1/4 凯利
            kelly_percent = kelly_percent * 0.5

            # 限制最大仓位
            kelly_percent = min(kelly_percent, self.params.max_position)

            # 计算股数
            position_value = cash * kelly_percent
            price = data.close[0]
            size = int(position_value / price)

            return size

        # 卖出时全部卖出
        return self.broker.getposition(data).size


# 使用凯利仓位管理的策略
class KellyStrategy(bt.Strategy):
    """使用凯利公式的策略"""

    params = (
        ('sma_period', 20),
    )

    def __init__(self):
        self.sma = bt.indicators.SMA(period=self.params.sma_period)

    def next(self):
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                self.buy()  # 仓位由 Sizer 决定

        else:
            if self.data.close[0] < self.sma[0]:
                self.sell()


# 运行示例
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(KellyStrategy)

    # 添加凯利仓位管理
    cerebro.addsizer(KellySizer)

    # data = bt.feeds.GenericCSVData(dataname='your_data.csv')
    # cerebro.adddata(data)

    cerebro.broker.setcash(100000.0)
    cerebro.run()
```

---

## 10. 回测组合与分析

完整的回测流程，包含多种分析器。

```python
import backtrader as bt
from datetime import datetime

class MyStrategy(bt.Strategy):
    """你的策略"""
    params = (('period', 20),)

    def __init__(self):
        self.sma = bt.indicators.SMA(period=self.params.period)

    def next(self):
        if not self.position:
            if self.data.close > self.sma:
                self.buy()
        else:
            if self.data.close < self.sma:
                self.sell()


def run_backtest():
    """完整的回测流程"""

    # 1. 创建引擎
    cerebro = bt.Cerebro()

    # 2. 添加策略
    cerebro.addstrategy(MyStrategy)

    # 3. 添加数据
    # data = bt.feeds.GenericCSVData(
    #     dataname='your_data.csv',
    #     fromdate=datetime(2020, 1, 1),
    #     todate=datetime(2023, 12, 31),
    # )
    # cerebro.adddata(data)

    # 4. 设置初始资金和手续费
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    # 5. 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe',
                       timeframe=bt.TimeFrame.Days, annualize=True, riskfreerate=0.03)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    cerebro.addanalyzer(bt.analyzers.VWR, _name='vwr')

    # 6. 添加观察者
    cerebro.addobserver(bt.observers.Broker)
    cerebro.addobserver(bt.observers.Trades)
    cerebro.addobserver(bt.observers.BuySell)
    cerebro.addobserver(bt.observers.DrawDown)

    # 7. 运行回测
    print('=' * 50)
    print('回测开始')
    print(f'初始资金: {cerebro.broker.getvalue():.2f}')
    print('=' * 50)

    results = cerebro.run()
    strat = results[0]

    print('\n' + '=' * 50)
    print('回测结束')
    print(f'最终资金: {cerebro.broker.getvalue():.2f}')
    print('=' * 50)

    # 8. 打印分析结果
    print('\n' + '=' * 50)
    print('性能指标')
    print('=' * 50)

    # 夏普比率
    sharpe = strat.analyzers.sharpe.get_analysis()
    sharpe_ratio = sharpe.get('sharperatio', None)
    print(f"夏普比率: {sharpe_ratio:.3f}" if sharpe_ratio else "夏普比率: N/A")

    # 最大回撤
    drawdown = strat.analyzers.drawdown.get_analysis()
    print(f"最大回撤: {drawdown['max']['drawdown']:.2f}%")
    print(f"最长回撤期: {drawdown['max']['len']} 天")

    # 收益率
    returns = strat.analyzers.returns.get_analysis()
    print(f"总收益率: {returns['rtot']:.2%}")
    print(f"年化收益率: {returns['rnorm']:.2%}")

    # SQN（系统质量数）
    sqn = strat.analyzers.sqn.get_analysis()
    print(f"SQN: {sqn['sqn']:.2f}")

    # VWR（收益变异系数）
    vwr = strat.analyzers.vwr.get_analysis()
    print(f"VWR: {vwr.get('vwr', 0):.2f}")

    # 交易统计
    print('\n' + '=' * 50)
    print('交易统计')
    print('=' * 50)

    trades = strat.analyzers.trades.get_analysis()
    total_trades = trades.total.closed if trades.total.closed else 0

    if total_trades > 0:
        print(f"总交易次数: {total_trades}")
        print(f"盈利次数: {trades.won.total}")
        print(f"亏损次数: {trades.lost.total}")
        print(f"胜率: {trades.won.total / total_trades:.2%}")

        if trades.won.total > 0:
            print(f"平均盈利: {trades.won.pnl.average:.2f}")
            print(f"最大盈利: {trades.won.pnl.max:.2f}")

        if trades.lost.total > 0:
            print(f"平均亏损: {trades.lost.pnl.average:.2f}")
            print(f"最大亏损: {trades.lost.pnl.max:.2f}")

        print(f"平均持仓周期: {trades.len.average:.1f} 天")
    else:
        print("无交易记录")

    # 9. 绘制图表
    print('\n正在生成图表...')
    cerebro.plot(style='candlestick', barup='red', bardown='green')


if __name__ == '__main__':
    run_backtest()
```

---

## 运行所有示例

你可以将这些策略复制到单独的文件中运行，或者创建一个测试框架：

```python
import backtrader as bt

def test_strategy(strategy_class, strategy_name, **kwargs):
    """测试单个策略"""
    print(f'\n{"=" * 60}')
    print(f'测试策略: {strategy_name}')
    print(f'{"=" * 60}')

    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class, **kwargs)

    # 添加数据（这里需要替换为你的数据）
    # data = bt.feeds.GenericCSVData(dataname='your_data.csv')
    # cerebro.adddata(data)

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    print(f'初始资金: {cerebro.broker.getvalue():.2f}')
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    print(f'最终资金: {final_value:.2f}')
    print(f'收益率: {(final_value / 100000 - 1) * 100:.2f}%')

    strat = results[0]
    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', None)
    if sharpe:
        print(f'夏普比率: {sharpe:.3f}')

    drawdown = strat.analyzers.drawdown.get_analysis()
    print(f"最大回撤: {drawdown['max']['drawdown']:.2f}%")


if __name__ == '__main__':
    # 测试所有策略
    test_strategy(SmaCrossStrategy, '双均线交叉')
    test_strategy(RsiStrategy, 'RSI 策略')
    test_strategy(MacdStrategy, 'MACD 策略')
    test_strategy(BollingerBandsStrategy, '布林带策略')
    test_strategy(TurtleStrategy, '海龟交易法')
```

---

## 下一步

- **参数优化**: 使用 `cerebro.optstrategy()` 寻找最佳参数
- **组合策略**: 将多个信号结合，提高胜率
- **风险管理**: 加入更复杂的仓位管理和风险控制
- **实盘交易**: 使用 `IBBroker` 或 `OandaBroker` 连接实盘

更多信息请参考：
- [快速开始指南](quickstart.md)
- [项目架构文档](architecture.md)
- [官方文档](https://www.backtrader.com/)

---

**祝你交易顺利！** 📈
