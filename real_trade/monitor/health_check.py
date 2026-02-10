#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
HealthChecker - 健康检查

检查交易所连接、数据延迟、API 可用性等。
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import time
from typing import Any, Dict, Optional


class HealthChecker:
    """
    系统健康检查

    Usage::

        hc = HealthChecker()
        hc.check_store(store)
        hc.check_data_freshness(last_bar_time, max_delay=120)
        print(hc.status())
    """

    def __init__(self):
        self._checks: Dict[str, Dict[str, Any]] = {}

    def check_store(self, store) -> bool:
        """检查交易所连接"""
        start = time.time()
        try:
            ok = store.test_connection()
            latency = time.time() - start
            self._checks["exchange_connection"] = {
                "ok": ok,
                "latency_ms": round(latency * 1000, 1),
                "checked_at": datetime.datetime.now().isoformat(),
            }
            return ok
        except Exception as e:
            self._checks["exchange_connection"] = {
                "ok": False,
                "error": str(e),
                "checked_at": datetime.datetime.now().isoformat(),
            }
            return False

    def check_data_freshness(
        self, last_bar_time: Optional[datetime.datetime], max_delay_seconds: float = 120
    ) -> bool:
        """检查数据是否新鲜"""
        if last_bar_time is None:
            self._checks["data_freshness"] = {"ok": False, "error": "no data"}
            return False

        delay = (datetime.datetime.now() - last_bar_time).total_seconds()
        ok = delay <= max_delay_seconds
        self._checks["data_freshness"] = {
            "ok": ok,
            "delay_seconds": round(delay, 1),
            "max_allowed": max_delay_seconds,
            "checked_at": datetime.datetime.now().isoformat(),
        }
        return ok

    def check_balance(
        self, store, min_balance: float = 0.0, currency: str = "USDT"
    ) -> bool:
        """检查余额是否充足"""
        try:
            balance = store.get_balance(currency)
            ok = balance >= min_balance
            self._checks["balance"] = {
                "ok": ok,
                "balance": balance,
                "min_required": min_balance,
                "currency": currency,
                "checked_at": datetime.datetime.now().isoformat(),
            }
            return ok
        except Exception as e:
            self._checks["balance"] = {"ok": False, "error": str(e)}
            return False

    def status(self) -> Dict[str, Any]:
        all_ok = all(c.get("ok", False) for c in self._checks.values())
        return {
            "healthy": all_ok,
            "checks": self._checks.copy(),
        }

    @property
    def is_healthy(self) -> bool:
        return all(c.get("ok", False) for c in self._checks.values())
