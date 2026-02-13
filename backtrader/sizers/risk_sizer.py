#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Risk-Based Sizer Implementation
Based on the detailed technical implementation roadmap
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import backtrader as bt


class RiskBasedSizer(bt.Sizer):
    """
    基于风险的仓位管理器
    根据ATR波动率和风险百分比动态计算仓位大小
    """

    params = (
        ("risk_per_trade", 0.02),  # 每笔交易风险比例 (2%)
        ("max_position_pct", 0.3),  # 最大持仓比例 (30%)
        ("volatility_period", 20),  # 波动率计算周期
        ("atr_multiplier", 2.0),  # ATR止损倍数
        ("min_position_size", 1),  # 最小仓位大小
        ("_debug", False),  # 调试模式
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        """
        计算仓位大小的核心方法

        Args:
            comminfo: 佣金信息对象
            cash: 可用现金
            data: 数据源
            isbuy: 是否买入

        Returns:
            int: 计算出的仓位大小
        """
        try:
            # 1. 计算ATR波动率
            atr = self._calculate_atr(data, self.p.volatility_period)
            if self.p._debug:
                print(f"ATR计算结果: {atr}")

            # 2. 计算风险金额
            risk_amount = cash * self.p.risk_per_trade
            if self.p._debug:
                print(f"风险金额: {risk_amount}")

            # 3. 计算基于ATR的仓位大小
            if atr > 0 and data.close[0] > 0:
                # 使用ATR作为止损距离来计算仓位
                position_size = risk_amount / (atr * self.p.atr_multiplier)
                position_value = position_size * data.close[0]

                if self.p._debug:
                    print(f"基于ATR的仓位: {position_size}, 价值: {position_value}")
            else:
                # ATR不可用时使用默认仓位 (10%现金)
                position_size = (cash * 0.1) / data.close[0]
                if self.p._debug:
                    print(f"使用默认仓位: {position_size}")

            # 4. 应用最大持仓限制
            max_size = (cash * self.p.max_position_pct) / data.close[0]
            final_size = min(position_size, max_size)

            if self.p._debug:
                print(f"应用最大限制后: {final_size}")

            # 5. 确保最小仓位大小
            final_size = max(final_size, self.p.min_position_size)

            # 6. 考虑佣金和滑点
            final_size = self._adjust_for_costs(final_size, comminfo, data, cash)

            if self.p._debug:
                print(f"最终仓位大小: {int(final_size)}")

            return int(final_size)

        except Exception as e:
            if self.p._debug:
                print(f"仓位计算错误: {e}")
            # 出错时返回最小仓位
            return self.p.min_position_size

    def _calculate_atr(self, data, period):
        """
        计算ATR指标

        Args:
            data: 数据源
            period: 计算周期

        Returns:
            float: ATR值
        """
        if len(data) < period + 1:
            return 0

        atr_sum = 0
        for i in range(period):
            # 计算真实波幅 (True Range)
            high = data.high[-(i + 1)]
            low = data.low[-(i + 1)]
            prev_close = (
                data.close[-(i + 2)] if i + 2 <= len(data) else data.close[-(i + 1)]
            )

            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)

            true_range = max(tr1, tr2, tr3)
            atr_sum += true_range

        return atr_sum / period

    def _adjust_for_costs(self, size, comminfo, data, cash):
        """
        考虑佣金和滑点调整仓位大小

        Args:
            size: 初始仓位大小
            comminfo: 佣金信息
            data: 数据源
            cash: 可用现金

        Returns:
            float: 调整后的仓位大小
        """
        # 简化的成本调整 - 预留一定比例用于交易成本
        cost_reserve = 0.05  # 预留5%用于成本
        adjusted_size = size * (1 - cost_reserve)

        # 确保调整后不会超过可用资金
        max_affordable = cash / data.close[0]
        return min(adjusted_size, max_affordable)


class FixedRiskSizer(RiskBasedSizer):
    """
    固定风险Sizer - 使用固定的止损距离而非ATR
    """

    params = (
        ("fixed_stop_distance", 0.02),  # 固定止损距离 (2%)
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        """
        使用固定止损距离计算仓位
        """
        try:
            # 计算风险金额
            risk_amount = cash * self.p.risk_per_trade

            # 使用固定止损距离计算仓位
            stop_distance = data.close[0] * self.p.fixed_stop_distance
            if stop_distance > 0:
                position_size = risk_amount / stop_distance
            else:
                position_size = cash * 0.1 / data.close[0]

            # 应用最大持仓限制
            max_size = (cash * self.p.max_position_pct) / data.close[0]
            final_size = min(position_size, max_size)

            # 确保最小仓位大小
            final_size = max(final_size, self.p.min_position_size)

            # 考虑成本调整
            final_size = self._adjust_for_costs(final_size, comminfo, data, cash)

            return int(final_size)

        except Exception as e:
            if self.p._debug:
                print(f"固定风险仓位计算错误: {e}")
            return self.p.min_position_size


# 便捷函数
def create_risk_sizer(
    risk_percent=0.02,
    max_position=0.3,
    volatility_period=20,
    atr_multiplier=2.0,
    sizer_type="atr",
):
    """
    创建风险Sizer的便捷函数

    Args:
        risk_percent: 每笔交易风险比例
        max_position: 最大持仓比例
        volatility_period: 波动率计算周期
        atr_multiplier: ATR倍数
        sizer_type: Sizer类型 ('atr' 或 'fixed')

    Returns:
        RiskBasedSizer实例
    """
    if sizer_type == "fixed":
        return FixedRiskSizer(
            risk_per_trade=risk_percent,
            max_position_pct=max_position,
            fixed_stop_distance=0.02,
        )
    else:
        return RiskBasedSizer(
            risk_per_trade=risk_percent,
            max_position_pct=max_position,
            volatility_period=volatility_period,
            atr_multiplier=atr_multiplier,
        )
