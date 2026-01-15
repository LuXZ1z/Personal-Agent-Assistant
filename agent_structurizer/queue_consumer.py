"""
文本结构化Agent的队列消费者
从raw_text队列消费消息，处理后发送到structured_data队列
"""
import time
import json
import redis
from redis.exceptions import RedisError
from typing import Optional

from shared.config import settings
from shared.message_types import RawTextMessage, StructuredDataMessage
from agent_structurizer.structurizer import Structurizer
from shared.utils import setup_logger

logger = setup_logger(__name__)


class StructurizerConsumer:
    """文本结构化消费者"""
    
    def __init__(self):
        """初始化消费者"""
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("文本结构化消费者初始化成功")
        except RedisError as e:
            logger.error(f"Redis连接失败: {e}")
            raise
        
        self.structurizer = Structurizer()
    
    def run(self):
        """运行消费者（主循环）"""
        logger.info("文本结构化消费者开始运行")
        
        while True:
            try:
                # 从raw_text队列消费消息
                message_json = self.redis_client.brpop("raw_text", timeout=1)
                if message_json:
                    # 解析消息（可能是RawTextMessage或包含business_type的字典）
                    message_data = json.loads(message_json[1])
                    
                    # 提取business_type（如果存在）
                    business_type = message_data.get("business_type")
                    
                    # 创建RawTextMessage对象
                    message = RawTextMessage(
                        message_id=message_data.get("message_id"),
                        text=message_data.get("text"),
                        user_id=message_data.get("user_id"),
                        table_name=message_data.get("table_name")
                    )
                    
                    logger.info(f"收到文本消息: {message.message_id}, business_type={business_type}")
                    
                    # 进行结构化处理（传入business_type）
                    structured_message = self.structurizer.structure(message, business_type=business_type)
                    
                    # 发送到structured_data队列
                    self.redis_client.lpush("structured_data", structured_message.model_dump_json())
                    logger.info(f"结构化数据已发送: {structured_message.message_id}")
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止文本结构化消费者")
                break
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
                time.sleep(1)  # 出错后短暂休眠
        
        logger.info("文本结构化消费者已停止")


def main():
    """主函数"""
    try:
        consumer = StructurizerConsumer()
        consumer.run()
    except Exception as e:
        logger.error(f"文本结构化消费者启动失败: {e}")
        raise


if __name__ == "__main__":
    main()

