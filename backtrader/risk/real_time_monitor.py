#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实时风控监控系统 (Real-Time Risk Monitor)
基于backtrader Analyzer的企业级实时风险监控

核心功能：
1. 动态止损系统
2. 风险预算管理
3. VaR/CVaR实时计算
4. 压力测试引擎
5. 熔断机制
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt
import numpy as np
import pandas as pd
from collections import deque
import datetime
import warnings


class RealTimeRiskMonitor(bt.Analyzer):
    """
    实时风险监控Analyzer - 持续监控投资组合风险状况
    """
    
    params = (
        ('var_confidence_level', 0.95),      # VaR置信水平
        ('cvar_confidence_level', 0.95),     # CVaR置信水平
        ('lookback_period', 252),            # 回看周期（交易日）
        ('stress_test_scenarios', None),     # 压力测试场景
        ('circuit_breaker_threshold', 0.1),  # 熔断阈值（单日最大跌幅）
        ('risk_budget_limit', 0.02),         # 风险预算限制
        ('enable_var_monitoring', True),     # 启用VaR监控
        ('enable_cvar_monitoring', True),    # 启用CVaR监控
        ('enable_stress_testing', True),     # 启用压力测试
        ('enable_circuit_breaker', True),    # 启用熔断机制
    )

    def __init__(self):
        super(RealTimeRiskMonitor, self).__init__()
        
        # 风险数据存储
        self.returns_history = deque(maxlen=self.p.lookback_period)
        self.portfolio_values = deque(maxlen=self.p.lookback_period)
        self.drawdown_history = deque(maxlen=self.p.lookback_period)
        
        # 风险指标缓存
        self.current_var = 0.0
        self.current_cvar = 0.0
        self.current_drawdown = 0.0
        self.current_volatility = 0.0
        self.risk_budget_used = 0.0
        
        # 警报和熔断状态
        self.alerts = []
        self.circuit_breaker_triggered = False
        self.last_portfolio_value = None
        self.start_value = None
        
        # 压力测试场景
        self.stress_scenarios = self.p.stress_test_scenarios or self._default_stress_scenarios()
        
        # 统计计数器
        self.var_violations = 0
        self.cvar_violations = 0
        self.drawdown_violations = 0
        self.risk_budget_violations = 0
        
    def _default_stress_scenarios(self):
        """默认压力测试场景"""
        return {
            'market_crash_10': -0.10,      # 市场暴跌10%
            'market_crash_20': -0.20,      # 市场暴跌20%
            'volatility_spike': 2.0,       # 波动率翻倍
            'liquidity_dry_up': 0.5,       # 流动性枯竭50%
            'black_swan': -0.30,           # 黑天鹅事件-30%
        }
    
    def start(self):
        """初始化"""
        self.start_value = self.strategy.broker.getvalue()
        self.last_portfolio_value = self.start_value
        
    def next(self):
        """每周期执行风险监控"""
        current_value = self.strategy.broker.getvalue()
        
        # 计算收益率
        if self.last_portfolio_value:
            returns = (current_value - self.last_portfolio_value) / self.last_portfolio_value
            self.returns_history.append(returns)
            self.portfolio_values.append(current_value)
            
            # 计算回撤
            drawdown = self._calculate_drawdown()
            self.drawdown_history.append(drawdown)
            self.current_drawdown = drawdown
            
        self.last_portfolio_value = current_value
        
        # 执行各项风险监控
        self._monitor_var()
        self._monitor_cvar()
        self._monitor_drawdown()
        self._monitor_risk_budget()
        self._perform_stress_tests()
        self._check_circuit_breaker()
        
    def _calculate_drawdown(self):
        """计算当前回撤"""
        if not self.portfolio_values:
            return 0.0
            
        peak = max(self.portfolio_values)
        current = self.portfolio_values[-1]
        return (peak - current) / peak if peak > 0 else 0.0
    
    def _monitor_var(self):
        """VaR监控"""
        if not self.p.enable_var_monitoring or len(self.returns_history) < 30:
            return
            
        returns_array = np.array(list(self.returns_history))
        var_threshold = np.percentile(returns_array, (1 - self.p.var_confidence_level) * 100)
        self.current_var = abs(var_threshold)
        
        # 检查VaR违规
        if len(returns_array) > 0 and returns_array[-1] < -self.current_var:
            self.var_violations += 1
            self._trigger_alert('VAR_VIOLATION', 
                              f"VaR违规: 实际损失{-returns_array[-1]:.2%} > VaR阈值{self.current_var:.2%}")
    
    def _monitor_cvar(self):
        """CVaR监控"""
        if not self.p.enable_cvar_monitoring or len(self.returns_history) < 30:
            return
            
        returns_array = np.array(list(self.returns_history))
        var_threshold = np.percentile(returns_array, (1 - self.p.cvar_confidence_level) * 100)
        cvar_returns = returns_array[returns_array <= var_threshold]
        self.current_cvar = abs(np.mean(cvar_returns)) if len(cvar_returns) > 0 else 0.0
        
        # 检查CVaR违规
        if self.current_cvar > self.p.risk_budget_limit:
            self.cvar_violations += 1
            self._trigger_alert('CVAR_VIOLATION',
                              f"CVaR超限: {self.current_cvar:.2%} > 限制{self.p.risk_budget_limit:.2%}")
    
    def _monitor_drawdown(self):
        """回撤监控"""
        if self.current_drawdown > self.p.circuit_breaker_threshold:
            self.drawdown_violations += 1
            self._trigger_alert('DRAWDOWN_EXCEEDED',
                              f"回撤超限: {self.current_drawdown:.2%} > 阈值{self.p.circuit_breaker_threshold:.2%}")
    
    def _monitor_risk_budget(self):
        """风险预算监控"""
        if not self.start_value:
            return
            
        current_value = self.strategy.broker.getvalue()
        total_return = (current_value - self.start_value) / self.start_value
        self.risk_budget_used = abs(total_return)
        
        if self.risk_budget_used > self.p.risk_budget_limit:
            self.risk_budget_violations += 1
            self._trigger_alert('RISK_BUDGET_EXCEEDED',
                              f"风险预算超支: 已用{self.risk_budget_used:.2%} > 限制{self.p.risk_budget_limit:.2%}")
    
    def _perform_stress_tests(self):
        """执行压力测试"""
        if not self.p.enable_stress_testing:
            return
            
        current_value = self.strategy.broker.getvalue()
        
        stress_results = {}
        for scenario_name, shock in self.stress_scenarios.items():
            stressed_value = current_value * (1 + shock)
            stress_loss = (current_value - stressed_value) / current_value
            stress_results[scenario_name] = {
                'shock': shock,
                'loss': stress_loss,
                'stressed_value': stressed_value
            }
            
            # 检查极端情况
            if stress_loss > 0.25:  # 损失超过25%
                self._trigger_alert('SEVERE_STRESS_TEST',
                                  f"严重压力测试结果: {scenario_name}导致损失{stress_loss:.2%}")
        
        return stress_results
    
    def _check_circuit_breaker(self):
        """检查熔断条件"""
        if not self.p.enable_circuit_breaker:
            return
            
        # 单日跌幅熔断
        if len(self.returns_history) > 0:
            daily_return = self.returns_history[-1]
            if daily_return < -self.p.circuit_breaker_threshold:
                self.circuit_breaker_triggered = True
                self._trigger_alert('CIRCUIT_BREAKER_TRIGGERED',
                                  f"熔断机制触发: 单日跌幅{abs(daily_return):.2%} > 阈值{self.p.circuit_breaker_threshold:.2%}")
                # 这里可以实现实际的交易暂停逻辑
    
    def _trigger_alert(self, alert_type, message):
        """触发风险警报"""
        alert = {
            'timestamp': self.strategy.datetime.datetime(),
            'type': alert_type,
            'message': message,
            'portfolio_value': self.strategy.broker.getvalue(),
            'drawdown': self.current_drawdown,
            'var': self.current_var,
            'cvar': self.current_cvar
        }
        self.alerts.append(alert)
        
        # 通过Strategy通知机制发送警报
        if hasattr(self.strategy, 'notify_store'):
            self.strategy.notify_store({'risk_alert': alert})
    
    def get_analysis(self):
        """获取风险分析结果"""
        return {
            'current_var': self.current_var,
            'current_cvar': self.current_cvar,
            'current_drawdown': self.current_drawdown,
            'current_volatility': self.current_volatility,
            'risk_budget_used': self.risk_budget_used,
            'var_violations': self.var_violations,
            'cvar_violations': self.cvar_violations,
            'drawdown_violations': self.drawdown_violations,
            'risk_budget_violations': self.risk_budget_violations,
            'alerts_count': len(self.alerts),
            'circuit_breaker_triggered': self.circuit_breaker_triggered,
            'total_periods': len(self.returns_history),
            'confidence_levels': {
                'var': self.p.var_confidence_level,
                'cvar': self.p.cvar_confidence_level
            }
        }
    
    def get_alerts(self, alert_type=None):
        """获取警报信息"""
        if alert_type:
            return [alert for alert in self.alerts if alert['type'] == alert_type]
        return self.alerts.copy()
    
    def get_stress_test_results(self):
        """获取压力测试结果"""
        return self._perform_stress_tests()
    
    def reset(self):
        """重置监控器状态"""
        self.returns_history.clear()
        self.portfolio_values.clear()
        self.drawdown_history.clear()
        self.alerts.clear()
        self.circuit_breaker_triggered = False
        self.var_violations = 0
        self.cvar_violations = 0
        self.drawdown_violations = 0
        self.risk_budget_violations = 0


