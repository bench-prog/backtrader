#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级数据存储系统 (Enterprise Data Storage System)
基于backtrader架构的多类型数据存储解决方案

支持的数据存储类型：
1. 时序数据库 (InfluxDB/TimescaleDB)
2. 关系数据库 (PostgreSQL/MySQL)
3. NoSQL数据库 (MongoDB)
4. 缓存系统 (Redis/Memcached)
5. 对象存储 (MinIO/S3)
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import json
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Dict, List


class DataStorageError(Exception):
    """数据存储异常基类"""

    pass


class ConnectionPool:
    """
    连接池管理器
    """

    def __init__(self, max_connections: int = 10, connection_timeout: int = 30):
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.connections = deque()
        self.lock = threading.RLock()
        self.active_connections = 0

    def get_connection(self):
        """获取连接"""
        with self.lock:
            if self.connections:
                return self.connections.popleft()
            elif self.active_connections < self.max_connections:
                self.active_connections += 1
                return None  # 需要创建新连接
            else:
                raise DataStorageError("连接池已满")

    def return_connection(self, connection):
        """归还连接"""
        with self.lock:
            if connection:
                self.connections.append(connection)

    def close_all(self):
        """关闭所有连接"""
        with self.lock:
            while self.connections:
                conn = self.connections.popleft()
                try:
                    conn.close()
                except:
                    pass
            self.active_connections = 0


