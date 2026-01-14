"""
数据模型定义
定义数据库模型和业务数据模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class StructuredRecord(Base):
    """
    结构化记录表
    存储所有结构化的数据记录
    """
    __tablename__ = "structured_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_text = Column(Text, nullable=False, comment="原始自然语言文本")
    structured_data = Column(JSON, nullable=False, comment="结构化JSON数据")
    record_type = Column(String(50), nullable=True, comment="记录类型（随笔/记账/员工等）")
    table_name = Column(String(100), nullable=True, comment="表名/目录名（虚拟目录）")
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
    extra_metadata = Column(JSON, nullable=True, comment="额外元数据（如：标签、分类等）")
    
    # 创建索引
    __table_args__ = (
        Index("idx_record_type", "record_type"),
        Index("idx_table_name", "table_name"),
        Index("idx_created_at", "created_at"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "original_text": self.original_text,
            "structured_data": self.structured_data,
            "record_type": self.record_type,
            "table_name": self.table_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.extra_metadata,
        }

