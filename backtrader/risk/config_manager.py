#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
风控配置管理中心 (Risk Configuration Manager)
企业级风控规则配置和管理模块

核心功能：
1. 风控规则DSL (领域特定语言)
2. 动态规则加载
3. 多账户风控隔离
4. 风控参数热更新
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import json
import os
import threading
from collections import defaultdict
from typing import Any, Callable, Dict, List

import yaml


class RiskRule:
    """
    风控规则基类
    """

    def __init__(self, name: str, description: str = "", enabled: bool = True):
        self.name = name
        self.description = description
        self.enabled = enabled
        self.violation_count = 0
        self.last_violation = None

    def check(self, context: Dict[str, Any]) -> tuple:
        """
        执行规则检查
        返回: (passed: bool, message: str)
        """
        raise NotImplementedError("子类必须实现check方法")

    def reset(self):
        """重置规则状态"""
        self.violation_count = 0
        self.last_violation = None


class LeverageLimitRule(RiskRule):
    """杠杆限制规则"""

    def __init__(self, max_leverage: float = 2.0, **kwargs):
        super().__init__("leverage_limit", "杠杆率限制", **kwargs)
        self.max_leverage = max_leverage

    def check(self, context: Dict[str, Any]) -> tuple:
        if not self.enabled:
            return True, ""

        current_leverage = context.get("current_leverage", 0)
        if current_leverage > self.max_leverage:
            self.violation_count += 1
            self.last_violation = datetime.datetime.now()
            return False, f"杠杆超限: {current_leverage:.2f} > {self.max_leverage}"
        return True, ""


class PositionConcentrationRule(RiskRule):
    """持仓集中度规则"""

    def __init__(self, max_concentration: float = 0.3, **kwargs):
        super().__init__("position_concentration", "持仓集中度限制", **kwargs)
        self.max_concentration = max_concentration

    def check(self, context: Dict[str, Any]) -> tuple:
        if not self.enabled:
            return True, ""

        concentration = context.get("position_concentration", 0)
        if concentration > self.max_concentration:
            self.violation_count += 1
            self.last_violation = datetime.datetime.now()
            return (
                False,
                f"持仓集中度过高: {concentration:.2%} > {self.max_concentration:.2%}",
            )
        return True, ""


class DailyLossLimitRule(RiskRule):
    """日亏损限制规则"""

    def __init__(self, max_daily_loss: float = 0.05, **kwargs):
        super().__init__("daily_loss_limit", "日亏损限制", **kwargs)
        self.max_daily_loss = max_daily_loss

    def check(self, context: Dict[str, Any]) -> tuple:
        if not self.enabled:
            return True, ""

        daily_loss = context.get("daily_loss", 0)
        if daily_loss > self.max_daily_loss:
            self.violation_count += 1
            self.last_violation = datetime.datetime.now()
            return False, f"日亏损超限: {daily_loss:.2%} > {self.max_daily_loss:.2%}"
        return True, ""


class MarketImpactRule(RiskRule):
    """市场冲击成本规则"""

    def __init__(self, max_impact: float = 0.02, **kwargs):
        super().__init__("market_impact", "市场冲击成本限制", **kwargs)
        self.max_impact = max_impact

    def check(self, context: Dict[str, Any]) -> tuple:
        if not self.enabled:
            return True, ""

        impact_cost = context.get("market_impact", 0)
        if impact_cost > self.max_impact:
            self.violation_count += 1
            self.last_violation = datetime.datetime.now()
            return False, f"市场冲击成本过高: {impact_cost:.2%} > {self.max_impact:.2%}"
        return True, ""


