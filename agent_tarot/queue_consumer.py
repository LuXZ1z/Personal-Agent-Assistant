"""
塔罗牌队列消费者
从队列消费塔罗牌请求并处理
"""
import json
import time
import redis
from redis.exceptions import RedisError

from shared.config import settings
from shared.message_types import TarotRequest, TarotResult
from shared.utils import setup_logger
from agent_tarot.tarot_service import TarotService
from agent_tarot.llm_client import TarotLLMClient

logger = setup_logger(__name__)


class TarotQueueConsumer:
    """塔罗牌队列消费者"""
    
    def __init__(self):
        """初始化队列消费者"""
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("塔罗牌队列消费者初始化成功")
        except RedisError as e:
            logger.error(f"Redis连接失败: {e}")
            raise
        
        self.tarot_service = TarotService()
        self.llm_client = TarotLLMClient()
    
    def process_tarot_request(self, request: TarotRequest) -> TarotResult:
        """
        处理塔罗牌请求
        
        Args:
            request: 塔罗牌请求
            
        Returns:
            塔罗牌结果
        """
        try:
            logger.info(f"处理塔罗牌请求: request_id={request.request_id}, spread_type={request.spread_type}")
            
            # 抽取牌
            cards = self.tarot_service.draw_spread(request.spread_type)
            
            # 生成解读
            interpretation = self.llm_client.interpret_tarot(
                cards=cards,
                spread_type=request.spread_type,
                question=request.question
            )
            
            # 构建结果
            result = TarotResult(
                request_id=request.request_id,
                success=True,
                spread_type=request.spread_type,
                cards=cards,
                interpretation=interpretation
            )
            
            logger.info(f"塔罗牌请求处理成功: request_id={request.request_id}")
            return result
            
        except Exception as e:
            logger.error(f"处理塔罗牌请求失败: {e}")
            return TarotResult(
                request_id=request.request_id,
                success=False,
                spread_type=request.spread_type,
                error=str(e)
            )
    
    def _send_result(self, result: TarotResult) -> None:
        """
        发送结果到队列
        
        Args:
            result: 塔罗牌结果
        """
        try:
            self.redis_client.lpush("tarot_result", result.model_dump_json())
        except Exception as e:
            logger.error(f"发送塔罗牌结果失败: {e}")
            raise
    
    def run(self):
        """运行队列消费者（主循环）"""
        logger.info("塔罗牌队列消费者开始运行")
        
        while True:
            try:
                # 从tarot_request队列消费消息
                message_json = self.redis_client.brpop("tarot_request", timeout=1)
                if message_json:
                    request = TarotRequest.model_validate_json(message_json[1])
                    result = self.process_tarot_request(request)
                    self._send_result(result)
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止塔罗牌队列消费者")
                break
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
                time.sleep(1)  # 出错后短暂休眠
        
        logger.info("塔罗牌队列消费者已停止")


def main():
    """主函数"""
    consumer = TarotQueueConsumer()
    consumer.run()


if __name__ == "__main__":
    main()

