"""
微信响应管理器
管理stream_id和响应内容的映射，处理异步响应
"""
import json
import time
import uuid
from typing import Optional, Dict
from datetime import datetime, timedelta
import redis
from redis.exceptions import RedisError

from shared.config import settings
from shared.message_types import WeChatResponse, BusinessResponse
from shared.utils import setup_logger

logger = setup_logger(__name__)


class ResponseManager:
    """响应管理器"""
    
    def __init__(self):
        """初始化响应管理器"""
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("响应管理器初始化成功")
        except RedisError as e:
            logger.error(f"Redis连接失败: {e}")
            raise
        
        # 使用Redis存储stream状态，key格式: stream:{stream_id}
        # 存储格式: {"message_id": "...", "content": "...", "finish": false, "created_at": "..."}
        self.stream_prefix = "stream:"
        self.stream_ttl = 300  # stream状态保留5分钟
    
    def create_stream(self, message_id: str) -> str:
        """
        创建新的stream
        
        Args:
            message_id: 消息ID
            
        Returns:
            stream_id
        """
        stream_id = str(uuid.uuid4())[:16]  # 使用UUID的前16位作为stream_id
        stream_key = f"{self.stream_prefix}{stream_id}"
        
        stream_data = {
            "message_id": message_id,
            "content": "正在处理...",
            "finish": False,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            self.redis_client.setex(
                stream_key,
                self.stream_ttl,
                json.dumps(stream_data, ensure_ascii=False)
            )
            logger.info(f"创建stream: stream_id={stream_id}, message_id={message_id}")
            return stream_id
        except Exception as e:
            logger.error(f"创建stream失败: {e}")
            raise
    
    def update_stream(self, stream_id: str, content: str, finish: bool = False) -> bool:
        """
        更新stream内容
        
        Args:
            stream_id: stream ID
            content: 新的内容
            finish: 是否完成
            
        Returns:
            是否更新成功
        """
        stream_key = f"{self.stream_prefix}{stream_id}"
        
        try:
            stream_data_json = self.redis_client.get(stream_key)
            if not stream_data_json:
                logger.warning(f"Stream不存在: {stream_id}")
                return False
            
            stream_data = json.loads(stream_data_json)
            stream_data["content"] = content
            stream_data["finish"] = finish
            stream_data["updated_at"] = datetime.utcnow().isoformat()
            
            self.redis_client.setex(
                stream_key,
                self.stream_ttl,
                json.dumps(stream_data, ensure_ascii=False)
            )
            logger.debug(f"更新stream: stream_id={stream_id}, finish={finish}")
            return True
        except Exception as e:
            logger.error(f"更新stream失败: {e}")
            return False
    
    def get_stream(self, stream_id: str) -> Optional[Dict]:
        """
        获取stream信息
        
        Args:
            stream_id: stream ID
            
        Returns:
            stream信息字典，包含content和finish
        """
        stream_key = f"{self.stream_prefix}{stream_id}"
        
        try:
            stream_data_json = self.redis_client.get(stream_key)
            if not stream_data_json:
                return None
            
            stream_data = json.loads(stream_data_json)
            return {
                "content": stream_data.get("content", ""),
                "finish": stream_data.get("finish", False)
            }
        except Exception as e:
            logger.error(f"获取stream失败: {e}")
            return None
    
    def process_response_queue(self) -> None:
        """
        处理响应队列，更新对应的stream
        这个方法应该在后台任务中持续运行
        注意：只处理 WeChatResponse 格式的消息，BusinessResponse 由 background_business_response_processor 处理
        """
        try:
            # 从队列右侧弹出消息（FIFO）
            response_json = self.redis_client.rpop("wechat_responses")
            if not response_json:
                return
            
            # 先尝试解析为JSON，检查消息类型
            try:
                message_data = json.loads(response_json)
            except json.JSONDecodeError as e:
                logger.error(f"解析响应JSON失败: {e}")
                return
            
            # 检查是否为 BusinessResponse 格式（有 request_id 但没有 message_id）
            # 如果是，放回队列让 background_business_response_processor 处理
            if "request_id" in message_data and "message_id" not in message_data:
                # 这是 BusinessResponse，放回队列右侧，让 background_business_response_processor 处理
                # 使用 rpush 放回右侧，这样 background_business_response_processor 的 rpop 更容易取到
                self.redis_client.rpush("wechat_responses", response_json)
                logger.debug(f"检测到 BusinessResponse，已放回队列: request_id={message_data.get('request_id')}")
                return
            
            # 尝试解析为 WeChatResponse
            try:
                response = WeChatResponse.model_validate_json(response_json)
                logger.info(f"收到响应消息: message_id={response.message_id}")
                
                # 查找对应的stream_id
                # 我们需要维护message_id到stream_id的映射
                mapping_key = f"msg_to_stream:{response.message_id}"
                stream_id = self.redis_client.get(mapping_key)
                
                if stream_id:
                    # 更新stream内容
                    success = self.update_stream(stream_id, response.text, finish=True)
                    if success:
                        logger.info(f"更新stream完成: stream_id={stream_id}, message_id={response.message_id}")
                    else:
                        logger.warning(f"更新stream失败: stream_id={stream_id}, message_id={response.message_id}")
                    # 删除映射（可选，也可以保留一段时间）
                    self.redis_client.delete(mapping_key)
                else:
                    logger.warning(f"未找到stream_id映射: message_id={response.message_id}, 可能已过期")
            except Exception as e:
                # 如果不是 WeChatResponse 格式，可能是其他格式，记录警告并跳过
                logger.debug(f"消息不是 WeChatResponse 格式，跳过: {e}")
                # 如果是 BusinessResponse，放回队列
                if "request_id" in message_data:
                    self.redis_client.rpush("wechat_responses", response_json)
                
        except Exception as e:
            logger.error(f"处理响应队列失败: {e}", exc_info=True)
    
    def link_message_to_stream(self, message_id: str, stream_id: str) -> None:
        """
        建立message_id到stream_id的映射
        
        Args:
            message_id: 消息ID
            stream_id: stream ID
        """
        mapping_key = f"msg_to_stream:{message_id}"
        try:
            self.redis_client.setex(mapping_key, self.stream_ttl, stream_id)
            logger.debug(f"建立映射: message_id={message_id} -> stream_id={stream_id}")
        except Exception as e:
            logger.error(f"建立映射失败: {e}")
    
    def close(self) -> None:
        """关闭Redis连接"""
        try:
            self.redis_client.close()
            logger.info("响应管理器Redis连接已关闭")
        except Exception as e:
            logger.error(f"关闭Redis连接失败: {e}")

