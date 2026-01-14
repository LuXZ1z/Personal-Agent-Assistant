"""
数据存储Agent的队列消费者
从structured_data队列消费消息，存储到数据库
"""
import time
import redis
from redis.exceptions import RedisError

from shared.config import settings
from shared.message_types import StructuredDataMessage, StorageResult
from agent_storage.storage_service import StorageService
from shared.utils import setup_logger

logger = setup_logger(__name__)


class StorageConsumer:
    """数据存储消费者"""
    
    def __init__(self):
        """初始化消费者"""
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("数据存储消费者初始化成功")
        except RedisError as e:
            logger.error(f"Redis连接失败: {e}")
            raise
        
        self.storage_service = StorageService()
    
    def run(self):
        """运行消费者（主循环）"""
        logger.info("数据存储消费者开始运行")
        
        while True:
            try:
                # 从structured_data队列消费消息
                message_json = self.redis_client.brpop("structured_data", timeout=1)
                if message_json:
                    message = StructuredDataMessage.model_validate_json(message_json[1])
                    logger.info(f"收到结构化数据: {message.message_id}")
                    
                    # 存储数据
                    result = self.storage_service.store(message)
                    
                    # 发送存储结果到队列
                    self.redis_client.lpush("storage_result", result.model_dump_json())
                    logger.info(f"存储结果已发送: {result.message_id}, success={result.success}")
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止数据存储消费者")
                break
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
                time.sleep(1)  # 出错后短暂休眠
        
        logger.info("数据存储消费者已停止")


def main():
    """主函数"""
    try:
        consumer = StorageConsumer()
        consumer.run()
    except Exception as e:
        logger.error(f"数据存储消费者启动失败: {e}")
        raise


if __name__ == "__main__":
    main()

