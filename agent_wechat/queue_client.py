"""
Redis队列客户端
处理消息的发送和接收
"""
import json
import time
from typing import Optional
import redis
from redis.exceptions import RedisError

from shared.config import settings
from shared.message_types import WeChatMessage, WeChatResponse
from shared.utils import setup_logger

logger = setup_logger(__name__)


class QueueClient:
    """Redis队列客户端"""
    
    def __init__(self):
        """初始化Redis连接"""
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            # 测试连接
            self.redis_client.ping()
            logger.info(f"Redis连接成功: {settings.redis_url}")
        except RedisError as e:
            logger.error(f"Redis连接失败: {e}")
            raise
    
    def send_wechat_message(self, message: WeChatMessage) -> None:
        """
        发送微信消息到队列
        
        Args:
            message: 微信消息对象
        """
        try:
            queue_name = "wechat_messages"
            message_json = message.model_dump_json()
            self.redis_client.lpush(queue_name, message_json)
            logger.debug(f"发送消息到队列 {queue_name}: {message.message_id}")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            raise
    
    def receive_wechat_response(self, message_id: str, timeout: int = 30) -> Optional[WeChatResponse]:
        """
        接收微信响应消息
        
        Args:
            message_id: 消息ID
            timeout: 超时时间（秒）
            
        Returns:
            响应消息，如果超时则返回None
        """
        try:
            queue_name = "wechat_responses"
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # 从队列右侧弹出消息（FIFO）
                message_json = self.redis_client.rpop(queue_name)
                if message_json:
                    response = WeChatResponse.model_validate_json(message_json)
                    # 检查消息ID是否匹配
                    if response.message_id == message_id:
                        logger.debug(f"接收到响应消息: {message_id}")
                        return response
                    else:
                        # 不匹配，放回队列
                        self.redis_client.rpush(queue_name, message_json)
                
                # 短暂休眠避免CPU占用过高
                time.sleep(0.1)
            
            logger.warning(f"接收响应超时: {message_id}")
            return None
        except Exception as e:
            logger.error(f"接收响应失败: {e}")
            return None
    
    def close(self) -> None:
        """关闭Redis连接"""
        try:
            self.redis_client.close()
            logger.info("Redis连接已关闭")
        except Exception as e:
            logger.error(f"关闭Redis连接失败: {e}")

