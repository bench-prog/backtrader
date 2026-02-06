# Bybit Real Trade Module

专业的 Bybit 交易系统核心模块，为 Backtrader 提供完整的 Bybit 交易所集成。

## 🎯 功能特性

### 核心组件

- **BybitStore** - 交易所连接管理
  - 单例模式，避免重复连接
  - 支持测试网和主网
  - 线程安全
  - 连接池管理

- **BybitBroker** - 交易经纪商
  - 模拟交易模式（Paper Trading）
  - 实盘交易模式（Live Trading）
  - 完整的订单管理
  - 持仓和资金管理
  - 支持市价单、限价单、止损单

- **BybitData** - 数据源
  - 实时数据流
  - 历史数据加载
  - 多时间周期支持（1m ~ 1M）
  - 自动时间戳转换

### 工具模块

- **Config** - 配置管理
  - 支持文件、环境变量、代码配置
  - JSON 和 Python 配置文件
  - 配置验证

- **Logger** - 日志系统
  - 统一日志接口
  - 文件和控制台输出
  - 可配置日志级别

- **Validators** - 验证器
  - 交易对验证
  - 时间周期验证
  - API 密钥验证
  - 订单参数验证

## 📦 安装

```bash
# 确保已安装 backtrader 和 ccxt
pip install backtrader ccxt

# 从项目根目录使用
cd /path/to/backtrader
```

## 🚀 快速开始

### 方式 1: 使用便捷函数

```python
import backtrader as bt
from real_trade.bybit import create_bybit_engine

# 创建引擎（自动配置所有组件）
store, broker, data = create_bybit_engine(
    apikey='YOUR_API_KEY',
    secret='YOUR_SECRET',
    symbol='BTC/USDT',
    timeframe='1h',
    testnet=True,          # 使用测试网
    paper_trading=True,    # 模拟交易
    cash=10000.0
)

# 创建策略
class MyStrategy(bt.Strategy):
    def next(self):
        if not self.position:
            self.buy()
        else:
            self.sell()

# 运行回测
cerebro = bt.Cerebro()
cerebro.setbroker(broker)
cerebro.adddata(data)
cerebro.addstrategy(MyStrategy)
cerebro.run()
```

### 方式 2: 分步配置

```python
from real_trade.bybit import BybitStore, BybitBroker, BybitData
import backtrader as bt

# 1. 创建 Store
store = BybitStore.get_instance(
    apikey='YOUR_API_KEY',
    secret='YOUR_SECRET',
    testnet=True,
    proxy='http://127.0.0.1:7890'  # 可选代理
)

# 2. 创建 Broker
broker = BybitBroker(
    store,
    paper_trading=True,  # 模拟交易
    cash=10000.0
)

# 3. 创建 Data Feed
data = BybitData.from_timeframe_string(
    '1h',
    store,
    symbol='BTC/USDT',
    backtest=False  # False = 实时数据
)

# 4. 配置 Cerebro
cerebro = bt.Cerebro()
cerebro.setbroker(broker)
cerebro.adddata(data)
cerebro.addstrategy(MyStrategy)

# 5. 运行
cerebro.run()
```

### 方式 3: 使用配置文件

```python
from real_trade.bybit import Config, load_config_from_file, BybitStore, BybitBroker, BybitData

# 从文件加载配置
config = load_config_from_file('config.json')

# 或从环境变量
config = Config.from_env()

# 使用配置创建组件
store = BybitStore.get_instance(
    apikey=config.apikey,
    secret=config.secret,
    testnet=config.testnet
)

broker = BybitBroker(store, paper_trading=config.paper_trading, cash=config.initial_cash)
data = BybitData.from_timeframe_string(config.timeframe, store, symbol=config.symbol)
```

## 📖 使用示例

### 示例 1: 简单均线策略

```python
import backtrader as bt
from real_trade.bybit import create_bybit_engine

class SimpleMAStrategy(bt.Strategy):
    params = (('fast_period', 10), ('slow_period', 30),)

    def __init__(self):
        self.fast_ma = bt.indicators.SMA(period=self.p.fast_period)
        self.slow_ma = bt.indicators.SMA(period=self.p.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:  # 金叉
                self.buy()
        else:
            if self.crossover < 0:  # 死叉
                self.sell()

# 创建引擎
store, broker, data = create_bybit_engine(
    apikey='YOUR_KEY',
    secret='YOUR_SECRET',
    symbol='BTC/USDT',
    timeframe='1h',
    paper_trading=True
)

# 运行
cerebro = bt.Cerebro()
cerebro.setbroker(broker)
cerebro.adddata(data)
cerebro.addstrategy(SimpleMAStrategy)
cerebro.run()
```

### 示例 2: 回测模式

```python
from real_trade.bybit import BybitStore, BybitData
from datetime import datetime
import backtrader as bt

# 创建 Store（无需 API 密钥用于回测）
store = BybitStore.get_instance(testnet=True)

# 创建历史数据源
data = BybitData(
    store,
    symbol='BTC/USDT',
    backtest=True,  # 回测模式
    fromdate=datetime(2024, 1, 1),
    todate=datetime(2024, 12, 31),
    ccxt_timeframe='1h'
)

# 标准 backtrader 回测流程
cerebro = bt.Cerebro()
cerebro.adddata(data)
cerebro.addstrategy(MyStrategy)
cerebro.run()
cerebro.plot()
```

