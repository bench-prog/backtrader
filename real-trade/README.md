# Real Trade Module

专业的实盘交易模块集合，为 Backtrader 提供真实交易所的集成。

## 📁 模块结构

```
real-trade/
├── __init__.py              # 模块入口
│
├── bybit/                   # Bybit 交易所模块 ✅
│   ├── __init__.py          # Bybit 入口
│   ├── store.py             # 交易所连接管理
│   ├── broker.py            # 交易经纪商
│   ├── datafeed.py          # 数据源
│   ├── utils/               # 工具模块
│   ├── strategies/          # 策略库
│   ├── examples/            # 示例代码
│   └── README.md            # Bybit 详细文档
│
├── binance/                 # Binance 交易所模块 🚧 计划中
│
├── okx/                     # OKX 交易所模块 🚧 计划中
│
└── README.md                # 本文档
```

## 🎯 当前状态

### ✅ 已完成
- **Bybit 模块** - 完整实现，支持模拟和实盘交易

### 🚧 计划中
- **Binance 模块** - 待开发
- **OKX 模块** - 待开发
- **Huobi 模块** - 待开发

## 🚀 快速开始

### Bybit 交易

```python
from real_trade.bybit import create_bybit_engine
import backtrader as bt

# 创建 Bybit 交易引擎
store, broker, data = create_bybit_engine(
    apikey='YOUR_API_KEY',
    secret='YOUR_SECRET',
    symbol='BTC/USDT',
    timeframe='1h',
    testnet=True,
    paper_trading=True,
    cash=10000.0
)

# 定义策略
class MyStrategy(bt.Strategy):
    def next(self):
        if not self.position:
            self.buy()
        else:
            self.sell()

# 运行
cerebro = bt.Cerebro()
cerebro.setbroker(broker)
cerebro.adddata(data)
cerebro.addstrategy(MyStrategy)
cerebro.run()
```

## 📖 详细文档

每个交易所模块都有自己的详细文档：

- **Bybit**: [real-trade/bybit/README.md](bybit/README.md)
- **Binance**: 待添加
- **OKX**: 待添加

## 🏗️ 架构设计

### 核心组件

每个交易所模块都遵循统一的架构：

```
Store (交易所连接) → Broker (经纪商) → Strategy (策略)
                  ↓
              Data Feed (数据源) → Strategy (策略)
```

1. **Store** - 管理与交易所的连接
   - 单例模式
   - 连接池
   - API 调用封装

2. **Broker** - 处理订单和持仓
   - 模拟交易模式
   - 实盘交易模式
   - 订单管理
   - 资金管理

3. **Data Feed** - 提供市场数据
   - 实时数据流
   - 历史数据加载
   - 多时间周期

4. **Utils** - 工具模块
   - 配置管理
   - 日志系统
   - 验证器

### 设计原则

- **模块化**: 每个交易所独立模块
- **可扩展**: 易于添加新交易所
- **统一接口**: 相同的 API 设计
- **安全第一**: 默认模拟交易模式

## 🔌 统一 API

所有交易所模块遵循统一的 API 设计：

```python
# 创建引擎（便捷函数）
store, broker, data = create_xxx_engine(
    apikey='key',
    secret='secret',
    symbol='BTC/USDT',
    timeframe='1h',
    testnet=True,
    paper_trading=True
)

# 或分步配置
from real_trade.xxx import XXXStore, XXXBroker, XXXData

store = XXXStore.get_instance(...)
broker = XXXBroker(store, ...)
data = XXXData.from_timeframe_string(..., store)
```

## 🛡️ 安全特性

1. **默认安全**: 所有模块默认启用模拟交易
2. **多层防护**:
   - 测试网优先
   - 模拟交易模式
   - 参数验证
3. **明确确认**: 真实交易需要明确指定

## 🤝 贡献指南

### 添加新交易所

1. 创建新目录：`real-trade/exchange_name/`
2. 实现核心组件：
   - `store.py`
   - `broker.py`
   - `datafeed.py`
   - `utils/`
3. 编写文档：`README.md`
4. 添加示例：`examples/`
5. 编写测试：`tests/`

### 代码规范

- 遵循 PEP 8
- 添加类型注解
- 编写文档字符串
- 添加单元测试

## 📄 许可证

本项目遵循 GNU General Public License v3.0 许可证。

## 🔗 相关资源

- [Backtrader 官网](https://www.backtrader.com/)
- [CCXT 文档](https://docs.ccxt.com/)
- [项目架构文档](../.claude/architecture.md)
- [快速开始指南](../.claude/quickstart.md)
- [实战示例集](../.claude/examples.md)

## ⚠️ 风险警告

加密货币交易存在高风险，可能导致资金损失。本模块仅供学习和研究使用，使用者需自行承担所有风险。

**在使用真实资金前，请务必：**
1. 充分测试策略
2. 从小额开始
3. 设置止损
4. 不要投入超过承受能力的资金

---

**版本**: 1.0.0
**最后更新**: 2026-02-07
