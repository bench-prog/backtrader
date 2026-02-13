#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Monitoring Integration for Backtrader
基于现有backtrader框架实现的监控功能集成
无需修改框架核心代码，完全利用Analyzer机制
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import json
from typing import Any, Dict

import backtrader as bt


class SystemHealthMonitor(bt.Analyzer):
    """
    系统健康监控Analyzer
    集成健康检查功能到backtrader框架中
    """

    params = (
        ("max_data_delay", 120),  # 最大数据延迟秒数
        ("min_balance", 0.0),  # 最小余额要求
        ("currency", "USDT"),  # 余额币种
        ("check_interval", 10),  # 检查间隔（周期数）
        ("_debug", False),
    )

    def __init__(self):
        super(SystemHealthMonitor, self).__init__()
        self.health_checks = []
        self.check_counter = 0
        self.last_check_time = None

    def start(self):
        """初始化监控"""
        super(SystemHealthMonitor, self).start()
        if self.p._debug:
            print("SystemHealthMonitor 初始化完成")

    def next(self):
        """每个周期检查系统健康状态"""
        self.check_counter += 1

        # 按指定间隔进行检查
        if self.check_counter % self.p.check_interval == 0:
            self._perform_health_check()

    def _perform_health_check(self):
        """执行健康检查"""
        check_result = {
            "timestamp": self.strategy.datetime.datetime().isoformat(),
            "checks": {},
        }

        # 1. 检查交易所连接（如果使用实盘）
        if hasattr(self.strategy.broker, "store") and self.strategy.broker.store:
            try:
                store = self.strategy.broker.store
                if hasattr(store, "test_connection"):
                    connection_ok = store.test_connection()
                    check_result["checks"]["exchange_connection"] = {
                        "ok": connection_ok,
                        "type": "connection",
                    }
            except Exception as e:
                check_result["checks"]["exchange_connection"] = {
                    "ok": False,
                    "error": str(e),
                    "type": "connection",
                }

        # 2. 检查数据新鲜度
        self._check_data_freshness(check_result)

        # 3. 检查账户余额
        self._check_balance(check_result)

        # 4. 检查策略状态
        self._check_strategy_status(check_result)

        # 保存检查结果
        self.health_checks.append(check_result)

        # 限制历史记录长度
        if len(self.health_checks) > 100:
            self.health_checks.pop(0)

        # 输出健康状态（可选）
        if self.p._debug and not self._is_system_healthy(check_result):
            self._print_health_warning(check_result)

    def _check_data_freshness(self, check_result: dict):
        """检查数据新鲜度"""
        try:
            current_time = self.strategy.datetime.datetime()
            data_times = []

            # 收集所有数据的时间戳
            for data in self.strategy.datas:
                if len(data) > 0:
                    data_time = data.datetime.datetime(0)
                    data_times.append(data_time)

            if data_times:
                latest_data_time = max(data_times)
                delay_seconds = (current_time - latest_data_time).total_seconds()
                is_fresh = delay_seconds <= self.p.max_data_delay

                check_result["checks"]["data_freshness"] = {
                    "ok": is_fresh,
                    "delay_seconds": round(delay_seconds, 1),
                    "max_allowed": self.p.max_data_delay,
                    "type": "data",
                }
            else:
                check_result["checks"]["data_freshness"] = {
                    "ok": False,
                    "error": "no data available",
                    "type": "data",
                }

        except Exception as e:
            check_result["checks"]["data_freshness"] = {
                "ok": False,
                "error": str(e),
                "type": "data",
            }

    def _check_balance(self, check_result: dict):
        """检查账户余额"""
        try:
            if hasattr(self.strategy.broker, "store") and self.strategy.broker.store:
                store = self.strategy.broker.store
                if hasattr(store, "get_balance"):
                    balance = store.get_balance(self.p.currency)
                    balance_ok = balance >= self.p.min_balance

                    check_result["checks"]["balance"] = {
                        "ok": balance_ok,
                        "balance": balance,
                        "min_required": self.p.min_balance,
                        "currency": self.p.currency,
                        "type": "financial",
                    }
                else:
                    # 使用broker的基本余额检查
                    current_value = self.strategy.broker.getvalue()
                    balance_ok = current_value >= self.p.min_balance
                    check_result["checks"]["balance"] = {
                        "ok": balance_ok,
                        "balance": current_value,
                        "min_required": self.p.min_balance,
                        "currency": "portfolio_value",
                        "type": "financial",
                    }
            else:
                # 回测模式下检查账户价值
                current_value = self.strategy.broker.getvalue()
                balance_ok = current_value > 0
                check_result["checks"]["balance"] = {
                    "ok": balance_ok,
                    "balance": current_value,
                    "type": "financial",
                }

        except Exception as e:
            check_result["checks"]["balance"] = {
                "ok": False,
                "error": str(e),
                "type": "financial",
            }

    def _check_strategy_status(self, check_result: dict):
        """检查策略状态"""
        try:
            # 检查是否有未完成订单
            pending_orders = len(
                [
                    order
                    for order in self.strategy.broker.orders
                    if not order.isbuy() and not order.issell()
                ]
            )

            # 检查持仓情况
            positions = sum(
                1
                for data in self.strategy.datas
                if self.strategy.getposition(data).size != 0
            )

            check_result["checks"]["strategy_status"] = {
                "ok": True,
                "pending_orders": pending_orders,
                "active_positions": positions,
                "type": "strategy",
            }

        except Exception as e:
            check_result["checks"]["strategy_status"] = {
                "ok": False,
                "error": str(e),
                "type": "strategy",
            }

    def _is_system_healthy(self, check_result: dict) -> bool:
        """判断系统是否健康"""
        checks = check_result.get("checks", {})
        return all(check.get("ok", False) for check in checks.values())

    def _print_health_warning(self, check_result: dict):
        """打印健康警告"""
        print(f"\n⚠️  系统健康警告 [{check_result['timestamp']}]:")
        for check_name, check_info in check_result["checks"].items():
            if not check_info.get("ok", True):
                error_msg = check_info.get("error", "unknown error")
                print(f"  - {check_name}: {error_msg}")

    def get_analysis(self):
        """获取健康监控分析结果"""
        # 计算总体健康状态
        healthy_count = 0
        total_checks = 0

        for check_record in self.health_checks:
            checks = check_record.get("checks", {})
            for check in checks.values():
                total_checks += 1
                if check.get("ok", False):
                    healthy_count += 1

        health_ratio = healthy_count / total_checks if total_checks > 0 else 1.0

        return {
            "overall_health": health_ratio,
            "is_healthy": health_ratio >= 0.8,  # 80%以上认为健康
            "total_checks": len(self.health_checks),
            "health_history": self.health_checks[-20:],  # 最近20次检查
            "latest_check": self.health_checks[-1] if self.health_checks else None,
        }