class BaseDataStorage(ABC):
    """
    数据存储抽象基类
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection_pool = ConnectionPool(
            max_connections=config.get("max_connections", 10)
        )
        self._connected = False
        self._lock = threading.RLock()

    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass

    @abstractmethod
    def store_data(self, data: Dict[str, Any], table: str = None) -> bool:
        """存储数据"""
        pass

    @abstractmethod
    def retrieve_data(self, query: Dict[str, Any], table: str = None) -> List[Dict]:
        """检索数据"""
        pass

    @abstractmethod
    def delete_data(self, query: Dict[str, Any], table: str = None) -> bool:
        """删除数据"""
        pass

    def _get_connection(self):
        """获取数据库连接"""
        return self.connection_pool.get_connection()

    def _return_connection(self, connection):
        """归还数据库连接"""
        self.connection_pool.return_connection(connection)


class TimeSeriesStorage(BaseDataStorage):
    """
    时序数据存储 (InfluxDB/TimescaleDB)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = None
        self.database = config.get("database", "backtrader")
        self.retention_policy = config.get("retention_policy", "autogen")

    def connect(self) -> bool:
        """连接时序数据库"""
        try:
            if self.config.get("type") == "influxdb":
                from influxdb_client import InfluxDBClient

                self.client = InfluxDBClient(
                    url=self.config.get("url", "http://localhost:8086"),
                    token=self.config.get("token"),
                    org=self.config.get("org", "-"),
                    timeout=self.config.get("timeout", 30),
                )
            elif self.config.get("type") == "timescaledb":
                import psycopg2

                self.client = psycopg2.connect(
                    host=self.config.get("host", "localhost"),
                    port=self.config.get("port", 5432),
                    database=self.config.get("database", "timescaledb"),
                    user=self.config.get("user"),
                    password=self.config.get("password"),
                )

            self._connected = True
            print(f"✅ 时序数据库连接成功: {self.config.get('type')}")
            return True

        except Exception as e:
            print(f"❌ 时序数据库连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开时序数据库连接"""
        try:
            if self.client:
                self.client.close()
            self._connected = False
            return True
        except Exception as e:
            print(f"❌ 断开连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self._connected or not self.client:
            return False
        try:
            if self.config.get("type") == "influxdb":
                self.client.ping()
            elif self.config.get("type") == "timescaledb":
                self.client.cursor().execute("SELECT 1")
            return True
        except:
            return False

    def store_data(
        self, data: Dict[str, Any], measurement: str = "market_data"
    ) -> bool:
        """存储时序数据"""
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            timestamp = data.get("timestamp") or datetime.datetime.now()

            if self.config.get("type") == "influxdb":
                from influxdb_client import Point

                point = Point(measurement)

                # 添加标签和字段
                for key, value in data.items():
                    if key != "timestamp":
                        if isinstance(value, (str, bool)):
                            point.tag(key, str(value))
                        else:
                            point.field(key, value)

                point.time(timestamp)
                write_api = self.client.write_api()
                write_api.write(bucket=self.database, record=point)

            elif self.config.get("type") == "timescaledb":
                cursor = self.client.cursor()
                columns = ", ".join(data.keys())
                placeholders = ", ".join(["%s"] * len(data))
                values = list(data.values())

                query = f"INSERT INTO {measurement} ({columns}) VALUES ({placeholders})"
                cursor.execute(query, values)
                self.client.commit()
                cursor.close()

            return True

        except Exception as e:
            print(f"❌ 存储时序数据失败: {e}")
            return False

    def retrieve_data(
        self, query: Dict[str, Any], measurement: str = "market_data"
    ) -> List[Dict]:
        """检索时序数据"""
        if not self.is_connected():
            return []

        try:
            results = []

            if self.config.get("type") == "influxdb":
                query_api = self.client.query_api()
                flux_query = f'''
                from(bucket: "{self.database}")
                  |> range(start: {query.get("start", "-1h")}, stop: {query.get("stop", "now()")})
                  |> filter(fn: (r) => r._measurement == "{measurement}")
                '''

                tables = query_api.query(flux_query)
                for table in tables:
                    for record in table.records:
                        results.append(
                            {
                                "time": record.get_time(),
                                "measurement": record.get_measurement(),
                                **record.values,
                            }
                        )

            elif self.config.get("type") == "timescaledb":
                cursor = self.client.cursor()
                where_clause = (
                    " AND ".join([f"{k} = %s" for k in query.keys()])
                    if query
                    else "TRUE"
                )
                query_sql = f"SELECT * FROM {measurement} WHERE {where_clause} ORDER BY time DESC LIMIT %s"
                values = list(query.values()) + [query.get("limit", 1000)]

                cursor.execute(query_sql, values)
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                cursor.close()

            return results

        except Exception as e:
            print(f"❌ 检索时序数据失败: {e}")
            return []


class RelationalStorage(BaseDataStorage):
    """
    关系型数据库存储 (PostgreSQL/MySQL)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.engine = None
        self.connection = None

    def connect(self) -> bool:
        """连接关系型数据库"""
        try:
            if self.config.get("type") == "postgresql":
                import psycopg2

                self.connection = psycopg2.connect(
                    host=self.config.get("host", "localhost"),
                    port=self.config.get("port", 5432),
                    database=self.config.get("database", "backtrader"),
                    user=self.config.get("user"),
                    password=self.config.get("password"),
                    connect_timeout=self.config.get("timeout", 30),
                )
            elif self.config.get("type") == "mysql":
                import pymysql

                self.connection = pymysql.connect(
                    host=self.config.get("host", "localhost"),
                    port=self.config.get("port", 3306),
                    database=self.config.get("database", "backtrader"),
                    user=self.config.get("user"),
                    password=self.config.get("password"),
                    connect_timeout=self.config.get("timeout", 30),
                )

            self._connected = True
            print(f"✅ 关系型数据库连接成功: {self.config.get('type')}")
            return True

        except Exception as e:
            print(f"❌ 关系型数据库连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开关系型数据库连接"""
        try:
            if self.connection:
                self.connection.close()
            self._connected = False
            return True
        except Exception as e:
            print(f"❌ 断开连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self._connected or not self.connection:
            return False
        try:
            self.connection.ping()
            return True
        except:
            return False

    def store_data(self, data: Dict[str, Any], table: str = "trading_records") -> bool:
        """存储关系型数据"""
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            cursor = self.connection.cursor()
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            values = list(data.values())

            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            cursor.execute(query, values)
            self.connection.commit()
            cursor.close()

            return True

        except Exception as e:
            print(f"❌ 存储关系型数据失败: {e}")
            return False

    def retrieve_data(
        self, query: Dict[str, Any], table: str = "trading_records"
    ) -> List[Dict]:
        """检索关系型数据"""
        if not self.is_connected():
            return []

        try:
            cursor = self.connection.cursor()
            where_clause = (
                " AND ".join([f"{k} = %s" for k in query.keys()]) if query else "TRUE"
            )
            query_sql = f"SELECT * FROM {table} WHERE {where_clause}"
            values = list(query.values()) if query else []

            cursor.execute(query_sql, values)
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()

            return results

        except Exception as e:
            print(f"❌ 检索关系型数据失败: {e}")
            return []


class CacheStorage(BaseDataStorage):
    """
    缓存存储 (Redis/Memcached)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = None
        self.default_ttl = config.get("default_ttl", 3600)  # 默认1小时过期

    def connect(self) -> bool:
        """连接缓存系统"""
        try:
            if self.config.get("type") == "redis":
                import redis

                self.client = redis.Redis(
                    host=self.config.get("host", "localhost"),
                    port=self.config.get("port", 6379),
                    db=self.config.get("database", 0),
                    password=self.config.get("password"),
                    decode_responses=True,
                    socket_connect_timeout=self.config.get("timeout", 5),
                )
            elif self.config.get("type") == "memcached":
                import memcache

                servers = self.config.get("servers", ["localhost:11211"])
                self.client = memcache.Client(servers)

            # 测试连接
            self.client.ping() if hasattr(
                self.client, "ping"
            ) else self.client.get_stats()

            self._connected = True
            print(f"✅ 缓存系统连接成功: {self.config.get('type')}")
            return True

        except Exception as e:
            print(f"❌ 缓存系统连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开缓存系统连接"""
        try:
            if self.client:
                if hasattr(self.client, "close"):
                    self.client.close()
            self._connected = False
            return True
        except Exception as e:
            print(f"❌ 断开连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self._connected or not self.client:
            return False
        try:
            self.client.ping() if hasattr(
                self.client, "ping"
            ) else self.client.get_stats()
            return True
        except:
            return False

    def store_data(self, data: Dict[str, Any], key: str = None) -> bool:
        """存储缓存数据"""
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            cache_key = key or f"data_{int(time.time())}"
            ttl = data.get("ttl", self.default_ttl)

            if self.config.get("type") == "redis":
                serialized_data = json.dumps(data, default=str)
                self.client.setex(cache_key, ttl, serialized_data)
            elif self.config.get("type") == "memcached":
                self.client.set(cache_key, data, time=ttl)

            return True

        except Exception as e:
            print(f"❌ 存储缓存数据失败: {e}")
            return False

    def retrieve_data(self, query: Dict[str, Any], key: str = None) -> List[Dict]:
        """检索缓存数据"""
        if not self.is_connected():
            return []

        try:
            cache_key = key or query.get("key")
            if not cache_key:
                return []

            if self.config.get("type") == "redis":
                cached_data = self.client.get(cache_key)
                if cached_data:
                    return [json.loads(cached_data)]
            elif self.config.get("type") == "memcached":
                cached_data = self.client.get(cache_key)
                if cached_data:
                    return [cached_data]

            return []

        except Exception as e:
            print(f"❌ 检索缓存数据失败: {e}")
            return []


class ObjectStorage(BaseDataStorage):
    """
    对象存储 (MinIO/S3)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = None
        self.bucket = config.get("bucket", "backtrader-data")

    def connect(self) -> bool:
        """连接对象存储"""
        try:
            if self.config.get("type") == "minio":
                from minio import Minio

                self.client = Minio(
                    self.config.get("endpoint", "localhost:9000"),
                    access_key=self.config.get("access_key"),
                    secret_key=self.config.get("secret_key"),
                    secure=self.config.get("secure", False),
                )
            elif self.config.get("type") == "s3":
                import boto3

                self.client = boto3.client(
                    "s3",
                    aws_access_key_id=self.config.get("access_key"),
                    aws_secret_access_key=self.config.get("secret_key"),
                    region_name=self.config.get("region", "us-east-1"),
                )

            # 确保bucket存在
            if self.config.get("type") == "minio":
                if not self.client.bucket_exists(self.bucket):
                    self.client.make_bucket(self.bucket)
            elif self.config.get("type") == "s3":
                try:
                    self.client.head_bucket(Bucket=self.bucket)
                except:
                    self.client.create_bucket(Bucket=self.bucket)

            self._connected = True
            print(f"✅ 对象存储连接成功: {self.config.get('type')}")
            return True

        except Exception as e:
            print(f"❌ 对象存储连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开对象存储连接"""
        self._connected = False
        return True  # 对象存储通常不需要显式断开

    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self._connected or not self.client:
            return False
        try:
            if self.config.get("type") == "minio":
                self.client.bucket_exists(self.bucket)
            elif self.config.get("type") == "s3":
                self.client.head_bucket(Bucket=self.bucket)
            return True
        except:
            return False

    def store_data(self, data: Dict[str, Any], object_name: str = None) -> bool:
        """存储对象数据"""
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            obj_name = object_name or f"data_{int(time.time())}.json"

            # 序列化数据
            serialized_data = json.dumps(data, default=str).encode("utf-8")

            if self.config.get("type") == "minio":
                from io import BytesIO

                data_stream = BytesIO(serialized_data)
                self.client.put_object(
                    self.bucket,
                    obj_name,
                    data_stream,
                    len(serialized_data),
                    content_type="application/json",
                )
            elif self.config.get("type") == "s3":
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=obj_name,
                    Body=serialized_data,
                    ContentType="application/json",
                )

            return True

        except Exception as e:
            print(f"❌ 存储对象数据失败: {e}")
            return False

    def retrieve_data(
        self, query: Dict[str, Any], object_name: str = None
    ) -> List[Dict]:
        """检索对象数据"""
        if not self.is_connected():
            return []

        try:
            obj_name = object_name or query.get("object_name")
            if not obj_name:
                return []

            if self.config.get("type") == "minio":
                response = self.client.get_object(self.bucket, obj_name)
                data = response.read().decode("utf-8")
                response.close()
                response.release_conn()
                return [json.loads(data)]
            elif self.config.get("type") == "s3":
                response = self.client.get_object(Bucket=self.bucket, Key=obj_name)
                data = response["Body"].read().decode("utf-8")
                return [json.loads(data)]

        except Exception as e:
            print(f"❌ 检索对象数据失败: {e}")
            return []


class DataStorageManager:
    """
    数据存储管理器 - 统一管理多种存储类型
    """

    def __init__(self):
        self.storages = {}
        self.default_storage = None
        self._lock = threading.RLock()

    def add_storage(
        self, name: str, storage: BaseDataStorage, is_default: bool = False
    ):
        """添加存储实例"""
        with self._lock:
            self.storages[name] = storage
            if is_default:
                self.default_storage = name

    def get_storage(self, name: str = None) -> BaseDataStorage:
        """获取存储实例"""
        with self._lock:
            storage_name = name or self.default_storage
            if storage_name and storage_name in self.storages:
                return self.storages[storage_name]
            return None

    def store_data(
        self, data: Dict[str, Any], storage_name: str = None, **kwargs
    ) -> bool:
        """存储数据到指定存储"""
        storage = self.get_storage(storage_name)
        if storage:
            return storage.store_data(data, **kwargs)
        return False

    def retrieve_data(
        self, query: Dict[str, Any], storage_name: str = None, **kwargs
    ) -> List[Dict]:
        """从指定存储检索数据"""
        storage = self.get_storage(storage_name)
        if storage:
            return storage.retrieve_data(query, **kwargs)
        return []

    def connect_all(self) -> Dict[str, bool]:
        """连接所有存储"""
        results = {}
        with self._lock:
            for name, storage in self.storages.items():
                results[name] = storage.connect()
        return results

    def disconnect_all(self) -> Dict[str, bool]:
        """断开所有存储连接"""
        results = {}
        with self._lock:
            for name, storage in self.storages.items():
                results[name] = storage.disconnect()
        return results

    def get_connection_status(self) -> Dict[str, bool]:
        """获取所有存储连接状态"""
        status = {}
        with self._lock:
            for name, storage in self.storages.items():
                status[name] = storage.is_connected()
        return status


# 便捷工厂函数
def create_data_storage(config: Dict[str, Any]) -> BaseDataStorage:
    """根据配置创建数据存储实例"""
    storage_type = config.get("type", "").lower()

    if storage_type in ["influxdb", "timescaledb"]:
        return TimeSeriesStorage(config)
    elif storage_type in ["postgresql", "mysql"]:
        return RelationalStorage(config)
    elif storage_type in ["redis", "memcached"]:
        return CacheStorage(config)
    elif storage_type in ["minio", "s3"]:
        return ObjectStorage(config)
    else:
        raise ValueError(f"不支持的存储类型: {storage_type}")


def create_storage_manager(configs: Dict[str, Dict]) -> DataStorageManager:
    """创建存储管理器"""
    manager = DataStorageManager()

    for name, config in configs.items():
        try:
            storage = create_data_storage(config)
            is_default = config.get("default", False)
            manager.add_storage(name, storage, is_default)
        except Exception as e:
            print(f"❌ 创建存储 {name} 失败: {e}")

    return manager


# 使用示例
if __name__ == "__main__":
    # 配置示例
    storage_configs = {
        "timeseries": {
            "type": "influxdb",
            "url": "http://localhost:8086",
            "token": "your-token",
            "org": "backtrader",
            "database": "market_data",
            "default": True,
        },
        "relational": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "backtrader",
            "user": "postgres",
            "password": "password",
        },
        "cache": {"type": "redis", "host": "localhost", "port": 6379, "database": 0},
    }

    # 创建存储管理器
    storage_manager = create_storage_manager(storage_configs)

    # 连接所有存储
    connection_results = storage_manager.connect_all()
    print("连接结果:", connection_results)

    # 存储示例数据
    market_data = {
        "symbol": "BTC/USDT",
        "price": 45000.0,
        "volume": 100.5,
        "timestamp": datetime.datetime.now(),
    }

    success = storage_manager.store_data(
        market_data, "timeseries", measurement="market_prices"
    )
    print(f"数据存储结果: {success}")