class RiskConfigurationManager:
    """
    风控配置管理器 - 管理风控规则集合
    """

    def __init__(self, account_id: str = "default"):
        self.account_id = account_id
        self.rules: Dict[str, RiskRule] = {}
        self.rule_groups: Dict[str, List[str]] = defaultdict(list)
        self.violation_callbacks: List[Callable] = []
        self._lock = threading.RLock()

        # 默认规则组
        self.rule_groups["pre_trade"].extend(
            ["leverage_limit", "position_concentration", "market_impact"]
        )
        self.rule_groups["real_time"].extend(["daily_loss_limit"])

    def add_rule(self, rule: RiskRule, groups: List[str] = None):
        """添加风控规则"""
        with self._lock:
            self.rules[rule.name] = rule
            if groups:
                for group in groups:
                    if rule.name not in self.rule_groups[group]:
                        self.rule_groups[group].append(rule.name)

    def remove_rule(self, rule_name: str):
        """移除风控规则"""
        with self._lock:
            if rule_name in self.rules:
                del self.rules[rule_name]
                # 从所有组中移除
                for group_rules in self.rule_groups.values():
                    if rule_name in group_rules:
                        group_rules.remove(rule_name)

    def enable_rule(self, rule_name: str, enabled: bool = True):
        """启用/禁用规则"""
        with self._lock:
            if rule_name in self.rules:
                self.rules[rule_name].enabled = enabled

    def check_rules(
        self, context: Dict[str, Any], group: str = None
    ) -> Dict[str, tuple]:
        """
        执行规则检查
        返回: {rule_name: (passed, message)}
        """
        with self._lock:
            results = {}
            rules_to_check = self.rule_groups[group] if group else self.rules.keys()

            for rule_name in rules_to_check:
                if rule_name in self.rules:
                    rule = self.rules[rule_name]
                    passed, message = rule.check(context)
                    results[rule_name] = (passed, message)

                    # 触发违规回调
                    if not passed:
                        self._trigger_violation_callbacks(rule_name, message, context)

            return results

    def add_violation_callback(self, callback: Callable):
        """添加违规回调函数"""
        with self._lock:
            self.violation_callbacks.append(callback)

    def _trigger_violation_callbacks(
        self, rule_name: str, message: str, context: Dict[str, Any]
    ):
        """触发违规回调"""
        violation_info = {
            "timestamp": datetime.datetime.now(),
            "account_id": self.account_id,
            "rule_name": rule_name,
            "message": message,
            "context": context,
        }

        for callback in self.violation_callbacks:
            try:
                callback(violation_info)
            except Exception as e:
                print(f"违规回调执行错误: {e}")

    def get_rule_statistics(self) -> Dict[str, Dict]:
        """获取规则统计信息"""
        with self._lock:
            stats = {}
            for name, rule in self.rules.items():
                stats[name] = {
                    "name": rule.name,
                    "description": rule.description,
                    "enabled": rule.enabled,
                    "violation_count": rule.violation_count,
                    "last_violation": rule.last_violation,
                }
            return stats

    def reset_statistics(self):
        """重置统计信息"""
        with self._lock:
            for rule in self.rules.values():
                rule.reset()

    def export_config(self, filepath: str, format: str = "json"):
        """导出配置"""
        config = {
            "account_id": self.account_id,
            "rules": {},
            "rule_groups": dict(self.rule_groups),
        }

        for name, rule in self.rules.items():
            config["rules"][name] = {
                "type": rule.__class__.__name__,
                "enabled": rule.enabled,
                "parameters": self._extract_rule_parameters(rule),
            }

        if format.lower() == "json":
            with open(filepath, "w") as f:
                json.dump(config, f, indent=2, default=str)
        elif format.lower() == "yaml":
            with open(filepath, "w") as f:
                yaml.dump(config, f, default_flow_style=False)

    def _extract_rule_parameters(self, rule: RiskRule) -> Dict:
        """提取规则参数"""
        # 这里可以根据具体规则类型提取参数
        params = {}
        if hasattr(rule, "max_leverage"):
            params["max_leverage"] = rule.max_leverage
        if hasattr(rule, "max_concentration"):
            params["max_concentration"] = rule.max_concentration
        if hasattr(rule, "max_daily_loss"):
            params["max_daily_loss"] = rule.max_daily_loss
        if hasattr(rule, "max_impact"):
            params["max_impact"] = rule.max_impact
        return params

    def import_config(self, filepath: str):
        """导入配置"""
        with self._lock:
            if filepath.endswith(".json"):
                with open(filepath, "r") as f:
                    config = json.load(f)
            elif filepath.endswith((".yaml", ".yml")):
                with open(filepath, "r") as f:
                    config = yaml.safe_load(f)
            else:
                raise ValueError("不支持的配置文件格式")

            self.account_id = config.get("account_id", self.account_id)
            self.rule_groups = defaultdict(list, config.get("rule_groups", {}))

            # 重建规则
            self.rules.clear()
            for name, rule_config in config.get("rules", {}).items():
                rule = self._create_rule_from_config(name, rule_config)
                if rule:
                    self.rules[name] = rule

    def _create_rule_from_config(self, name: str, config: Dict) -> RiskRule:
        """根据配置创建规则"""
        rule_type = config.get("type")
        enabled = config.get("enabled", True)
        params = config.get("parameters", {})

        rule_mapping = {
            "LeverageLimitRule": lambda: LeverageLimitRule(enabled=enabled, **params),
            "PositionConcentrationRule": lambda: PositionConcentrationRule(
                enabled=enabled, **params
            ),
            "DailyLossLimitRule": lambda: DailyLossLimitRule(enabled=enabled, **params),
            "MarketImpactRule": lambda: MarketImpactRule(enabled=enabled, **params),
        }

        if rule_type in rule_mapping:
            return rule_mapping[rule_type]()
        return None