class DynamicStopLoss(bt.Observer):
    """
    动态止损观察器 - 基于波动率调整止损水平
    """
    
    lines = ('stop_loss',)
    plotinfo = dict(plot=True, subplot=False)
    
    params = (
        ('atr_period', 14),
        ('stop_multiplier', 2.0),
        ('trailing', True),
    )
    
    def __init__(self):
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        self.stop_level = None
        
    def next(self):
        """计算动态止损水平"""
        if not len(self.atr):
            return
            
        current_price = self.data.close[0]
        atr_value = self.atr[0]
        
        if self.p.trailing:
            # 追踪止损
            new_stop = current_price - self.p.stop_multiplier * atr_value
            if self.stop_level is None or new_stop > self.stop_level:
                self.stop_level = new_stop
        else:
            # 固定止损
            if self.stop_level is None:
                self.stop_level = current_price - self.p.stop_multiplier * atr_value
        
        self.lines.stop_loss[0] = self.stop_level


def add_real_time_risk_monitoring(cerebro, **monitor_params):
    """
    为Cerebro添加实时风险监控
    
    使用示例:
    cerebro = bt.Cerebro()
    risk_monitor = add_real_time_risk_monitoring(cerebro,
        var_confidence_level=0.95,
        circuit_breaker_threshold=0.1,
        risk_budget_limit=0.02
    )
    """
    risk_monitor = RealTimeRiskMonitor(**monitor_params)
    cerebro.addanalyzer(risk_monitor)
    return risk_monitor


# 风控策略混入类
class RiskControlMixin:
    """
    风险控制混入类 - 为策略添加风控功能
    """
    
    def __init__(self):
        super(RiskControlMixin, self).__init__()
        self.risk_monitor = None
        
    def set_risk_monitor(self, risk_monitor):
        """设置风险监控器"""
        self.risk_monitor = risk_monitor
        
    def check_risk_limits(self):
        """检查风险限制"""
        if not self.risk_monitor:
            return True
            
        analysis = self.risk_monitor.get_analysis()
        
        # 检查各种风险指标
        if analysis['circuit_breaker_triggered']:
            self.log("风险警告: 熔断机制已触发")
            return False
            
        if analysis['var_violations'] > 0:
            self.log(f"风险警告: VaR违规 {analysis['var_violations']} 次")
            
        if analysis['drawdown_violations'] > 0:
            self.log(f"风险警告: 回撤超限 {analysis['drawdown_violations']} 次")
            
        return True
        
    def get_risk_status(self):
        """获取当前风险状态"""
        if not self.risk_monitor:
            return {}
        return self.risk_monitor.get_analysis()