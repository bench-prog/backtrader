# 配置文件说明

## 配置方式

系统支持三种配置方式：

### 1. JSON 文件

```python
from real_trade.utils.config import GlobalConfig
from real_trade.stores import BinanceStore
from real_trade.brokers import BinanceBroker
from real_trade.feeds import BinanceData

cfg = GlobalConfig.from_json("config/binance/my_config.json")

store = BinanceStore.get_instance(
    apikey=cfg.apikey,
    secret=cfg.secret,
    testnet=cfg.testnet,
    market_type=cfg.market_type,
)
broker = BinanceBroker(store, paper_trading=cfg.paper_trading, cash=cfg.cash)
data = BinanceData.from_timeframe_string(cfg.timeframe, store, symbol=cfg.symbol, backtest=cfg.backtest)
```

### 2. GlobalConfig 对象

```python
from real_trade.utils.config import GlobalConfig

cfg = GlobalConfig(symbol="ETH/USDT", timeframe="15m", backtest=True)
```

### 3. 使用 TradingRunner（推荐）

```python
from real_trade.engine import TradingRunner

runner = TradingRunner(
    exchange="binance",
    symbol="BTC/USDT",
    timeframe="1h",
    strategy_cls=MyStrategy,
    backtest=True,
)
runner.run()
```

## JSON 配置格式

推荐使用**扁平结构**（与 `GlobalConfig` 字段完全一致）：

```json
{
  "exchange": "binance",
  "apikey": "",
  "secret": "",
  "testnet": true,
  "market_type": "future",
  "symbol": "BTC/USDT",
  "timeframe": "15m",
  "paper_trading": true,
  "cash": 10000.0,
  "commission": 0.001,
  "backtest": true,
  "historical_limit": 500
}
```

## 核心参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `apikey` | str | "" | API Key |
| `secret` | str | "" | API Secret |
| `testnet` | bool | true | true: Demo Trading; false: 生产环境 |
| `market_type` | str | "spot" | spot / future / delivery |
| `symbol` | str | "BTC/USDT" | 交易对 |
| `timeframe` | str | "1h" | K线周期 (1m, 5m, 15m, 1h, 4h, 1d 等) |
| `paper_trading` | bool | true | true: 本地模拟; false: 真实发送订单 |
| `cash` | float | 10000.0 | 初始资金 |
| `commission` | float | 0.001 | 手续费率 (0.001 = 0.1%) |
| `backtest` | bool | false | true: 历史数据回测; false: 实时数据 |
| `historical_limit` | int | 1000 | 加载K线数量 |
| `fromdate` | str | null | 回测起始日期 "2024-01-01" |
| `todate` | str | null | 回测结束日期 |
| `proxy` | str | null | 代理地址，null 时自动检测系统代理 |

## 运行模式

### 回测（最快，不需要 API 密钥）

```json
{"backtest": true, "paper_trading": true}
```

### Demo Trading 实盘测试

```json
{"testnet": true, "paper_trading": false, "backtest": false}
```

需要 Demo Trading API 密钥。

### 生产实盘（谨慎！）

```json
{"testnet": false, "paper_trading": false, "backtest": false}
```

真实资金交易，请充分测试后使用。

## 工具

```bash
# 交互式生成配置文件
python real_trade/tools/binance/config_generator.py

# 验证配置文件
python real_trade/tools/binance/config_validator.py my_config.json
```

## 获取 Demo Trading API 密钥

- Futures: https://testnet.binancefuture.com/ (GitHub 登录)
- Spot: https://testnet.binance.vision/

## 安全建议

1. 不要提交包含真实密钥的配置文件到 Git
2. `.gitignore` 已排除所有 `*.json`，仅保留 `*.json.template`
3. 建议使用环境变量存储生产环境密钥（`RT_APIKEY`, `RT_SECRET`）
