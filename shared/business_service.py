"""
业务服务模块
管理不同业务类型的选择和路由
"""
from typing import Optional, Dict
from enum import Enum
import redis
from redis.exceptions import RedisError

from shared.config import settings
from shared.utils import setup_logger

logger = setup_logger(__name__)


class BusinessType(str, Enum):
    """业务类型枚举"""
    ACCOUNTING = "记账"  # 记账业务
    ESSAY = "随笔"  # 随笔业务
    EMPLOYEE = "员工"  # 员工管理业务
    TAROT = "塔罗牌"  # 塔罗牌业务
    GENERAL = "通用"  # 通用业务（默认）


class BusinessService:
    """业务服务管理器"""
    
    # 业务类型关键词映射
    BUSINESS_KEYWORDS = {
        BusinessType.ACCOUNTING: ["记账", "账本", "支出", "收入", "花费", "消费"],
        BusinessType.ESSAY: ["随笔", "日记", "记录", "想法", "思考"],
        BusinessType.EMPLOYEE: ["员工", "工作", "任务", "工作情况"],
        BusinessType.TAROT: ["塔罗牌", "塔罗", "占卜", "抽牌"],
    }
    
    def __init__(self):
        """初始化业务服务"""
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("业务服务初始化成功")
        except RedisError as e:
            logger.error(f"Redis连接失败: {e}")
            raise
        
        # 使用Redis存储用户选择的业务类型，key格式: user_business:{user_id}
        self.user_business_prefix = "user_business:"
        self.business_ttl = 86400  # 24小时过期
    
    def set_user_business(self, user_id: str, business_type: BusinessType) -> None:
        """
        设置用户选择的业务类型
        
        Args:
            user_id: 用户ID
            business_type: 业务类型
        """
        if not user_id:
            return
        
        try:
            key = f"{self.user_business_prefix}{user_id}"
            self.redis_client.setex(key, self.business_ttl, business_type.value)
            logger.info(f"用户 {user_id} 选择业务: {business_type.value}")
        except Exception as e:
            logger.error(f"设置用户业务失败: {e}")
    
    def get_user_business(self, user_id: str) -> BusinessType:
        """
        获取用户选择的业务类型
        
        Args:
            user_id: 用户ID
            
        Returns:
            业务类型，如果未选择则返回GENERAL
        """
        if not user_id:
            return BusinessType.GENERAL
        
        try:
            key = f"{self.user_business_prefix}{user_id}"
            business_value = self.redis_client.get(key)
            if business_value:
                return BusinessType(business_value)
        except Exception as e:
            logger.error(f"获取用户业务失败: {e}")
        
        return BusinessType.GENERAL
    
    def detect_business_type(self, text: str) -> Optional[BusinessType]:
        """
        从文本中检测业务类型
        
        Args:
            text: 文本内容
            
        Returns:
            检测到的业务类型，如果无法检测则返回None
        """
        text_lower = text.lower()
        
        # 检查业务关键词
        for business_type, keywords in self.BUSINESS_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return business_type
        
        return None
    
    def parse_business_command(self, text: str) -> Optional[BusinessType]:
        """
        解析业务选择命令
        
        支持的命令格式：
        - 进入记账 / 切换到记账 / 选择记账
        - 进入随笔 / 切换到随笔
        - 进入员工管理 / 切换到员工
        - 进入塔罗牌 / 切换到塔罗牌
        
        Args:
            text: 命令文本
            
        Returns:
            业务类型，如果不是业务选择命令则返回None
        """
        text_lower = text.lower()
        text_original = text  # 保留原始文本用于精确匹配
        
        # 检查业务选择关键词
        business_keywords = ["进入", "切换到", "选择", "打开", "切换"]
        has_business_keyword = any(keyword in text_original for keyword in business_keywords)
        
        if not has_business_keyword:
            return None
        
        # 提取业务类型（按优先级匹配）
        # 先检查完整的业务类型名称
        for business_type, type_keywords in self.BUSINESS_KEYWORDS.items():
            for type_keyword in type_keywords:
                if type_keyword in text_lower:
                    return business_type
        
        return None
    
    def get_business_prompt_template(self, business_type: BusinessType) -> Optional[str]:
        """
        获取业务对应的prompt模板名称
        
        Args:
            business_type: 业务类型
            
        Returns:
            prompt模板名称
        """
        prompt_map = {
            BusinessType.ACCOUNTING: "ACCOUNTING_PROMPT_TEMPLATE",
            BusinessType.ESSAY: "ESSAY_PROMPT_TEMPLATE",
            BusinessType.EMPLOYEE: "EMPLOYEE_PROMPT_TEMPLATE",
        }
        return prompt_map.get(business_type)
    
    def get_record_type(self, business_type: BusinessType) -> str:
        """
        获取业务对应的记录类型
        
        Args:
            business_type: 业务类型
            
        Returns:
            记录类型字符串
        """
        return business_type.value
    
    def close(self) -> None:
        """关闭Redis连接"""
        try:
            self.redis_client.close()
            logger.info("业务服务Redis连接已关闭")
        except Exception as e:
            logger.error(f"关闭Redis连接失败: {e}")


# 全局业务服务实例
business_service = BusinessService()

