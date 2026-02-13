#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Portfolio Optimization Implementation
Based on the real_trade/analyzers/portfolio_optimizer.py
Integrated with backtrader main framework
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np
from scipy.optimize import minimize

import backtrader as bt
from backtrader.utils.py3 import with_metaclass


@dataclass
class PortfolioWeights:
    """投资组合权重数据类"""
    weights: Dict[str, float]
    expected_return: float
    risk: float
    sharpe_ratio: float


class MeanVarianceOptimizer(bt.Analyzer):
    """
    均值-方差投资组合优化器
    基于Markowitz现代投资组合理论，集成到backtrader框架中
    """
    
    params = (
        ('target_return', None),      # 目标收益率
        ('risk_free_rate', 0.02),     # 无风险利率
        ('short_allowed', False),     # 是否允许卖空
        ('regularization', 0.01),     # 正则化参数
        ('lookback_period', 252),     # 回 lookback 周期
        ('_debug', False),            # 调试模式
    )

    def __init__(self):
        super(MeanVarianceOptimizer, self).__init__()
        self.returns_history = {}
        self.weights_history = []
        self.efficient_frontier = []
        self.current_portfolio = None

    def start(self):
        """初始化分析器"""
        super(MeanVarianceOptimizer, self).start()
        if self.p._debug:
            print("MeanVarianceOptimizer 初始化完成")

    def _calculate_returns(self, data_name: str) -> np.ndarray:
        """计算收益率序列"""
        if data_name not in self.returns_history:
            try:
                data = self.strategy.getdatabyname(data_name)
                # 获取足够的历史数据
                prices = []
                max_len = min(len(data), self.p.lookback_period)
                for i in range(-max_len, 0):
                    prices.append(data.close[i])
                
                if len(prices) > 1:
                    prices = np.array(prices)
                    returns = np.diff(np.log(prices))
                    self.returns_history[data_name] = returns
                else:
                    self.returns_history[data_name] = np.array([0.0])
            except Exception as e:
                if self.p._debug:
                    print(f"计算 {data_name} 收益率时出错: {e}")
                self.returns_history[data_name] = np.array([0.0])
                
        return self.returns_history[data_name]

    def _calculate_covariance_matrix(self, data_names: List[str]) -> np.ndarray:
        """计算协方差矩阵"""
        try:
            returns_list = []
            valid_names = []
            
            for name in data_names:
                returns = self._calculate_returns(name)
                if len(returns) > 1:
                    returns_list.append(returns)
                    valid_names.append(name)
            
            if len(returns_list) < 2:
                # 如果有效资产少于2个，返回单位矩阵
                return np.eye(len(data_names))
            
            # 对齐长度
            min_length = min(len(ret) for ret in returns_list)
            aligned_returns = [ret[-min_length:] for ret in returns_list]
            
            returns_matrix = np.column_stack(aligned_returns)
            cov_matrix = np.cov(returns_matrix.T)
            
            # 添加正则化避免奇异矩阵
            cov_matrix += np.eye(len(valid_names)) * self.p.regularization
            
            # 扩展到原始维度
            full_cov_matrix = np.eye(len(data_names)) * self.p.regularization
            for i, name_i in enumerate(data_names):
                if name_i in valid_names:
                    idx_i = valid_names.index(name_i)
                    for j, name_j in enumerate(data_names):
                        if name_j in valid_names:
                            idx_j = valid_names.index(name_j)
                            full_cov_matrix[i, j] = cov_matrix[idx_i, idx_j]
            
            return full_cov_matrix
            
        except Exception as e:
            if self.p._debug:
                print(f"计算协方差矩阵时出错: {e}")
            return np.eye(len(data_names)) * self.p.regularization

    def _calculate_expected_returns(self, data_names: List[str]) -> np.ndarray:
        """计算预期收益率"""
        returns = []
        for name in data_names:
            ret_series = self._calculate_returns(name)
            if len(ret_series) > 0:
                # 使用历史平均收益率作为预期收益率（年化）
                expected_ret = np.mean(ret_series) * 252
            else:
                expected_ret = 0.0
            returns.append(expected_ret)
        return np.array(returns)

    def optimize(self, data_names: List[str]) -> PortfolioWeights:
        """执行投资组合优化"""
        if len(data_names) < 2:
            # 单资产情况
            weights = {name: 1.0 if i == 0 else 0.0 for i, name in enumerate(data_names)}
            return PortfolioWeights(weights, 0.0, 0.0, 0.0)

        try:
            # 计算必要参数
            expected_returns = self._calculate_expected_returns(data_names)
            cov_matrix = self._calculate_covariance_matrix(data_names)
            
            if self.p._debug:
                print(f"预期收益率: {expected_returns}")
                print(f"协方差矩阵形状: {cov_matrix.shape}")

            # 定义约束条件
            constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0}]  # 权重和为1

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
                constraints.append({
                    'type': 'eq',
                    'fun': lambda x: np.dot(x, expected_returns) - self.p.target_return,
                })

            # 初始猜测（等权重）
            initial_weights = np.array([1.0 / len(data_names)] * len(data_names))

            # 执行优化
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 100}
            )

            if result.success:
                optimal_weights = result.x
                portfolio_return = np.dot(optimal_weights, expected_returns)
                portfolio_risk = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
                
                if portfolio_risk > 0:
                    sharpe_ratio = (portfolio_return - self.p.risk_free_rate) / portfolio_risk
                else:
                    sharpe_ratio = 0.0

                weights_dict = {name: float(weight) for name, weight in zip(data_names, optimal_weights)}
                
                portfolio_result = PortfolioWeights(
                    weights=weights_dict,
                    expected_return=float(portfolio_return),
                    risk=float(portfolio_risk),
                    sharpe_ratio=float(sharpe_ratio),
                )
                
                # 保存到历史记录
                self.weights_history.append(weights_dict)
                if len(self.weights_history) > 50:  # 限制历史记录长度
                    self.weights_history.pop(0)
                    
                self.current_portfolio = portfolio_result
                return portfolio_result
            else:
                if self.p._debug:
                    print(f"优化失败: {result.message}")
                # 优化失败，返回等权重
                equal_weights = {name: 1.0 / len(data_names) for name in data_names}
                return PortfolioWeights(equal_weights, 0.0, 0.0, 0.0)
                
        except Exception as e:
            if self.p._debug:
                print(f"优化过程出错: {e}")
            # 出错时返回等权重
            equal_weights = {name: 1.0 / len(data_names) for name in data_names}
            return PortfolioWeights(equal_weights, 0.0, 0.0, 0.0)

    def next(self):
        """每个周期调用"""
        # 获取所有数据名称
        data_names = [data._name for data in self.strategy.datas if hasattr(data, '_name')]
        
        if len(data_names) >= 2:
            # 定期重新优化（每20个周期）
            if len(getattr(self, '_optimization_counter', [])) % 20 == 0:
                portfolio = self.optimize(data_names)
                if self.p._debug:
                    print(f"优化结果: {portfolio}")
            
            # 初始化计数器
            if not hasattr(self, '_optimization_counter'):
                self._optimization_counter = 0
            self._optimization_counter += 1

    def get_analysis(self):
        """获取分析结果"""
        return {
            'efficient_frontier': self.efficient_frontier,
            'weights_history': self.weights_history,
            'current_weights': self.weights_history[-1] if self.weights_history else {},
            'current_portfolio': self.current_portfolio.__dict__ if self.current_portfolio else {},
            'optimization_count': len(self.weights_history)
        }


