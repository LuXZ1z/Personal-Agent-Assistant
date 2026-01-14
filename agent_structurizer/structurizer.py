"""
文本结构化处理逻辑
将原始文本转换为结构化数据
"""
from typing import Dict, Any
from shared.message_types import RawTextMessage, StructuredDataMessage, StructuredData
from agent_structurizer.llm_client import LLMClient
from agent_structurizer.prompt_templates import STRUCTURE_PROMPT_TEMPLATE
from shared.utils import setup_logger

logger = setup_logger(__name__)


class Structurizer:
    """文本结构化器"""
    
    def __init__(self):
        """初始化结构化器"""
        self.llm_client = LLMClient()
    
    def structure(self, message: RawTextMessage) -> StructuredDataMessage:
        """
        将原始文本转换为结构化数据
        
        Args:
            message: 原始文本消息
            
        Returns:
            结构化数据消息
        """
        try:
            logger.info(f"开始结构化处理: message_id={message.message_id}")
            
            # 调用LLM API进行结构化
            structured_dict = self.llm_client.structure_text(
                text=message.text,
                prompt_template=STRUCTURE_PROMPT_TEMPLATE
            )
            
            # 构建结构化数据对象
            structured_data = StructuredData(
                type=structured_dict.get("type", "其他"),
                fields=structured_dict.get("fields", {}),
                summary=structured_dict.get("summary", message.text[:50])
            )
            
            # 构建结构化数据消息
            structured_message = StructuredDataMessage(
                message_id=message.message_id,
                original_text=message.text,
                structured_data=structured_data,
                table_name=message.table_name
            )
            
            logger.info(f"结构化处理完成: type={structured_data.type}, message_id={message.message_id}")
            return structured_message
            
        except Exception as e:
            logger.error(f"结构化处理失败: {e}")
            # 返回默认结构
            structured_data = StructuredData(
                type="其他",
                fields={"text": message.text},
                summary=message.text[:50]
            )
            return StructuredDataMessage(
                message_id=message.message_id,
                original_text=message.text,
                structured_data=structured_data,
                table_name=message.table_name
            )

