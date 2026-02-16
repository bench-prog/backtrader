#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业级消息队列系统
Enterprise Message Queue System for Backtrader

模块结构:
├── message_queue.py    # 消息队列实现
└── __init__.py         # 模块初始化
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# 消息队列组件
from .message_queue import (
    BaseMessageQueue,
    KafkaMessageQueue,
    MemoryMessageQueue,
    Message,
    MessageQueueError,
    MessageQueueManager,
    RabbitMQMessageQueue,
    create_message_queue,
    create_queue_manager,
)

__all__ = [
    "MessageQueueError",
    "Message",
    "BaseMessageQueue",
    "MemoryMessageQueue",
    "RabbitMQMessageQueue",
    "KafkaMessageQueue",
    "MessageQueueManager",
    "create_message_queue",
    "create_queue_manager",
]

__version__ = "1.0.0"
__author__ = "Backtrader Messaging Team"