class MultiAccountRiskManager:
    """
    多账户风控管理器 - 管理多个账户的风控配置
    """

    def __init__(self):
        self.accounts: Dict[str, RiskConfigurationManager] = {}
        self.global_rules: Dict[str, RiskRule] = {}
        self._lock = threading.RLock()

    def add_account(self, account_id: str) -> RiskConfigurationManager:
        """添加账户"""
        with self._lock:
            if account_id not in self.accounts:
                self.accounts[account_id] = RiskConfigurationManager(account_id)
            return self.accounts[account_id]

    def get_account_manager(self, account_id: str) -> RiskConfigurationManager:
        """获取账户管理器"""
        with self._lock:
            return self.accounts.get(account_id)

    def add_global_rule(self, rule: RiskRule):
        """添加全局规则（适用于所有账户）"""
        with self._lock:
            self.global_rules[rule.name] = rule

    def check_all_accounts(
        self, context_getter: Callable[[str], Dict]
    ) -> Dict[str, Dict]:
        """检查所有账户"""
        with self._lock:
            results = {}
            for account_id, manager in self.accounts.items():
                context = context_getter(account_id)
                # 合并全局规则和账户特定规则
                account_results = manager.check_rules(context)
                global_results = {}
                for rule_name, rule in self.global_rules.items():
                    passed, message = rule.check(context)
                    global_results[rule_name] = (passed, message)

                results[account_id] = {**account_results, **global_results}
            return results

    def export_all_configs(self, directory: str):
        """导出所有账户配置"""
        with self._lock:
            os.makedirs(directory, exist_ok=True)
            for account_id, manager in self.accounts.items():
                filepath = os.path.join(directory, f"risk_config_{account_id}.json")
                manager.export_config(filepath)


def create_default_risk_config(account_id: str = "default") -> RiskConfigurationManager:
    """
    创建默认风控配置
    """
    manager = RiskConfigurationManager(account_id)

    # 添加默认规则
    manager.add_rule(LeverageLimitRule(max_leverage=2.0), ["pre_trade"])
    manager.add_rule(PositionConcentrationRule(max_concentration=0.3), ["pre_trade"])
    manager.add_rule(DailyLossLimitRule(max_daily_loss=0.05), ["real_time"])
    manager.add_rule(MarketImpactRule(max_impact=0.02), ["pre_trade"])

    return manager


# 便捷函数
def load_risk_config_from_file(
    filepath: str, account_id: str = "default"
) -> RiskConfigurationManager:
    """从文件加载风控配置"""
    manager = RiskConfigurationManager(account_id)
    manager.import_config(filepath)
    return manager


def save_risk_config_to_file(
    manager: RiskConfigurationManager, filepath: str, format: str = "json"
):
    """保存风控配置到文件"""
    manager.export_config(filepath, format)
