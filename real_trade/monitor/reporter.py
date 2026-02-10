#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Reporter - 定期报告

生成文本/JSON 格式的交易报告，可配合通知模块发送。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import json
from typing import Any, Dict, Optional


class Reporter:
    """
    交易报告生成器

    Usage::

        reporter = Reporter()
        text = reporter.generate_text(tracker.summary(), hc.status())
        json_str = reporter.generate_json(tracker.summary())
    """

    @staticmethod
    def generate_text(
        performance: Dict[str, Any], health: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成文本报告"""
        lines = [
            "=" * 40,
            f"  Trading Report  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 40,
            f"  Current Value : {performance.get('current_value', 'N/A')}",
            f"  Return        : {performance.get('return_pct', 'N/A')}",
            f"  Net P&L       : {performance.get('net_pnl', 'N/A')}",
            f"  Max Drawdown  : {performance.get('max_drawdown', 'N/A')}",
            f"  Trades        : {performance.get('trade_count', 0)}",
            f"  Win Rate      : {performance.get('win_rate', 'N/A')}",
            f"  Profit Factor : {performance.get('profit_factor', 'N/A')}",
        ]

        if health:
            lines.append("-" * 40)
            lines.append(
                f"  System Health : {'OK' if health.get('healthy') else 'WARN'}"
            )
            for name, check in health.get("checks", {}).items():
                status = "OK" if check.get("ok") else "FAIL"
                lines.append(f"    {name}: {status}")

        lines.append("=" * 40)
        return "\n".join(lines)

    @staticmethod
    def generate_json(
        performance: Dict[str, Any], health: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成 JSON 报告"""
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "performance": performance,
        }
        if health:
            report["health"] = health
        return json.dumps(report, indent=2, ensure_ascii=False)
