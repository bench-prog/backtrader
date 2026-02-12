#!/usr/bin/env python3
"""
Backtrader动态风险分析器
将独立的风险引擎重构为标准的backtrader Analyzer组件
"""

from collections import deque
from typing import Dict, List, Optional

import numpy as np

import backtrader as bt


class DynamicRiskAnalyzer(bt.Analyzer):
    """
    动态风险分析器
    继承自bt.Analyzer，实时计算VaR、CVaR、最大回撤等风险指标
    """

    params = (
        ("lookback_period", 50),  # 回看周期
        ("confidence_level", 0.95),  # 置信水平
        ("risk_free_rate", 0.02),  # 无风险利率
        ("calculate_var", True),  # 是否计算VaR
        ("calculate_cvar", True),  # 是否计算CVaR
        ("calculate_drawdown", True),  # 是否计算回撤
        ("calculate_volatility", True),  # 是否计算波动率
    )

    def __init__(self):
        super().__init__()

        # 数据存储
        self.returns = deque(maxlen=self.p.lookback_period)
        self.portfolio_values = deque(maxlen=self.p.lookback_period)
        self.timestamps = deque(maxlen=self.p.lookback_period)

        # 风险指标历史
        self.var_history = []
        self.cvar_history = []
        self.drawdown_history = []
        self.volatility_history = []
        self.sharpe_history = []

        # 当前状态
        self.current_var = 0.0
        self.current_cvar = 0.0
        self.current_drawdown = 0.0
        self.current_volatility = 0.0
        self.current_sharpe = 0.0
        self.max_drawdown = 0.0

        # Z分数查表（替代math.erfinv）
        self.z_score_table = self._create_z_score_table()

    def _create_z_score_table(self) -> Dict[float, float]:
        """创建Z分数查表"""
        table = {}
        confidence_levels = [0.90, 0.95, 0.99]
        z_scores = [1.28, 1.645, 2.33]  # 对应的Z分数

        for conf, z_score in zip(confidence_levels, z_scores):
            table[conf] = z_score

        return table

    def _calculate_returns(self, portfolio_value: float) -> Optional[float]:
        """计算收益率"""
        if len(self.portfolio_values) == 0:
            return None

        previous_value = self.portfolio_values[-1]
        if previous_value == 0:
            return None

        return (portfolio_value - previous_value) / previous_value

    def _calculate_var(self, returns: List[float]) -> float:
        """计算VaR (Value at Risk)"""
        if len(returns) < 10:
            return 0.0

        returns_array = np.array(returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)

        # 使用查表法获取Z分数
        z_score = self.z_score_table.get(self.p.confidence_level, 1.645)

        # VaR = -(mean - z * std)
        var = -(mean_return - z_score * std_return)
        return max(0.0, var)  # 确保非负

    def _calculate_cvar(self, returns: List[float]) -> float:
        """计算CVaR (Conditional Value at Risk)"""
        if len(returns) < 10:
            return 0.0

        var_threshold = self._calculate_var(returns)
        returns_array = np.array(returns)

        # 计算低于VaR的损失平均值
        tail_losses = returns_array[returns_array <= -var_threshold]

        if len(tail_losses) == 0:
            return var_threshold

        cvar = -np.mean(tail_losses)
        return max(0.0, cvar)

    def _calculate_drawdown(self, portfolio_values: List[float]) -> tuple:
        """计算回撤指标"""
        if len(portfolio_values) < 2:
            return 0.0, 0.0

        peak = portfolio_values[0]
        max_drawdown = 0.0
        current_drawdown = 0.0

        for value in portfolio_values:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
                current_drawdown = drawdown

        return current_drawdown, max_drawdown

    def _calculate_volatility(self, returns: List[float]) -> float:
        """计算波动率"""
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns)
        return np.std(returns_array) * np.sqrt(252)  # 年化波动率

    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """计算夏普比率"""
        if len(returns) < 10:
            return 0.0

        returns_array = np.array(returns)
        mean_return = np.mean(returns_array) * 252  # 年化
        volatility = self._calculate_volatility(returns)

        if volatility == 0:
            return 0.0

        sharpe = (mean_return - self.p.risk_free_rate) / volatility
        return sharpe

    def next(self):
        """每个bar执行"""
        portfolio_value = self.strategy.broker.getvalue()

        # 计算收益率
        ret = self._calculate_returns(portfolio_value)
        if ret is not None:
            self.returns.append(ret)

        # 存储数据
        self.portfolio_values.append(portfolio_value)
        self.timestamps.append(self.strategy.datetime.datetime())

        # 计算风险指标
        if len(self.returns) >= 10:
            returns_list = list(self.returns)
            portfolio_list = list(self.portfolio_values)

            if self.p.calculate_var:
                self.current_var = self._calculate_var(returns_list)
                self.var_history.append(
                    (self.strategy.datetime.datetime(), self.current_var)
                )

            if self.p.calculate_cvar:
                self.current_cvar = self._calculate_cvar(returns_list)
                self.cvar_history.append(
                    (self.strategy.datetime.datetime(), self.current_cvar)
                )

            if self.p.calculate_drawdown:
                current_dd, max_dd = self._calculate_drawdown(portfolio_list)
                self.current_drawdown = current_dd
                self.max_drawdown = max(self.max_drawdown, max_dd)
                self.drawdown_history.append(
                    (self.strategy.datetime.datetime(), current_dd)
                )

            if self.p.calculate_volatility:
                self.current_volatility = self._calculate_volatility(returns_list)
                self.volatility_history.append(
                    (self.strategy.datetime.datetime(), self.current_volatility)
                )

            # 计算夏普比率
            self.current_sharpe = self._calculate_sharpe_ratio(returns_list)
            self.sharpe_history.append(
                (self.strategy.datetime.datetime(), self.current_sharpe)
            )

    def get_analysis(self) -> Dict:
        """获取分析结果"""
        return {
            "current_var": self.current_var,
            "current_cvar": self.current_cvar,
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown,
            "current_volatility": self.current_volatility,
            "current_sharpe": self.current_sharpe,
            "var_history": self.var_history,
            "cvar_history": self.cvar_history,
            "drawdown_history": self.drawdown_history,
            "volatility_history": self.volatility_history,
            "sharpe_history": self.sharpe_history,
            "risk_level": self._assess_risk_level(),
        }

    def _assess_risk_level(self) -> str:
        """评估风险等级"""
        if self.current_var > 0.05 or self.max_drawdown > 0.10:
            return "HIGH"
        elif self.current_var > 0.03 or self.max_drawdown > 0.05:
            return "MEDIUM"
        else:
            return "LOW"

    def notify_order(self, order):
        """订单通知"""
        pass

    def notify_trade(self, trade):
        """交易通知"""
        pass


class RiskBasedSizer(bt.Sizer):
    """
    基于风险的仓位管理器
    根据动态风险评估结果调整仓位大小
    """

    params = (
        ("risk_per_trade", 0.02),  # 每笔交易风险占比
        ("max_position_size", 0.1),  # 最大仓位占比
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        """计算仓位大小"""
        # 获取风险分析器
        risk_analyzer = None
        for analyzer in self.strategy.analyzers:
            if isinstance(analyzer, DynamicRiskAnalyzer):
                risk_analyzer = analyzer
                break

        if risk_analyzer is None:
            # 如果没有风险分析器，使用默认仓位
            return int(cash * self.p.max_position_size / data.close[0])

        # 根据风险等级调整仓位
        risk_level = risk_analyzer._assess_risk_level()
        risk_multiplier = {"LOW": 1.0, "MEDIUM": 0.7, "HIGH": 0.4}[risk_level]

        # 计算基于风险的仓位
        adjusted_risk = self.p.risk_per_trade * risk_multiplier
        position_value = self.strategy.broker.getvalue() * adjusted_risk

        size = int(position_value / data.close[0])
        max_size = int(cash * self.p.max_position_size / data.close[0])

        return min(size, max_size)
