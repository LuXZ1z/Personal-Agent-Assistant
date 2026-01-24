"""
用户数据库管理器
为每个用户创建和管理独立的SQLite数据库文件
"""
from pathlib import Path
from typing import Dict, Optional
from sqlalchemy.orm import Session
import threading

from shared.config import settings
from shared.models import Base
from core.database.base import DatabaseManager
from shared.utils import setup_logger

logger = setup_logger(__name__)


class UserDatabase(DatabaseManager):
    """单个用户的数据库实例"""
    
    def __init__(self, user_id: str, db_path: str):
        """
        初始化用户数据库
        
        Args:
            user_id: 用户ID
            db_path: 数据库文件路径
        """
        self.user_id = user_id
        # 确保路径是绝对路径字符串
        if isinstance(db_path, Path):
            db_path = str(db_path.absolute())
        elif not Path(db_path).is_absolute():
            db_path = str(Path(db_path).absolute())
        
        logger.info(f"正在创建用户数据库: {user_id} -> {db_path}")
        super().__init__(db_path)
        logger.info(f"用户数据库初始化成功: {user_id} -> {db_path}")


class UserDatabaseManager:
    """用户数据库管理器（单例）"""
    
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
        """初始化管理器"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._databases: Dict[str, UserDatabase] = {}
        self._lock = threading.Lock()
        
        # 确保用户数据库目录存在
        self.user_db_dir = Path(settings.user_database_dir)
        self.user_db_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"用户数据库管理器初始化成功，目录: {self.user_db_dir}")
    
    def get_user_db(self, user_id: str, bot_id: Optional[str] = None) -> UserDatabase:
        """
        获取用户的数据库实例（如果不存在则创建）
        
        Args:
            user_id: 用户ID
            bot_id: 机器人ID，如果提供则使用 bot_id/user_id.db 目录结构
            
        Returns:
            用户数据库实例
        """
        if not user_id:
            raise ValueError("user_id 不能为空")
        
        # 清理无效字符，确保文件名安全
        safe_user_id = self._sanitize_user_id(user_id)
        
        # 如果提供了 bot_id，使用 bot_id/user_id.db 目录结构
        if bot_id:
            safe_bot_id = self._sanitize_user_id(bot_id)
            # 使用 bot_id/user_id.db 的目录结构
            bot_dir = self.user_db_dir / safe_bot_id
            bot_dir.mkdir(parents=True, exist_ok=True)
            db_path = bot_dir / f"{safe_user_id}.db"
            db_key = f"{safe_bot_id}/{safe_user_id}"
        else:
            # 兼容旧代码，如果没有 bot_id，只使用 user_id（放在根目录）
            db_path = self.user_db_dir / f"{safe_user_id}.db"
            db_key = safe_user_id
        
        with self._lock:
            if db_key in self._databases:
                return self._databases[db_key]
            
            # 创建新的用户数据库
            # 确保路径是绝对路径
            db_path_str = str(db_path.absolute()) if isinstance(db_path, Path) else str(db_path)
            logger.info(f"准备创建数据库: bot_id={bot_id}, user_id={user_id}, db_path={db_path_str}")
            try:
                user_db = UserDatabase(db_key, db_path_str)
                self._databases[db_key] = user_db
                logger.info(f"数据库创建成功: {db_key} -> {db_path_str}")
                # 验证文件是否真的创建了
                if Path(db_path_str).exists():
                    logger.info(f"✓ 数据库文件已确认存在: {db_path_str}")
                else:
                    logger.warning(f"⚠ 数据库文件不存在: {db_path_str}")
                return user_db
            except Exception as e:
                logger.error(f"创建数据库失败: {e}", exc_info=True)
                raise
    
    def get_user_session(self, user_id: str, bot_id: Optional[str] = None) -> Session:
        """
        获取用户的数据库会话
        
        Args:
            user_id: 用户ID
            bot_id: 机器人ID，如果提供则使用 bot_id_user_id 格式
            
        Returns:
            数据库会话对象
        """
        user_db = self.get_user_db(user_id, bot_id)
        return user_db.get_session()
    
    def initialize_user_db(self, user_id: str, bot_id: Optional[str] = None) -> bool:
        """
        初始化用户数据库（如果不存在）
        
        Args:
            user_id: 用户ID
            bot_id: 机器人ID，如果提供则使用 bot_id_user_id 格式
            
        Returns:
            是否成功初始化
        """
        try:
            self.get_user_db(user_id, bot_id)
            return True
        except Exception as e:
            logger.error(f"初始化用户 {user_id} 数据库失败: {e}")
            return False
    
    def _sanitize_user_id(self, user_id: str) -> str:
        """
        清理用户ID，确保可以作为文件名
        
        Args:
            user_id: 原始用户ID
            
        Returns:
            清理后的用户ID
        """
        # 移除或替换不安全字符
        safe_id = user_id.replace("/", "_").replace("\\", "_")
        safe_id = safe_id.replace("..", "_")
        # 限制长度
        if len(safe_id) > 100:
            safe_id = safe_id[:100]
        return safe_id
    
    def close_user_db(self, user_id: str, bot_id: Optional[str] = None):
        """
        关闭指定用户的数据库连接
        
        Args:
            user_id: 用户ID
            bot_id: 机器人ID，如果提供则使用 bot_id/user_id.db 目录结构
        """
        safe_user_id = self._sanitize_user_id(user_id)
        if bot_id:
            safe_bot_id = self._sanitize_user_id(bot_id)
            db_key = f"{safe_bot_id}/{safe_user_id}"
        else:
            db_key = safe_user_id
        
        with self._lock:
            if db_key in self._databases:
                self._databases[db_key].close()
                del self._databases[db_key]
                logger.info(f"已关闭用户 {user_id} 的数据库连接")
    
    def close_all(self):
        """关闭所有用户数据库连接"""
        with self._lock:
            for user_id, db in list(self._databases.items()):
                try:
                    db.close()
                except Exception as e:
                    logger.error(f"关闭用户 {user_id} 数据库失败: {e}")
            self._databases.clear()
            logger.info("已关闭所有用户数据库连接")
    
    # 实现DatabaseManager接口，代理到用户数据库
    def get_session(self, user_id: Optional[str] = None, bot_id: Optional[str] = None) -> Session:
        """
        获取数据库会话（兼容DatabaseManager接口）
        
        Args:
            user_id: 用户ID，必须提供
            bot_id: 机器人ID，如果提供则使用 bot_id_user_id 格式
            
        Returns:
            数据库会话对象
        """
        if not user_id:
            raise ValueError("user_id 必须提供")
        return self.get_user_session(user_id, bot_id)
    
    def create_record(
        self,
        original_text: str,
        structured_data: dict,
        record_type: str,
        table_name: Optional[str] = None,
        metadata: Optional[dict] = None,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None
    ):
        """创建记录（代理到用户数据库）"""
        if not user_id:
            raise ValueError("user_id 必须提供")
        user_db = self.get_user_db(user_id, bot_id)
        return user_db.create_record(
            original_text=original_text,
            structured_data=structured_data,
            record_type=record_type,
            table_name=table_name,
            metadata=metadata
        )
    
    def query_records(
        self,
        filters: Optional[dict] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None
    ):
        """查询记录（代理到用户数据库）"""
        if not user_id:
            raise ValueError("user_id 必须提供")
        user_db = self.get_user_db(user_id, bot_id)
        return user_db.query_records(
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by
        )
    
    def get_record(self, record_id: int, user_id: Optional[str] = None, bot_id: Optional[str] = None):
        """获取记录（代理到用户数据库）"""
        if not user_id:
            raise ValueError("user_id 必须提供")
        user_db = self.get_user_db(user_id, bot_id)
        return user_db.get_record(record_id)
    
    def update_record(
        self,
        record_id: int,
        original_text: Optional[str] = None,
        structured_data: Optional[dict] = None,
        record_type: Optional[str] = None,
        table_name: Optional[str] = None,
        metadata: Optional[dict] = None,
        user_id: Optional[str] = None,
        bot_id: Optional[str] = None
    ) -> bool:
        """更新记录（代理到用户数据库）"""
        if not user_id:
            raise ValueError("user_id 必须提供")
        user_db = self.get_user_db(user_id, bot_id)
        return user_db.update_record(
            record_id=record_id,
            original_text=original_text,
            structured_data=structured_data,
            record_type=record_type,
            table_name=table_name,
            metadata=metadata
        )
    
    def delete_record(self, record_id: int, user_id: Optional[str] = None, bot_id: Optional[str] = None) -> bool:
        """删除记录（代理到用户数据库）"""
        if not user_id:
            raise ValueError("user_id 必须提供")
        user_db = self.get_user_db(user_id, bot_id)
        return user_db.delete_record(record_id)
    
    def get_statistics(self, filters: Optional[dict] = None, user_id: Optional[str] = None, bot_id: Optional[str] = None):
        """获取统计信息（代理到用户数据库）"""
        if not user_id:
            raise ValueError("user_id 必须提供")
        user_db = self.get_user_db(user_id, bot_id)
        return user_db.get_statistics(filters=filters)

