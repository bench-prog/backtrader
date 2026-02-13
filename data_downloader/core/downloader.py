#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Core Downloader Base Class

数据下载器的核心基类，定义统一的接口和通用功能。
"""

import abc
import datetime
import io
from typing import Optional, Union


class BaseDownloader(abc.ABC):
    """数据下载器基类"""

    def __init__(self):
        self.datafile: Optional[io.StringIO] = None
        self.error: Optional[str] = None

    @abc.abstractmethod
    def download(self, output_file: Union[str, io.TextIOBase]) -> bool:
        """
        下载数据到指定文件

        Args:
            output_file: 输出文件路径或文件对象

        Returns:
            bool: 下载是否成功
        """
        pass

    def _validate_dates(self, fromdate: str, todate: str) -> tuple:
        """
        验证和解析日期字符串

        Args:
            fromdate: 开始日期 (YYYY-MM-DD)
            todate: 结束日期 (YYYY-MM-DD)

        Returns:
            tuple: (datetime对象, datetime对象)

        Raises:
            ValueError: 日期格式错误或逻辑错误
        """
        try:
            from_dt = datetime.datetime.strptime(fromdate, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid fromdate format: {fromdate}. Expected YYYY-MM-DD"
            ) from e

        try:
            to_dt = datetime.datetime.strptime(todate, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid todate format: {todate}. Expected YYYY-MM-DD"
            ) from e

        if from_dt > to_dt:
            raise ValueError("fromdate must be before or equal to todate")

        return from_dt, to_dt

    def _write_output(self, output_file: Union[str, io.TextIOBase]) -> None:
        """
        将下载的数据写入输出文件

        Args:
            output_file: 输出文件路径或文件对象
        """
        if not self.datafile:
            raise RuntimeError("No data to write")

        if isinstance(output_file, str):
            # 字符串路径 - 打开文件
            with io.open(output_file, "w", encoding="utf-8") as f:
                self.datafile.seek(0)
                f.write(self.datafile.getvalue())
        else:
            # 文件对象
            self.datafile.seek(0)
            if hasattr(output_file, "write"):
                output_file.write(self.datafile.getvalue())
            else:
                raise TypeError("output_file must be a string path or file-like object")

    def get_data_as_string(self) -> str:
        """
        获取下载数据的字符串表示

        Returns:
            str: CSV格式的数据字符串

        Raises:
            RuntimeError: 没有可用数据
        """
        if not self.datafile:
            raise RuntimeError("No data available")

        self.datafile.seek(0)
        return self.datafile.getvalue()

    def is_successful(self) -> bool:
        """
        检查下载是否成功

        Returns:
            bool: True表示成功，False表示失败
        """
        return self.datafile is not None and self.error is None

    def get_error(self) -> Optional[str]:
        """
        获取错误信息

        Returns:
            str: 错误信息，如果没有错误则返回None
        """
        return self.error