class RiskParityOptimizer(bt.Analyzer):
    """
    风险平价投资组合优化器
    使每个资产对组合风险的贡献相等
    """
    
    params = (
        ('tolerance', 1e-6),          # 收敛容忍度
        ('max_iterations', 100),      # 最大迭代次数
        ('regularization', 0.01),     # 正则化参数
        ('lookback_period', 252),     # 回 lookback 周期
        ('_debug', False),
    )

    def __init__(self):
        super(RiskParityOptimizer, self).__init__()
        self.returns_history = {}
        self.weights_history = []
        self.current_portfolio = None

    def _calculate_marginal_risk_contribution(
        self, weights: np.ndarray, cov_matrix: np.ndarray
    ) -> np.ndarray:
        """计算边际风险贡献"""
        try:
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            if portfolio_variance <= 0:
                return np.zeros_like(weights)
            marginal_contrib = np.dot(cov_matrix, weights) / np.sqrt(portfolio_variance)
            return marginal_contrib
        except:
            return np.zeros_like(weights)

    def optimize(self, data_names: List[str]) -> PortfolioWeights:
        """执行风险平价优化"""
        if len(data_names) < 2:
            weights = {name: 1.0 if i == 0 else 0.0 for i, name in enumerate(data_names)}
            return PortfolioWeights(weights, 0.0, 0.0, 0.0)

        try:
            # 计算协方差矩阵
            cov_matrix = self._calculate_covariance_matrix(data_names)
            n_assets = len(data_names)

            # 初始化权重（等权重）
            weights = np.array([1.0 / n_assets] * n_assets)

            # 迭代优化
            for iteration in range(self.p.max_iterations):
                # 计算边际风险贡献
                marginal_risk = self._calculate_marginal_risk_contribution(weights, cov_matrix)

                # 计算目标风险贡献（相等）
                total_risk_contribution = np.sum(weights * marginal_risk)
                if total_risk_contribution <= 0:
                    break
                target_risk = total_risk_contribution / n_assets

                # 更新权重
                new_weights = weights * target_risk / (marginal_risk + 1e-8)

                # 归一化
                weight_sum = np.sum(new_weights)
                if weight_sum > 0:
                    new_weights = new_weights / weight_sum
                else:
                    new_weights = np.array([1.0 / n_assets] * n_assets)

                # 检查收敛
                if np.linalg.norm(new_weights - weights) < self.p.tolerance:
                    weights = new_weights
                    break

                weights = new_weights

            # 计算组合统计
            expected_returns = self._calculate_expected_returns(data_names)
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            if portfolio_risk > 0:
                sharpe_ratio = portfolio_return / portfolio_risk
            else:
                sharpe_ratio = 0.0

            weights_dict = {name: float(weight) for name, weight in zip(data_names, weights)}

            portfolio_result = PortfolioWeights(
                weights=weights_dict,
                expected_return=float(portfolio_return),
                risk=float(portfolio_risk),
                sharpe_ratio=float(sharpe_ratio),
            )

            # 保存历史记录
            self.weights_history.append(weights_dict)
            if len(self.weights_history) > 50:
                self.weights_history.pop(0)
                
            self.current_portfolio = portfolio_result
            return portfolio_result
            
        except Exception as e:
            if self.p._debug:
                print(f"风险平价优化出错: {e}")
            # 出错时返回等权重
            equal_weights = {name: 1.0 / len(data_names) for name in data_names}
            return PortfolioWeights(equal_weights, 0.0, 0.0, 0.0)

    def _calculate_covariance_matrix(self, data_names: List[str]) -> np.ndarray:
        """计算协方差矩阵"""
        try:
            returns_list = []
            valid_names = []
            
            for name in data_names:
                returns = self._calculate_returns(name)
                if len(returns) > 1:
                    returns_list.append(returns)
                    valid_names.append(name)
            
            if len(returns_list) < 2:
                return np.eye(len(data_names))
            
            # 对齐长度
            min_length = min(len(ret) for ret in returns_list)
            aligned_returns = [ret[-min_length:] for ret in returns_list]
            
            returns_matrix = np.column_stack(aligned_returns)
            cov_matrix = np.cov(returns_matrix.T)
            cov_matrix += np.eye(len(valid_names)) * self.p.regularization
            
            # 扩展到原始维度
            full_cov_matrix = np.eye(len(data_names)) * self.p.regularization
            for i, name_i in enumerate(data_names):
                if name_i in valid_names:
                    idx_i = valid_names.index(name_i)
                    for j, name_j in enumerate(data_names):
                        if name_j in valid_names:
                            idx_j = valid_names.index(name_j)
                            full_cov_matrix[i, j] = cov_matrix[idx_i, idx_j]
            
            return full_cov_matrix
            
        except Exception as e:
            if self.p._debug:
                print(f"计算协方差矩阵时出错: {e}")
            return np.eye(len(data_names)) * self.p.regularization

    def _calculate_expected_returns(self, data_names: List[str]) -> np.ndarray:
        """计算预期收益率"""
        returns = []
        for name in data_names:
            ret_series = self._calculate_returns(name)
            if len(ret_series) > 0:
                expected_ret = np.mean(ret_series) * 252
            else:
                expected_ret = 0.0
            returns.append(expected_ret)
        return np.array(returns)

    def _calculate_returns(self, data_name: str) -> np.ndarray:
        """计算收益率序列"""
        if data_name not in self.returns_history:
            try:
                data = self.strategy.getdatabyname(data_name)
                prices = []
                max_len = min(len(data), self.p.lookback_period)
                for i in range(-max_len, 0):
                    prices.append(data.close[i])
                
                if len(prices) > 1:
                    prices = np.array(prices)
                    returns = np.diff(np.log(prices))
                    self.returns_history[data_name] = returns
                else:
                    self.returns_history[data_name] = np.array([0.0])
            except Exception as e:
                if self.p._debug:
                    print(f"计算 {data_name} 收益率时出错: {e}")
                self.returns_history[data_name] = np.array([0.0])
                
        return self.returns_history[data_name]

    def next(self):
        """每个周期调用"""
        data_names = [data._name for data in self.strategy.datas if hasattr(data, '_name')]
        
        if len(data_names) >= 2:
            # 定期重新优化（每25个周期）
            if len(getattr(self, '_optimization_counter', [])) % 25 == 0:
                portfolio = self.optimize(data_names)
                if self.p._debug:
                    print(f"风险平价优化结果: {portfolio}")
            
            if not hasattr(self, '_optimization_counter'):
                self._optimization_counter = 0
            self._optimization_counter += 1

    def get_analysis(self):
        """获取分析结果"""
        return {
            'weights_history': self.weights_history,
            'current_weights': self.weights_history[-1] if self.weights_history else {},
            'current_portfolio': self.current_portfolio.__dict__ if self.current_portfolio else {},
            'optimization_count': len(self.weights_history)
        }


