"""
命令解析器
使用规则引擎解析命令类型，不调用LLM API
"""
from typing import Tuple, Optional
from shared.rule_engine import rule_engine, CommandType
from shared.message_types import RawTextMessage, QueryRequest, SummaryRequest
from shared.utils import setup_logger

logger = setup_logger(__name__)


class CommandParser:
    """命令解析器"""
    
    def __init__(self):
        """初始化命令解析器"""
        self.rule_engine = rule_engine
    
    def parse_message(self, text: str, user_id: Optional[str] = None, table_name: Optional[str] = None) -> Tuple[str, dict]:
        """
        解析消息，返回消息类型和解析结果
        
        Args:
            text: 消息文本
            user_id: 用户ID
            table_name: 当前选择的表/目录名
            
        Returns:
            (消息类型, 解析结果字典)
            消息类型: "text", "query", "summary", "navigate"
        """
        text = text.strip()
        if not text:
            return "text", {}
        
        # 使用规则引擎解析命令类型
        command_type, param = self.rule_engine.parse_command_type(text)
        
        if command_type == CommandType.NAVIGATE:
            # 导航命令：选择表/目录
            new_table_name = param or self.rule_engine._extract_table_name(text)
            return "navigate", {
                "table_name": new_table_name,
                "user_id": user_id
            }
        
        elif command_type == CommandType.QUERY:
            # 查询命令
            params = self.rule_engine.parse_query_params(text)
            query_type = self.rule_engine.determine_query_type(params)
            
            # 如果用户当前选择了表/目录，添加到参数中
            if table_name and "table_name" not in params:
                params["table_name"] = table_name
            
            return "query", {
                "query_type": query_type,
                "params": params,
                "user_id": user_id
            }
        
        elif command_type == CommandType.SUMMARY:
            # 总结命令
            # 先解析查询参数（总结可能包含查询条件）
            params = self.rule_engine.parse_query_params(text)
            query_type = self.rule_engine.determine_query_type(params)
            
            # 如果用户当前选择了表/目录，添加到参数中
            if table_name and "table_name" not in params:
                params["table_name"] = table_name
            
            return "summary", {
                "query_type": query_type,
                "params": params,
                "user_id": user_id
            }
        
        else:
            # 普通文本消息
            return "text", {
                "text": text,
                "user_id": user_id,
                "table_name": table_name
            }

