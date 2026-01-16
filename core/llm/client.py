"""
LLM客户端
调用OpenAI API进行文本处理
"""
import json
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI
from openai import APIError

from shared.config import settings
from shared.utils import setup_logger

logger = setup_logger(__name__)


class LLMClient:
    """LLM客户端 - 提供统一的大语言模型调用接口"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化LLM客户端
        
        Args:
            api_key: API密钥，如果为None则使用配置中的密钥
            base_url: API基础URL，如果为None则使用配置中的URL
        """
        self.client = OpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.openai_base_url
        )
        self.max_retries = 3
        self.retry_delay = 1  # 秒
    
    def structure_text(self, text: str, prompt_template: str) -> Dict[str, Any]:
        """
        将文本转换为结构化数据
        
        Args:
            text: 原始文本
            prompt_template: 提示词模板（支持format格式，如"{text}"）
            
        Returns:
            结构化数据字典，包含：
                - type: 记录类型
                - fields: 字段字典
                - summary: 摘要
                
        Raises:
            Exception: 如果处理失败
        """
        # 格式化提示词模板
        try:
            prompt = prompt_template.format(text=text)
        except KeyError:
            # 如果模板中没有{text}，直接使用模板
            prompt = prompt_template.replace("{text}", text)
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"调用LLM API进行结构化 (尝试 {attempt + 1}/{self.max_retries})")
                
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个专业的数据结构化助手，能够将自然语言文本转换为结构化的JSON数据。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                # 提取回复内容
                content = response.choices[0].message.content.strip()
                logger.debug(f"LLM回复: {content[:200]}...")
                
                # 尝试解析JSON
                # 如果回复包含代码块，提取JSON部分
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # 解析JSON
                structured_data = json.loads(content)
                
                # 验证数据结构
                if not isinstance(structured_data, dict):
                    raise ValueError("结构化数据必须是字典类型")
                if "type" not in structured_data:
                    structured_data["type"] = "其他"
                if "fields" not in structured_data:
                    structured_data["fields"] = {}
                if "summary" not in structured_data:
                    structured_data["summary"] = text[:50]  # 使用前50个字符作为摘要
                
                logger.info(f"文本结构化成功: type={structured_data.get('type')}")
                return structured_data
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    # 最后一次尝试失败，返回默认结构
                    logger.error("JSON解析最终失败，返回默认结构")
                    return {
                        "type": "其他",
                        "fields": {"text": text},
                        "summary": text[:50]
                    }
                time.sleep(self.retry_delay * (attempt + 1))
            
            except APIError as e:
                logger.error(f"OpenAI API错误 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (attempt + 1))
            
            except Exception as e:
                logger.error(f"处理失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (attempt + 1))
        
        # 如果所有重试都失败，返回默认结构
        return {
            "type": "其他",
            "fields": {"text": text},
            "summary": text[:50]
        }
    
    def summarize(self, records: List[Dict[str, Any]], summary_type: str = "general", custom_prompt: Optional[str] = None) -> str:
        """
        对多条记录进行总结
        
        Args:
            records: 记录列表，每个记录可以是字典或对象，需要包含structured_data或summary字段
            summary_type: 总结类型（general, detailed, analysis）
            custom_prompt: 自定义提示词，如果提供则忽略summary_type
            
        Returns:
            总结文本
        """
        # 构建记录文本
        records_text = "\n".join([
            f"- {self._extract_summary(r)}"
            for r in records[:50]  # 最多50条
        ])
        
        if custom_prompt:
            prompt = custom_prompt.format(records_data=records_text)
        elif summary_type == "general":
            prompt = f"请对以下记录进行简要总结：\n\n{records_text}\n\n请用一段话概括这些记录的主要内容。"
        elif summary_type == "detailed":
            prompt = f"请对以下记录进行详细总结：\n\n{records_text}\n\n请详细分析这些记录的内容和特点。"
        else:  # analysis
            prompt = f"请对以下记录进行分析：\n\n{records_text}\n\n请分析这些记录的趋势和模式。"
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个专业的数据分析助手，能够对多条记录进行总结和分析。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=1500
                )
                
                summary = response.choices[0].message.content.strip()
                logger.info(f"总结完成: {len(summary)} 字符")
                return summary
                
            except Exception as e:
                logger.error(f"总结失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    return f"共 {len(records)} 条记录"
                time.sleep(self.retry_delay * (attempt + 1))
        
        return f"共 {len(records)} 条记录"
    
    def analyze(self, content: str, analysis_type: str = "general", custom_prompt: Optional[str] = None) -> str:
        """
        分析内容
        
        Args:
            content: 要分析的内容
            analysis_type: 分析类型（general, detailed, sentiment, theme等）
            custom_prompt: 自定义提示词，如果提供则忽略analysis_type
            
        Returns:
            分析结果文本
        """
        if custom_prompt:
            prompt = custom_prompt.format(content=content)
        elif analysis_type == "general":
            prompt = f"请对以下内容进行一般性分析：\n\n{content}\n\n请提供你的分析和见解。"
        elif analysis_type == "detailed":
            prompt = f"请对以下内容进行详细分析：\n\n{content}\n\n请从多个角度深入分析。"
        elif analysis_type == "sentiment":
            prompt = f"请分析以下内容的情感倾向：\n\n{content}\n\n请判断情感是积极、消极还是中性，并说明理由。"
        elif analysis_type == "theme":
            prompt = f"请分析以下内容的主题和核心思想：\n\n{content}\n\n请提取主要主题和关键观点。"
        else:
            prompt = f"请对以下内容进行分析：\n\n{content}\n\n请提供你的分析和见解。"
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个专业的分析助手，能够对内容进行深入分析。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
                
                analysis = response.choices[0].message.content.strip()
                logger.info(f"分析完成: {len(analysis)} 字符")
                return analysis
                
            except Exception as e:
                logger.error(f"分析失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    return "分析失败，请稍后重试"
                time.sleep(self.retry_delay * (attempt + 1))
        
        return "分析失败，请稍后重试"
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        通用对话接口
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}, ...]
            temperature: 温度参数（0-2），控制随机性
            max_tokens: 最大token数
            
        Returns:
            回复文本
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                reply = response.choices[0].message.content.strip()
                logger.debug(f"对话回复: {len(reply)} 字符")
                return reply
                
            except Exception as e:
                logger.error(f"对话失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (attempt + 1))
        
        raise Exception("对话失败，已达到最大重试次数")
    
    def _extract_summary(self, record: Any) -> str:
        """
        从记录中提取摘要
        
        Args:
            record: 记录对象或字典
            
        Returns:
            摘要文本
        """
        if isinstance(record, dict):
            if 'structured_data' in record:
                return record['structured_data'].get('summary', '')
            elif 'summary' in record:
                return record['summary']
            else:
                return str(record)
        else:
            # 假设是对象，尝试获取属性
            if hasattr(record, 'structured_data'):
                return getattr(record.structured_data, 'summary', '') if hasattr(record.structured_data, 'summary') else record.structured_data.get('summary', '')
            elif hasattr(record, 'summary'):
                return record.summary
            else:
                return str(record)

