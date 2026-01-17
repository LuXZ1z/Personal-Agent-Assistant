"""
消息处理工具函数
用于美化和截断微信消息
"""
import re
from typing import Optional


def beautify_message(text: str) -> str:
    """
    美化消息内容，去除markdown格式符号
    
    Args:
        text: 原始消息文本
        
    Returns:
        美化后的消息文本
    """
    if not text:
        return text
    
    # 去除markdown格式符号
    # 去除 **粗体** 符号
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # 去除 *斜体* 符号
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', text)
    # 去除 __粗体__ 符号
    text = re.sub(r'__([^_]+)__', r'\1', text)
    # 去除 _斜体_ 符号
    text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'\1', text)
    # 去除 # 标题符号（保留内容）
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # 去除 ```代码块``` 符号（保留内容）
    text = re.sub(r'```[a-z]*\n?', '', text)
    # 去除 `行内代码` 符号（保留内容）
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 去除 [链接](url) 格式，只保留链接文本
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # 去除多余的换行（连续3个以上换行变为2个）
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 去除行首行尾空格
    text = text.strip()
    
    return text


def truncate_message(text: str, max_bytes: int = 4096, encoding: str = 'utf-8') -> str:
    """
    截断消息到指定字节数
    
    Args:
        text: 原始消息文本
        max_bytes: 最大字节数（默认4096，微信限制）
        encoding: 编码方式（默认utf-8）
        
    Returns:
        截断后的消息文本，如果超出限制会添加提示
    """
    if not text:
        return text
    
    # 计算当前字节数
    current_bytes = len(text.encode(encoding))
    
    if current_bytes <= max_bytes:
        return text
    
    # 需要截断
    truncated = text
    truncated_bytes = current_bytes
    
    # 逐步截断，直到符合要求
    # 预留一些空间用于添加提示信息
    max_content_bytes = max_bytes - 50  # 预留50字节用于提示
    
    while truncated_bytes > max_content_bytes:
        # 按字符截断（而不是按字节），避免截断多字节字符
        ratio = max_content_bytes / truncated_bytes
        new_length = int(len(truncated) * ratio)
        truncated = truncated[:new_length]
        truncated_bytes = len(truncated.encode(encoding))
    
    # 确保不会截断在中间字符
    while len(truncated.encode(encoding)) > max_content_bytes:
        truncated = truncated[:-1]
    
    # 添加截断提示
    truncated += f"\n\n...（消息过长，已截断，原始长度: {len(text)} 字符）"
    
    return truncated


def format_message(text: str, max_bytes: int = 4096) -> str:
    """
    格式化消息：美化并截断
    
    Args:
        text: 原始消息文本
        max_bytes: 最大字节数（默认4096，微信限制）
        
    Returns:
        格式化后的消息文本
    """
    if not text:
        return text
    
    # 先美化
    beautified = beautify_message(text)
    
    # 再截断
    formatted = truncate_message(beautified, max_bytes=max_bytes)
    
    return formatted