class PerformanceSummary(bt.Analyzer):
    """
    绩效汇总Analyzer
    整合backtrader内置的多个分析器结果
    """

    def __init__(self):
        super(PerformanceSummary, self).__init__()
        self.initial_value = 0
        self.final_value = 0

    def start(self):
        """记录初始价值"""
        self.initial_value = self.strategy.broker.getvalue()

    def stop(self):
        """记录最终价值"""
        self.final_value = self.strategy.broker.getvalue()

    def get_analysis(self):
        """获取综合绩效分析"""
        # 这里可以整合多个内置分析器的结果
        return {
            "initial_value": self.initial_value,
            "final_value": self.final_value,
            "net_pnl": self.final_value - self.initial_value,
            "return_pct": (self.final_value - self.initial_value) / self.initial_value
            if self.initial_value > 0
            else 0,
        }


class ReportGenerator:
    """
    报告生成器
    基于Analyzer结果生成各种格式的报告
    """

    @staticmethod
    def generate_text_report(analyzers_results: Dict[str, Any]) -> str:
        """生成文本格式报告"""
        lines = [
            "=" * 50,
            f"  Trading Report  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 50,
        ]

        # 添加绩效信息
        if "performance" in analyzers_results:
            perf = analyzers_results["performance"]
            lines.extend(
                [
                    f"  Initial Value : ${perf.get('initial_value', 0):,.2f}",
                    f"  Final Value   : ${perf.get('final_value', 0):,.2f}",
                    f"  Net P&L       : ${perf.get('net_pnl', 0):,.2f}",
                    f"  Return        : {perf.get('return_pct', 0):.2%}",
                    "",
                ]
            )

        # 添加风险信息
        if "risk_analyzer" in analyzers_results:
            risk = analyzers_results["risk_analyzer"]
            metrics = risk.get("risk_metrics", {})
            lines.extend(
                [
                    "  Risk Metrics:",
                    f"    Max Drawdown : {metrics.get('max_drawdown', 0):.2%}",
                    f"    Position Risk: {metrics.get('position_risk', 0):.2%}",
                    f"    Current Status: {risk.get('current_status', 'UNKNOWN')}",
                    "",
                ]
            )

        # 添加健康信息
        if "health_monitor" in analyzers_results:
            health = analyzers_results["health_monitor"]
            lines.extend(
                [
                    "  System Health:",
                    f"    Overall Health: {health.get('overall_health', 0):.1%}",
                    f"    Is Healthy: {'YES' if health.get('is_healthy', False) else 'NO'}",
                    f"    Total Checks: {health.get('total_checks', 0)}",
                    "",
                ]
            )

        # 添加投资组合信息
        if "portfolio_optimizer" in analyzers_results:
            portfolio = analyzers_results["portfolio_optimizer"]
            current_port = portfolio.get("current_portfolio", {})
            if current_port:
                lines.extend(
                    [
                        "  Portfolio Optimization:",
                        f"    Expected Return: {current_port.get('expected_return', 0):.2%}",
                        f"    Risk: {current_port.get('risk', 0):.2%}",
                        f"    Sharpe Ratio: {current_port.get('sharpe_ratio', 0):.2f}",
                        "",
                    ]
                )

        lines.append("=" * 50)
        return "\n".join(lines)

    @staticmethod
    def generate_json_report(analyzers_results: Dict[str, Any]) -> str:
        """生成JSON格式报告"""
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "summary": analyzers_results,
        }
        return json.dumps(report, indent=2, ensure_ascii=False)

    @staticmethod
    def generate_brief_report(analyzers_results: Dict[str, Any]) -> str:
        """生成简要报告"""
        perf = analyzers_results.get("performance", {})
        health = analyzers_results.get("health_monitor", {})
        risk = analyzers_results.get("risk_analyzer", {})

        return (
            f"📊 回报: {perf.get('return_pct', 0):.2%} | "
            f"💰 净利润: ${perf.get('net_pnl', 0):,.2f} | "
            f"⚠️ 健康: {'🟢' if health.get('is_healthy', False) else '🔴'} | "
            f"📉 最大回撤: {risk.get('risk_metrics', {}).get('max_drawdown', 0):.2%}"
        )


