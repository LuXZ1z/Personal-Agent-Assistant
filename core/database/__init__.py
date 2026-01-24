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


def get_database_manager(user_id: Optional[str] = None, bot_id: Optional[str] = None) -> DatabaseManager:
    """
    获取数据库管理器实例
    
    Args:
        user_id: 用户ID，如果提供则使用用户数据库，否则使用全局数据库
        bot_id: 机器人ID，如果提供则使用 bot_id_user_id 格式的数据库路径
        
    Returns:
        数据库管理器实例
    """
    global _database_manager, _user_database_manager
    
    if user_id:
        if _user_database_manager is None:
            _user_database_manager = UserDatabaseManager()
        # 将 bot_id 存储到管理器实例中，以便后续使用
        if bot_id:
            _user_database_manager._current_bot_id = bot_id
        return _user_database_manager
    else:
        if _database_manager is None:
            _database_manager = DatabaseManager()
        return _database_manager

