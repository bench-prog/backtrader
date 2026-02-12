#!/usr/bin/env python3
"""
Backtrader投资组合优化器
实现现代投资组合理论和风险平价策略
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
from scipy.optimize import minimize

import backtrader as bt


@dataclass
class PortfolioWeights:
    """投资组合权重"""

    weights: Dict[str, float]
    expected_return: float
    risk: float
    sharpe_ratio: float


class MeanVarianceOptimizer(bt.Analyzer):
    """
    均值-方差投资组合优化器
    基于Markowitz现代投资组合理论
    """

    params = (
        ("target_return", None),  # 目标收益率
        ("risk_free_rate", 0.02),  # 无风险利率
        ("short_allowed", False),  # 是否允许卖空
        ("regularization", 0.01),  # 正则化参数
    )

    def __init__(self):
        super().__init__()
        self.returns_history = {}
        self.weights_history = []
        self.efficient_frontier = []

    def _calculate_returns(self, data_name: str) -> np.ndarray:
        """计算收益率序列"""
        if data_name not in self.returns_history:
            data = self.strategy.getdatabyname(data_name)
            prices = np.array([data.close[i] for i in range(len(data))])
            returns = np.diff(np.log(prices))
            self.returns_history[data_name] = returns
        return self.returns_history[data_name]

    def _calculate_covariance_matrix(self, data_names: List[str]) -> np.ndarray:
        """计算协方差矩阵"""
        returns_matrix = np.column_stack(
            [self._calculate_returns(name) for name in data_names]
        )

        # 计算协方差矩阵
        cov_matrix = np.cov(returns_matrix.T)

        # 添加正则化避免奇异矩阵
        cov_matrix += np.eye(len(data_names)) * self.p.regularization

        return cov_matrix

    def _calculate_expected_returns(self, data_names: List[str]) -> np.ndarray:
        """计算预期收益率"""
        returns = []
        for name in data_names:
            ret_series = self._calculate_returns(name)
            # 使用历史平均收益率作为预期收益率
            expected_ret = np.mean(ret_series) * 252  # 年化
            returns.append(expected_ret)
        return np.array(returns)

    def optimize(self, data_names: List[str]) -> PortfolioWeights:
        """执行投资组合优化"""
        if len(data_names) < 2:
            # 单资产情况
            weights = {
                name: 1.0 if i == 0 else 0.0 for i, name in enumerate(data_names)
            }
            return PortfolioWeights(weights, 0.0, 0.0, 0.0)

        # 计算必要参数
        expected_returns = self._calculate_expected_returns(data_names)
        cov_matrix = self._calculate_covariance_matrix(data_names)

        # 定义约束条件
        constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1.0}]  # 权重和为1

        # 定义边界条件
        if self.p.short_allowed:
            bounds = [(-1.0, 1.0) for _ in data_names]
        else:
            bounds = [(0.0, 1.0) for _ in data_names]

        # 目标函数：最小化投资组合方差
        def objective(weights):
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            return portfolio_variance

        # 如果指定了目标收益率，添加收益率约束
        if self.p.target_return is not None:
            constraints.append(
                {
                    "type": "eq",
                    "fun": lambda x: np.dot(x, expected_returns) - self.p.target_return,
                }
            )

        # 初始猜测（等权重）
        initial_weights = np.array([1.0 / len(data_names)] * len(data_names))

        # 执行优化
        result = minimize(
            objective,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            optimal_weights = result.x
            portfolio_return = np.dot(optimal_weights, expected_returns)
            portfolio_risk = np.sqrt(
                np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights))
            )
            sharpe_ratio = (portfolio_return - self.p.risk_free_rate) / portfolio_risk

            weights_dict = {
                name: weight for name, weight in zip(data_names, optimal_weights)
            }

            return PortfolioWeights(
                weights=weights_dict,
                expected_return=portfolio_return,
                risk=portfolio_risk,
                sharpe_ratio=sharpe_ratio,
            )
        else:
            # 优化失败，返回等权重
            equal_weights = {name: 1.0 / len(data_names) for name in data_names}
            return PortfolioWeights(equal_weights, 0.0, 0.0, 0.0)

    def get_analysis(self):
        """获取分析结果"""
        return {
            "efficient_frontier": self.efficient_frontier,
            "weights_history": self.weights_history,
            "current_weights": self.weights_history[-1] if self.weights_history else {},
        }


class RiskParityOptimizer(bt.Analyzer):
    """
    风险平价投资组合优化器
    使每个资产对组合风险的贡献相等
    """

    params = (
        ("tolerance", 1e-6),  # 收敛容忍度
        ("max_iterations", 100),  # 最大迭代次数
        ("regularization", 0.01),  # 正则化参数
    )

    def __init__(self):
        super().__init__()
        self.returns_history = {}
        self.weights_history = []

    def _calculate_marginal_risk_contribution(
        self, weights: np.ndarray, cov_matrix: np.ndarray
    ) -> np.ndarray:
        """计算边际风险贡献"""
        portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
        marginal_contrib = np.dot(cov_matrix, weights) / np.sqrt(portfolio_variance)
        return marginal_contrib

    def optimize(self, data_names: List[str]) -> PortfolioWeights:
        """执行风险平价优化"""
        if len(data_names) < 2:
            weights = {
                name: 1.0 if i == 0 else 0.0 for i, name in enumerate(data_names)
            }
            return PortfolioWeights(weights, 0.0, 0.0, 0.0)

        # 计算协方差矩阵
        cov_matrix = self._calculate_covariance_matrix(data_names)
        n_assets = len(data_names)

        # 初始化权重（等权重）
        weights = np.array([1.0 / n_assets] * n_assets)

        # 迭代优化
        for iteration in range(self.p.max_iterations):
            # 计算边际风险贡献
            marginal_risk = self._calculate_marginal_risk_contribution(
                weights, cov_matrix
            )

            # 计算目标风险贡献（相等）
            target_risk = np.sum(weights * marginal_risk) / n_assets

            # 更新权重
            new_weights = weights * target_risk / (marginal_risk + 1e-8)

            # 归一化
            new_weights = new_weights / np.sum(new_weights)

            # 检查收敛
            if np.linalg.norm(new_weights - weights) < self.p.tolerance:
                weights = new_weights
                break

            weights = new_weights

        # 计算组合统计
        expected_returns = self._calculate_expected_returns(data_names)
        portfolio_return = np.dot(weights, expected_returns)
        portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe_ratio = portfolio_return / portfolio_risk  # 简化版Sharpe比率

        weights_dict = {name: weight for name, weight in zip(data_names, weights)}

        return PortfolioWeights(
            weights=weights_dict,
            expected_return=portfolio_return,
            risk=portfolio_risk,
            sharpe_ratio=sharpe_ratio,
        )

    def _calculate_covariance_matrix(self, data_names: List[str]) -> np.ndarray:
        """计算协方差矩阵"""
        returns_matrix = np.column_stack(
            [self._calculate_returns(name) for name in data_names]
        )
        cov_matrix = np.cov(returns_matrix.T)
        cov_matrix += np.eye(len(data_names)) * self.p.regularization
        return cov_matrix

    def _calculate_expected_returns(self, data_names: List[str]) -> np.ndarray:
        """计算预期收益率"""
        returns = []
        for name in data_names:
            ret_series = self._calculate_returns(name)
            expected_ret = np.mean(ret_series) * 252
            returns.append(expected_ret)
        return np.array(returns)

    def _calculate_returns(self, data_name: str) -> np.ndarray:
        """计算收益率序列"""
        if data_name not in self.returns_history:
            data = self.strategy.getdatabyname(data_name)
            prices = np.array([data.close[i] for i in range(len(data))])
            returns = np.diff(np.log(prices))
            self.returns_history[data_name] = returns
        return self.returns_history[data_name]


class PortfolioRebalancer:
    """
    投资组合再平衡器
    根据优化结果调整持仓
    """

    def __init__(self, strategy: bt.Strategy):
        self.strategy = strategy
        self.target_weights = {}

    def set_target_weights(self, weights: Dict[str, float]):
        """设置目标权重"""
        self.target_weights = weights

    def rebalance(self, tolerance: float = 0.05) -> List[Tuple[str, int, float]]:
        """执行再平衡"""
        trades = []
        current_value = self.strategy.broker.getvalue()

        for data_name, target_weight in self.target_weights.items():
            try:
                data = self.strategy.getdatabyname(data_name)
                current_position = self.strategy.getposition(data)
                current_weight = (
                    (current_position.size * data.close[0]) / current_value
                    if current_value > 0
                    else 0
                )

                # 如果偏离目标权重超过容忍度，则调整
                if abs(current_weight - target_weight) > tolerance:
                    target_value = current_value * target_weight
                    target_size = int(target_value / data.close[0])
                    size_diff = target_size - current_position.size

                    if size_diff != 0:
                        trades.append((data_name, size_diff, data.close[0]))

            except Exception as e:
                print(f"再平衡 {data_name} 时出错: {e}")

        return trades