# 便捷函数
def add_monitoring_analyzers(cerebro: bt.Cerebro, health_monitor_params: dict = None):
    """
    为Cerebro添加全套监控分析器的便捷函数

    Args:
        cerebro: Cerebro实例
        health_monitor_params: 健康监控器参数

    Returns:
        dict: 添加的分析器名称映射
    """
    analyzers_added = {}

    # 添加绩效汇总分析器
    cerebro.addanalyzer(PerformanceSummary, _name="performance")
    analyzers_added["performance"] = "PerformanceSummary"

    # 添加系统健康监控
    health_params = health_monitor_params or {}
    cerebro.addanalyzer(SystemHealthMonitor, _name="health_monitor", **health_params)
    analyzers_added["health_monitor"] = "SystemHealthMonitor"

    # 返回添加的分析器信息
    return analyzers_added


def collect_analyzer_results(strategy) -> Dict[str, Any]:
    """
    收集策略中所有分析器的结果

    Args:
        strategy: backtrader策略实例

    Returns:
        Dict[str, Any]: 所有分析器结果的字典
    """
    results = {}
    if hasattr(strategy, "analyzers"):
        for analyzer in strategy.analyzers:
            name = getattr(analyzer, "_name", analyzer.__class__.__name__)
            try:
                results[name] = analyzer.get_analysis()
            except Exception as e:
                results[name] = {"error": str(e)}

    return results
