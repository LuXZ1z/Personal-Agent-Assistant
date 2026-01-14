"""
存储服务
处理数据存储操作（纯规则实现）
"""
from typing import Optional
from sqlalchemy.orm import Session

from shared.message_types import StructuredDataMessage, StorageResult
from shared.models import StructuredRecord
from agent_storage.database import db
from shared.utils import setup_logger

logger = setup_logger(__name__)


class StorageService:
    """存储服务类"""
    
    def __init__(self):
        """初始化存储服务"""
        self.db = db
    
    def store(self, message: StructuredDataMessage) -> StorageResult:
        """
        存储结构化数据
        
        Args:
            message: 结构化数据消息
            
        Returns:
            存储结果
        """
        session = self.db.get_session()
        try:
            # 创建记录
            record = StructuredRecord(
                original_text=message.original_text,
                structured_data=message.structured_data.model_dump(),
                record_type=message.structured_data.type,
                table_name=message.table_name,
                metadata=None  # 可以扩展元数据
            )
            
            # 保存到数据库
            session.add(record)
            session.commit()
            session.refresh(record)
            
            logger.info(f"数据存储成功: record_id={record.id}, message_id={message.message_id}")
            
            return StorageResult(
                message_id=message.message_id,
                success=True,
                record_id=record.id
            )
            
        except Exception as e:
            session.rollback()
            logger.error(f"数据存储失败: {e}")
            return StorageResult(
                message_id=message.message_id,
                success=False,
                error=str(e)
            )
        finally:
            session.close()

