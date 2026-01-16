"""
总结服务
调用LLM API对查询结果进行总结
"""
from shared.message_types import QueryRequest, QueryResult, SummaryRequest, SummaryResult
from agent_service.query_service import QueryService
from agent_service.llm_client import LLMClient
from shared.utils import setup_logger

logger = setup_logger(__name__)


class SummaryService:
    """总结服务类"""
    
    def __init__(self):
        """初始化总结服务"""
        self.query_service = QueryService()
        self.llm_client = LLMClient()
    
    def summarize(self, request: SummaryRequest) -> SummaryResult:
        """
        对查询结果进行总结（先查询再总结）
        
        Args:
            request: 总结请求（包含查询参数）
            
        Returns:
            总结结果
        """
        try:
            # 先执行查询
            query_request = QueryRequest(
                request_id=request.request_id,  # 使用相同的request_id
                query_type=request.query_type,
                params=request.params,
                user_id=request.user_id,
                table_name=request.table_name
            )
            
            query_result = self.query_service.query(query_request)
            
            if not query_result.success:
                return SummaryResult(
                    request_id=request.request_id,
                    success=False,
                    error=f"查询失败，无法进行总结: {query_result.error}"
                )
            
            if query_result.count == 0:
                return SummaryResult(
                    request_id=request.request_id,
                    success=True,
                    summary="未找到相关记录"
                )
            
            # 调用LLM API进行总结
            summary_text = self.llm_client.summarize(
                records=query_result.records,
                summary_type=request.summary_type
            )
            
            logger.info(f"总结完成: request_id={request.request_id}, length={len(summary_text)}")
            
            return SummaryResult(
                request_id=request.request_id,
                success=True,
                summary=summary_text
            )
            
        except Exception as e:
            logger.error(f"总结失败: {e}")
            return SummaryResult(
                request_id=request.request_id,
                success=False,
                error=str(e)
            )

