# 配置文件说明

## 可用配置文件

| 文件 | 用途 | API密钥 |
|------|------|---------|
| `futures_backtest.json` | 历史数据回测 | 不需要 |
| `futures_live_demo.json` | Demo Trading 实盘测试 | 需要 |
| `*.template` | 配置模板 | - |

## 配置文件结构

```json
{
  "api": {
    "apikey": "",                   // API 密钥
    "secret": "",                   // Secret
    "testnet": true,                // true: Demo Trading; false: 生产环境
    "market_type": "future"         // spot: 现货; future: 合约
  },
  "trading": {
    "paper_trading": true,          // true: 本地模拟; false: 真实发送订单
    "initial_cash": 10000.0,        // 初始资金
    "commission": 0.001             // 手续费率 (0.001 = 0.1%)
  },
  "data": {
    "symbol": "BTC/USDT",           // 交易对
    "timeframe": "15m",             // K线周期 (1m, 5m, 15m, 1h, 4h, 1d等)
    "backtest": true,               // true: 历史数据; false: 实时数据
    "historical_limit": 500         // 加载K线数量
  },
  "strategy": {
    // 策略参数（可选，根据策略自定义）
    "rsi_period": 7,
    "ma_fast": 3,
    "ma_slow": 10
  },
  "proxy": {
    "auto_detect": true,            // 自动检测系统代理
    "proxy_url": ""                 // 手动指定代理
  }
}
```

## 三个关键配置

### 1. `testnet` - 环境选择
- `true`: 连接 Demo Trading（虚拟资金）
- `false`: 连接生产环境（真实资金）

### 2. `paper_trading` - 订单执行
- `true`: 订单只在本地模拟，**不发送**到交易所
- `false`: 订单**真实发送**到交易所

### 3. `backtest` - 数据模式
- `true`: 使用历史数据回测
- `false`: 使用实时数据流

## 运行模式组合

### 模式 1：回测（最快）⭐
```json
{"data": {"backtest": true}, "trading": {"paper_trading": true}}
```
- 历史数据 + 本地模拟
- 不需要 API 密钥
- 适合策略开发

**使用：** `futures_backtest.json`

### 模式 2：Demo Trading 实盘（推荐测试）⭐
```json
{"api": {"testnet": true}, "data": {"backtest": false}, "trading": {"paper_trading": false}}
```
- 连接 Demo Trading
- 真实订单流程
- 虚拟资金
- 适合上线前测试

**使用：** `futures_live_demo.json`

### 模式 3：生产实盘（谨慎！）
```json
{"api": {"testnet": false}, "data": {"backtest": false}, "trading": {"paper_trading": false}}
```
- 真实资金交易
- 需充分测试

## 使用方法

### 1. 从配置文件创建引擎
```python
from real_trade.binance import create_binance_engine_from_config

store, broker, data, config = create_binance_engine_from_config("futures_backtest.json")
```

### 2. 读取配置值
```python
from real_trade.binance import load_binance_config, get_config_value

config = load_binance_config("futures_backtest.json")
symbol = get_config_value(config, "data.symbol", "BTC/USDT")
rsi_period = get_config_value(config, "strategy.rsi_period", 14)
```

### 3. 创建自定义配置
```bash
# 方法1：交互式生成
cd ../tools && python config_generator.py

# 方法2：复制模板
cp futures_testnet.json.template my_config.json
# 编辑 my_config.json
```

### 4. 验证配置
```bash
cd ../tools && python config_validator.py my_config.json
```

## 获取 Demo Trading API 密钥

### Futures（合约）
1. 访问 https://testnet.binancefuture.com/
2. GitHub 登录
3. 生成 API Key

### Spot（现货）
1. 访问 https://testnet.binance.vision/
2. 注册并生成密钥

## 安全建议

⚠️ **重要：**
1. 不要提交包含真实密钥的配置文件到 Git
2. `.gitignore` 已自动配置
3. Demo Trading 不影响真实资金
4. 建议使用环境变量存储生产环境密钥

## 常见问题

**Q: testnet=true 还需要 paper_trading 吗？**

A: 是的，它们控制不同层级：
- `testnet=true` → 连接到 Demo Trading 环境
- `paper_trading=false` → 真实发送订单到 Demo Trading
- 组合使用可以测试完整订单流程

**Q: backtest=true 时需要 API 密钥吗？**

A: 不需要。回测模式只使用历史数据，不连接交易所。

**Q: 如何切换到生产环境？**

A: 创建新配置文件，设置 `testnet=false`，并使用生产环境 API 密钥。**谨慎操作！**
