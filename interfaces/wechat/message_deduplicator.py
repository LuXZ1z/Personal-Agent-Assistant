"""
消息去重器
避免处理重复的微信消息（微信会重试）
"""
import time
import threading
from typing import Set

from shared.utils import setup_logger

logger = setup_logger(__name__)


class MessageDeduplicator:
    """消息去重器（单例）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化去重器"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        # 存储已处理的消息：key = (user_id, msg_id, content_hash), value = timestamp
        self._processed_messages: Set[str] = set()
        self._lock = threading.Lock()
        self._cleanup_interval = 300  # 5分钟清理一次
        self._message_ttl = 300  # 消息保留5分钟
        self._last_cleanup = time.time()
        
        logger.info("消息去重器初始化成功")
    
    def is_duplicate(self, user_id: str, msg_id: str, content: str) -> bool:
        """
        检查消息是否重复
        
        Args:
            user_id: 用户ID
            msg_id: 消息ID
            content: 消息内容
            
        Returns:
            是否为重复消息
        """
        # 定期清理过期消息
        self._cleanup_expired()
        
        # 生成消息唯一标识
        # 优先使用 msg_id，如果没有则使用 (user_id + timestamp + content_hash) 作为标识
        # 注意：如果没有msg_id，只使用content_hash可能导致不同消息被误判为重复
        if msg_id:
            message_key = f"{user_id}:{msg_id}"
        else:
            # 如果没有msg_id，使用时间戳+内容hash，避免不同消息被误判为重复
            import hashlib
            import time
            content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
            # 添加时间戳（精确到秒），这样相同内容但不同时间的消息不会被误判
            timestamp = int(time.time())
            message_key = f"{user_id}:{timestamp}:{content_hash}"
            logger.debug(f"消息无msg_id，使用时间戳+内容hash: user_id={user_id}, timestamp={timestamp}, content_hash={content_hash}")
        
        with self._lock:
            if message_key in self._processed_messages:
                logger.warning(f"检测到重复消息: user_id={user_id}, msg_id={msg_id}, message_key={message_key}")
                return True
            
            # 记录已处理的消息
            self._processed_messages.add(message_key)
            logger.debug(f"记录新消息: user_id={user_id}, msg_id={msg_id}, message_key={message_key}, total_messages={len(self._processed_messages)}")
            return False
    
    def _cleanup_expired(self):
        """清理过期的消息记录（简化实现：定期清理所有记录）"""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = current_time
        # 简化实现：定期清理所有记录（因为消息TTL是5分钟，而清理间隔也是5分钟）
        # 实际可以维护更精细的时间戳记录
        with self._lock:
            # 如果记录太多，清理一部分
            if len(self._processed_messages) > 1000:
                # 保留最近的一半
                items = list(self._processed_messages)
                self._processed_messages = set(items[-500:])
                logger.debug(f"清理消息记录，保留 {len(self._processed_messages)} 条")


# 全局消息去重器实例
message_deduplicator = MessageDeduplicator()

