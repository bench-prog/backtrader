#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级消息队列系统 (Enterprise Message Queue System)
基于backtrader架构的消息队列解决方案

支持的消息队列类型：
1. RabbitMQ
2. Apache Kafka
3. 内存队列 (用于开发测试)
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import json
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Any, Callable, Dict, Optional


class MessageQueueError(Exception):
    """消息队列异常基类"""

    pass


class Message:
    """
    消息实体类
    """

    def __init__(
        self,
        topic: str,
        data: Any,
        message_id: str = None,
        priority: int = 0,
        ttl: int = None,
    ):
        self.message_id = message_id or str(uuid.uuid4())
        self.topic = topic
        self.data = data
        self.priority = priority
        self.ttl = ttl
        self.created_at = datetime.datetime.now()
        self.delivered_at = None
        self.retry_count = 0
        self.max_retries = 3

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "topic": self.topic,
            "data": self.data,
            "priority": self.priority,
            "ttl": self.ttl,
            "created_at": self.created_at.isoformat(),
            "delivered_at": self.delivered_at.isoformat()
            if self.delivered_at
            else None,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        """从字典创建消息"""
        msg = cls(
            topic=data["topic"],
            data=data["data"],
            message_id=data["message_id"],
            priority=data.get("priority", 0),
            ttl=data.get("ttl"),
        )
        msg.created_at = datetime.datetime.fromisoformat(data["created_at"])
        if data.get("delivered_at"):
            msg.delivered_at = datetime.datetime.fromisoformat(data["delivered_at"])
        msg.retry_count = data.get("retry_count", 0)
        return msg

    def is_expired(self) -> bool:
        """检查消息是否过期"""
        if not self.ttl:
            return False
        expire_time = self.created_at + datetime.timedelta(seconds=self.ttl)
        return datetime.datetime.now() > expire_time


