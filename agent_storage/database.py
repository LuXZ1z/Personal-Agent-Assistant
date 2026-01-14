"""
数据库模块
定义SQLAlchemy模型和数据库连接
"""
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from shared.config import settings
from shared.models import Base, StructuredRecord
from shared.utils import setup_logger

logger = setup_logger(__name__)


class Database:
    """数据库管理类"""
    
    def __init__(self):
        """初始化数据库连接"""
        # 确保数据库目录存在
        db_path = Path(settings.database_path)
        if db_path.parent:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建SQLite引擎
        # 使用StaticPool确保多线程安全
        database_url = f"sqlite:///{settings.database_path}"
        self.engine = create_engine(
            database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False  # 设置为True可以查看SQL语句
        )
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # 创建表
        self.create_tables()
        
        logger.info(f"数据库初始化成功: {settings.database_path}")
    
    def create_tables(self):
        """创建数据库表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("数据库表创建成功")
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
    
    def close(self):
        """关闭数据库连接"""
        try:
            self.engine.dispose()
            logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {e}")


# 全局数据库实例
db = Database()

