"""
文本结构化处理逻辑
将原始文本转换为结构化数据
"""
from typing import Dict, Any, Optional
from datetime import datetime
from shared.message_types import RawTextMessage, StructuredDataMessage, StructuredData
from agent_structurizer.llm_client import LLMClient
from agent_structurizer.prompt_templates import (
    STRUCTURE_PROMPT_TEMPLATE,
    ACCOUNTING_PROMPT_TEMPLATE,
    ESSAY_PROMPT_TEMPLATE,
    EMPLOYEE_PROMPT_TEMPLATE
)
from shared.business_service import BusinessType
from shared.utils import setup_logger

logger = setup_logger(__name__)


class Structurizer:
    """文本结构化器"""
    
    def __init__(self):
        """初始化结构化器"""
        self.llm_client = LLMClient()
    
    def structure(self, message: RawTextMessage, business_type: Optional[str] = None) -> StructuredDataMessage:
        """
        将原始文本转换为结构化数据
        
        Args:
            message: 原始文本消息
            business_type: 业务类型（记账/随笔/员工等）
            
        Returns:
            结构化数据消息
        """
        try:
            logger.info(f"开始结构化处理: message_id={message.message_id}, business_type={business_type}")
            
            # 根据业务类型选择prompt模板
            prompt_template = self._get_prompt_template(business_type)
            
            # 调用LLM API进行结构化
            structured_dict = self.llm_client.structure_text(
                text=message.text,
                prompt_template=prompt_template
            )
            
            # 如果指定了业务类型，确保type字段正确
            if business_type:
                structured_dict["type"] = business_type
            
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
    
    def _get_prompt_template(self, business_type: Optional[str]) -> str:
        """
        根据业务类型获取对应的prompt模板
        
        Args:
            business_type: 业务类型
            
        Returns:
            prompt模板字符串
        """
        if not business_type:
            return STRUCTURE_PROMPT_TEMPLATE
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        if business_type == BusinessType.ACCOUNTING.value:
            # 记账业务
            return ACCOUNTING_PROMPT_TEMPLATE.format(current_date=current_date)
        elif business_type == BusinessType.ESSAY.value:
            # 随笔业务
            return ESSAY_PROMPT_TEMPLATE.replace("{current_date}", current_date)
        elif business_type == BusinessType.EMPLOYEE.value:
            # 员工管理业务
            return EMPLOYEE_PROMPT_TEMPLATE.replace("{current_date}", current_date)
        else:
            # 默认使用通用模板
            return STRUCTURE_PROMPT_TEMPLATE

