#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Strategy Visual Debugger - 策略可视化调试器

提供实时策略状态监控、交易信号可视化、资金曲线跟踪等功能。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Any, Deque, Dict, Optional

import matplotlib.pyplot as plt

from ..utils import get_logger


@dataclass
class SignalEvent:
    """信号事件"""

    timestamp: float
    signal_type: str  # 'buy', 'sell', 'hold'
    price: float
    strength: float  # 信号强度 0-1
    reason: str  # 信号产生原因
    strategy_name: str


@dataclass
class PositionEvent:
    """持仓事件"""

    timestamp: float
    symbol: str
    direction: str  # 'long', 'short'
    size: float
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    status: str = "open"  # 'open', 'closed'


@dataclass
class StrategyMetrics:
    """策略指标"""

    timestamp: float
    equity: float
    cash: float
    positions_value: float
    total_value: float
    drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float


class StrategyVisualDebugger:
    """策略可视化调试器主类"""

    def __init__(
        self,
        update_interval: float = 1.0,
        history_size: int = 1000,
        enable_plotting: bool = True,
    ):
        """
        初始化策略调试器

        Args:
            update_interval: 更新间隔（秒）
            history_size: 历史数据保存数量
            enable_plotting: 是否启用图形绘制
        """
        self.update_interval = update_interval
        self.history_size = history_size
        self.enable_plotting = enable_plotting

        # 数据存储
        self.signals: Deque[SignalEvent] = deque(maxlen=history_size)
        self.positions: Dict[str, PositionEvent] = {}
        self.closed_positions: Deque[PositionEvent] = deque(maxlen=history_size)
        self.metrics_history: Deque[StrategyMetrics] = deque(maxlen=history_size)
        self.price_history: Deque[tuple] = deque(
            maxlen=history_size
        )  # (timestamp, price)

        # 实时状态
        self.current_equity = 0.0
        self.current_cash = 0.0
        self.current_positions_value = 0.0
        self.current_total_value = 0.0

        # 控制变量
        self.is_running = False
        self.update_thread = None
        self.logger = get_logger("strategy_debugger")

        # 图形相关
        self.fig = None
        self.axes = None
        if enable_plotting:
            self._setup_plot()

    def _setup_plot(self):
        """设置图形界面"""
        try:
            plt.ion()  # 开启交互模式
            self.fig, self.axes = plt.subplots(2, 2, figsize=(15, 10))
            self.fig.suptitle("Strategy Real-time Monitor", fontsize=16)

            # 子图布局
            self.price_ax = self.axes[0, 0]  # 价格图
            self.equity_ax = self.axes[0, 1]  # 资金曲线
            self.signals_ax = self.axes[1, 0]  # 信号图
            self.metrics_ax = self.axes[1, 1]  # 指标图

            plt.tight_layout()
        except Exception as e:
            self.logger.warning(f"图形初始化失败: {e}")
            self.enable_plotting = False

    def start_monitoring(self):
        """开始监控"""
        if self.is_running:
            return

        self.is_running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        self.logger.info("策略调试器开始监控")

    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
        self.logger.info("策略调试器停止监控")

    def _update_loop(self):
        """更新循环"""
        while self.is_running:
            try:
                self._update_display()
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"更新循环错误: {e}")
                time.sleep(1.0)

    def _update_display(self):
        """更新显示"""
        if not self.enable_plotting:
            return

        try:
            self._update_price_chart()
            self._update_equity_chart()
            self._update_signals_chart()
            self._update_metrics_chart()

            plt.pause(0.001)  # 短暂暂停以更新图形
        except Exception as e:
            self.logger.error(f"显示更新错误: {e}")

    def _update_price_chart(self):
        """更新价格图表"""
        if not self.price_history:
            return

        self.price_ax.clear()
        timestamps, prices = zip(*list(self.price_history))

        # 绘制价格线
        self.price_ax.plot(timestamps, prices, "b-", linewidth=1, label="Price")

        # 绘制买卖信号
        buy_signals = [
            (s.timestamp, s.price) for s in self.signals if s.signal_type == "buy"
        ]
        sell_signals = [
            (s.timestamp, s.price) for s in self.signals if s.signal_type == "sell"
        ]

        if buy_signals:
            buy_times, buy_prices = zip(*buy_signals)
            self.price_ax.scatter(
                buy_times, buy_prices, color="green", marker="^", s=50, label="Buy"
            )

        if sell_signals:
            sell_times, sell_prices = zip(*sell_signals)
            self.price_ax.scatter(
                sell_times, sell_prices, color="red", marker="v", s=50, label="Sell"
            )

        # 绘制持仓区间
        for pos in self.positions.values():
            if pos.status == "open":
                self.price_ax.axvspan(
                    pos.timestamp,
                    timestamps[-1],
                    alpha=0.2,
                    color="green" if pos.direction == "long" else "red",
                )

        self.price_ax.set_title("Price Action & Signals")
        self.price_ax.set_ylabel("Price")
        self.price_ax.legend()
        self.price_ax.grid(True)

    def _update_equity_chart(self):
        """更新资金曲线图表"""
        if not self.metrics_history:
            return

        self.equity_ax.clear()
        timestamps = [m.timestamp for m in self.metrics_history]
        equities = [m.equity for m in self.metrics_history]
        drawdowns = [m.drawdown * 100 for m in self.metrics_history]  # 转换为百分比

        # 绘制资金曲线
        self.equity_ax.plot(timestamps, equities, "purple", linewidth=2, label="Equity")

        # 绘制回撤
        ax2 = self.equity_ax.twinx()
        ax2.fill_between(timestamps, drawdowns, 0, alpha=0.3, color="red")
        ax2.set_ylabel("Drawdown (%)", color="red")
        ax2.tick_params(axis="y", labelcolor="red")

        self.equity_ax.set_title("Equity Curve & Drawdown")
        self.equity_ax.set_ylabel("Equity")
        self.equity_ax.legend()
        self.equity_ax.grid(True)

    def _update_signals_chart(self):
        """更新信号图表"""
        if not self.signals:
            return

        self.signals_ax.clear()

        # 统计信号类型
        signal_counts = defaultdict(int)
        for signal in self.signals:
            signal_counts[signal.signal_type] += 1

        if signal_counts:
            labels = list(signal_counts.keys())
            sizes = list(signal_counts.values())
            colors = {"buy": "green", "sell": "red", "hold": "blue"}

            self.signals_ax.pie(
                sizes,
                labels=labels,
                autopct="%1.1f%%",
                colors=[colors.get(label, "gray") for label in labels],
            )
            self.signals_ax.set_title("Signal Distribution")

    def _update_metrics_chart(self):
        """更新指标图表"""
        if not self.metrics_history:
            return

        self.metrics_ax.clear()

        latest_metrics = self.metrics_history[-1]

        # 创建指标雷达图数据
        metrics_data = {
            "Sharpe Ratio": min(latest_metrics.sharpe_ratio / 3.0, 1.0),  # 归一化到0-1
            "Win Rate": latest_metrics.win_rate,
            "Profit Factor": min(latest_metrics.profit_factor / 5.0, 1.0),  # 归一化
            "Drawdown Control": max(
                1.0 - latest_metrics.drawdown / 0.2, 0.0
            ),  # 回撤控制
        }

        # 绘制雷达图
        categories = list(metrics_data.keys())
        values = list(metrics_data.values())

        angles = [
            n / float(len(categories)) * 2 * 3.14159 for n in range(len(categories))
        ]
        angles += angles[:1]  # 闭合图形
        values += values[:1]

        self.metrics_ax.plot(angles, values, "o-", linewidth=2)
        self.metrics_ax.fill(angles, values, alpha=0.25)
        self.metrics_ax.set_xticks(angles[:-1])
        self.metrics_ax.set_xticklabels(categories)
        self.metrics_ax.set_ylim(0, 1)
        self.metrics_ax.set_title("Performance Metrics")

    def record_signal(
        self,
        signal_type: str,
        price: float,
        strength: float = 1.0,
        reason: str = "",
        strategy_name: str = "default",
    ):
        """记录交易信号"""
        signal = SignalEvent(
            timestamp=time.time(),
            signal_type=signal_type,
            price=price,
            strength=strength,
            reason=reason,
            strategy_name=strategy_name,
        )
        self.signals.append(signal)
        self.logger.debug(f"记录信号: {signal_type} @ {price}")

    def record_price(self, price: float):
        """记录价格数据"""
        self.price_history.append((time.time(), price))

    def update_position(
        self,
        symbol: str,
        direction: str,
        size: float,
        entry_price: float,
        exit_price: Optional[float] = None,
    ):
        """更新持仓状态"""
        if exit_price is None:
            # 开仓
            position = PositionEvent(
                timestamp=time.time(),
                symbol=symbol,
                direction=direction,
                size=size,
                entry_price=entry_price,
                status="open",
            )
            self.positions[symbol] = position
            self.logger.info(f"开仓: {symbol} {direction} {size}@{entry_price}")
        else:
            # 平仓
            if symbol in self.positions:
                position = self.positions[symbol]
                position.exit_price = exit_price
                position.pnl = (exit_price - position.entry_price) * position.size
                if position.direction == "short":
                    position.pnl = -position.pnl
                position.status = "closed"

                self.closed_positions.append(position)
                del self.positions[symbol]
                self.logger.info(f"平仓: {symbol} {position.pnl:+.2f}")

    def update_metrics(
        self,
        equity: float,
        cash: float,
        positions_value: float,
        sharpe_ratio: float = 0.0,
        win_rate: float = 0.0,
        profit_factor: float = 0.0,
    ):
        """更新策略指标"""
        total_value = cash + positions_value
        peak_value = max([m.total_value for m in self.metrics_history] or [total_value])
        drawdown = (peak_value - total_value) / peak_value if peak_value > 0 else 0.0

        metrics = StrategyMetrics(
            timestamp=time.time(),
            equity=equity,
            cash=cash,
            positions_value=positions_value,
            total_value=total_value,
            drawdown=drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
        )

        self.metrics_history.append(metrics)
        self.current_equity = equity
        self.current_cash = cash
        self.current_positions_value = positions_value
        self.current_total_value = total_value

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        return {
            "current_status": {
                "equity": self.current_equity,
                "cash": self.current_cash,
                "positions_value": self.current_positions_value,
                "total_value": self.current_total_value,
                "open_positions": len(self.positions),
                "recent_signals": len(
                    [
                        s
                        for s in list(self.signals)[-10:]
                        if s.signal_type in ["buy", "sell"]
                    ]
                ),
            },
            "performance": {
                "total_signals": len(self.signals),
                "buy_signals": len([s for s in self.signals if s.signal_type == "buy"]),
                "sell_signals": len(
                    [s for s in self.signals if s.signal_type == "sell"]
                ),
                "winning_trades": len(
                    [p for p in self.closed_positions if p.pnl and p.pnl > 0]
                ),
                "total_trades": len(self.closed_positions),
            },
            "latest_metrics": asdict(self.metrics_history[-1])
            if self.metrics_history
            else {},
            "timestamp": time.time(),
        }

    def export_data(self, filepath: str):
        """导出数据到文件"""
        data = {
            "signals": [asdict(s) for s in self.signals],
            "positions": [asdict(p) for p in self.closed_positions],
            "metrics": [asdict(m) for m in self.metrics_history],
            "price_history": list(self.price_history),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        self.logger.info(f"数据已导出到: {filepath}")

    def print_dashboard(self):
        """打印控制台仪表板"""
        dashboard = self.get_dashboard_data()
        status = dashboard["current_status"]
        perf = dashboard["performance"]

        print("\n" + "=" * 60)
        print("📊 策略实时监控仪表板")
        print("=" * 60)
        print("💰 资金状况:")
        print(f"  总资产: ${status['total_value']:,.2f}")
        print(f"  可用资金: ${status['cash']:,.2f}")
        print(f"  持仓价值: ${status['positions_value']:,.2f}")
        print(f"  净资产: ${status['equity']:,.2f}")
        print()
        print("📈 交易统计:")
        print(f"  持仓数量: {status['open_positions']}")
        print(f"  总信号数: {perf['total_signals']}")
        print(f"  买入信号: {perf['buy_signals']}")
        print(f"  卖出信号: {perf['sell_signals']}")
        print(f"  已平仓交易: {perf['total_trades']}")
        print()
        print("🎯 最新指标:")
        if dashboard["latest_metrics"]:
            metrics = dashboard["latest_metrics"]
            print(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
            print(f"  胜率: {metrics.get('win_rate', 0) * 100:.1f}%")
            print(f"  盈亏比: {metrics.get('profit_factor', 0):.2f}")
            print(f"  当前回撤: {metrics.get('drawdown', 0) * 100:.2f}%")
        print("=" * 60)


# 便利函数
def create_debugger(**kwargs) -> StrategyVisualDebugger:
    """创建调试器实例"""
    return StrategyVisualDebugger(**kwargs)


def demo_strategy_debugger():
    """调试器演示函数"""
    debugger = create_debugger(update_interval=0.5, enable_plotting=False)
    debugger.start_monitoring()

    # 模拟策略执行
    current_price = 50000.0
    equity = 100000.0
    cash = 100000.0

    print("开始策略调试演示...")

    for i in range(50):
        # 模拟价格变化
        price_change = (i % 10 - 5) * 100  # 简单的锯齿状价格
        current_price += price_change
        debugger.record_price(current_price)

        # 模拟交易信号
        if i % 15 == 0:
            debugger.record_signal("buy", current_price, 0.8, f"信号{i}")
        elif i % 15 == 7:
            debugger.record_signal("sell", current_price, 0.7, f"信号{i}")

        # 模拟开平仓
        if i % 20 == 5:
            debugger.update_position("BTCUSDT", "long", 1.0, current_price)
        elif i % 20 == 15:
            debugger.update_position("BTCUSDT", "long", 1.0, 0, current_price)

        # 更新指标
        debugger.update_metrics(
            equity=equity,
            cash=cash,
            positions_value=0,
            sharpe_ratio=1.5,
            win_rate=0.6,
            profit_factor=1.8,
        )

        # 每10步打印一次仪表板
        if i % 10 == 9:
            debugger.print_dashboard()

        time.sleep(0.1)

    debugger.stop_monitoring()
    print("演示完成!")


__all__ = [
    "SignalEvent",
    "PositionEvent",
    "StrategyMetrics",
    "StrategyVisualDebugger",
    "create_debugger",
    "demo_strategy_debugger",
]