### 示例 3: 实盘交易

```python
from real_trade.bybit import create_bybit_engine

# ⚠️ 注意：这将使用真实资金！
store, broker, data = create_bybit_engine(
    apikey='YOUR_MAINNET_KEY',
    secret='YOUR_MAINNET_SECRET',
    symbol='BTC/USDT',
    timeframe='5m',
    testnet=False,         # 主网
    paper_trading=False,   # 真实交易
    cash=1000.0
)

# 其余配置相同...
```

## 🔧 配置管理

### 配置文件示例 (config.json)

```json
{
  "apikey": "YOUR_API_KEY",
  "secret": "YOUR_SECRET",
  "testnet": true,
  "proxy": null,
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "market_type": "spot",
  "paper_trading": true,
  "initial_cash": 10000.0,
  "commission": 0.001,
  "backtest": false,
  "log_level": "INFO"
}
```

### 环境变量配置

```bash
export BYBIT_API_KEY="your_key"
export BYBIT_API_SECRET="your_secret"
export BYBIT_TESTNET="true"
export BYBIT_SYMBOL="BTC/USDT"
export BYBIT_TIMEFRAME="1h"
export BYBIT_PAPER_TRADING="true"
export BYBIT_INITIAL_CASH="10000.0"
```

## 📊 支持的时间周期

| 周期 | 说明 | 周期 | 说明 |
|------|------|------|------|
| `1m` | 1分钟 | `1h` | 1小时 |
| `3m` | 3分钟 | `2h` | 2小时 |
| `5m` | 5分钟 | `4h` | 4小时 |
| `15m` | 15分钟 | `6h` | 6小时 |
| `30m` | 30分钟 | `12h` | 12小时 |
| | | `1d` | 1天 |
| | | `1w` | 1周 |
| | | `1M` | 1月 |

## 🛡️ 安全建议

1. **永远不要硬编码 API 密钥**
   - 使用环境变量
   - 使用配置文件（加入 .gitignore）
   - 使用密钥管理服务

2. **限制 API 权限**
   - 只授予必要的权限
   - 设置 IP 白名单
   - 定期轮换密钥

3. **先测试，再实盘**
   - 回测模式 → 模拟交易 → 测试网 → 小额实盘

4. **风险管理**
   - 设置止损
   - 控制仓位大小
   - 监控账户状态

## 🏗️ 项目结构

```
real-trade/bybit/
├── __init__.py              # 模块入口
├── store.py                 # BybitStore - 交易所连接管理
├── broker.py                # BybitBroker - 交易经纪商
├── datafeed.py              # BybitData - 数据源
│
├── utils/                   # 工具模块
│   ├── __init__.py
│   ├── config.py            # 配置管理
│   ├── logger.py            # 日志系统
│   └── validators.py        # 验证器
│
├── strategies/              # 策略库（待扩展）
│   └── __init__.py
│
├── examples/                # 示例代码
│   └── basic_trading.py     # 基础交易示例
│
├── tests/                   # 测试（待添加）
│   └── test_broker.py
│
└── README.md                # 本文档
```

## 🔌 API 参考

### BybitStore

```python
store = BybitStore.get_instance(
    apikey: str = "",
    secret: str = "",
    testnet: bool = True,
    proxy: str = None,
    market_type: str = "spot"  # spot, linear, inverse
)

# 方法
store.test_connection() -> bool
store.get_balance(currency='USDT') -> float
store.get_total_value(currency='USDT') -> float
store.get_positions(symbols=None) -> list
store.get_open_orders(symbol=None) -> list
```

### BybitBroker

```python
broker = BybitBroker(
    store: BybitStore,
    paper_trading: bool = True,
    base_currency: str = "USDT",
    cash: float = 10000.0
)

# 方法
broker.getcash() -> float
broker.getvalue() -> float
broker.getposition(data) -> bt.Position
broker.submit(order) -> order
broker.cancel(order)
broker.get_paper_summary() -> dict
```

### BybitData

```python
data = BybitData.from_timeframe_string(
    timeframe_str: str,  # '1m', '1h', '1d' etc.
    store: BybitStore,
    symbol: str = "BTC/USDT",
    backtest: bool = False,
    fromdate: datetime = None,
    todate: datetime = None
)

# 或者
data = BybitData(
    store: BybitStore,
    symbol: str = "BTC/USDT",
    timeframe: bt.TimeFrame = bt.TimeFrame.Minutes,
    compression: int = 1,
    ccxt_timeframe: str = "1m",
    backtest: bool = False
)
```

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

## 📄 许可证

本项目遵循 GNU General Public License v3.0 许可证。

## 🔗 相关资源

- [Backtrader 文档](https://www.backtrader.com/)
- [CCXT 文档](https://docs.ccxt.com/)
- [Bybit API 文档](https://bybit-exchange.github.io/docs/)
- [项目架构文档](../../.claude/architecture.md)

---

**⚠️ 风险警告**: 加密货币交易存在高风险，可能导致资金损失。本模块仅供学习和研究使用，使用者需自行承担所有风险。