class PortfolioRebalancer:
    """
    投资组合再平衡器
    根据优化结果调整持仓，集成到backtrader策略中
    """
    
    def __init__(self, strategy: bt.Strategy):
        self.strategy = strategy
        self.target_weights = {}
        self.last_rebalance = 0

    def set_target_weights(self, weights: Dict[str, float]):
        """设置目标权重"""
        self.target_weights = weights

    def rebalance(self, tolerance: float = 0.05, min_interval: int = 10) -> List[Tuple[str, int, float]]:
        """
        执行再平衡
        
        Args:
            tolerance: 权重偏离容忍度
            min_interval: 最小再平衡间隔周期数
            
        Returns:
            List[Tuple[str, int, float]]: (资产名, 调整数量, 当前价格)
        """
        # 检查是否满足最小间隔
        current_bar = len(self.strategy)
        if current_bar - self.last_rebalance < min_interval:
            return []

        trades = []
        try:
            current_value = self.strategy.broker.getvalue()
            
            for data_name, target_weight in self.target_weights.items():
                try:
                    data = self.strategy.getdatabyname(data_name)
                    current_position = self.strategy.getposition(data)
                    current_weight = (
                        (current_position.size * data.close[0]) / current_value
                        if current_value > 0 and current_position.size != 0
                        else 0
                    )

                    # 如果偏离目标权重超过容忍度，则调整
                    if abs(current_weight - target_weight) > tolerance:
                        target_value = current_value * target_weight
                        target_size = int(target_value / data.close[0])
                        size_diff = target_size - current_position.size

                        if size_diff != 0:
                            trades.append((data_name, size_diff, float(data.close[0])))
                            
                except Exception as e:
                    print(f"再平衡 {data_name} 时出错: {e}")

            # 更新上次再平衡时间
            if trades:
                self.last_rebalance = current_bar
                
        except Exception as e:
            print(f"再平衡过程出错: {e}")

        return trades


# 便捷工厂函数
def create_portfolio_optimizer(optimizer_type: str = 'mean_variance', **kwargs):
    """
    创建投资组合优化器的便捷函数
    
    Args:
        optimizer_type: 优化器类型 ('mean_variance' 或 'risk_parity')
        **kwargs: 传递给优化器的参数
        
    Returns:
        对应的优化器类实例
    """
    if optimizer_type == 'risk_parity':
        return RiskParityOptimizer(**kwargs)
    else:
        return MeanVarianceOptimizer(**kwargs)