"""
消息路由逻辑
从队列消费消息并路由到对应的处理队列
"""
import json
import time
from typing import Optional, Dict
import redis
from redis.exceptions import RedisError

from shared.config import settings
from shared.message_types import (
    WeChatMessage, RawTextMessage, QueryRequest, SummaryRequest, 
    StorageResult, QueryResult, SummaryResult, WeChatResponse,
    TarotRequest, TarotResult
)
from agent_router.command_parser import CommandParser
from shared.utils import setup_logger

logger = setup_logger(__name__)


class MessageRouter:
    """消息路由器"""
    
    def __init__(self):
        """初始化消息路由器"""
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("消息路由器初始化成功")
        except RedisError as e:
            logger.error(f"Redis连接失败: {e}")
            raise
        
        self.command_parser = CommandParser()
        # 存储用户当前选择的表/目录（简单的内存存储，实际可以改为Redis）
        self.user_tables: Dict[str, str] = {}
    
    def route_message(self, message: WeChatMessage) -> None:
        """
        路由消息到对应的队列
        
        Args:
            message: 微信消息对象
        """
        try:
            # 获取用户当前选择的表/目录
            table_name = self.user_tables.get(message.user_id or "")
            
            # 解析消息
            msg_type, parsed_data = self.command_parser.parse_message(
                text=message.text,
                user_id=message.user_id,
                table_name=table_name
            )
            
            logger.info(f"消息类型: {msg_type}, message_id: {message.message_id}")
            
            if msg_type == "navigate":
                # 导航命令：更新用户选择的表/目录
                new_table_name = parsed_data.get("table_name")
                if new_table_name and message.user_id:
                    self.user_tables[message.user_id] = new_table_name
                    logger.info(f"用户 {message.user_id} 切换到表/目录: {new_table_name}")
                
                # 发送响应消息
                response = WeChatResponse(
                    message_id=message.message_id,
                    text=f"已切换到: {new_table_name or '默认'}"
                )
                self._send_response(response)
            
            elif msg_type == "query":
                # 查询命令：发送到查询队列
                query_request = QueryRequest(
                    query_type=parsed_data["query_type"],
                    params=parsed_data["params"],
                    user_id=parsed_data.get("user_id"),
                    table_name=parsed_data["params"].get("table_name")
                )
                self._send_to_queue("query_request", query_request.model_dump_json())
                logger.info(f"查询请求已发送: {query_request.request_id}")
            
            elif msg_type == "summary":
                # 总结命令：发送总结请求（包含查询参数）
                from shared.message_types import SummaryRequest
                summary_request = SummaryRequest(
                    query_type=parsed_data["query_type"],
                    params=parsed_data["params"],
                    user_id=parsed_data.get("user_id"),
                    table_name=parsed_data["params"].get("table_name")
                )
                self._send_to_queue("summary_request", summary_request.model_dump_json())
                logger.info(f"总结请求已发送: {summary_request.request_id}")
            
            elif msg_type == "tarot":
                # 塔罗牌命令：发送塔罗牌请求
                tarot_request = TarotRequest(
                    spread_type=parsed_data.get("spread_type", "single"),
                    question=parsed_data.get("question"),
                    user_id=parsed_data.get("user_id")
                )
                self._send_to_queue("tarot_request", tarot_request.model_dump_json())
                logger.info(f"塔罗牌请求已发送: {tarot_request.request_id}")
            
            else:
                # 普通文本消息：发送到文本结构化队列
                raw_text_message = RawTextMessage(
                    message_id=message.message_id,
                    text=parsed_data["text"],
                    user_id=parsed_data.get("user_id"),
                    table_name=parsed_data.get("table_name")
                )
                self._send_to_queue("raw_text", raw_text_message.model_dump_json())
                logger.info(f"文本消息已发送到结构化队列: {raw_text_message.message_id}")
        
        except Exception as e:
            logger.error(f"路由消息失败: {e}")
            # 发送错误响应
            response = WeChatResponse(
                message_id=message.message_id,
                text=f"处理失败: {str(e)}"
            )
            self._send_response(response)
    
    def _send_to_queue(self, queue_name: str, message_json: str) -> None:
        """
        发送消息到队列
        
        Args:
            queue_name: 队列名称
            message_json: 消息JSON字符串
        """
        try:
            self.redis_client.lpush(queue_name, message_json)
        except Exception as e:
            logger.error(f"发送消息到队列失败: {queue_name}, {e}")
            raise
    
    def _send_response(self, response: WeChatResponse) -> None:
        """
        发送响应消息到队列
        
        Args:
            response: 响应消息对象
        """
        try:
            self._send_to_queue("wechat_responses", response.model_dump_json())
        except Exception as e:
            logger.error(f"发送响应失败: {e}")
            raise
    
    def process_storage_result(self, result: StorageResult) -> None:
        """
        处理存储结果
        
        Args:
            result: 存储结果
        """
        try:
            if result.success:
                response = WeChatResponse(
                    message_id=result.message_id,
                    text="已保存"
                )
            else:
                response = WeChatResponse(
                    message_id=result.message_id,
                    text=f"保存失败: {result.error or '未知错误'}"
                )
            self._send_response(response)
        except Exception as e:
            logger.error(f"处理存储结果失败: {e}")
    
    def process_query_result(self, result: QueryResult) -> None:
        """
        处理查询结果
        
        Args:
            result: 查询结果
        """
        try:
            if result.success:
                if result.count == 0:
                    response_text = "未找到相关记录"
                else:
                    # 格式化查询结果
                    response_text = f"找到 {result.count} 条记录：\n"
                    for i, record in enumerate(result.records[:10], 1):  # 最多显示10条
                        record_type = record.get("record_type", "未知")
                        summary = record.get("structured_data", {}).get("summary", "")
                        response_text += f"{i}. [{record_type}] {summary}\n"
                    if result.count > 10:
                        response_text += f"... 还有 {result.count - 10} 条记录"
            else:
                response_text = f"查询失败: {result.error or '未知错误'}"
            
            response = WeChatResponse(
                message_id=result.request_id,  # 使用request_id作为message_id
                text=response_text
            )
            self._send_response(response)
        except Exception as e:
            logger.error(f"处理查询结果失败: {e}")
    
    def process_summary_result(self, result: SummaryResult) -> None:
        """
        处理总结结果
        
        Args:
            result: 总结结果
        """
        try:
            if result.success and result.summary:
                response = WeChatResponse(
                    message_id=result.request_id,
                    text=result.summary
                )
            else:
                response = WeChatResponse(
                    message_id=result.request_id,
                    text=f"总结失败: {result.error or '未知错误'}"
                )
            self._send_response(response)
        except Exception as e:
            logger.error(f"处理总结结果失败: {e}")
    
    def process_tarot_result(self, result: TarotResult) -> None:
        """
        处理塔罗牌结果
        
        Args:
            result: 塔罗牌结果
        """
        try:
            if result.success and result.interpretation:
                # 构建响应文本
                response_text = "🔮 塔罗牌占卜结果 🔮\n\n"
                
                # 显示抽取的牌
                spread_names = {
                    "single": "单张牌",
                    "three_card": "三张牌（过去-现在-未来）",
                    "five_card": "五张牌（凯尔特十字简化版）"
                }
                response_text += f"✨ 牌阵类型：{spread_names.get(result.spread_type, result.spread_type)}\n\n"
                
                positions_map = {
                    "single": ["单张牌"],
                    "three_card": ["过去", "现在", "未来"],
                    "five_card": ["现状", "挑战", "过去", "未来", "结果"]
                }
                positions = positions_map.get(result.spread_type, [])
                
                response_text += "📌 抽取的牌：\n"
                for i, card in enumerate(result.cards):
                    position = positions[i] if i < len(positions) else f"位置{i+1}"
                    position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
                    response_text += f"  {position}: {card['name']} ({card.get('position', '正位')}) {position_emoji}\n"
                
                response_text += "\n" + "="*50 + "\n\n"
                response_text += result.interpretation
                
                response = WeChatResponse(
                    message_id=result.request_id,
                    text=response_text
                )
            else:
                response = WeChatResponse(
                    message_id=result.request_id,
                    text=f"🔮 占卜失败: {result.error or '未知错误'}"
                )
            self._send_response(response)
        except Exception as e:
            logger.error(f"处理塔罗牌结果失败: {e}")
    
    def run(self):
        """运行消息路由器（主循环）"""
        logger.info("消息路由器开始运行")
        
        while True:
            try:
                # 从wechat_messages队列消费消息
                message_json = self.redis_client.brpop("wechat_messages", timeout=1)
                if message_json:
                    message = WeChatMessage.model_validate_json(message_json[1])
                    self.route_message(message)
                
                # 处理存储结果
                storage_result_json = self.redis_client.brpop("storage_result", timeout=0.1)
                if storage_result_json:
                    result = StorageResult.model_validate_json(storage_result_json[1])
                    self.process_storage_result(result)
                
                # 处理查询结果
                query_result_json = self.redis_client.brpop("query_result", timeout=0.1)
                if query_result_json:
                    result = QueryResult.model_validate_json(query_result_json[1])
                    self.process_query_result(result)
                
                # 处理总结结果
                summary_result_json = self.redis_client.brpop("summary_result", timeout=0.1)
                if summary_result_json:
                    result = SummaryResult.model_validate_json(summary_result_json[1])
                    self.process_summary_result(result)
                
                # 处理塔罗牌结果
                tarot_result_json = self.redis_client.brpop("tarot_result", timeout=0.1)
                if tarot_result_json:
                    result = TarotResult.model_validate_json(tarot_result_json[1])
                    self.process_tarot_result(result)
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止消息路由器")
                break
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
                time.sleep(1)  # 出错后短暂休眠
        
        logger.info("消息路由器已停止")

