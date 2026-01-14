"""
数据服务Agent的队列消费者
处理查询和总结请求
"""
import time
import redis
from redis.exceptions import RedisError

from shared.config import settings
from shared.message_types import QueryRequest, SummaryRequest
from agent_service.query_service import QueryService
from agent_service.summary_service import SummaryService
from shared.utils import setup_logger

logger = setup_logger(__name__)


class ServiceConsumer:
    """数据服务消费者"""
    
    def __init__(self):
        """初始化消费者"""
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("数据服务消费者初始化成功")
        except RedisError as e:
            logger.error(f"Redis连接失败: {e}")
            raise
        
        self.query_service = QueryService()
        self.summary_service = SummaryService()
    
    def run(self):
        """运行消费者（主循环）"""
        logger.info("数据服务消费者开始运行")
        
        while True:
            try:
                # 处理查询请求
                query_json = self.redis_client.brpop("query_request", timeout=1)
                if query_json:
                    query_request = QueryRequest.model_validate_json(query_json[1])
                    logger.info(f"收到查询请求: {query_request.request_id}")
                    
                    # 执行查询
                    query_result = self.query_service.query(query_request)
                    
                    # 发送查询结果
                    self.redis_client.lpush("query_result", query_result.model_dump_json())
                    logger.info(f"查询结果已发送: {query_request.request_id}, count={query_result.count}")
                    
                    # 检查是否有待处理的总结请求（这里简化处理，实际可以更复杂）
                    # 如果查询结果成功且有记录，可以自动触发总结（可选）
                
                # 处理总结请求
                summary_json = self.redis_client.brpop("summary_request", timeout=0.1)
                if summary_json:
                    summary_request = SummaryRequest.model_validate_json(summary_json[1])
                    logger.info(f"收到总结请求: {summary_request.request_id}")
                    
                    # 执行总结
                    summary_result = self.summary_service.summarize(summary_request)
                    
                    # 发送总结结果
                    self.redis_client.lpush("summary_result", summary_result.model_dump_json())
                    logger.info(f"总结结果已发送: {summary_request.request_id}, success={summary_result.success}")
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止数据服务消费者")
                break
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
                time.sleep(1)  # 出错后短暂休眠
        
        logger.info("数据服务消费者已停止")


def main():
    """主函数"""
    try:
        consumer = ServiceConsumer()
        consumer.run()
    except Exception as e:
        logger.error(f"数据服务消费者启动失败: {e}")
        raise


if __name__ == "__main__":
    main()

