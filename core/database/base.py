"""
数据库基类和通用操作
提供统一的数据库CRUD接口
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from shared.config import settings
from shared.models import Base, StructuredRecord
from shared.utils import setup_logger

logger = setup_logger(__name__)


class DatabaseManager:
    """数据库管理器基类 - 提供统一的数据库操作接口"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径，如果为None则使用配置中的路径
        """
        if db_path is None:
            db_path = settings.database_path
        
        # 确保数据库目录存在
        db_file = Path(db_path)
        if db_file.parent:
            db_file.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"数据库目录已确保存在: {db_file.parent}")
        
        # 创建SQLite引擎
        database_url = f"sqlite:///{db_path}"
        logger.debug(f"创建数据库引擎: {database_url}")
        self.engine = create_engine(
            database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False
        )
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # 创建表
        logger.debug(f"开始创建数据库表: {db_path}")
        self.create_tables()
        
        # 验证文件是否真的创建了
        if db_file.exists():
            logger.info(f"数据库管理器初始化成功: {db_path} (文件已存在)")
        else:
            logger.warning(f"数据库管理器初始化完成，但文件不存在: {db_path} (SQLite可能延迟创建)")
    
    def create_tables(self):
        """创建数据库表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.debug("数据库表创建成功")
        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise
    
    def get_session(self) -> Session:
        """
        获取数据库会话
        
        Returns:
            数据库会话对象
        """
        return self.SessionLocal()
    
    def create_record(
        self,
        original_text: str,
        structured_data: Dict[str, Any],
        record_type: str,
        table_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StructuredRecord:
        """
        创建记录
        
        Args:
            original_text: 原始文本
            structured_data: 结构化数据
            record_type: 记录类型
            table_name: 表名/目录名
            metadata: 额外元数据
            
        Returns:
            创建的记录对象
        """
        session = self.get_session()
        try:
            record = StructuredRecord(
                original_text=original_text,
                structured_data=structured_data,
                record_type=record_type,
                table_name=table_name,
                extra_metadata=metadata
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info(f"记录创建成功: id={record.id}, type={record_type}")
            return record
        except Exception as e:
            session.rollback()
            logger.error(f"创建记录失败: {e}")
            raise
        finally:
            session.close()
    
    def query_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[StructuredRecord]:
        """
        查询记录
        
        Args:
            filters: 查询过滤条件，支持：
                - record_type: 记录类型
                - table_name: 表名
                - date_from: 开始日期 (YYYY-MM-DD)
                - date_to: 结束日期 (YYYY-MM-DD)
                - keyword: 关键词搜索（在original_text中搜索）
            limit: 限制返回数量
            offset: 偏移量
            order_by: 排序字段（如 'created_at' 或 '-created_at'）
            
        Returns:
            记录列表
        """
        session = self.get_session()
        try:
            query = session.query(StructuredRecord)
            
            # 应用过滤条件
            if filters:
                if 'record_type' in filters:
                    query = query.filter(StructuredRecord.record_type == filters['record_type'])
                
                if 'table_name' in filters:
                    query = query.filter(StructuredRecord.table_name == filters['table_name'])
                
                if 'date_from' in filters:
                    date_from = datetime.strptime(filters['date_from'], "%Y-%m-%d").date()
                    query = query.filter(
                        StructuredRecord.created_at >= datetime.combine(date_from, datetime.min.time())
                    )
                
                if 'date_to' in filters:
                    date_to = datetime.strptime(filters['date_to'], "%Y-%m-%d").date()
                    query = query.filter(
                        StructuredRecord.created_at <= datetime.combine(date_to, datetime.max.time())
                    )
                
                if 'keyword' in filters:
                    keyword = filters['keyword']
                    query = query.filter(StructuredRecord.original_text.contains(keyword))
            
            # 排序
            if order_by:
                if order_by.startswith('-'):
                    # 降序
                    field = getattr(StructuredRecord, order_by[1:], None)
                    if field:
                        query = query.order_by(field.desc())
                else:
                    # 升序
                    field = getattr(StructuredRecord, order_by, None)
                    if field:
                        query = query.order_by(field.asc())
            else:
                # 默认按创建时间降序
                query = query.order_by(StructuredRecord.created_at.desc())
            
            # 分页
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            records = query.all()
            logger.debug(f"查询到 {len(records)} 条记录")
            return records
            
        except Exception as e:
            logger.error(f"查询记录失败: {e}")
            raise
        finally:
            session.close()
    
    def get_record(self, record_id: int) -> Optional[StructuredRecord]:
        """
        根据ID获取单条记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录对象，如果不存在则返回None
        """
        session = self.get_session()
        try:
            record = session.query(StructuredRecord).filter(
                StructuredRecord.id == record_id
            ).first()
            return record
        except Exception as e:
            logger.error(f"获取记录失败: {e}")
            raise
        finally:
            session.close()
    
    def update_record(
        self,
        record_id: int,
        original_text: Optional[str] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        record_type: Optional[str] = None,
        table_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新记录
        
        Args:
            record_id: 记录ID
            original_text: 原始文本
            structured_data: 结构化数据
            record_type: 记录类型
            table_name: 表名
            metadata: 额外元数据
            
        Returns:
            是否更新成功
        """
        session = self.get_session()
        try:
            record = session.query(StructuredRecord).filter(
                StructuredRecord.id == record_id
            ).first()
            
            if not record:
                logger.warning(f"记录不存在: id={record_id}")
                return False
            
            # 更新字段
            if original_text is not None:
                record.original_text = original_text
            if structured_data is not None:
                record.structured_data = structured_data
            if record_type is not None:
                record.record_type = record_type
            if table_name is not None:
                record.table_name = table_name
            if metadata is not None:
                record.extra_metadata = metadata
            
            record.updated_at = datetime.utcnow()
            
            session.commit()
            logger.info(f"记录更新成功: id={record_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"更新记录失败: {e}")
            raise
        finally:
            session.close()
    
    def delete_record(self, record_id: int) -> bool:
        """
        删除记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否删除成功
        """
        session = self.get_session()
        try:
            record = session.query(StructuredRecord).filter(
                StructuredRecord.id == record_id
            ).first()
            
            if not record:
                logger.warning(f"记录不存在: id={record_id}")
                return False
            
            session.delete(record)
            session.commit()
            logger.info(f"记录删除成功: id={record_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"删除记录失败: {e}")
            raise
        finally:
            session.close()
    
    def get_statistics(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            filters: 过滤条件（同query_records）
            
        Returns:
            统计信息字典，包含：
                - total_count: 总记录数
                - by_type: 按类型统计
                - by_table: 按表统计
                - date_range: 日期范围
        """
        session = self.get_session()
        try:
            query = session.query(StructuredRecord)
            
            # 应用过滤条件（同query_records）
            if filters:
                if 'record_type' in filters:
                    query = query.filter(StructuredRecord.record_type == filters['record_type'])
                if 'table_name' in filters:
                    query = query.filter(StructuredRecord.table_name == filters['table_name'])
                if 'date_from' in filters:
                    date_from = datetime.strptime(filters['date_from'], "%Y-%m-%d").date()
                    query = query.filter(
                        StructuredRecord.created_at >= datetime.combine(date_from, datetime.min.time())
                    )
                if 'date_to' in filters:
                    date_to = datetime.strptime(filters['date_to'], "%Y-%m-%d").date()
                    query = query.filter(
                        StructuredRecord.created_at <= datetime.combine(date_to, datetime.max.time())
                    )
            
            # 总记录数
            total_count = query.count()
            
            # 按类型统计
            type_stats = session.query(
                StructuredRecord.record_type,
                func.count(StructuredRecord.id).label('count')
            ).group_by(StructuredRecord.record_type).all()
            by_type = {stat[0] or '未知': stat[1] for stat in type_stats}
            
            # 按表统计
            table_stats = session.query(
                StructuredRecord.table_name,
                func.count(StructuredRecord.id).label('count')
            ).filter(
                StructuredRecord.table_name.isnot(None)
            ).group_by(StructuredRecord.table_name).all()
            by_table = {stat[0]: stat[1] for stat in table_stats}
            
            # 日期范围
            date_range = session.query(
                func.min(StructuredRecord.created_at).label('min_date'),
                func.max(StructuredRecord.created_at).label('max_date')
            ).first()
            
            result = {
                'total_count': total_count,
                'by_type': by_type,
                'by_table': by_table,
                'date_range': {
                    'min': date_range[0].isoformat() if date_range[0] else None,
                    'max': date_range[1].isoformat() if date_range[1] else None
                } if date_range else {'min': None, 'max': None}
            }
            
            logger.debug(f"统计信息: total={total_count}")
            return result
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise
        finally:
            session.close()
    
    def close(self):
        """关闭数据库连接"""
        try:
            self.engine.dispose()
            logger.debug("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {e}")

