# Bybit Live Trading with CCXT

这个示例展示了如何使用CCXT库连接Bybit交易所，并通过backtrader执行实时交易。

## 功能特性

- ✅ 实时数据流（从Bybit获取OHLCV数据）
- ✅ **新增：CCXTBybitBroker** - 真实的交易所broker实现
- ✅ **新增：模拟交易模式（Paper Trading）** - 使用实时数据但本地模拟订单
- ✅ 实时订单执行
- ✅ 仓位管理
- ✅ 简单移动平均线交叉策略
- ✅ 支持测试网（模拟交易）
- ✅ 支持回测模式（历史数据）
- ✅ 支持实盘交易
- ✅ 支持代理连接

## 三种交易模式

### 1. 回测模式（Backtest Mode）
- 使用历史数据
- 快速验证策略逻辑
- 不需要API密钥

### 2. 模拟交易模式（Paper Trading Mode）⭐ 推荐
- 使用实时市场数据
- 订单在本地模拟执行
- 不会产生真实交易
- **这是默认模式**

### 3. 实盘交易模式（Live Trading Mode）⚠️
- 真实订单发送到交易所
- 使用真实资金
- 需要谨慎使用

## 安装依赖

```bash
pip install ccxt
```

## 获取API密钥

### 测试网（推荐用于学习）

