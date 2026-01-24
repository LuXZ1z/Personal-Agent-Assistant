"""
消息处理工具函数
用于美化和分批次发送微信消息
"""
import re
from typing import List, Optional


def beautify_message(text: str) -> str:
    """
    美化消息内容，去除markdown格式符号，转换转义字符
    
    Args:
        text: 原始消息文本
        
    Returns:
        美化后的消息文本
    """
    if not text:
        return text
    
    # 先处理转义字符（将字符串形式的转义字符转换为实际字符）
    # 例如：将 "\\n" 转换为实际的换行符
    # 注意：只处理字符串形式的转义序列，不影响已经存在的实际换行符
    
    # 手动处理常见的转义序列（更安全可靠）
    # 按顺序处理，避免重复替换
    escape_map = {
        r"\n": "\n",    # 换行符（两个字符：\ 和 n）
        r"\t": "\t",    # 制表符
        r"\r": "\r",    # 回车符
        r"\"": "\"",    # 双引号
        r"\'": "'",     # 单引号
    }
    
    # 先处理反斜杠，避免影响其他转义序列的识别
    # 将真正的反斜杠（连续两个反斜杠）替换为临时标记
    text = text.replace(r"\\", "\x00DOUBLE_BACKSLASH\x00")
    
    # 处理其他转义序列
    for escaped, actual in escape_map.items():
        text = text.replace(escaped, actual)
    
    # 恢复真正的反斜杠（连续两个反斜杠）
    text = text.replace("\x00DOUBLE_BACKSLASH\x00", "\\")
    
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
    # 预留空间用于添加序号（格式：[1/3] + 两个换行）。通常 9 字符以内，预留 10 更贴近上限且更不易产生碎片段落。
    max_content_chars = max_chars - 10
    if max_content_chars <= 0:
        max_content_chars = max_chars

    parts: List[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_content_chars:
            parts.append(remaining.rstrip())
            break

        window = remaining[:max_content_chars]
        cut = window.rfind("\n")
        # 如果换行位置太靠前，会产生很短的“碎片段落”，体验很差；此时忽略换行改为硬切
        min_reasonable_cut = max(50, int(max_content_chars * 0.4))
        if cut < min_reasonable_cut:
            # 没有合适的换行点，按硬切
            cut = max_content_chars
        else:
            # 在换行符之后切（保留换行语义）
            cut = cut + 1

        chunk = remaining[:cut]
        remaining = remaining[cut:]
        parts.append(chunk.rstrip())

    total_parts = len(parts)
    if total_parts <= 1:
        return parts

    messages: List[str] = []
    for idx, p in enumerate(parts, 1):
        messages.append(f"{p}\n\n[{idx}/{total_parts}]")
    return messages


def format_message(text: str) -> str:
    """
    格式化消息：美化（含转义字符转换）并返回字符串
    
    Args:
        text: 原始消息文本
        
    Returns:
        格式化后的消息字符串（不做分片）
    """
    if not text:
        return text
    
    # 先美化
    return beautify_message(text)

