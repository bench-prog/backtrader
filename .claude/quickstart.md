# Backtrader 快速开始指南

## 5 分钟上手

本指南帮助你在 5 分钟内完成第一个回测策略。

---

## 目录

- [安装](#安装)
- [第一个策略](#第一个策略)
- [数据导入](#数据导入)
- [运行回测](#运行回测)
- [查看结果](#查看结果)
- [下一步](#下一步)

---

## 安装

```bash
# 从源码安装
cd /path/to/backtrader
pip install -e .

# 或使用 pip 安装稳定版
pip install backtrader

# 可选：安装绘图依赖
pip install matplotlib
```

---

## 第一个策略

创建一个简单的均线交叉策略：

```python
import backtrader as bt

class SmaCross(bt.Strategy):
    """简单的均线交叉策略"""

    # 定义参数
    params = (
        ('fast_period', 10),  # 快线周期
        ('slow_period', 30),  # 慢线周期
    )

    def __init__(self):
        """初始化：创建指标"""
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

    def next(self):
        """每个数据点的交易逻辑"""
        # 如果没有持仓
        if not self.position:
            # 金叉：快线上穿慢线，买入
            if self.crossover > 0:
                self.buy()

        # 如果有持仓
        else:
            # 死叉：快线下穿慢线，卖出
            if self.crossover < 0:
                self.sell()

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f'买入: 价格={order.executed.price:.2f}, '
                      f'成本={order.executed.value:.2f}, '
                      f'手续费={order.executed.comm:.2f}')
            elif order.issell():
                print(f'卖出: 价格={order.executed.price:.2f}, '
                      f'成本={order.executed.value:.2f}, '
                      f'手续费={order.executed.comm:.2f}')

    def notify_trade(self, trade):
        """交易完成通知"""
        if trade.isclosed:
            print(f'交易盈亏: 毛利={trade.pnl:.2f}, 净利={trade.pnlcomm:.2f}')
```

---

## 数据导入

Backtrader 支持多种数据源，以下是最常用的几种：

### 方式 1: 从 CSV 文件导入

```python
import backtrader as bt
from datetime import datetime

# 创建数据源
data = bt.feeds.GenericCSVData(
    dataname='your_data.csv',

    # 日期列
    dtformat='%Y-%m-%d',
    datetime=0,

    # OHLC 列索引
    open=1,
    high=2,
    low=3,
    close=4,
    volume=5,
    openinterest=-1,  # -1 表示没有这一列

    # 日期范围（可选）
    fromdate=datetime(2020, 1, 1),
    todate=datetime(2023, 12, 31),
)
```

CSV 文件格式示例：
```csv
date,open,high,low,close,volume
2020-01-02,100.5,102.3,99.8,101.2,1000000
2020-01-03,101.5,103.0,100.5,102.5,1200000
...
```

### 方式 2: 从 Pandas DataFrame 导入

```python
import pandas as pd
import backtrader as bt

# 读取数据
df = pd.read_csv('your_data.csv', parse_dates=['date'], index_col='date')

# 创建数据源
data = bt.feeds.PandasData(
    dataname=df,
    datetime=None,  # 使用索引作为日期
    open='open',
    high='high',
    low='low',
    close='close',
    volume='volume',
    openinterest=None,
)
```

### 方式 3: Yahoo Finance（历史数据）

```python
import backtrader as bt
from datetime import datetime

data = bt.feeds.YahooFinanceData(
    dataname='AAPL',
    fromdate=datetime(2020, 1, 1),
    todate=datetime(2023, 12, 31),
)
```

### 方式 4: 程序生成数据

```python
import backtrader as bt
import random
from datetime import datetime, timedelta

class RandomData(bt.DataBase):
    """随机生成的数据（用于测试）"""

    def _load(self):
        if len(self) >= 252:  # 252 个交易日
            return False

        # 生成随机 OHLC
        base = 100 + random.random() * 20
        self.lines.datetime[0] = bt.date2num(
            datetime(2020, 1, 1) + timedelta(days=len(self))
        )
        self.lines.open[0] = base
        self.lines.high[0] = base + random.random() * 2
        self.lines.low[0] = base - random.random() * 2
        self.lines.close[0] = base + random.random() * 2 - 1
        self.lines.volume[0] = random.randint(100000, 1000000)

        return True

data = RandomData()
```

---

## 运行回测

将数据、策略和引擎组合起来：

```python
import backtrader as bt

# 1. 创建 Cerebro 引擎
cerebro = bt.Cerebro()

# 2. 添加策略
cerebro.addstrategy(SmaCross)

# 3. 添加数据
data = bt.feeds.GenericCSVData(dataname='your_data.csv')
cerebro.adddata(data)

# 4. 设置初始资金
cerebro.broker.setcash(100000.0)

# 5. 设置手续费（万分之一）
cerebro.broker.setcommission(commission=0.0001)

# 6. 设置每次交易的股数
cerebro.addsizer(bt.sizers.FixedSize, stake=100)

# 7. 打印初始资金
print(f'初始资金: {cerebro.broker.getvalue():.2f}')

# 8. 运行回测
cerebro.run()

# 9. 打印最终资金
print(f'最终资金: {cerebro.broker.getvalue():.2f}')
```

---

## 查看结果

### 1. 基本输出

运行上面的代码会输出：
```
初始资金: 100000.00
买入: 价格=105.50, 成本=10550.00, 手续费=1.06
卖出: 价格=112.30, 成本=10550.00, 手续费=1.12
交易盈亏: 毛利=780.00, 净利=777.82
...
最终资金: 115230.45
```

### 2. 添加分析器

获取详细的性能指标：

```python
# 添加分析器
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

# 运行并获取结果
results = cerebro.run()
strat = results[0]

# 打印分析结果
print('\n===== 性能指标 =====')
print(f"夏普比率: {strat.analyzers.sharpe.get_analysis()['sharperatio']:.2f}")
print(f"最大回撤: {strat.analyzers.drawdown.get_analysis()['max']['drawdown']:.2f}%")
print(f"总收益率: {strat.analyzers.returns.get_analysis()['rtot']:.2%}")

# 交易统计
trades = strat.analyzers.trades.get_analysis()
print(f"\n===== 交易统计 =====")
print(f"总交易次数: {trades.total.closed}")
print(f"盈利次数: {trades.won.total}")
print(f"亏损次数: {trades.lost.total}")
print(f"胜率: {trades.won.total / trades.total.closed:.2%}")
```

### 3. 绘制图表

```python
# 绘制回测结果图表
cerebro.plot(style='candlestick')
```

这会显示：
- K 线图
- 均线指标
- 买卖信号标记
- 资金曲线
- 成交量

---

## 完整示例代码

```python
import backtrader as bt
from datetime import datetime

class SmaCross(bt.Strategy):
    params = (('fast', 10), ('slow', 30),)

    def __init__(self):
        self.fast_sma = bt.indicators.SMA(period=self.p.fast)
        self.slow_sma = bt.indicators.SMA(period=self.p.slow)
        self.crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        else:
            if self.crossover < 0:
                self.sell()

if __name__ == '__main__':
    # 创建引擎
    cerebro = bt.Cerebro()

    # 添加策略
    cerebro.addstrategy(SmaCross)

    # 添加数据
    data = bt.feeds.GenericCSVData(
        dataname='your_data.csv',
        dtformat='%Y-%m-%d',
        datetime=0, open=1, high=2, low=3, close=4, volume=5,
        openinterest=-1,
        fromdate=datetime(2020, 1, 1),
        todate=datetime(2023, 12, 31),
    )
    cerebro.adddata(data)

    # 配置
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0001)
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    # 运行
    print(f'初始资金: {cerebro.broker.getvalue():.2f}')
    results = cerebro.run()
    print(f'最终资金: {cerebro.broker.getvalue():.2f}')

    # 打印分析结果
    strat = results[0]
    print(f"夏普比率: {strat.analyzers.sharpe.get_analysis()['sharperatio']:.2f}")
    print(f"最大回撤: {strat.analyzers.drawdown.get_analysis()['max']['drawdown']:.2f}%")

    # 绘图
    cerebro.plot()
```

---

## 常用配置

### 1. 设置手续费

```python
# 按比例收费（例如万分之三）
cerebro.broker.setcommission(commission=0.0003)

# 固定手续费
cerebro.broker.setcommission(commission=5.0)

# 更复杂的手续费设置
cerebro.broker.setcommission(
    commission=0.0003,
    margin=2000.0,      # 保证金
    mult=10.0,          # 乘数
    commtype=bt.CommInfoBase.COMM_PERC,  # 百分比模式
)
```

### 2. 设置滑点

```python
# 固定滑点（价格偏移）
cerebro.broker.set_slippage_fixed(0.05)

# 百分比滑点
cerebro.broker.set_slippage_perc(0.001)  # 0.1%
```

### 3. 设置订单类型

```python
class MyStrategy(bt.Strategy):
    def next(self):
        # 市价单（默认）
        self.buy()

        # 限价单
        self.buy(price=self.data.close[0] * 0.99, exectype=bt.Order.Limit)

        # 止损单
        self.buy(price=self.data.close[0] * 1.01, exectype=bt.Order.Stop)

        # 止盈止损单
        self.buy(
            price=self.data.close[0],
            exectype=bt.Order.Market,
            stopPrice=self.data.close[0] * 0.95,  # 止损
            limitPrice=self.data.close[0] * 1.05,  # 止盈
        )
```

### 4. 仓位管理

```python
# 固定股数
cerebro.addsizer(bt.sizers.FixedSize, stake=100)

# 按百分比下单（使用可用资金的 50%）
cerebro.addsizer(bt.sizers.PercentSizer, percents=50)

# 自定义仓位大小
class MyStrategy(bt.Strategy):
    def next(self):
        # 计算目标仓位
        size = int(self.broker.getvalue() * 0.5 / self.data.close[0])
        self.buy(size=size)
```

---

## 调试技巧

### 1. 打印日志

```python
class MyStrategy(bt.Strategy):
    def log(self, txt, dt=None):
        """日志函数"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

    def next(self):
        self.log(f'Close: {self.data.close[0]:.2f}')

        if self.crossover > 0:
            self.log('买入信号')
            self.buy()
```

### 2. 使用观察者

```python
# 添加观察者
cerebro.addobserver(bt.observers.Broker)      # 资金曲线
cerebro.addobserver(bt.observers.Trades)      # 交易标记
cerebro.addobserver(bt.observers.BuySell)     # 买卖信号
cerebro.addobserver(bt.observers.DrawDown)    # 回撤曲线
```

### 3. 检查数据

```python
class MyStrategy(bt.Strategy):
    def prenext(self):
        """数据不足时调用"""
        print(f'数据不足，当前长度: {len(self)}')

    def next(self):
        print(f'Date: {self.data.datetime.date(0)}')
        print(f'OHLC: {self.data.open[0]}, {self.data.high[0]}, '
              f'{self.data.low[0]}, {self.data.close[0]}')
        print(f'Volume: {self.data.volume[0]}')
```

---

## 下一步

恭喜！你已经掌握了 Backtrader 的基础用法。接下来可以：

1. **学习更多指标** - 查看 [实战示例集](examples.md)
2. **优化策略参数** - 使用 `cerebro.optstrategy()` 进行参数优化
3. **多时间框架** - 在一个策略中使用多个时间周期
4. **实盘交易** - 接入真实经纪商（IB、Oanda 等）
5. **自定义组件** - 编写自己的指标、分析器等

### 推荐学习资源

- **实战示例集**: [examples.md](examples.md) - 包含 10+ 经典策略实现
- **架构文档**: [architecture.md](architecture.md) - 深入理解框架设计
- **官方文档**: https://www.backtrader.com/
- **社区论坛**: https://community.backtrader.com/

---

## 常见问题

### Q: 为什么我的策略不执行交易？

A: 检查以下几点：
1. 数据是否正确加载
2. 指标是否需要预热期（`prenext()` vs `next()`）
3. 订单是否被正确提交（检查 `notify_order()`）
4. 资金是否足够（检查 `cerebro.broker.getcash()`）

### Q: 如何加速回测？

A:
1. 使用向量化指标（`once()` 方法）
2. 减少不必要的日志输出
3. 关闭绘图功能
4. 使用参数优化时启用多进程

### Q: 如何处理缺失数据？

A:
```python
data = bt.feeds.GenericCSVData(
    dataname='data.csv',
    missing=-999,  # 缺失值标记
)

# 或在策略中检查
def next(self):
    if self.data.close[0] != -999:
        # 处理逻辑
        pass
```

---

**祝你回测愉快！** 🚀
