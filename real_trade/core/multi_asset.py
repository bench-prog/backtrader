#!/usr/bin/env python3
"""
多资产交易支持系统
实现对股票、期货、期权等多种资产类别的统一支持
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

import numpy as np

import backtrader as bt


class AssetType(Enum):
    """资产类型枚举"""

    STOCK = "stock"  # 股票
    FUTURE = "future"  # 期货
    OPTION = "option"  # 期权
    FOREX = "forex"  # 外汇
    CRYPTO = "crypto"  # 加密货币
    BOND = "bond"  # 债券


class OptionType(Enum):
    """期权类型"""

    CALL = "call"  # 看涨期权
    PUT = "put"  # 看跌期权


@dataclass
class AssetInfo:
    """资产信息"""

    symbol: str
    asset_type: AssetType
    exchange: str
    currency: str
    contract_size: float = 1.0
    tick_size: float = 0.01
    multiplier: float = 1.0
    margin_rate: float = 1.0
    option_type: Optional[OptionType] = None
    strike_price: Optional[float] = None
    expiration_date: Optional[str] = None


class MultiAssetData(bt.feeds.PandasData):
    """
    多资产数据源
    支持不同类型资产的数据格式统一
    """

    params = (
        ("asset_info", None),  # AssetInfo对象
        ("adjust_for_splits", True),  # 是否调整拆分
        ("adjust_for_dividends", True),  # 是否调整分红
    )

    def __init__(self):
        super().__init__()
        self.asset_info = self.p.asset_info or AssetInfo(
            symbol="UNKNOWN",
            asset_type=AssetType.STOCK,
            exchange="UNKNOWN",
            currency="USD",
        )

    def get_contract_value(self, price: float, size: int) -> float:
        """计算合约价值"""
        return price * size * self.asset_info.contract_size * self.asset_info.multiplier

    def get_margin_requirement(self, price: float, size: int) -> float:
        """计算保证金要求"""
        contract_value = self.get_contract_value(price, size)
        return contract_value * self.asset_info.margin_rate


class MultiAssetCommissionInfo(bt.CommInfoBase):
    """
    多资产佣金信息
    支持不同类型资产的佣金计算
    """

    def __init__(self, asset_info: AssetInfo):
        super().__init__()
        self.asset_info = asset_info

    def _getcommission(self, size, price, pseudoexec):
        """计算佣金"""
        contract_value = (
            price
            * abs(size)
            * self.asset_info.contract_size
            * self.asset_info.multiplier
        )

        if self.asset_info.asset_type == AssetType.STOCK:
            # 股票佣金：固定费用+比例费用
            fixed_fee = 0.0  # 有些券商免佣
            percentage_fee = contract_value * 0.001  # 0.1% 佣金
            return max(fixed_fee, percentage_fee)

        elif self.asset_info.asset_type == AssetType.FUTURE:
            # 期货佣金：每手固定费用
            return abs(size) * 2.0  # 假设每手2美元

        elif self.asset_info.asset_type == AssetType.OPTION:
            # 期权佣金：每份固定费用
            return abs(size) * 0.5  # 假设每份0.5美元

        elif self.asset_info.asset_type == AssetType.FOREX:
            # 外汇点差
            spread = self.asset_info.tick_size * 2  # 买卖价差
            return contract_value * spread

        elif self.asset_info.asset_type == AssetType.CRYPTO:
            # 加密货币：百分比费用
            return contract_value * 0.002  # 0.2% 费用

        else:
            # 默认佣金
            return contract_value * 0.001


class MultiAssetSizer(bt.Sizer):
    """
    多资产仓位管理器
    根据资产类型调整仓位大小
    """

    params = (
        ("risk_per_trade", 0.02),  # 每笔交易风险比例
        ("max_position_value", 0.1),  # 最大仓位价值比例
    )

    def __init__(self):
        super().__init__()
        self.asset_configs = {}  # 不同资产的配置

    def set_asset_config(self, asset_type: AssetType, config: Dict):
        """设置特定资产类型的配置"""
        self.asset_configs[asset_type] = config

    def _getsizing(self, comminfo, cash, data, isbuy):
        """计算仓位大小"""
        if not hasattr(data, "asset_info"):
            # 不是多资产数据源，使用默认计算
            return int(cash * self.p.max_position_value / data.close[0])

        asset_info = data.asset_info
        current_price = data.close[0]

        # 获取资产特定配置
        config = self.asset_configs.get(asset_info.asset_type, {})
        risk_pct = config.get("risk_per_trade", self.p.risk_per_trade)
        max_pos_pct = config.get("max_position_value", self.p.max_position_value)

        # 计算基于风险的仓位
        portfolio_value = self.broker.getvalue()
        risk_amount = portfolio_value * risk_pct

        if asset_info.asset_type == AssetType.STOCK:
            # 股票：基于股价波动计算仓位
            atr = self._calculate_atr(data, 14)
            position_size = int(risk_amount / (atr * asset_info.contract_size))

        elif asset_info.asset_type == AssetType.FUTURE:
            # 期货：基于合约价值计算
            contract_value = (
                current_price * asset_info.contract_size * asset_info.multiplier
            )
            position_size = int(risk_amount / (contract_value * 0.02))  # 假设2%波动

        elif asset_info.asset_type == AssetType.OPTION:
            # 期权：基于权利金计算
            position_size = int(risk_amount / current_price)

        elif asset_info.asset_type == AssetType.FOREX:
            # 外汇：基于货币对点值计算
            pip_value = asset_info.tick_size * asset_info.contract_size
            position_size = int(risk_amount / (pip_value * 100))  # 100点波动

        elif asset_info.asset_type == AssetType.CRYPTO:
            # 加密货币：简单比例计算
            position_size = int((portfolio_value * max_pos_pct) / current_price)

        else:
            position_size = int(cash * max_pos_pct / current_price)

        # 限制最大仓位
        max_affordable = int(cash * 0.95 / current_price)
        position_size = min(position_size, max_affordable)

        return max(0, position_size)

    def _calculate_atr(self, data, period: int) -> float:
        """计算ATR"""
        if len(data) < period + 1:
            return data.close[0] * 0.02  # 默认2%波动

        trs = []
        for i in range(-period, 0):
            high = data.high[i]
            low = data.low[i]
            prev_close = data.close[i - 1] if i > -len(data) else data.close[i]

            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            tr = max(tr1, tr2, tr3)
            trs.append(tr)

        return np.mean(trs)


class MultiAssetStrategy(bt.Strategy):
    """
    多资产交易策略基类
    支持同时交易多种资产类别
    """

    params = (
        ("printlog", True),
        ("diversification_limit", 0.25),  # 单一资产最大占比
    )

    def __init__(self):
        super().__init__()
        self.asset_positions = {}  # 资产仓位记录
        self.correlation_matrix = {}  # 资产相关性矩阵

    def log(self, txt, level="INFO"):
        """日志记录"""
        if self.p.printlog:
            timestamp = self.datetime.datetime().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} | {level} | {txt}")

    def next(self):
        """主逻辑循环"""
        # 更新资产仓位信息
        self._update_asset_positions()

        # 检查分散化限制
        self._check_diversification()

        # 生成交易信号
        self.generate_signals()

    def _update_asset_positions(self):
        """更新各资产仓位"""
        for data in self.datas:
            position = self.getposition(data)
            if position.size != 0:
                self.asset_positions[data._name] = {
                    "size": position.size,
                    "price": position.price,
                    "value": position.size * data.close[0],
                    "pnl": position.size * (data.close[0] - position.price),
                }
            elif data._name in self.asset_positions:
                del self.asset_positions[data._name]

    def _check_diversification(self):
        """检查投资组合分散化"""
        total_value = self.broker.getvalue()
        if total_value <= 0:
            return

        for asset_name, pos_info in self.asset_positions.items():
            asset_ratio = abs(pos_info["value"]) / total_value
            if asset_ratio > self.p.diversification_limit:
                self.log(
                    f"警告: {asset_name} 仓位占比 {asset_ratio:.2%} 超过限制 {self.p.diversification_limit:.2%}",
                    "WARNING",
                )

    def get_asset_info(self, data) -> Optional[AssetInfo]:
        """获取资产信息"""
        if hasattr(data, "asset_info"):
            return data.asset_info
        return None

    def calculate_portfolio_risk(self) -> float:
        """计算投资组合风险"""
        if not self.asset_positions:
            return 0.0

        # 简化的风险计算
        total_risk = 0.0
        total_value = sum(abs(pos["value"]) for pos in self.asset_positions.values())

        if total_value == 0:
            return 0.0

        for pos in self.asset_positions.values():
            asset_weight = abs(pos["value"]) / total_value
            # 假设每种资产风险为2%
            asset_risk = asset_weight * 0.02
            total_risk += asset_risk

        return total_risk

    def generate_signals(self):
        """
        生成交易信号 - 由子类实现
        """
        pass


# 便捷的资产信息创建函数
def create_stock_info(symbol: str, exchange: str, **kwargs) -> AssetInfo:
    """创建股票资产信息"""
    return AssetInfo(
        symbol=symbol,
        asset_type=AssetType.STOCK,
        exchange=exchange,
        currency=kwargs.get("currency", "USD"),
        contract_size=1.0,
        tick_size=0.01,
        multiplier=1.0,
        margin_rate=1.0,
    )


def create_future_info(
    symbol: str, exchange: str, contract_size: float, **kwargs
) -> AssetInfo:
    """创建期货资产信息"""
    return AssetInfo(
        symbol=symbol,
        asset_type=AssetType.FUTURE,
        exchange=exchange,
        currency=kwargs.get("currency", "USD"),
        contract_size=contract_size,
        tick_size=kwargs.get("tick_size", 0.01),
        multiplier=kwargs.get("multiplier", 1.0),
        margin_rate=kwargs.get("margin_rate", 0.1),  # 期货通常10%保证金
    )


def create_option_info(
    symbol: str,
    exchange: str,
    option_type: OptionType,
    strike_price: float,
    expiration_date: str,
    **kwargs,
) -> AssetInfo:
    """创建期权资产信息"""
    return AssetInfo(
        symbol=symbol,
        asset_type=AssetType.OPTION,
        exchange=exchange,
        currency=kwargs.get("currency", "USD"),
        contract_size=100.0,  # 期权通常100股一份
        tick_size=0.01,
        multiplier=1.0,
        margin_rate=kwargs.get("margin_rate", 1.0),
        option_type=option_type,
        strike_price=strike_price,
        expiration_date=expiration_date,
    )
