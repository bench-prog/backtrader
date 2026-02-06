# Bybit CCXT 交易示例创建完成

## 📁 文件位置

- **主程序**: `samples/ccxt-bybit/bybit-live-trading.py`
- **文档**: `samples/ccxt-bybit/README.md`

## ✅ 功能特性

### 1. 多种运行模式
- **回测模式** (`--backtest`): 使用历史数据测试策略
- **测试网模式** (`--testnet`): 使用Bybit测试网进行模拟交易
- **实盘模式** (`--live`): 真实交易（需谨慎使用）

### 2. 策略实现
- 简单移动平均线交叉策略（SMA Crossover）
- 可自定义快速/慢速MA周期
- 完整的订单和交易通知

### 3. 数据源
- 基于CCXT库连接Bybit交易所
- 支持多种时间周期（1m, 5m, 15m, 30m, 1h, 4h, 1d）
- 支持代理配置

### 4. 风险管理
- 可配置订单大小
- 可配置手续费率
- 可配置初始资金

## 🚀 使用示例

### 回测模式（推荐先测试）

```bash
# 基本回测
python bybit-live-trading.py \
    --backtest \
    --symbol BTC/USDT \
    --timeframe 1h \
    --fromdate 2024-01-01 \
    --todate 2024-01-31 \
    --proxy http://127.0.0.1:7890

# 带详细日志和图表
python bybit-live-trading.py \
    --backtest \
    --symbol BTC/USDT \
    --timeframe 1h \
    --fromdate 2024-01-01 \
    --todate 2024-01-31 \
    --proxy http://127.0.0.1:7890 \
    --verbose \
    --plot

# 自定义策略参数
python bybit-live-trading.py \
    --backtest \
    --symbol ETH/USDT \
    --timeframe 4h \
    --fromdate 2024-01-01 \
    --fast-period 5 \
    --slow-period 20 \
    --cash 50000 \
    --commission 0.0005 \
    --proxy http://127.0.0.1:7890
```

### 测试网模拟交易

```bash
python bybit-live-trading.py \
    --testnet \
    --apikey YOUR_TESTNET_API_KEY \
    --secret YOUR_TESTNET_SECRET \
    --symbol BTC/USDT \
    --timeframe 5m \
    --order-size 0.001 \
    --verbose
```

### 实盘交易（谨慎使用！）

```bash
python bybit-live-trading.py \
    --live \
    --apikey YOUR_API_KEY \
    --secret YOUR_SECRET \
    --symbol BTC/USDT \
    --timeframe 5m \
    --order-size 0.001 \
    --verbose
```

## 📊 测试结果

```bash
# 测试运行（2024-01-01 到 2024-01-07，1小时周期）
Loading historical data for BTC/USDT...
Loaded 1999 candles
Starting Portfolio Value: 10000.00
Final Portfolio Value: 9991.50
```

## 🔧 技术实现

### CCXTBybitData 类
自定义数据源，继承自 `bt.DataBase`：
- 支持历史数据加载（回测模式）
- 支持实时数据流（实盘模式）
- 自动处理时间周期转换
- 代理支持

### SMACrossStrategy 类
移动平均线交叉策略：
- 快速MA上穿慢速MA时买入
- 快速MA下穿慢速MA时卖出
- 完整的订单和交易通知

## ⚠️ 重要提示

### 安全建议
1. **永远不要在代码中硬编码API密钥**
2. **先在回测模式充分测试**
3. **然后在测试网进行模拟交易**
4. **最后才考虑小额实盘交易**
5. **设置API密钥的IP白名单**

### 代理配置
由于网络限制，访问Bybit需要代理：
```bash
--proxy http://127.0.0.1:7890
```

或设置环境变量：
```bash
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
```

## 📚 相关资源

- [CCXT文档](https://docs.ccxt.com/)
- [Bybit API文档](https://bybit-exchange.github.io/docs/)
- [Backtrader文档](https://www.backtrader.com/docu/)
- [Bybit测试网](https://testnet.bybit.com/)

## 🎯 下一步

可以基于这个示例进行扩展：

1. **更复杂的策略**：
   - 添加RSI、MACD等技术指标
   - 多时间周期分析
   - 机器学习预测

2. **风险管理**：
   - 止损止盈
   - 仓位管理
   - 最大回撤控制

3. **通知功能**：
   - 邮件通知
   - Telegram机器人
   - 微信通知

4. **数据持久化**：
   - 保存交易记录到数据库
   - 导出交易报告
   - 性能分析

## 免责声明

本示例仅用于教育和学习目的。加密货币交易存在高风险，可能导致资金损失。使用本代码进行实盘交易的任何损失，作者不承担任何责任。请在充分了解风险的情况下谨慎交易。
