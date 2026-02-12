#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Dynamic Grid Trading Bot for Binance - Binance动态网格交易机器人
==================================================================

基于真实BTC数据的动态网格交易策略实现。
该策略会根据市场波动动态调整网格间距和仓位大小。

核心特性:
- 动态网格间距调整（基于ATR和波动率）
- 智能仓位管理（基于账户资金和风险控制）
- 实时止损和止盈机制
- 网格密度自适应调节
- 支持真实数据回测和模拟交易

策略原理:
1. 在价格区间内设置多个网格点
2. 价格触及网格线时自动买卖
3. 根据波动率动态调整网格密度
4. 通过均值回归获取收益
"""

import logging
import math
import os
import sys

import pandas as pd

# 添加项目路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

import backtrader as bt

# 简单日志配置
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


class DynamicGridStrategy(bt.Strategy):
    """
    动态网格交易策略

    参数说明:
    - grid_levels: 网格层数
    - grid_spacing: 基础网格间距比例
    - atr_period: ATR计算周期
    - risk_percent: 每笔交易风险百分比
    - max_positions: 最大持仓数量
    - take_profit_ratio: 止盈比例
    - stop_loss_ratio: 止损比例
    """

    params = (
        ("grid_levels", 10),  # 网格层数
        ("grid_spacing", 0.02),  # 基础网格间距(2%)
        ("atr_period", 14),  # ATR周期
        ("risk_percent", 0.01),  # 每笔风险1%
        ("max_positions", 5),  # 最大持仓数
        ("take_profit_ratio", 0.03),  # 止盈3%
        ("stop_loss_ratio", 0.02),  # 止损2%
        ("printlog", True),  # 是否打印日志
    )

    def __init__(self):
        """初始化策略"""
        # 技术指标
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        self.sma = bt.indicators.SMA(period=20)

        # 网格相关变量
        self.grid_prices = []  # 网格价格点
        self.active_orders = {}  # 活跃订单字典
        self.position_prices = {}  # 持仓价格记录
        self.last_grid_update = None  # 上次网格更新时间

        # 风险管理变量
        self.initial_cash = self.broker.get_cash()
        self.max_drawdown = 0
        self.peak_value = self.initial_cash

        # 统计变量
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0

        if self.p.printlog:
            logger.info("🎯 动态网格交易策略初始化完成")
            logger.info(
                f"📊 参数设置: 网格层数={self.p.grid_levels}, 基础间距={self.p.grid_spacing * 100:.1f}%"
            )

    def start(self):
        """策略开始时调用"""
        # 初始化网格
        self._initialize_grid()

    def next(self):
        """每个时间周期调用"""
        current_price = self.data.close[0]

        # 更新风险管理统计
        self._update_risk_stats()

        # 动态调整网格（每6小时检查一次）
        if (
            self.last_grid_update is None or len(self) - self.last_grid_update > 72
        ):  # 假设1小时K线，72 = 6小时
            self._adjust_grid_dynamically()
            self.last_grid_update = len(self)

        # 检查现有订单触发
        self._check_order_triggers(current_price)

        # 检查止盈止损
        self._check_take_profit_stop_loss(current_price)

        # 记录日志
        if self.p.printlog and len(self) % 24 == 0:  # 每天打印一次
            self._print_status()

    def _initialize_grid(self):
        """初始化网格"""
        current_price = self.data.close[0]

        # 计算动态网格间距
        dynamic_spacing = self._calculate_dynamic_spacing()

        # 在当前价格上下创建网格
        self.grid_prices = []
        mid_point = self.p.grid_levels // 2

        for i in range(self.p.grid_levels):
            # 网格价格 = 当前价格 × (1 ± 动态间距)^距离
            distance = i - mid_point
            grid_price = current_price * (1 + dynamic_spacing) ** distance
            self.grid_prices.append(grid_price)

        if self.p.printlog:
            logger.info(f"🔗 网格初始化完成，当前价格: ${current_price:.2f}")
            logger.info(f"📏 动态网格间距: {dynamic_spacing * 100:.2f}%")
            logger.info(
                f"📊 网格价格点: {[f'${p:.2f}' for p in self.grid_prices[:3]]} ... {[f'${p:.2f}' for p in self.grid_prices[-3:]]}"
            )

    def _calculate_dynamic_spacing(self) -> float:
        """计算动态网格间距"""
        if len(self.atr) < self.p.atr_period:
            return self.p.grid_spacing

        # 基于ATR和价格的动态间距
        current_atr = self.atr[0]
        current_price = self.data.close[0]
        atr_ratio = current_atr / current_price  # ATR占价格的比例

        # 基础间距 × (1 + ATR比率调整)
        # 市场波动大时增加网格间距，波动小时减小间距
        volatility_multiplier = 1 + min(atr_ratio * 10, 2)  # 最大调整200%
        dynamic_spacing = self.p.grid_spacing * volatility_multiplier

        # 限制在合理范围内
        return max(min(dynamic_spacing, 0.05), 0.01)  # 1%-5%之间

    def _adjust_grid_dynamically(self):
        """动态调整网格"""
        current_price = self.data.close[0]
        old_prices = self.grid_prices.copy()

        # 重新初始化网格
        self._initialize_grid()

        if self.p.printlog:
            price_change = (
                (current_price - old_prices[len(old_prices) // 2])
                / old_prices[len(old_prices) // 2]
                * 100
            )
            logger.info(f"🔄 网格动态调整 (价格变化: {price_change:+.2f}%)")

    def _check_order_triggers(self, current_price: float):
        """检查订单触发"""
        # 检查是否有新的网格点被触及
        for i, grid_price in enumerate(self.grid_prices):
            grid_key = f"grid_{i}"

            # 检查向上穿越（做空机会）
            if (
                len(self.data.close) > 1
                and self.data.close[-1] < grid_price <= current_price
                and grid_key not in self.active_orders
            ):
                self._place_sell_order(grid_price, grid_key)

            # 检查向下穿越（做多机会）
            elif (
                len(self.data.close) > 1
                and self.data.close[-1] > grid_price >= current_price
                and grid_key not in self.active_orders
            ):
                self._place_buy_order(grid_price, grid_key)

    def _place_buy_order(self, price: float, grid_key: str):
        """放置买单"""
        # 检查持仓限制
        if len(self.position_prices) >= self.p.max_positions:
            if self.p.printlog:
                logger.info(f"⚠️ 达到最大持仓限制 ({self.p.max_positions})，跳过买单")
            return

        # 计算仓位大小
        position_size = self._calculate_position_size(price, "buy")

        if position_size > 0:
            # 下买单
            order = self.buy(size=position_size, price=price, exectype=bt.Order.Limit)
            self.active_orders[grid_key] = {
                "order": order,
                "type": "buy",
                "price": price,
                "size": position_size,
            }

            if self.p.printlog:
                logger.info(f"📈 下买单: 价格${price:.2f}, 数量{position_size:.4f}")

    def _place_sell_order(self, price: float, grid_key: str):
        """放置卖单"""
        # 检查是否有对应的多头持仓
        buy_grid_key = grid_key  # 简化处理，实际应匹配对应买单
        if buy_grid_key in self.position_prices:
            position_info = self.position_prices[buy_grid_key]

            # 下卖单平仓
            order = self.sell(
                size=position_info["size"], price=price, exectype=bt.Order.Limit
            )
            self.active_orders[grid_key] = {
                "order": order,
                "type": "sell",
                "price": price,
                "size": position_info["size"],
                "related_buy": buy_grid_key,
            }

            if self.p.printlog:
                logger.info(
                    f"📉 下卖单: 价格${price:.2f}, 数量{position_info['size']:.4f}"
                )

    def _calculate_position_size(self, price: float, order_type: str) -> float:
        """计算仓位大小"""
        available_cash = self.broker.get_cash()

        # 基于风险百分比计算仓位
        risk_amount = available_cash * self.p.risk_percent

        if order_type == "buy":
            # 买单：基于止损距离计算仓位
            stop_loss_distance = price * self.p.stop_loss_ratio
            position_size = (
                risk_amount / stop_loss_distance if stop_loss_distance > 0 else 0
            )
        else:
            # 卖单：使用已有持仓大小
            position_size = 0

        # 转换为最小交易单位（假设BTC最小单位为0.00001）
        position_size = math.floor(position_size / 0.00001) * 0.00001

        # 确保不超过可用资金
        max_affordable = available_cash / price * 0.95  # 留5%余量
        position_size = min(position_size, max_affordable)

        return max(position_size, 0)

    def notify_order(self, order):
        """订单状态变化通知"""
        if order.status in [order.Completed]:
            if order.isbuy():
                # 买单成交
                grid_key = None
                for key, order_info in self.active_orders.items():
                    if order_info["order"] == order:
                        grid_key = key
                        break

                if grid_key:
                    self.position_prices[grid_key] = {
                        "price": order.executed.price,
                        "size": order.executed.size,
                        "time": self.datas[0].datetime.datetime(0),
                    }
                    self.total_trades += 1

                    if self.p.printlog:
                        logger.info(
                            f"✅ 买单成交: 价格${order.executed.price:.2f}, 数量{order.executed.size:.4f}"
                        )

            else:
                # 卖单成交
                sell_grid_key = None
                buy_grid_key = None

                for key, order_info in self.active_orders.items():
                    if order_info["order"] == order:
                        sell_grid_key = key
                        buy_grid_key = order_info.get("related_buy")
                        break

                if buy_grid_key and buy_grid_key in self.position_prices:
                    # 计算收益
                    buy_price = self.position_prices[buy_grid_key]["price"]
                    sell_price = order.executed.price
                    size = order.executed.size
                    pnl = (sell_price - buy_price) * size

                    self.total_pnl += pnl
                    if pnl > 0:
                        self.winning_trades += 1

                    # 清理记录
                    del self.position_prices[buy_grid_key]
                    self.total_trades += 1

                    if self.p.printlog:
                        logger.info(
                            f"✅ 卖单成交: 价格${sell_price:.2f}, 收益${pnl:.2f}"
                        )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if self.p.printlog:
                logger.warning(f"❌ 订单{order.Status[order.status]}: {order.ref}")

        # 清理已完成的订单
        orders_to_remove = []
        for key, order_info in self.active_orders.items():
            if order_info["order"].status in [
                order.Completed,
                order.Canceled,
                order.Rejected,
            ]:
                orders_to_remove.append(key)

        for key in orders_to_remove:
            del self.active_orders[key]

    def _check_take_profit_stop_loss(self, current_price: float):
        """检查止盈止损"""
        positions_to_close = []

        for grid_key, pos_info in self.position_prices.items():
            buy_price = pos_info["price"]

            # 止盈检查
            if current_price >= buy_price * (1 + self.p.take_profit_ratio):
                positions_to_close.append((grid_key, "take_profit"))

            # 止损检查
            elif current_price <= buy_price * (1 - self.p.stop_loss_ratio):
                positions_to_close.append((grid_key, "stop_loss"))

        # 执行平仓
        for grid_key, reason in positions_to_close:
            pos_info = self.position_prices[grid_key]
            order = self.sell(size=pos_info["size"])

            if self.p.printlog:
                reason_text = "止盈" if reason == "take_profit" else "止损"
                logger.info(
                    f"🔒 {reason_text}平仓: 入场${pos_info['price']:.2f} → 当前${current_price:.2f}"
                )

    def _update_risk_stats(self):
        """更新风险统计"""
        current_value = self.broker.get_value()

        # 更新峰值
        if current_value > self.peak_value:
            self.peak_value = current_value

        # 计算回撤
        drawdown = (self.peak_value - current_value) / self.peak_value
        self.max_drawdown = max(self.max_drawdown, drawdown)

    def _print_status(self):
        """打印状态信息"""
        current_price = self.data.close[0]
        portfolio_value = self.broker.get_value()
        cash = self.broker.get_cash()
        positions_count = len(self.position_prices)

        logger.info("=" * 60)
        logger.info(f"📅 时间: {self.datas[0].datetime.date(0)}")
        logger.info(f"💰 当前价格: ${current_price:.2f}")
        logger.info(f"💼 组合价值: ${portfolio_value:.2f}")
        logger.info(f"💵 可用现金: ${cash:.2f}")
        logger.info(f"📊 持仓数量: {positions_count}")
        logger.info(f"📈 网格间距: {self._calculate_dynamic_spacing() * 100:.2f}%")
        logger.info("=" * 60)

    def stop(self):
        """策略结束时调用"""
        if self.p.printlog:
            final_value = self.broker.get_value()
            total_return = (final_value - self.initial_cash) / self.initial_cash

            logger.info("=" * 60)
            logger.info("🏁 策略执行完成")
            logger.info(f"📊 初始资金: ${self.initial_cash:.2f}")
            logger.info(f"📊 最终资金: ${final_value:.2f}")
            logger.info(f"📊 总收益率: {total_return * 100:.2f}%")
            logger.info(f"📊 最大回撤: {self.max_drawdown * 100:.2f}%")
            logger.info(f"📊 总交易数: {self.total_trades}")
            if self.total_trades > 0:
                logger.info(
                    f"📊 胜率: {(self.winning_trades / self.total_trades * 100):.1f}%"
                )
            else:
                logger.info("📊 胜率: 0.0% (无交易)")
            logger.info(f"📊 总收益: ${self.total_pnl:.2f}")
            logger.info("=" * 60)


def load_binance_btc_data():
    """加载Binance BTC真实数据"""
    try:
        # 使用项目中的BTC数据
        data_file = os.path.join(project_root, "datas", "binance-btc-2015-2026.txt")

        if os.path.exists(data_file):
            logger.info("📂 加载真实BTC数据...")
            df = pd.read_csv(data_file)
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)

            # 确保列名正确
            if "Open" in df.columns:
                df = df.rename(
                    columns={
                        "Open": "open",
                        "High": "high",
                        "Low": "low",
                        "Close": "close",
                        "Volume": "volume",
                    }
                )

            logger.info(f"✅ 数据加载完成: {df.index[0]} 到 {df.index[-1]}")
            logger.info(f"📊 数据点数: {len(df)}")
            logger.info(
                f"💰 价格范围: ${df['close'].min():.2f} - ${df['close'].max():.2f}"
            )

            return df
        else:
            raise FileNotFoundError(f"数据文件不存在: {data_file}")

    except Exception as e:
        logger.error(f"❌ 数据加载失败: {e}")
        raise


def run_grid_trading_backtest():
    """运行网格交易回测"""
    print("🤖 Binance动态网格交易机器人")
    print("=" * 50)

    try:
        # 加载数据
        btc_data = load_binance_btc_data()

        # 创建回测引擎
        cerebro = bt.Cerebro()

        # 添加数据
        data = bt.feeds.PandasData(dataname=btc_data)
        cerebro.adddata(data)

        # 添加策略
        cerebro.addstrategy(DynamicGridStrategy)

        # 设置初始资金
        cerebro.broker.setcash(10000.0)  # 1万美元

        # 设置手续费（Binance现货费率）
        cerebro.broker.setcommission(commission=0.001)  # 0.1%

        # 运行回测
        print("🚀 开始网格交易回测...")
        initial_value = cerebro.broker.getvalue()
        results = cerebro.run()
        final_value = cerebro.broker.getvalue()

        # 计算结果
        total_return = (final_value - initial_value) / initial_value
        print("\n📊 回测结果:")
        print(f"💰 初始资金: ${initial_value:,.2f}")
        print(f"💰 最终资金: ${final_value:,.2f}")
        print(f"📈 总收益率: {total_return * 100:.2f}%")

        # 计算年化收益率
        days = len(btc_data)
        annual_return = (1 + total_return) ** (365 / days) - 1
        print(f"📊 年化收益率: {annual_return * 100:.2f}%")

        return results[0]

    except Exception as e:
        logger.error(f"❌ 回测执行失败: {e}")
        raise


if __name__ == "__main__":
    # 运行网格交易回测
    strategy = run_grid_trading_backtest()
