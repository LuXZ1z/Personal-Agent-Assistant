"""
数据库备份模块
提供定时备份用户数据库的功能
"""
import shutil
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import zipfile

from shared.config import settings
from shared.utils import setup_logger

logger = setup_logger(__name__)


class DatabaseBackupManager:
    """数据库备份管理器"""
    
    def __init__(self, backup_dir: Optional[str] = None, backup_interval_days: int = 3):
        """
        初始化备份管理器
        
        Args:
            backup_dir: 备份目录路径，如果为None则使用默认路径
            backup_interval_days: 备份间隔天数，默认3天
        """
        if backup_dir is None:
            backup_dir = Path(settings.user_database_dir).parent / "backups"
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.backup_interval_days = backup_interval_days
        self.user_db_dir = Path(settings.user_database_dir)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        logger.info(f"数据库备份管理器初始化: 备份目录={self.backup_dir}, 间隔={backup_interval_days}天")
    
    def backup_all_databases(self) -> dict:
        """
        备份所有用户数据库
        
        Returns:
            备份结果字典，包含成功和失败的数量
        """
        if not self.user_db_dir.exists():
            logger.warning(f"用户数据库目录不存在: {self.user_db_dir}")
            return {"success": 0, "failed": 0, "total": 0}
        
        # 递归获取所有数据库文件（支持 bot_id/user_id.db 目录结构）
        db_files = list(self.user_db_dir.rglob("*.db"))
        if not db_files:
            logger.info("没有找到需要备份的数据库文件")
            return {"success": 0, "failed": 0, "total": 0}
        
        logger.info(f"开始备份 {len(db_files)} 个数据库文件...")
        
        success_count = 0
        failed_count = 0
        
        # 创建备份时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = self.backup_dir / timestamp
        backup_subdir.mkdir(parents=True, exist_ok=True)
        
        for db_file in db_files:
            try:
                # 计算相对路径，保持目录结构（如 bot_id/user_id.db）
                relative_path = db_file.relative_to(self.user_db_dir)
                backup_file = backup_subdir / relative_path
                
                # 确保目标目录存在
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 复制数据库文件
                shutil.copy2(db_file, backup_file)
                logger.debug(f"备份成功: {relative_path} -> {backup_file}")
                success_count += 1
            except Exception as e:
                logger.error(f"备份失败: {db_file}, 错误: {e}")
                failed_count += 1
        
        # 创建压缩包
        zip_file = self.backup_dir / f"backup_{timestamp}.zip"
        try:
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 递归添加所有文件，保持目录结构
                for file in backup_subdir.rglob("*"):
                    if file.is_file():
                        relative_path = file.relative_to(backup_subdir)
                        zipf.write(file, relative_path)
            
            # 删除未压缩的备份目录
            shutil.rmtree(backup_subdir)
            logger.info(f"备份压缩包创建成功: {zip_file}")
        except Exception as e:
            logger.error(f"创建备份压缩包失败: {e}")
        
        result = {
            "success": success_count,
            "failed": failed_count,
            "total": len(db_files),
            "backup_file": str(zip_file)
        }
        
        logger.info(f"备份完成: 成功={success_count}, 失败={failed_count}, 总计={len(db_files)}")
        
        # 清理旧备份（保留最近30天的备份）
        self._cleanup_old_backups()
        
        return result
    
    def _cleanup_old_backups(self, keep_days: int = 30):
        """
        清理旧的备份文件
        
        Args:
            keep_days: 保留天数，默认30天
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=keep_days)
            deleted_count = 0
            
            for backup_file in self.backup_dir.glob("backup_*.zip"):
                try:
                    # 从文件名提取时间戳
                    # 格式: backup_20240124_120000.zip
                    file_time_str = backup_file.stem.replace("backup_", "")
                    file_time = datetime.strptime(file_time_str, "%Y%m%d_%H%M%S")
                    
                    if file_time < cutoff_time:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.debug(f"删除旧备份: {backup_file.name}")
                except Exception as e:
                    logger.warning(f"处理备份文件失败: {backup_file.name}, 错误: {e}")
            
            if deleted_count > 0:
                logger.info(f"清理完成: 删除了 {deleted_count} 个旧备份文件")
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
    
    def should_backup(self) -> bool:
        """
        检查是否需要执行备份
        
        Returns:
            是否需要备份
        """
        # 查找最新的备份文件
        backup_files = list(self.backup_dir.glob("backup_*.zip"))
        if not backup_files:
            # 没有备份文件，需要备份
            return True
        
        # 获取最新的备份文件
        latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
        latest_backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
        
        # 检查是否超过备份间隔
        time_since_backup = datetime.now() - latest_backup_time
        return time_since_backup >= timedelta(days=self.backup_interval_days)
    
    def start_auto_backup(self):
        """启动自动备份线程"""
        if self._running:
            logger.warning("自动备份已经在运行中")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._backup_loop, daemon=True)
        self._thread.start()
        logger.info("自动备份线程已启动")
    
    def stop_auto_backup(self):
        """停止自动备份线程"""
        if not self._running:
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("自动备份线程已停止")
    
    def _backup_loop(self):
        """备份循环（在后台线程中运行）"""
        logger.info("备份循环开始，检查间隔: 每6小时")
        
        while self._running:
            try:
                # 检查是否需要备份
                if self.should_backup():
                    logger.info("触发定时备份...")
                    result = self.backup_all_databases()
                    logger.info(f"定时备份完成: {result}")
                else:
                    # 计算下次备份时间
                    backup_files = list(self.backup_dir.glob("backup_*.zip"))
                    if backup_files:
                        latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
                        latest_backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
                        next_backup_time = latest_backup_time + timedelta(days=self.backup_interval_days)
                        logger.debug(f"下次备份时间: {next_backup_time}")
                
                # 每6小时检查一次
                for _ in range(6 * 60):  # 6小时 = 360分钟
                    if not self._running:
                        break
                    time.sleep(60)  # 每分钟检查一次是否停止
                    
            except Exception as e:
                logger.error(f"备份循环异常: {e}", exc_info=True)
                # 发生异常时等待1小时再重试
                for _ in range(60):
                    if not self._running:
                        break
                    time.sleep(60)


# 全局备份管理器实例
_backup_manager: Optional[DatabaseBackupManager] = None


def get_backup_manager(backup_interval_days: int = 3) -> DatabaseBackupManager:
    """
    获取备份管理器实例
    
    Args:
        backup_interval_days: 备份间隔天数，默认3天
        
    Returns:
        备份管理器实例
    """
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = DatabaseBackupManager(backup_interval_days=backup_interval_days)
    return _backup_manager