1. 访问 [Bybit Testnet](https://testnet.bybit.com/)
2. 注册账号
3. 进入 API Management 创建API密钥
4. 保存 API Key 和 Secret

### 实盘（谨慎使用）

1. 访问 [Bybit](https://www.bybit.com/)
2. 注册并完成KYC
3. 进入 API Management 创建API密钥
4. 设置IP白名单和权限

## 使用方法

### 1. 回测模式（推荐先测试策略）

使用历史数据测试策略，无需API密钥：

```bash
python bybit-live-trading.py --backtest --symbol BTC/USDT --fromdate 2024-01-01 --plot
```

参数说明：
- `--backtest`: 启用回测模式
- `--symbol`: 交易对（如 BTC/USDT, ETH/USDT）
- `--fromdate`: 开始日期
- `--todate`: 结束日期（可选，默认到最新）
- `--plot`: 绘制结果图表

### 2. 模拟交易模式（Paper Trading）⭐ 推荐

**这是默认模式**，使用实时数据但订单只在本地模拟：

```bash
python bybit-live-trading.py \
    --apikey YOUR_API_KEY \
    --secret YOUR_SECRET \
    --symbol BTC/USDT \
    --paper-trading \
    --verbose
```

**特点**：
- ✅ 使用真实市场数据
- ✅ 订单在本地模拟执行
- ✅ 不会产生真实交易
- ✅ 适合测试策略在实时市场的表现

参数说明：
- `--paper-trading`: 启用模拟交易（默认已启用）
- `--verbose`: 显示详细日志

### 3. 测试网交易（推荐用于测试真实订单）

在Bybit测试网上执行真实订单（使用测试资金）：

```bash
python bybit-live-trading.py \
    --testnet \
    --apikey YOUR_TESTNET_API_KEY \
    --secret YOUR_TESTNET_SECRET \
    --symbol BTC/USDT \
    --no-paper-trading \
    --verbose
```

参数说明：
- `--testnet`: 使用测试网
- `--no-paper-trading`: 禁用模拟交易，发送真实订单
- `--apikey`: 测试网API密钥
- `--secret`: 测试网密钥

### 4. 实盘交易（谨慎使用！）

### 4. 实盘交易（谨慎使用！）

**警告：实盘交易涉及真实资金，请确保充分测试策略后再使用！**

```bash
python bybit-live-trading.py \
    --apikey YOUR_API_KEY \
    --secret YOUR_SECRET \
    --symbol BTC/USDT \
    --no-paper-trading \
    --order-size 0.001 \
    --verbose
```

参数说明：
- `--no-paper-trading`: **必须明确指定才会发送真实订单**
- `--order-size`: 每次交易的数量（基础货币单位，如0.001 BTC）

### 5. 使用代理连接

如果需要通过代理连接交易所：

```bash
python bybit-live-trading.py \
    --apikey YOUR_KEY \
    --secret YOUR_SECRET \
    --proxy http://127.0.0.1:7890 \
    --symbol BTC/USDT
```

## 策略参数

### 移动平均线参数

```bash
python bybit-live-trading.py \
    --backtest \
    --fast-period 10 \
    --slow-period 30
```

- `--fast-period`: 快速移动平均线周期（默认10）
- `--slow-period`: 慢速移动平均线周期（默认30）

### 交易参数

```bash
python bybit-live-trading.py \
    --backtest \
    --cash 10000 \
    --commission 0.001 \
    --order-size 0.01
```

- `--cash`: 初始资金（默认10000 USDT）
- `--commission`: 手续费率（默认0.001 = 0.1%）
- `--order-size`: 订单大小（默认0.01）

### 时间周期

```bash
python bybit-live-trading.py \
    --backtest \
    --timeframe 1h
```

支持的时间周期：
- `1m`: 1分钟
- `5m`: 5分钟
- `15m`: 15分钟
- `30m`: 30分钟
- `1h`: 1小时
- `4h`: 4小时
- `1d`: 1天

## 策略说明

### 简单移动平均线交叉策略

这是一个经典的趋势跟踪策略：

**买入信号**：
- 当快速移动平均线（默认10周期）向上穿过慢速移动平均线（默认30周期）时买入

**卖出信号**：
- 当快速移动平均线向下穿过慢速移动平均线时卖出

**风险提示**：
- 这是一个简单的示例策略，仅用于教学目的
- 实际交易前请充分回测和优化策略
- 建议添加止损、止盈等风险管理措施

## 完整示例

### 示例1：回测BTC/USDT（2024年数据）

```bash
python bybit-live-trading.py \
    --backtest \
    --symbol BTC/USDT \
    --timeframe 1h \
    --fromdate 2024-01-01 \
    --todate 2024-12-31 \
    --fast-period 10 \
    --slow-period 30 \
    --cash 10000 \
    --commission 0.001 \
    --plot \
    --verbose
```

### 示例2：测试网实时交易

```bash
python bybit-live-trading.py \
    --testnet \
    --apikey YOUR_TESTNET_KEY \
    --secret YOUR_TESTNET_SECRET \
    --symbol BTC/USDT \
    --timeframe 5m \
    --order-size 0.001 \
    --verbose
```

### 示例3：回测ETH/USDT

```bash
python bybit-live-trading.py \
    --backtest \
    --symbol ETH/USDT \
    --timeframe 4h \
    --fromdate 2024-01-01 \
    --plot
```

## 代码结构

### SMACrossStrategy 类

实现简单移动平均线交叉策略：
- `__init__()`: 初始化指标
- `next()`: 每个bar执行的逻辑
- `notify_order()`: 订单状态通知
- `notify_trade()`: 交易完成通知

### CCXTBybitData 类

CCXT数据源实现：
- `__init__()`: 初始化CCXT连接
- `_load_historical_data()`: 加载历史数据（回测模式）
- `_load_live()`: 加载实时数据（实盘模式）

### CCXTBybitBroker 类 ⭐ 新增

真实的交易所broker实现：

**核心方法**：
- `getcash()`: 获取可用余额
- `getvalue()`: 获取账户总价值
- `getposition()`: 获取持仓信息
- `submit()`: 提交订单
- `cancel()`: 取消订单

**模拟交易模式**：
- 本地计算持仓和余额
- 模拟订单执行
- 检查保证金是否足够
- 不发送真实订单到交易所

**实盘交易模式**：
- 向交易所发送真实订单
- 从交易所获取账户信息
- 实时查询订单状态
- 支持订单取消

## 注意事项

### 安全建议

1. **永远不要在代码中硬编码API密钥**
2. **使用环境变量存储敏感信息**
3. **设置API密钥的IP白名单**
4. **限制API密钥的权限（只开启交易权限）**
5. **定期更换API密钥**

### 交易建议

1. **先在回测模式充分测试策略**
2. **然后在测试网进行模拟交易**
3. **最后才考虑小额实盘交易**
4. **设置合理的止损和仓位管理**
5. **不要投入超过承受能力的资金**

### 技术建议

1. **监控网络连接状态**
2. **处理API限流**
3. **记录所有交易日志**
4. **定期检查账户余额**
5. **实现异常处理和重连机制**

## 扩展功能

你可以基于这个示例添加更多功能：

1. **更复杂的策略**：
   - RSI、MACD、布林带等技术指标
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

## 故障排除

### 问题1：CCXT模块未找到

```bash
pip install ccxt
```

### 问题2：API连接失败

- 检查API密钥是否正确
- 检查网络连接
- 检查是否使用了正确的测试网/实盘设置
- 检查IP白名单设置

### 问题3：订单被拒绝

- 检查账户余额
- 检查订单大小是否符合交易所要求
- 检查API权限设置

### 问题4：数据加载失败

- 检查交易对符号是否正确（如 BTC/USDT）
- 检查时间周期是否支持
- 检查网络连接

## 相关资源

- [CCXT文档](https://docs.ccxt.com/)
- [Bybit API文档](https://bybit-exchange.github.io/docs/)
- [Backtrader文档](https://www.backtrader.com/docu/)
- [Bybit测试网](https://testnet.bybit.com/)

## 免责声明

本示例仅用于教育和学习目的。加密货币交易存在高风险，可能导致资金损失。使用本代码进行实盘交易的任何损失，作者不承担任何责任。请在充分了解风险的情况下谨慎交易。
