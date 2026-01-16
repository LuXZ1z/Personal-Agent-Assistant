"""
会话管理器
管理用户会话状态（当前业务类型、对话上下文等）
"""
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import threading

from shared.utils import setup_logger

logger = setup_logger(__name__)


class SessionState:
    """会话状态"""
    
    def __init__(self, user_id: str):
        """
        初始化会话状态
        
        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.business_type: str = "menu"  # menu/accounting/essay/employee/tarot
        self.sub_menu: Optional[str] = None  # 子菜单状态：None/main/add/query/update/delete/switch/list/analyze
        self.table_name: Optional[str] = None  # 当前表/目录名
        self.last_activity: float = time.time()
        self.context: Dict[str, Any] = {}  # 业务上下文
        self.expire_at: float = time.time() + 1800  # 30分钟后过期
    
    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = time.time()
        self.expire_at = time.time() + 1800  # 重置过期时间
    
    def is_expired(self) -> bool:
        """检查是否已过期"""
        return time.time() > self.expire_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "business_type": self.business_type,
            "table_name": self.table_name,
            "last_activity": self.last_activity,
            "expire_at": self.expire_at,
            "context": self.context
        }


class SessionManager:
    """会话管理器（单例）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化会话管理器"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._sessions: Dict[str, SessionState] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = 300  # 5分钟清理一次过期会话
        self._last_cleanup = time.time()
        
        logger.info("会话管理器初始化成功")
    
    def get_session(self, user_id: str) -> SessionState:
        """
        获取用户会话状态（如果不存在则创建）
        
        Args:
            user_id: 用户ID
            
        Returns:
            会话状态对象
        """
        if not user_id:
            raise ValueError("user_id 不能为空")
        
        # 定期清理过期会话
        self._cleanup_expired_sessions()
        
        with self._lock:
            if user_id in self._sessions:
                session = self._sessions[user_id]
                # 检查是否过期
                if session.is_expired():
                    logger.debug(f"用户 {user_id} 会话已过期，创建新会话")
                    session = SessionState(user_id)
                    self._sessions[user_id] = session
                else:
                    session.update_activity()
                return session
            else:
                # 创建新会话
                session = SessionState(user_id)
                self._sessions[user_id] = session
                logger.debug(f"为用户 {user_id} 创建新会话")
                return session
    
    def update_business_type(self, user_id: str, business_type: str, table_name: Optional[str] = None):
        """
        更新用户的业务类型
        
        Args:
            user_id: 用户ID
            business_type: 业务类型（menu/accounting/essay/employee/tarot）
            table_name: 表/目录名（可选）
        """
        session = self.get_session(user_id)
        session.business_type = business_type
        if table_name:
            session.table_name = table_name
        session.update_activity()
        logger.debug(f"用户 {user_id} 切换到业务: {business_type}, 表: {table_name}")
    
    def update_context(self, user_id: str, context: Dict[str, Any]):
        """
        更新用户会话上下文
        
        Args:
            user_id: 用户ID
            context: 上下文字典
        """
        session = self.get_session(user_id)
        session.context.update(context)
        session.update_activity()
    
    def get_context(self, user_id: str, key: str, default: Any = None) -> Any:
        """
        获取会话上下文中的值
        
        Args:
            user_id: 用户ID
            key: 上下文键
            default: 默认值
            
        Returns:
            上下文值
        """
        session = self.get_session(user_id)
        return session.context.get(key, default)
    
    def clear_session(self, user_id: str):
        """
        清除用户会话
        
        Args:
            user_id: 用户ID
        """
        with self._lock:
            if user_id in self._sessions:
                del self._sessions[user_id]
                logger.debug(f"已清除用户 {user_id} 的会话")
    
    def reset_to_menu(self, user_id: str):
        """
        重置用户会话到菜单状态
        
        Args:
            user_id: 用户ID
        """
        session = self.get_session(user_id)
        session.business_type = "menu"
        session.sub_menu = None
        session.table_name = None
        session.context.clear()
        session.update_activity()
        logger.debug(f"用户 {user_id} 已重置到菜单状态")
    
    def set_sub_menu(self, user_id: str, sub_menu: str):
        """
        设置子菜单状态
        
        Args:
            user_id: 用户ID
            sub_menu: 子菜单状态（main/add/query/update/delete/switch/list/analyze）
        """
        session = self.get_session(user_id)
        session.sub_menu = sub_menu
        session.update_activity()
        logger.debug(f"用户 {user_id} 设置子菜单: {sub_menu}")
    
    def _cleanup_expired_sessions(self):
        """清理过期的会话"""
        current_time = time.time()
        # 每5分钟清理一次
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = current_time
        
        with self._lock:
            expired_users = [
                user_id for user_id, session in self._sessions.items()
                if session.is_expired()
            ]
            
            for user_id in expired_users:
                del self._sessions[user_id]
                logger.debug(f"已清理过期会话: {user_id}")
            
            if expired_users:
                logger.info(f"清理了 {len(expired_users)} 个过期会话")
    
    def get_all_sessions(self) -> Dict[str, SessionState]:
        """
        获取所有会话（用于调试）
        
        Returns:
            所有会话的字典
        """
        self._cleanup_expired_sessions()
        with self._lock:
            return self._sessions.copy()


# 全局会话管理器实例
session_manager = SessionManager()

