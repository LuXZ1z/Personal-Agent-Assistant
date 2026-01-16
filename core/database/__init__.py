"""
数据库基础功能模块
提供统一的数据库操作接口，支持单数据库和多用户数据库两种模式
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from core.database.base import DatabaseManager
from core.database.user_manager import UserDatabaseManager

# 导出统一接口
__all__ = [
    'DatabaseManager',
    'UserDatabaseManager',
    'get_database_manager',
]

# 全局数据库管理器实例
_database_manager: Optional[DatabaseManager] = None
_user_database_manager: Optional[UserDatabaseManager] = None


def get_database_manager(user_id: Optional[str] = None) -> DatabaseManager:
    """
    获取数据库管理器实例
    
    Args:
        user_id: 用户ID，如果提供则使用用户数据库，否则使用全局数据库
        
    Returns:
        数据库管理器实例
    """
    global _database_manager, _user_database_manager
    
    if user_id:
        if _user_database_manager is None:
            _user_database_manager = UserDatabaseManager()
        return _user_database_manager
    else:
        if _database_manager is None:
            _database_manager = DatabaseManager()
        return _database_manager

