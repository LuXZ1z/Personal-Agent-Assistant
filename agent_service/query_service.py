"""
查询服务
纯规则实现数据库查询
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from shared.message_types import QueryRequest, QueryResult
from shared.models import StructuredRecord
from agent_storage.database import db
from shared.utils import setup_logger

logger = setup_logger(__name__)


class QueryService:
    """查询服务类"""
    
    def __init__(self):
        """初始化查询服务"""
        self.db = db
    
    def query(self, request: QueryRequest) -> QueryResult:
        """
        执行查询
        
        Args:
            request: 查询请求
            
        Returns:
            查询结果
        """
        session = self.db.get_session()
        try:
            # 构建查询
            query = session.query(StructuredRecord)
            
            # 根据查询类型添加过滤条件
            if request.query_type == "by_table" and request.params.get("table_name"):
                query = query.filter(StructuredRecord.table_name == request.params["table_name"])
            
            elif request.query_type == "by_type" and request.params.get("type"):
                query = query.filter(StructuredRecord.record_type == request.params["type"])
            
            elif request.query_type == "by_date":
                if "start_date" in request.params and "end_date" in request.params:
                    # 日期范围查询
                    start_date = datetime.strptime(request.params["start_date"], "%Y-%m-%d").date()
                    end_date = datetime.strptime(request.params["end_date"], "%Y-%m-%d").date()
                    query = query.filter(
                        and_(
                            StructuredRecord.created_at >= datetime.combine(start_date, datetime.min.time()),
                            StructuredRecord.created_at <= datetime.combine(end_date, datetime.max.time())
                        )
                    )
                elif "date" in request.params:
                    # 单个日期查询
                    query_date = datetime.strptime(request.params["date"], "%Y-%m-%d").date()
                    query = query.filter(
                        and_(
                            StructuredRecord.created_at >= datetime.combine(query_date, datetime.min.time()),
                            StructuredRecord.created_at < datetime.combine(query_date, datetime.max.time()) + timedelta(days=1)
                        )
                    )
            
            elif request.query_type == "by_keyword" and request.params.get("keyword"):
                # 关键词查询（在原始文本和结构化数据中搜索）
                keyword = request.params["keyword"]
                query = query.filter(
                    or_(
                        StructuredRecord.original_text.contains(keyword),
                        StructuredRecord.structured_data.contains({"summary": keyword})
                    )
                )
            
            # 如果指定了表/目录，添加过滤条件
            if request.table_name:
                query = query.filter(StructuredRecord.table_name == request.table_name)
            
            # 按创建时间倒序排列
            query = query.order_by(StructuredRecord.created_at.desc())
            
            # 执行查询
            records = query.all()
            
            # 转换为字典列表
            records_list = [record.to_dict() for record in records]
            
            logger.info(f"查询完成: request_id={request.request_id}, count={len(records_list)}")
            
            return QueryResult(
                request_id=request.request_id,
                success=True,
                records=records_list,
                count=len(records_list)
            )
            
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return QueryResult(
                request_id=request.request_id,
                success=False,
                error=str(e)
            )
        finally:
            session.close()

