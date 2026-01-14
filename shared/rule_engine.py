"""
规则引擎基础类
提供命令解析和规则匹配的基础功能
"""
import re
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


class CommandType(str, Enum):
    """命令类型枚举"""
    TEXT = "text"  # 普通文本消息
    QUERY = "query"  # 查询命令
    SUMMARY = "summary"  # 总结命令
    NAVIGATE = "navigate"  # 导航命令（选择表/目录）
    TAROT = "tarot"  # 塔罗牌命令


class RuleEngine:
    """
    规则引擎基础类
    使用关键词匹配和正则表达式进行命令解析
    """
    
    # 命令关键词模式
    COMMAND_PATTERNS = {
        CommandType.QUERY: ["查询", "搜索", "查看", "列表", "显示", "找", "列出", "显示所有"],
        CommandType.SUMMARY: ["总结", "汇总", "分析", "统计", "概括"],
        CommandType.NAVIGATE: ["进入", "切换到", "打开", "选择", "切换", "进入目录", "进入表"],
        CommandType.TAROT: ["塔罗牌", "塔罗", "抽牌", "占卜", "tarot", "/tarot"],
    }
    
    # 查询参数模式
    QUERY_PATTERNS = {
        "by_type": [
            r"类型[：:]\s*(\w+)",
            r"类型\s+(\w+)",
            r"(\w+)类型",
        ],
        "by_date": [
            r"日期[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        ],
        "by_keyword": [
            r"关键词[：:]\s*(.+)",
            r"包含[：:]\s*(.+)",
            r"搜索[：:]\s*(.+)",
        ],
        "by_table": [
            r"表[：:]\s*(\w+)",
            r"目录[：:]\s*(\w+)",
            r"进入\s+(\w+)",
            r"切换到\s+(\w+)",
        ],
        "date_range": [
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*到\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*-\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        ],
    }
    
    def __init__(self):
        """初始化规则引擎"""
        # 编译正则表达式以提高性能
        self._compiled_patterns = {}
        for pattern_type, patterns in self.QUERY_PATTERNS.items():
            self._compiled_patterns[pattern_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def parse_command_type(self, text: str) -> Tuple[CommandType, Optional[str]]:
        """
        解析命令类型
        
        Args:
            text: 输入文本
            
        Returns:
            (命令类型, 提取的参数)
        """
        text = text.strip()
        
        # 检查导航命令
        for keyword in self.COMMAND_PATTERNS[CommandType.NAVIGATE]:
            if keyword in text:
                # 提取表/目录名
                table_name = self._extract_table_name(text)
                if table_name:
                    return CommandType.NAVIGATE, table_name
        
        # 检查查询命令
        for keyword in self.COMMAND_PATTERNS[CommandType.QUERY]:
            if keyword in text:
                return CommandType.QUERY, None
        
        # 检查总结命令
        for keyword in self.COMMAND_PATTERNS[CommandType.SUMMARY]:
            if keyword in text:
                return CommandType.SUMMARY, None
        
        # 检查塔罗牌命令
        for keyword in self.COMMAND_PATTERNS[CommandType.TAROT]:
            if keyword in text:
                return CommandType.TAROT, None
        
        # 默认为普通文本
        return CommandType.TEXT, None
    
    def _extract_table_name(self, text: str) -> Optional[str]:
        """
        提取表/目录名
        
        Args:
            text: 输入文本
            
        Returns:
            表/目录名，如果未找到则返回None
        """
        # 尝试匹配表/目录选择模式
        patterns = self._compiled_patterns.get("by_table", [])
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match.group(1) if match.lastindex >= 1 else None
        
        # 尝试从导航命令中提取
        for keyword in self.COMMAND_PATTERNS[CommandType.NAVIGATE]:
            if keyword in text:
                # 提取关键词后的内容
                parts = text.split(keyword, 1)
                if len(parts) > 1:
                    table_name = parts[1].strip()
                    # 移除可能的标点符号
                    table_name = re.sub(r'[，,。.\s]+', '', table_name)
                    if table_name:
                        return table_name
        
        return None
    
    def parse_query_params(self, text: str) -> Dict[str, Any]:
        """
        解析查询参数
        
        Args:
            text: 查询命令文本
            
        Returns:
            解析出的查询参数字典
        """
        params = {}
        
        # 解析类型
        for pattern in self._compiled_patterns.get("by_type", []):
            match = pattern.search(text)
            if match:
                params["type"] = match.group(1)
                break
        
        # 解析日期范围
        for pattern in self._compiled_patterns.get("date_range", []):
            match = pattern.search(text)
            if match:
                params["start_date"] = match.group(1).replace("/", "-")
                params["end_date"] = match.group(2).replace("/", "-")
                break
        
        # 如果没有日期范围，尝试解析单个日期
        if "start_date" not in params:
            for pattern in self._compiled_patterns.get("by_date", []):
                match = pattern.search(text)
                if match:
                    date_str = match.group(1).replace("/", "-")
                    params["date"] = date_str
                    break
        
        # 解析关键词
        for pattern in self._compiled_patterns.get("by_keyword", []):
            match = pattern.search(text)
            if match:
                params["keyword"] = match.group(1).strip()
                break
        
        # 解析表/目录
        table_name = self._extract_table_name(text)
        if table_name:
            params["table_name"] = table_name
        
        return params
    
    def determine_query_type(self, params: Dict[str, Any]) -> str:
        """
        根据参数确定查询类型
        
        Args:
            params: 查询参数字典
            
        Returns:
            查询类型字符串
        """
        if "table_name" in params:
            return "by_table"
        elif "type" in params:
            return "by_type"
        elif "start_date" in params or "date" in params:
            return "by_date"
        elif "keyword" in params:
            return "by_keyword"
        else:
            return "all"  # 查询所有


# 全局规则引擎实例
rule_engine = RuleEngine()

