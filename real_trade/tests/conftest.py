#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
pytest conftest - 公共 fixtures
"""

import pytest

import backtrader as bt


@pytest.fixture
def cerebro():
    """创建一个干净的 Cerebro 实例"""
    c = bt.Cerebro()
    c.broker.setcash(10000)
    return c


@pytest.fixture
def sample_data(tmp_path):
    """生成用于测试的样本 CSV 数据"""
    import csv
    import datetime

    csv_file = tmp_path / "sample.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
        base = datetime.datetime(2024, 1, 1)
        price = 100.0
        for i in range(200):
            dt = base + datetime.timedelta(hours=i)
            o = price
            h = price + 2
            l = price - 2
            c = price + (1 if i % 3 == 0 else -0.5)
            v = 1000 + i * 10
            writer.writerow([dt.strftime("%Y-%m-%d %H:%M:%S"), o, h, l, c, v])
            price = c

    return str(csv_file)
