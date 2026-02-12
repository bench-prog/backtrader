#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Risk Analyzer Implementation with Notification Integration
Based on the detailed technical implementation roadmap
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import datetime
from collections import defaultdict

import backtrader as bt
from backtrader.utils.py3 import with_metaclass


class RiskAnalyzer(bt.Analyzer):
    """
    风险分析器（利用现有通知机制）
    集成风险监控和标准通知功能
    """
    
    params = (
        ('max_drawdown_limit', 0.15),    # 最大回撤限制 (15%)
        ('max_position_risk', 0.3),      # 最大持仓风险 (30%)
        ('daily_loss_limit', 0.05),      # 每日损失限制 (5%)
        ('check_frequency', 1),          # 检查频率（周期数）
        ('_debug', False),               # 调试模式
    )

    def __init__(self):
        super(RiskAnalyzer, self).__init__()
        self.risk_metrics = {}
        self.daily_pnl = []
        self.check_counter = 0
        self.last_date = None
        self.risk_alerts = []  # 存储风险警报
        self.daily_returns = []  # 存储日收益率
        
        # 初始化风险指标
        self.max_drawdown = 0
        self.current_drawdown = 0
        self.peak_value = self.strategy.broker.getvalue()

    def start(self):
        """开始分析"""
        self.risk_metrics = {
            'max_drawdown': 0,
            'current_drawdown': 0,
            'position_risk': 0,
            'daily_return': 0,
            'volatility': 0,
            'sharpe_ratio': 0
        }

    def next(self):
        """每周期检查风险"""
        self.check_counter += 1
        
        # 按指定频率检查风险
        if self.check_counter % self.p.check_frequency == 0:
            self._check_position_risk()
            self._check_drawdown_risk()
            self._check_daily_risk()
            self._update_performance_metrics()
            
        # 检查日期变化（用于日风险计算）
        current_date = self.strategy.datetime.date()
        if self.last_date != current_date:
            self._handle_new_day(current_date)
            self.last_date = current_date

    def _check_position_risk(self):
        """检查持仓风险并通过标准机制通知"""
        try:
            total_value = self.strategy.broker.getvalue()
            positions_value = 0
            position_details = []
            
            # 计算总持仓价值
            for data in self.strategy.datas:
                position = self.strategy.getposition(data)
                if position.size != 0:
                    position_value = abs(position.size * data.close[0])
                    positions_value += position_value
                    position_details.append({
                        'symbol': data._name,
                        'size': position.size,
                        'value': position_value
                    })
                    
            # 计算持仓风险比例
            position_risk = positions_value / total_value if total_value > 0 else 0
            self.risk_metrics['position_risk'] = position_risk
            
            # 检查是否超过限制
            if position_risk > self.p.max_position_risk:
                alert_info = {
                    'type': 'high_position_risk',
                    'value': position_risk,
                    'limit': self.p.max_position_risk,
                    'positions': position_details,
                    'timestamp': self.strategy.datetime.datetime(),
                    'severity': 'WARNING'
                }
                
                self.risk_alerts.append(alert_info)
                
                # 通过Analyzer的标准输出机制
                self.rets.risk_alerts = getattr(self.rets, 'risk_alerts', [])
                self.rets.risk_alerts.append(alert_info)
                
                # 通过策略的log方法通知
                self.strategy.log(
                    f"风险警告: 持仓风险 {position_risk:.2%} 超过限制 {self.p.max_position_risk:.2%}",
                    self.strategy.datetime.datetime()
                )
                
                if self.p._debug:
                    print(f"持仓风险警报: {alert_info}")
                    
        except Exception as e:
            if self.p._debug:
                print(f"持仓风险检查错误: {e}")

    def _check_drawdown_risk(self):
        """检查回撤风险"""
        try:
            current_value = self.strategy.broker.getvalue()
            
            # 更新峰值
            if current_value > self.peak_value:
                self.peak_value = current_value
            
            # 计算当前回撤
            if self.peak_value > 0:
                self.current_drawdown = (self.peak_value - current_value) / self.peak_value
            else:
                self.current_drawdown = 0
                
            self.risk_metrics['current_drawdown'] = self.current_drawdown
            
            # 更新最大回撤
            if self.current_drawdown > self.max_drawdown:
                self.max_drawdown = self.current_drawdown
                self.risk_metrics['max_drawdown'] = self.max_drawdown
            
            # 检查回撤限制
            if self.current_drawdown > self.p.max_drawdown_limit:
                alert_info = {
                    'type': 'high_drawdown',
                    'value': self.current_drawdown,
                    'limit': self.p.max_drawdown_limit,
                    'peak_value': self.peak_value,
                    'current_value': current_value,
                    'timestamp': self.strategy.datetime.datetime(),
                    'severity': 'CRITICAL'
                }
                
                self.risk_alerts.append(alert_info)
                self.rets.risk_alerts = getattr(self.rets, 'risk_alerts', [])
                self.rets.risk_alerts.append(alert_info)
                
                self.strategy.log(
                    f"严重风险: 当前回撤 {self.current_drawdown:.2%} 超过限制 {self.p.max_drawdown_limit:.2%}",
                    self.strategy.datetime.datetime()
                )
                
                if self.p._debug:
                    print(f"回撤风险警报: {alert_info}")
                    
        except Exception as e:
            if self.p._debug:
                print(f"回撤风险检查错误: {e}")

    def _check_daily_risk(self):
        """检查每日风险"""
        try:
            # 这里可以实现更复杂的日风险检查
            # 目前主要是收集日收益率数据
            pass
        except Exception as e:
            if self.p._debug:
                print(f"日风险检查错误: {e}")

    def _update_performance_metrics(self):
        """更新性能指标"""
        try:
            # 计算波动率（简化版本）
            if len(self.daily_returns) > 1:
                avg_return = sum(self.daily_returns) / len(self.daily_returns)
                variance = sum((r - avg_return) ** 2 for r in self.daily_returns) / len(self.daily_returns)
                volatility = variance ** 0.5
                self.risk_metrics['volatility'] = volatility
                
                # 简化的夏普比率（假设无风险利率为0）
                if volatility > 0:
                    sharpe_ratio = avg_return / volatility if len(self.daily_returns) > 1 else 0
                    self.risk_metrics['sharpe_ratio'] = sharpe_ratio
                    
        except Exception as e:
            if self.p._debug:
                print(f"性能指标更新错误: {e}")

    def _handle_new_day(self, current_date):
        """处理新的一天"""
        try:
            # 计算当日收益
            current_value = self.strategy.broker.getvalue()
            # 这里需要前一天的价值来进行计算
            # 简化处理：假设初始资金为10000
            daily_return = (current_value - 10000) / 10000 if len(self.daily_returns) == 0 else 0
            self.daily_returns.append(daily_return)
            self.risk_metrics['daily_return'] = daily_return
            
            # 清理旧数据（保持最近30天）
            if len(self.daily_returns) > 30:
                self.daily_returns.pop(0)
                
        except Exception as e:
            if self.p._debug:
                print(f"新日处理错误: {e}")

    def get_analysis(self):
        """返回分析结果供外部使用"""
        return {
            'risk_metrics': self.risk_metrics,
            'risk_alerts': getattr(self.rets, 'risk_alerts', []),
            'current_status': self._get_current_status(),
            'performance_summary': self._get_performance_summary()
        }
    
    def _get_current_status(self):
        """获取当前风险状态"""
        alerts = getattr(self.rets, 'risk_alerts', [])
        if not alerts:
            return 'NORMAL'
        
        # 检查是否有严重警报
        critical_alerts = [a for a in alerts if a.get('severity') == 'CRITICAL']
        if critical_alerts:
            return 'CRITICAL'
        
        warning_alerts = [a for a in alerts if a.get('severity') == 'WARNING']
        if warning_alerts:
            return 'WARNING'
            
        return 'NORMAL'
    
    def _get_performance_summary(self):
        """获取性能摘要"""
        return {
            'total_alerts': len(self.risk_alerts),
            'critical_alerts': len([a for a in self.risk_alerts if a.get('severity') == 'CRITICAL']),
            'warning_alerts': len([a for a in self.risk_alerts if a.get('severity') == 'WARNING']),
            'data_points': len(self.daily_returns)
        }

    def notify_order(self, order):
        """订单通知处理（使用Strategy.notify机制）"""
        if order.status == order.Completed:
            # 可以在这里添加订单相关的风险检查
            pass

    def notify_trade(self, trade):
        """交易通知处理（使用Strategy.notify机制）"""
        if trade.isclosed:
            # 可以在这里添加交易结果的风险分析
            pass


