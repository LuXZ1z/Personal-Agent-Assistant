"""
消息类型定义
定义所有Agent之间传递的消息格式
"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    QUERY = "query"
    SUMMARY = "summary"
    STORAGE = "storage"
    RESPONSE = "response"


class WeChatMessage(BaseModel):
    """微信原始消息"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    msgtype: str = "text"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RawTextMessage(BaseModel):
    """原始文本消息"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    table_name: Optional[str] = None  # 当前选择的表/目录
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StructuredData(BaseModel):
    """结构化数据"""
    type: str  # 记录类型
    fields: Dict[str, Any]  # 动态字段
    summary: str  # 简要摘要


class StructuredDataMessage(BaseModel):
    """结构化数据消息"""
    message_id: str
    original_text: str
    structured_data: StructuredData
    table_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StorageResult(BaseModel):
    """存储结果消息"""
    message_id: str
    success: bool
    record_id: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryRequest(BaseModel):
    """查询请求消息"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_type: str  # by_type, by_date, by_keyword, by_table
    params: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    table_name: Optional[str] = None  # 当前选择的表/目录


class QueryResult(BaseModel):
    """查询结果消息"""
    request_id: str
    success: bool
    records: list = Field(default_factory=list)
    count: int = 0
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SummaryRequest(BaseModel):
    """总结请求消息"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_type: str  # 查询类型
    params: Dict[str, Any] = Field(default_factory=dict)  # 查询参数
    summary_type: str = "general"  # general, detailed, analysis
    user_id: Optional[str] = None
    table_name: Optional[str] = None  # 当前选择的表/目录


class SummaryResult(BaseModel):
    """总结结果消息"""
    request_id: str
    success: bool
    summary: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WeChatResponse(BaseModel):
    """微信响应消息"""
    message_id: str
    text: str
    msgtype: str = "text"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TarotRequest(BaseModel):
    """塔罗牌请求消息"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    spread_type: str = "single"  # single, three_card, five_card
    question: Optional[str] = None  # 用户的问题（可选）
    user_id: Optional[str] = None


class TarotResult(BaseModel):
    """塔罗牌结果消息"""
    request_id: str
    success: bool
    spread_type: str
    cards: list = Field(default_factory=list)  # 抽取的牌列表
    interpretation: Optional[str] = None  # LLM生成的解读
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

