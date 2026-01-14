"""
查询命令解析器
使用规则引擎解析查询命令，不调用LLM
"""
from typing import Dict, Any, Optional
from shared.rule_engine import rule_engine
from shared.utils import setup_logger

logger = setup_logger(__name__)


class QueryParser:
    """查询命令解析器"""
    
    def __init__(self):
        """初始化查询解析器"""
        self.rule_engine = rule_engine
    
    def parse_query_request(self, text: str, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        解析查询请求文本
        
        Args:
            text: 查询命令文本
            table_name: 当前选择的表/目录名
            
        Returns:
            解析后的查询参数字典
        """
        # 使用规则引擎解析查询参数
        params = self.rule_engine.parse_query_params(text)
        
        # 确定查询类型
        query_type = self.rule_engine.determine_query_type(params)
        
        # 如果用户当前选择了表/目录，添加到参数中
        if table_name and "table_name" not in params:
            params["table_name"] = table_name
        
        return {
            "query_type": query_type,
            "params": params
        }

