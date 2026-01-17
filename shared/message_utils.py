"""
消息处理工具函数
用于美化和分批次发送微信消息
"""
import re
from typing import List, Optional


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


def split_message(text: str, max_chars: int = 750) -> List[str]:
    """
    将消息分割成多个不超过指定字符数的消息块
    
    Args:
        text: 原始消息文本
        max_chars: 每个消息块的最大字符数（默认750，微信限制，包括空行和emoji）
        
    Returns:
        消息块列表，每个消息块不超过max_chars字符
    """
    if not text:
        return [text]
    
    # 计算当前字符数
    current_chars = len(text)
    
    if current_chars <= max_chars:
        return [text]
    
    # 需要分割
    messages = []
    remaining_text = text
    
    # 预留空间用于添加序号（格式：[1/3] 最多占用约10字符）
    max_content_chars = max_chars - 15
    
    # 先计算总部分数
    total_chars = len(text)
    total_parts = (total_chars + max_content_chars - 1) // max_content_chars
    
    part_num = 0
    
    while remaining_text:
        part_num += 1
        remaining_chars = len(remaining_text)
        
        if remaining_chars <= max_content_chars:
            # 最后一部分
            if total_parts > 1:
                messages.append(f"{remaining_text}\n\n[{part_num}/{total_parts}]")
            else:
                messages.append(remaining_text)
            break
        
        # 需要分割，尝试在换行处分割
        chunk = ""
        pos = 0
        
        # 按字符遍历，尽量在换行处断开
        last_newline_pos = -1
        while pos < len(remaining_text):
            char = remaining_text[pos]
            test_chunk = chunk + char
            test_chars = len(test_chunk)
            
            if test_chars > max_content_chars:
                # 超出限制，使用上次换行位置
                if last_newline_pos >= 0:
                    # 在换行处断开
                    chunk = remaining_text[:last_newline_pos + 1]
                    remaining_text = remaining_text[last_newline_pos + 1:]
                else:
                    # 没有换行，强制在当前字符前断开
                    chunk = remaining_text[:pos]
                    remaining_text = remaining_text[pos:]
                break
            
            chunk = test_chunk
            if char == '\n':
                last_newline_pos = pos
            
            pos += 1
        
        # 如果遍历完还没找到分割点，说明剩余部分都在限制内
        if pos >= len(remaining_text):
            chunk = remaining_text
            remaining_text = ""
        
        # 添加序号
        messages.append(f"{chunk.rstrip()}\n\n[{part_num}/{total_parts}]")
    
    return messages


def format_message(text: str, max_chars: int = 750) -> List[str]:
    """
    格式化消息：美化并分割成多个消息块
    
    Args:
        text: 原始消息文本
        max_chars: 每个消息块的最大字符数（默认750，微信限制，包括空行和emoji）
        
    Returns:
        格式化后的消息列表，每个消息不超过max_chars字符
    """
    if not text:
        return [text]
    
    # 先美化
    beautified = beautify_message(text)
    
    # 再分割
    messages = split_message(beautified, max_chars=max_chars)
    
    return messages

