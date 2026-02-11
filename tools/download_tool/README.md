# 数据下载工具

三个数据下载脚本，输出格式兼容 backtrader。

## 工具对比

| 工具 | 数据源 | 适用市场 |
|------|--------|----------|
| **yahoodownload.py** | Yahoo Finance | 全球股票、指数、期货、外汇、加密货币 |
| **aksharedownload.py** | AkShare | 中国A股、指数、基金、国内期货、国际期货 |
| **ccxtdownload.py** | CCXT | 加密货币交易所 (200+) |

## 使用示例

### 国际黄金数据

```bash
# Yahoo Finance (推荐 - 数据更完整)
python yahoodownload.py --ticker GC=F --fromdate 2015-01-01 --todate 2026-01-01 --outfile gold.txt

# AkShare (国内访问快)
python aksharedownload.py --symbol GC --market foreign_futures --fromdate 2015-01-01 --todate 2026-01-01 --outfile gold.txt
```

### 中国A股

```bash
# 平安银行，前复权
python aksharedownload.py --symbol 000001 --market stock --adjust qfq --fromdate 2015-01-01 --todate 2026-01-01 --outfile pingan.txt
```

### 美股

```bash
# 苹果股票
python yahoodownload.py --ticker AAPL --fromdate 2015-01-01 --todate 2026-01-01 --outfile aapl.txt
```

### 加密货币

```bash
# 比特币 (CCXT - 推荐)
python ccxtdownload.py --exchange binance --symbol BTC/USDT --timeframe 1d --fromdate 2020-01-01 --todate 2026-01-01 --outfile btc.txt

# 比特币 (Yahoo Finance)
python yahoodownload.py --ticker BTC-USD --fromdate 2020-01-01 --todate 2026-01-01 --outfile btc.txt
```

## 常用代码

**Yahoo Finance:**
- 黄金: GC=F (期货), GLD (ETF)
- 原油: CL=F
- 指数: ^GSPC (标普500), ^DJI (道琼斯)

**AkShare:**
- A股: 000001 (平安银行), 600519 (茅台)
- 指数: sh000001 (上证), sz399001 (深成指)
- 国内期货: AU0 (黄金主力), CU0 (铜主力)
- 国际期货: GC (黄金), SI (白银), CL (原油)

**CCXT:**
- 交易所: binance, okx, huobi, coinbase
- 交易对: BTC/USDT, ETH/USDT
