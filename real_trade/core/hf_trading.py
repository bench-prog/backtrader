#!/usr/bin/env python3
"""
高频交易框架
实现低延迟订单执行、套利策略和性能优化
"""

import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

import backtrader as bt


class OrderType(Enum):
    """订单类型"""

    MARKET = "market"  # 市价单
    LIMIT = "limit"  # 限价单
    STOP = "stop"  # 止损单
    STOP_LIMIT = "stop_limit"  # 止损限价单


class ExecutionMode(Enum):
    """执行模式"""

    NORMAL = "normal"  # 正常执行
    HIGH_FREQUENCY = "hf"  # 高频执行
    ARBITRAGE = "arb"  # 套利执行


@dataclass
class HFOrder:
    """高频订单"""

    order_id: str
    data: bt.DataBase
    order_type: OrderType
    size: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: float = 0.0
    execution_time: Optional[float] = None
    status: str = "pending"
    slippage: float = 0.0


class LatencyMonitor:
    """延迟监控器"""

    def __init__(self):
        self.latency_samples = []
        self.max_samples = 1000

    def record_latency(self, latency: float):
        """记录延迟样本"""
        self.latency_samples.append(latency)
        if len(self.latency_samples) > self.max_samples:
            self.latency_samples.pop(0)

    def get_statistics(self) -> Dict[str, float]:
        """获取延迟统计信息"""
        if not self.latency_samples:
            return {"avg": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0}

        samples = np.array(self.latency_samples)
        return {
            "avg": np.mean(samples),
            "min": np.min(samples),
            "max": np.max(samples),
            "p95": np.percentile(samples, 95),
            "std": np.std(samples),
        }

    def get_average_latency(self) -> float:
        """获取平均延迟"""
        if not self.latency_samples:
            return 0.0
        return np.mean(self.latency_samples)


class OrderExecutor:
    """订单执行器"""

    def __init__(self, mode: ExecutionMode = ExecutionMode.NORMAL):
        self.mode = mode
        self.pending_orders = {}  # order_id -> HFOrder
        self.executed_orders = {}  # order_id -> HFOrder
        self.latency_monitor = LatencyMonitor()
        self.execution_queue = queue.Queue()
        self.executor_thread = None
        self.running = False

    def start(self):
        """启动执行器"""
        if self.mode == ExecutionMode.HIGH_FREQUENCY:
            self.running = True
            self.executor_thread = threading.Thread(target=self._execution_loop)
            self.executor_thread.daemon = True
            self.executor_thread.start()

    def stop(self):
        """停止执行器"""
        self.running = False
        if self.executor_thread:
            self.executor_thread.join(timeout=1.0)

    def submit_order(self, order: HFOrder) -> str:
        """提交订单"""
        order.timestamp = time.time()
        self.pending_orders[order.order_id] = order

        if self.mode == ExecutionMode.HIGH_FREQUENCY:
            self.execution_queue.put(order.order_id)
        else:
            self._execute_order_immediately(order.order_id)

        return order.order_id

    def _execution_loop(self):
        """高频执行循环"""
        while self.running:
            try:
                order_id = self.execution_queue.get(timeout=0.001)
                if order_id in self.pending_orders:
                    self._execute_order_immediately(order_id)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"执行循环错误: {e}")

    def _execute_order_immediately(self, order_id: str):
        """立即执行订单"""
        """立即执行订单"""
        if order_id not in self.pending_orders:
            return

        order = self.pending_orders[order_id]
        start_time = time.time()

        try:
            # 模拟订单执行延迟
            if self.mode == ExecutionMode.HIGH_FREQUENCY:
                # 高频模式：极低延迟
                time.sleep(0.0001)  # 0.1ms
            elif self.mode == ExecutionMode.ARBITRAGE:
                # 套利模式：超低延迟
                time.sleep(0.00001)  # 0.01ms
            else:
                # 正常模式
                time.sleep(0.001)  # 1ms

            # 执行订单逻辑
            execution_price = self._calculate_execution_price(order)
            execution_time = time.time()

            # 记录滑点
            order.slippage = abs(execution_price - (order.price or order.data.close[0]))
            order.execution_time = execution_time
            order.status = "filled"

            # 移动到已执行订单
            self.executed_orders[order_id] = self.pending_orders.pop(order_id)

            # 记录延迟
            latency = (execution_time - start_time) * 1000  # 转换为毫秒
            self.latency_monitor.record_latency(latency)

        except Exception as e:
            order.status = "rejected"
            print(f"订单执行失败 {order_id}: {e}")

    def _calculate_execution_price(self, order: HFOrder) -> float:
        """计算执行价格"""
        current_price = order.data.close[0]

        if order.order_type == OrderType.MARKET:
            # 市价单：使用当前价格加少量滑点
            spread = order.data.close[0] * 0.0001  # 0.01% 滑点
            return current_price + (spread if order.size > 0 else -spread)

        elif order.order_type == OrderType.LIMIT:
            # 限价单：使用指定价格
            return order.price or current_price

        else:
            return current_price

    def get_pending_orders(self) -> List[HFOrder]:
        """获取待处理订单"""
        return list(self.pending_orders.values())

    def get_executed_orders(self) -> List[HFOrder]:
        """获取已执行订单"""
        return list(self.executed_orders.values())


