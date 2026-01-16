"""
任务管理器
管理正在处理的任务（如LLM调用），支持任务状态跟踪和取消
"""
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime

from shared.utils import setup_logger

logger = setup_logger(__name__)


class TaskInfo:
    """任务信息"""
    
    def __init__(self, user_id: str, task_type: str, content: str):
        """
        初始化任务信息
        
        Args:
            user_id: 用户ID
            task_type: 任务类型（如：tarot_single, essay_add等）
            content: 任务内容
        """
        self.user_id = user_id
        self.task_type = task_type
        self.content = content
        self.start_time = time.time()
        self.status = "processing"  # processing/completed/cancelled/error
        self.result: Optional[Dict[str, Any]] = None
        self.cancelled = False
    
    def get_elapsed_time(self) -> float:
        """获取已处理时间（秒）"""
        return time.time() - self.start_time
    
    def cancel(self):
        """取消任务"""
        self.cancelled = True
        self.status = "cancelled"
        logger.info(f"任务已取消: user_id={self.user_id}, task_type={self.task_type}")


class TaskManager:
    """任务管理器（单例）"""
    
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
        """初始化任务管理器"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._tasks: Dict[str, TaskInfo] = {}  # key: user_id, value: TaskInfo
        self._lock = threading.Lock()
        
        logger.info("任务管理器初始化成功")
    
    def start_task(self, user_id: str, task_type: str, content: str) -> str:
        """
        开始一个新任务
        
        Args:
            user_id: 用户ID
            task_type: 任务类型
            content: 任务内容
            
        Returns:
            任务ID（用于后续查询）
        """
        with self._lock:
            # 如果用户已有任务，先取消旧任务
            if user_id in self._tasks:
                old_task = self._tasks[user_id]
                if old_task.status == "processing":
                    old_task.cancel()
                    logger.info(f"取消用户 {user_id} 的旧任务: {old_task.task_type}")
            
            # 创建新任务
            task = TaskInfo(user_id, task_type, content)
            self._tasks[user_id] = task
            
            logger.info(f"开始任务: user_id={user_id}, task_type={task_type}")
            return user_id
    
    def get_task(self, user_id: str) -> Optional[TaskInfo]:
        """
        获取用户的任务
        
        Args:
            user_id: 用户ID
            
        Returns:
            任务信息，如果不存在则返回None
        """
        with self._lock:
            return self._tasks.get(user_id)
    
    def complete_task(self, user_id: str, result: Dict[str, Any]):
        """
        完成任务
        
        Args:
            user_id: 用户ID
            result: 任务结果
        """
        with self._lock:
            if user_id in self._tasks:
                task = self._tasks[user_id]
                if not task.cancelled:
                    task.status = "completed"
                    task.result = result
                    logger.info(f"任务完成: user_id={user_id}, task_type={task.task_type}, elapsed={task.get_elapsed_time():.1f}s")
                else:
                    logger.info(f"任务已取消，忽略结果: user_id={user_id}")
    
    def cancel_task(self, user_id: str) -> bool:
        """
        取消用户的任务
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功取消
        """
        with self._lock:
            if user_id in self._tasks:
                task = self._tasks[user_id]
                if task.status == "processing":
                    task.cancel()
                    # 清理任务
                    del self._tasks[user_id]
                    return True
            return False
    
    def cleanup_completed_tasks(self, max_age: int = 300):
        """
        清理已完成的任务（超过max_age秒）
        
        Args:
            max_age: 最大保留时间（秒）
        """
        current_time = time.time()
        with self._lock:
            expired_users = [
                user_id for user_id, task in self._tasks.items()
                if task.status in ["completed", "cancelled", "error"] 
                and current_time - task.start_time > max_age
            ]
            for user_id in expired_users:
                del self._tasks[user_id]
                logger.debug(f"清理过期任务: user_id={user_id}")


# 全局任务管理器实例
task_manager = TaskManager()