class MarketStateAnalyzer(bt.Analyzer):
    """
    市场状态分析器
    识别市场趋势/震荡状态和异常条件
    """
    
    params = (
        ('trend_period', 20),        # 趋势判断周期
        ('volatility_threshold', 0.02),  # 波动率阈值
        ('volume_threshold', 1.5),   # 成交量阈值倍数
        ('_debug', False),
    )

    def __init__(self):
        super(MarketStateAnalyzer, self).__init__()
        self.market_state = 'UNKNOWN'
        self.state_changes = []
        self.indicators = {}

    def next(self):
        """每周期分析市场状态"""
        self._analyze_trend()
        self._analyze_volatility()
        self._analyze_volume()
        self._determine_market_state()

    def _analyze_trend(self):
        """分析市场趋势"""
        # 简化的趋势分析
        if len(self.strategy.datas[0]) > self.p.trend_period:
            data = self.strategy.datas[0]
            # 计算简单移动平均线斜率
            sma_current = sum(data.close.get(ago=-i) for i in range(5)) / 5
            sma_previous = sum(data.close.get(ago=-(i+5)) for i in range(5)) / 5
            
            trend_slope = (sma_current - sma_previous) / sma_previous
            self.indicators['trend_slope'] = trend_slope
            
            if abs(trend_slope) > 0.01:  # 1%的趋势阈值
                self.indicators['trend_direction'] = 'UP' if trend_slope > 0 else 'DOWN'
            else:
                self.indicators['trend_direction'] = 'FLAT'

    def _analyze_volatility(self):
        """分析市场波动率"""
        data = self.strategy.datas[0]
        if len(data) > 10:
            # 计算近期价格波动率
            recent_prices = [data.close[0]] + [data.close[-i] for i in range(1, 11)]
            avg_price = sum(recent_prices) / len(recent_prices)
            volatility = sum(abs(p - avg_price) / avg_price for p in recent_prices) / len(recent_prices)
            self.indicators['volatility'] = volatility

    def _analyze_volume(self):
        """分析成交量"""
        data = self.strategy.datas[0]
        if hasattr(data, 'volume') and len(data.volume) > 20:
            current_volume = data.volume[0]
            avg_volume = sum(data.volume[-i] for i in range(1, 21)) / 20
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            self.indicators['volume_ratio'] = volume_ratio

    def _determine_market_state(self):
        """确定市场状态"""
        trend_dir = self.indicators.get('trend_direction', 'FLAT')
        volatility = self.indicators.get('volatility', 0)
        volume_ratio = self.indicators.get('volume_ratio', 1)
        
        # 判断市场状态
        if trend_dir in ['UP', 'DOWN'] and volatility < self.p.volatility_threshold:
            new_state = 'TRENDING'
        elif volatility > self.p.volatility_threshold:
            new_state = 'VOLATILE'
        elif volume_ratio > self.p.volume_threshold:
            new_state = 'HIGH_VOLUME'
        else:
            new_state = 'CONSOLIDATION'
            
        # 检查状态变化
        if new_state != self.market_state:
            state_change = {
                'from': self.market_state,
                'to': new_state,
                'timestamp': self.strategy.datetime.datetime(),
                'indicators': self.indicators.copy()
            }
            self.state_changes.append(state_change)
            self.market_state = new_state
            
            # 通过标准通知机制
            self.strategy.log(
                f"市场状态变化: {state_change['from']} → {state_change['to']}",
                self.strategy.datetime.datetime()
            )

    def get_analysis(self):
        """返回市场状态分析结果"""
        return {
            'current_state': self.market_state,
            'state_changes': self.state_changes,
            'indicators': self.indicators,
            'latest_change': self.state_changes[-1] if self.state_changes else None
        }


# 便捷函数
def create_risk_analyzers(max_drawdown=0.15, max_position_risk=0.3, daily_loss_limit=0.05):
    """
    创建风险分析器集合的便捷函数
    
    Args:
        max_drawdown: 最大回撤限制
        max_position_risk: 最大持仓风险
        daily_loss_limit: 每日损失限制
        
    Returns:
        dict: 包含各种风险分析器的字典
    """
    return {
        'risk_analyzer': RiskAnalyzer(
            max_drawdown_limit=max_drawdown,
            max_position_risk=max_position_risk,
            daily_loss_limit=daily_loss_limit
        ),
        'market_state': MarketStateAnalyzer()
    }