class ArbitrageDetector:
    """套利检测器"""

    def __init__(self, threshold: float = 0.001):  # 0.1% 阈值
        self.threshold = threshold
        self.price_history = {}  # data_name -> [prices]
        self.max_history = 100

    def add_price(self, data_name: str, price: float):
        """添加价格数据"""
        if data_name not in self.price_history:
            self.price_history[data_name] = []

        self.price_history[data_name].append(price)
        if len(self.price_history[data_name]) > self.max_history:
            self.price_history[data_name].pop(0)

    def detect_arbitrage_opportunities(
        self, data_pairs: List[Tuple[str, str]]
    ) -> List[Dict]:
        """检测套利机会"""
        opportunities = []

        for data1_name, data2_name in data_pairs:
            if (
                data1_name not in self.price_history
                or data2_name not in self.price_history
            ):
                continue

            prices1 = self.price_history[data1_name]
            prices2 = self.price_history[data2_name]

            if len(prices1) < 10 or len(prices2) < 10:
                continue

            # 计算最近的价格比率
            current_ratio = prices1[-1] / prices2[-1]
            historical_ratios = [
                p1 / p2 for p1, p2 in zip(prices1[-20:], prices2[-20:])
            ]
            avg_ratio = np.mean(historical_ratios)

            # 检查是否存在套利机会
            deviation = abs(current_ratio - avg_ratio) / avg_ratio

            if deviation > self.threshold:
                opportunities.append(
                    {
                        "pair": (data1_name, data2_name),
                        "ratio": current_ratio,
                        "avg_ratio": avg_ratio,
                        "deviation": deviation,
                        "direction": "long_first"
                        if current_ratio > avg_ratio
                        else "long_second",
                    }
                )

        return opportunities


class HFTradingStrategy(bt.Strategy):
    """
    高频交易策略基类
    专为低延迟执行和套利策略设计
    """

    params = (
        ("execution_mode", ExecutionMode.HIGH_FREQUENCY),
        ("latency_threshold", 5.0),  # 毫秒
        ("printlog", True),
        ("enable_arbitrage", False),
    )

    def __init__(self):
        super().__init__()

        # 初始化高频交易组件
        self.order_executor = OrderExecutor(self.p.execution_mode)
        self.arbitrage_detector = ArbitrageDetector()
        self.order_counter = 0

        # 性能统计
        self.total_orders = 0
        self.filled_orders = 0
        self.total_slippage = 0.0
        self.max_latency = 0.0

        # 启动执行器
        self.order_executor.start()

    def log(self, txt, level="INFO"):
        """日志记录"""
        if self.p.printlog:
            timestamp = self.datetime.datetime().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"{timestamp} | {level} | {txt}")

    def next(self):
        """主逻辑循环"""
        # 更新套利检测器
        if self.p.enable_arbitrage:
            self._update_arbitrage_detection()

        # 检查执行性能
        self._monitor_execution_performance()

        # 执行具体策略逻辑
        self.generate_hf_signals()

    def _update_arbitrage_detection(self):
        """更新套利检测"""
        # 为所有数据添加当前价格
        for data in self.datas:
            self.arbitrage_detector.add_price(data._name, data.close[0])

        # 检测套利机会
        data_pairs = [
            (d1._name, d2._name)
            for i, d1 in enumerate(self.datas)
            for d2 in self.datas[i + 1 :]
        ]

        opportunities = self.arbitrage_detector.detect_arbitrage_opportunities(
            data_pairs
        )

        for opp in opportunities:
            self.log(f"套利机会: {opp['pair']} 偏离 {opp['deviation']:.4f}")
            self.execute_arbitrage(opp)

    def _monitor_execution_performance(self):
        """监控执行性能"""
        stats = self.order_executor.latency_monitor.get_statistics()
        current_avg = stats["avg"]

        if current_avg > self.p.latency_threshold:
            self.log(
                f"警告: 平均延迟 {current_avg:.2f}ms 超过阈值 {self.p.latency_threshold}ms",
                "WARNING",
            )

        self.max_latency = max(self.max_latency, stats["max"])

    def generate_hf_signals(self):
        """
        生成高频交易信号 - 由子类实现
        """
        pass

    def execute_arbitrage(self, opportunity: Dict):
        """
        执行套利交易 - 由子类实现
        """
        pass

    def hf_buy(
        self, data: bt.DataBase, size: int, price: Optional[float] = None
    ) -> str:
        """高频买入"""
        self.order_counter += 1
        order = HFOrder(
            order_id=f"HF_BUY_{self.order_counter}",
            data=data,
            order_type=OrderType.MARKET,
            size=size,
            price=price,
        )

        order_id = self.order_executor.submit_order(order)
        self.total_orders += 1
        self.log(f"提交高频买入订单: {order_id}, 数量 {size}")
        return order_id

    def hf_sell(
        self, data: bt.DataBase, size: int, price: Optional[float] = None
    ) -> str:
        """高频卖出"""
        self.order_counter += 1
        order = HFOrder(
            order_id=f"HF_SELL_{self.order_counter}",
            data=data,
            order_type=OrderType.MARKET,
            size=-size,  # 负数表示卖出
            price=price,
        )

        order_id = self.order_executor.submit_order(order)
        self.total_orders += 1
        self.log(f"提交高频卖出订单: {order_id}, 数量 {size}")
        return order_id

    def stop(self):
        """策略结束"""
        # 停止执行器
        self.order_executor.stop()

        # 计算最终统计
        stats = self.order_executor.latency_monitor.get_statistics()

        self.log("=== 高频交易性能统计 ===")
        self.log(f"总订单数: {self.total_orders}")
        self.log(f"成交订单数: {len(self.order_executor.executed_orders)}")
        self.log(f"平均延迟: {stats['avg']:.2f}ms")
        self.log(f"最大延迟: {stats['max']:.2f}ms")
        self.log(f"95%延迟: {stats['p95']:.2f}ms")
        self.log(f"延迟标准差: {stats.get('std', 0):.2f}ms")


# 便捷的订单ID生成器
def generate_order_id(prefix: str = "HF") -> str:
    """生成唯一订单ID"""
    return f"{prefix}_{int(time.time() * 1000000)}_{np.random.randint(10000)}"
