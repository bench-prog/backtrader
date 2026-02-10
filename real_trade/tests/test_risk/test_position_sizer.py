#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
测试风控模块 - position_sizer
"""

import pytest


class TestFixedRatioSizer:
    def test_basic_calc(self):
        from real_trade.risk.position_sizer import FixedRatioSizer

        sizer = FixedRatioSizer(risk_pct=0.02, max_position_pct=0.3)

        class FakeBroker:
            def getvalue(self):
                return 10000.0

        class FakeData:
            class close:
                @staticmethod
                def __getitem__(idx):
                    return 100.0

        size = sizer.calc(FakeBroker(), FakeData())
        assert size == pytest.approx(2.0)  # 10000 * 0.02 / 100

    def test_max_position_cap(self):
        from real_trade.risk.position_sizer import FixedRatioSizer

        sizer = FixedRatioSizer(risk_pct=0.5, max_position_pct=0.1)

        class FakeBroker:
            def getvalue(self):
                return 10000.0

        class FakeData:
            class close:
                @staticmethod
                def __getitem__(idx):
                    return 100.0

        size = sizer.calc(FakeBroker(), FakeData())
        # risk: 10000*0.5/100=50, max: 10000*0.1/100=10 -> 取 min
        assert size == pytest.approx(10.0)


class TestKellySizer:
    def test_kelly(self):
        from real_trade.risk.position_sizer import KellySizer

        sizer = KellySizer(
            win_rate=0.6,
            avg_win_loss_ratio=1.5,
            fraction=1.0,
            max_position_pct=1.0,
        )

        class FakeBroker:
            def getvalue(self):
                return 10000.0

        class FakeData:
            class close:
                @staticmethod
                def __getitem__(idx):
                    return 50.0

        size = sizer.calc(FakeBroker(), FakeData())
        # kelly = (1.5*0.6 - 0.4)/1.5 = (0.9-0.4)/1.5 = 0.333
        # size = 10000 * 0.333 / 50 = 66.67
        assert size > 0