class BaseMessageQueue(ABC):
    """
    消息队列抽象基类
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.consumers = defaultdict(list)
        self.producers = []
        self._running = False
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
    def publish(self, message: Message) -> bool:
        """发布消息"""
        pass

    @abstractmethod
    def consume(self, topic: str, callback: Callable, auto_ack: bool = True) -> str:
        """订阅消息"""
        pass

    @abstractmethod
    def ack_message(self, message: Message) -> bool:
        """确认消息"""
        pass

    @abstractmethod
    def reject_message(self, message: Message, requeue: bool = True) -> bool:
        """拒绝消息"""
        pass

    def start_consuming(self):
        """开始消费消息"""
        with self._lock:
            self._running = True

    def stop_consuming(self):
        """停止消费消息"""
        with self._lock:
            self._running = False


class MemoryMessageQueue(BaseMessageQueue):
    """
    内存消息队列 (用于开发测试)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.topics = defaultdict(deque)
        self.message_store = {}  # 持久化存储
        self.delivery_tracking = {}  # 投递跟踪
        self.consumer_threads = {}

    def connect(self) -> bool:
        """连接内存队列"""
        try:
            self._running = True
            print("✅ 内存消息队列初始化成功")
            return True
        except Exception as e:
            print(f"❌ 内存消息队列初始化失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开内存队列"""
        try:
            self.stop_consuming()
            # 停止所有消费者线程
            for thread in self.consumer_threads.values():
                if thread.is_alive():
                    thread.join(timeout=1)
            return True
        except Exception as e:
            print(f"❌ 断开连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._running

    def publish(self, message: Message) -> bool:
        """发布消息到内存队列"""
        if not self._running:
            return False

        try:
            with self._lock:
                # 检查消息是否过期
                if message.is_expired():
                    print(f"⚠️  消息已过期，跳过发布: {message.message_id}")
                    return False

                # 存储消息
                self.message_store[message.message_id] = message
                self.topics[message.topic].append(message.message_id)

                print(f"📤 消息已发布: {message.message_id} -> {message.topic}")
                return True

        except Exception as e:
            print(f"❌ 发布消息失败: {e}")
            return False

    def consume(self, topic: str, callback: Callable, auto_ack: bool = True) -> str:
        """订阅内存队列消息"""
        consumer_id = str(uuid.uuid4())

        def consumer_worker():
            while self._running:
                try:
                    message = self._get_next_message(topic)
                    if message:
                        try:
                            callback(message)
                            if auto_ack:
                                self.ack_message(message)
                        except Exception as e:
                            print(f"❌ 消费者回调执行失败: {e}")
                            self.reject_message(message, requeue=True)
                    else:
                        time.sleep(0.1)  # 短暂休眠避免忙等待
                except Exception as e:
                    print(f"❌ 消费者工作线程错误: {e}")
                    time.sleep(1)

        # 启动消费者线程
        consumer_thread = threading.Thread(target=consumer_worker, daemon=True)
        consumer_thread.start()
        self.consumer_threads[consumer_id] = consumer_thread
        self.consumers[topic].append(consumer_id)

        print(f"📥 消费者已订阅主题: {topic} (ID: {consumer_id})")
        return consumer_id

    def _get_next_message(self, topic: str) -> Optional[Message]:
        """获取下一个消息"""
        with self._lock:
            if topic in self.topics and self.topics[topic]:
                message_id = self.topics[topic].popleft()
                message = self.message_store.get(message_id)

                if message and not message.is_expired():
                    message.delivered_at = datetime.datetime.now()
                    self.delivery_tracking[message_id] = {
                        "delivered_at": message.delivered_at,
                        "consumer_count": self.delivery_tracking.get(
                            message_id, {}
                        ).get("consumer_count", 0)
                        + 1,
                    }
                    return message
                elif message:
                    # 消息过期，删除它
                    del self.message_store[message_id]

            return None

    def ack_message(self, message: Message) -> bool:
        """确认消息处理完成"""
        try:
            with self._lock:
                if message.message_id in self.message_store:
                    del self.message_store[message.message_id]
                if message.message_id in self.delivery_tracking:
                    del self.delivery_tracking[message.message_id]
            print(f"✅ 消息确认: {message.message_id}")
            return True
        except Exception as e:
            print(f"❌ 消息确认失败: {e}")
            return False

    def reject_message(self, message: Message, requeue: bool = True) -> bool:
        """拒绝消息"""
        try:
            with self._lock:
                message.retry_count += 1

                if requeue and message.retry_count <= message.max_retries:
                    # 重新入队
                    self.topics[message.topic].append(message.message_id)
                    print(
                        f"🔄 消息重新入队: {message.message_id} (重试 {message.retry_count}/{message.max_retries})"
                    )
                else:
                    # 达到最大重试次数，丢弃消息
                    if message.message_id in self.message_store:
                        del self.message_store[message.message_id]
                    print(f"🗑️  消息丢弃: {message.message_id} (超过最大重试次数)")

            return True
        except Exception as e:
            print(f"❌ 消息拒绝失败: {e}")
            return False


class RabbitMQMessageQueue(BaseMessageQueue):
    """
    RabbitMQ消息队列
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection = None
        self.channel = None
        self.exchange = config.get("exchange", "backtrader_exchange")
        self.exchange_type = config.get("exchange_type", "topic")

    def connect(self) -> bool:
        """连接RabbitMQ"""
        try:
            import pika

            credentials = pika.PlainCredentials(
                self.config.get("username", "guest"),
                self.config.get("password", "guest"),
            )

            parameters = pika.ConnectionParameters(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 5672),
                virtual_host=self.config.get("virtual_host", "/"),
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # 声明交换机
            self.channel.exchange_declare(
                exchange=self.exchange, exchange_type=self.exchange_type, durable=True
            )

            self._running = True
            print("✅ RabbitMQ连接成功")
            return True

        except Exception as e:
            print(f"❌ RabbitMQ连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开RabbitMQ连接"""
        try:
            self.stop_consuming()
            if self.channel:
                self.channel.close()
            if self.connection:
                self.connection.close()
            self._running = False
            return True
        except Exception as e:
            print(f"❌ 断开RabbitMQ连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查连接状态"""
        return (
            self._running
            and self.connection
            and not self.connection.is_closed
            and self.channel
            and not self.channel.is_closed
        )

    def publish(self, message: Message) -> bool:
        """发布消息到RabbitMQ"""
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # 序列化消息
            message_body = json.dumps(message.to_dict(), default=str)

            # 发布消息
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=message.topic,
                body=message_body,
                properties=__import__("pika").BasicProperties(
                    delivery_mode=2,  # 持久化
                    priority=message.priority,
                    expiration=str(message.ttl * 1000) if message.ttl else None,
                ),
            )

            print(f"📤 RabbitMQ消息已发布: {message.message_id} -> {message.topic}")
            return True

        except Exception as e:
            print(f"❌ RabbitMQ发布消息失败: {e}")
            return False

    def consume(self, topic: str, callback: Callable, auto_ack: bool = True) -> str:
        """订阅RabbitMQ消息"""
        if not self.is_connected():
            return None

        try:
            # 声明队列
            result = self.channel.queue_declare(queue="", exclusive=True)
            queue_name = result.method.queue

            # 绑定队列到交换机
            self.channel.queue_bind(
                exchange=self.exchange, queue=queue_name, routing_key=topic
            )

            def rabbitmq_callback(ch, method, properties, body):
                try:
                    # 反序列化消息
                    message_data = json.loads(body.decode("utf-8"))
                    message = Message.from_dict(message_data)
                    message.delivered_at = datetime.datetime.now()

                    # 执行回调
                    callback(message)

                    # 自动确认
                    if auto_ack:
                        ch.basic_ack(delivery_tag=method.delivery_tag)

                except Exception as e:
                    print(f"❌ 消息处理失败: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

            # 开始消费
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=rabbitmq_callback,
                auto_ack=auto_ack,
            )

            consumer_id = str(uuid.uuid4())
            print(f"📥 RabbitMQ消费者已订阅: {topic} (队列: {queue_name})")
            return consumer_id

        except Exception as e:
            print(f"❌ RabbitMQ订阅失败: {e}")
            return None

    def ack_message(self, message: Message) -> bool:
        """RabbitMQ自动确认，无需手动调用"""
        return True

    def reject_message(self, message: Message, requeue: bool = True) -> bool:
        """RabbitMQ通过basic_nack处理，无需手动调用"""
        return True


class KafkaMessageQueue(BaseMessageQueue):
    """
    Kafka消息队列
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.producer = None
        self.consumer = None
        self.bootstrap_servers = config.get("bootstrap_servers", ["localhost:9092"])
        self.group_id = config.get("group_id", "backtrader_group")

    def connect(self) -> bool:
        """连接Kafka"""
        try:
            from kafka import KafkaProducer

            # 创建生产者
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                retries=3,
                acks="all",
            )

            self._running = True
            print("✅ Kafka连接成功")
            return True

        except Exception as e:
            print(f"❌ Kafka连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开Kafka连接"""
        try:
            self.stop_consuming()
            if self.producer:
                self.producer.close()
            if self.consumer:
                self.consumer.close()
            self._running = False
            return True
        except Exception as e:
            print(f"❌ 断开Kafka连接失败: {e}")
            return False

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._running and self.producer is not None

    def publish(self, message: Message) -> bool:
        """发布消息到Kafka"""
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # 发布消息
            future = self.producer.send(
                message.topic, key=message.message_id, value=message.to_dict()
            )

            # 等待发送完成
            record_metadata = future.get(timeout=10)
            print(
                f"📤 Kafka消息已发布: {message.message_id} -> {message.topic} (partition: {record_metadata.partition})"
            )
            return True

        except Exception as e:
            print(f"❌ Kafka发布消息失败: {e}")
            return False

    def consume(self, topic: str, callback: Callable, auto_ack: bool = True) -> str:
        """订阅Kafka消息"""
        try:
            from kafka import KafkaConsumer

            # 创建消费者
            self.consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                enable_auto_commit=auto_ack,
                auto_offset_reset="latest",
            )

            def kafka_consumer_worker():
                for message in self.consumer:
                    try:
                        message_obj = Message.from_dict(message.value)
                        message_obj.delivered_at = datetime.datetime.now()
                        callback(message_obj)
                    except Exception as e:
                        print(f"❌ Kafka消息处理失败: {e}")

            # 启动消费者线程
            consumer_thread = threading.Thread(
                target=kafka_consumer_worker, daemon=True
            )
            consumer_thread.start()

            consumer_id = str(uuid.uuid4())
            print(f"📥 Kafka消费者已订阅: {topic}")
            return consumer_id

        except Exception as e:
            print(f"❌ Kafka订阅失败: {e}")
            return None

    def ack_message(self, message: Message) -> bool:
        """Kafka自动提交偏移量"""
        return True

    def reject_message(self, message: Message, requeue: bool = True) -> bool:
        """Kafka通过偏移量管理处理重试"""
        return True


class MessageQueueManager:
    """
    消息队列管理器
    """

    def __init__(self):
        self.queues = {}
        self.default_queue = None
        self._lock = threading.RLock()

    def add_queue(self, name: str, queue: BaseMessageQueue, is_default: bool = False):
        """添加消息队列实例"""
        with self._lock:
            self.queues[name] = queue
            if is_default:
                self.default_queue = name

    def get_queue(self, name: str = None) -> BaseMessageQueue:
        """获取消息队列实例"""
        with self._lock:
            queue_name = name or self.default_queue
            if queue_name and queue_name in self.queues:
                return self.queues[queue_name]
            return None

    def publish_message(self, message: Message, queue_name: str = None) -> bool:
        """发布消息"""
        queue = self.get_queue(queue_name)
        if queue:
            return queue.publish(message)
        return False

    def subscribe_topic(
        self,
        topic: str,
        callback: Callable,
        queue_name: str = None,
        auto_ack: bool = True,
    ) -> str:
        """订阅主题"""
        queue = self.get_queue(queue_name)
        if queue:
            return queue.consume(topic, callback, auto_ack)
        return None

    def connect_all(self) -> Dict[str, bool]:
        """连接所有队列"""
        results = {}
        with self._lock:
            for name, queue in self.queues.items():
                results[name] = queue.connect()
        return results

    def disconnect_all(self) -> Dict[str, bool]:
        """断开所有队列连接"""
        results = {}
        with self._lock:
            for name, queue in self.queues.items():
                results[name] = queue.disconnect()
        return results


# 便捷工厂函数
def create_message_queue(config: Dict[str, Any]) -> BaseMessageQueue:
    """根据配置创建消息队列实例"""
    queue_type = config.get("type", "").lower()

    if queue_type == "memory":
        return MemoryMessageQueue(config)
    elif queue_type == "rabbitmq":
        return RabbitMQMessageQueue(config)
    elif queue_type == "kafka":
        return KafkaMessageQueue(config)
    else:
        raise ValueError(f"不支持的消息队列类型: {queue_type}")


def create_queue_manager(configs: Dict[str, Dict]) -> MessageQueueManager:
    """创建消息队列管理器"""
    manager = MessageQueueManager()

    for name, config in configs.items():
        try:
            queue = create_message_queue(config)
            is_default = config.get("default", False)
            manager.add_queue(name, queue, is_default)
        except Exception as e:
            print(f"❌ 创建消息队列 {name} 失败: {e}")

    return manager


# 使用示例
if __name__ == "__main__":
    # 配置示例
    queue_configs = {
        "memory": {"type": "memory", "default": True},
        "rabbitmq": {
            "type": "rabbitmq",
            "host": "localhost",
            "port": 5672,
            "username": "guest",
            "password": "guest",
        },
    }

    # 创建消息队列管理器
    queue_manager = create_queue_manager(queue_configs)

    # 连接所有队列
    connection_results = queue_manager.connect_all()
    print("连接结果:", connection_results)

    # 定义消息处理回调
    def message_handler(message: Message):
        print(f"📨 收到消息: {message.message_id}")
        print(f"   主题: {message.topic}")
        print(f"   数据: {message.data}")
        print(f"   优先级: {message.priority}")

    # 订阅主题
    consumer_id = queue_manager.subscribe_topic("market.data", message_handler)
    print(f"消费者ID: {consumer_id}")

    # 发布消息
    test_message = Message(
        topic="market.data",
        data={"symbol": "BTC/USDT", "price": 45000.0, "volume": 100.5},
        priority=1,
        ttl=3600,
    )

    success = queue_manager.publish_message(test_message)
    print(f"消息发布结果: {success}")

    # 保持程序运行一段时间
    time.sleep(5)

    # 断开连接
    queue_manager.disconnect_all()
