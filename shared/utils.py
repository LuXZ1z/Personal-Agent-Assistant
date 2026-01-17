"""
工具函数
提供通用的工具函数
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import colorlog

from shared.config import settings


def setup_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径（可选），如果包含 {timestamp} 会被替换为时间戳
        
    Returns:
        配置好的日志记录器
    """
    # 默认写入 settings.log_file，避免只在screen里看到日志导致排查困难
    if log_file is None:
        log_file = settings.log_file or None
    
    # 如果日志文件路径包含 {timestamp}，替换为时间戳（格式：YYYYMMDD_HHMMSS）
    if log_file and "{timestamp}" in log_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_file.replace("{timestamp}", timestamp)
    elif log_file:
        # 如果日志文件路径不包含时间戳，自动添加（避免覆盖）
        log_path = Path(log_file)
        if log_path.exists():
            # 文件已存在，添加时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = log_path.stem
            suffix = log_path.suffix
            log_file = str(log_path.parent / f"{stem}_{timestamp}{suffix}")

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 控制台handler（带颜色）
    console_handler = colorlog.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # 颜色格式
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        }
    )
    console_handler.setFormatter(color_formatter)
    logger.addHandler(console_handler)

    # 避免日志向root传播导致重复输出（uvicorn等可能配置root handler）
    logger.propagate = False
    
    # 文件handler（如果指定了日志文件）
    if log_file:
        file_path = Path(log_file)
        if file_path.parent:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        
        # 文件格式（不带颜色）
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def ensure_dir(path: str) -> Path:
    """
    确保目录存在
    
    Args:
        path: 目录路径
        
    Returns:
        Path对象
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

