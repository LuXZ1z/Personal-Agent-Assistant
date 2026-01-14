"""
LLM客户端
调用OpenAI API进行文本处理
"""
import json
import time
from typing import Optional, Dict, Any
from openai import OpenAI
from openai import APIError

from shared.config import settings
from shared.utils import setup_logger

logger = setup_logger(__name__)


class LLMClient:
    """LLM客户端"""
    
    def __init__(self):
        """初始化LLM客户端"""
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        self.max_retries = 3
        self.retry_delay = 1  # 秒
    
    def structure_text(self, text: str, prompt_template: str) -> Dict[str, Any]:
        """
        将文本转换为结构化数据
        
        Args:
            text: 原始文本
            prompt_template: 提示词模板
            
        Returns:
            结构化数据字典
            
        Raises:
            Exception: 如果处理失败
        """
        prompt = prompt_template.format(text=text)
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"调用LLM API (尝试 {attempt + 1}/{self.max_retries})")
                
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
                logger.debug(f"LLM回复: {content}")
                
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
    
    def summarize(self, records: list, summary_type: str = "general") -> str:
        """
        对多条记录进行总结
        
        Args:
            records: 记录列表
            summary_type: 总结类型（general, detailed, analysis）
            
        Returns:
            总结文本
        """
        # 构建提示词
        records_text = "\n".join([
            f"- {r.get('structured_data', {}).get('summary', '')}"
            for r in records[:50]  # 最多50条
        ])
        
        if summary_type == "general":
            prompt = f"请对以下记录进行简要总结：\n\n{records_text}\n\n请用一段话概括这些记录的主要内容。"
        elif summary_type == "detailed":
            prompt = f"请对以下记录进行详细总结：\n\n{records_text}\n\n请详细分析这些记录的内容和特点。"
        else:
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
                    max_tokens=500
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

