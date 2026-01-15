"""
用户数据库管理器
为每个用户创建和管理独立的SQLite数据库文件
"""
from pathlib import Path
from typing import Dict, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import threading

from shared.config import settings
from shared.models import Base, StructuredRecord
from shared.utils import setup_logger

logger = setup_logger(__name__)


class UserDatabase:
    """单个用户的数据库实例"""
    
    def __init__(self, user_id: str, db_path: str):
        """
        初始化用户数据库
        
        Args:
            user_id: 用户ID
            db_path: 数据库文件路径
        """
        self.user_id = user_id
        self.db_path = db_path
        
        # 创建SQLite引擎
        database_url = f"sqlite:///{db_path}"
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
        self.create_tables()
        
        logger.info(f"用户数据库初始化成功: {user_id} -> {db_path}")
    
    def create_tables(self):
        """创建数据库表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.debug(f"用户 {self.user_id} 数据库表创建成功")
        except Exception as e:
            logger.error(f"创建用户 {self.user_id} 数据库表失败: {e}")
            raise
    
    def get_session(self) -> Session:
        """
        获取数据库会话
        
        Returns:
            数据库会话对象
        """
        return self.SessionLocal()
    
    def close(self):
        """关闭数据库连接"""
        try:
            self.engine.dispose()
            logger.debug(f"用户 {self.user_id} 数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭用户 {self.user_id} 数据库连接失败: {e}")


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
    
    def get_user_db(self, user_id: str) -> UserDatabase:
        """
        获取用户的数据库实例（如果不存在则创建）
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户数据库实例
        """
        if not user_id:
            raise ValueError("user_id 不能为空")
        
        # 清理无效字符，确保文件名安全
        safe_user_id = self._sanitize_user_id(user_id)
        
        with self._lock:
            if safe_user_id in self._databases:
                return self._databases[safe_user_id]
            
            # 创建新的用户数据库
            db_path = self.user_db_dir / f"{safe_user_id}.db"
            user_db = UserDatabase(safe_user_id, str(db_path))
            self._databases[safe_user_id] = user_db
            
            return user_db
    
    def get_user_session(self, user_id: str) -> Session:
        """
        获取用户的数据库会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            数据库会话对象
        """
        user_db = self.get_user_db(user_id)
        return user_db.get_session()
    
    def initialize_user_db(self, user_id: str) -> bool:
        """
        初始化用户数据库（如果不存在）
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功初始化
        """
        try:
            self.get_user_db(user_id)
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
    
    def close_user_db(self, user_id: str):
        """
        关闭指定用户的数据库连接
        
        Args:
            user_id: 用户ID
        """
        safe_user_id = self._sanitize_user_id(user_id)
        with self._lock:
            if safe_user_id in self._databases:
                self._databases[safe_user_id].close()
                del self._databases[safe_user_id]
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


# 全局用户数据库管理器实例
user_db_manager = UserDatabaseManager()

