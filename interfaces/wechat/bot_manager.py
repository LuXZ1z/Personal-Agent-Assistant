"""
机器人配置管理器
管理多个机器人的配置和加解密器
"""
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import threading

from shared.utils import setup_logger
from shared.config import settings
from interfaces.wechat.message_crypt import WeChatMessageCrypt

logger = setup_logger(__name__)


class BotManager:
    """机器人配置管理器（单例）"""
    
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
        self._bots: Dict[str, Dict] = {}
        self._crypts: Dict[str, WeChatMessageCrypt] = {}
        self._lock = threading.Lock()
        
        # 加载配置
        self._load_config()
        
        logger.info(f"机器人管理器初始化成功，加载了 {len(self._bots)} 个机器人")
    
    def _load_config(self):
        """加载机器人配置"""
        config_path = Path(settings.bot_config_path)
        
        if not config_path.exists():
            logger.warning(f"机器人配置文件不存在: {config_path}，使用空配置")
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            bots_config = config_data.get('bots', {})
            
            with self._lock:
                self._bots = {}
                for bot_id, bot_config in bots_config.items():
                    if bot_config.get('enabled', True):
                        self._bots[bot_id] = bot_config.copy()
                        logger.info(f"加载机器人: {bot_id} - {bot_config.get('name', '未知')}")
                    else:
                        logger.debug(f"跳过禁用的机器人: {bot_id}")
                
        except Exception as e:
            logger.error(f"加载机器人配置失败: {e}", exc_info=True)
            raise
    
    def get_bot_config(self, bot_id: str) -> Dict:
        """
        获取机器人配置
        
        Args:
            bot_id: 机器人ID
            
        Returns:
            机器人配置字典
            
        Raises:
            ValueError: 如果机器人ID不存在
        """
        with self._lock:
            if bot_id not in self._bots:
                available_bots = ', '.join(self._bots.keys())
                raise ValueError(f"未知的机器人ID: {bot_id}，可用ID: {available_bots}")
            return self._bots[bot_id].copy()
    
    def get_crypt(self, bot_id: str) -> WeChatMessageCrypt:
        """
        获取机器人的加解密器（带缓存）
        
        Args:
            bot_id: 机器人ID
            
        Returns:
            加解密器实例
        """
        with self._lock:
            if bot_id not in self._crypts:
                config = self.get_bot_config(bot_id)
                self._crypts[bot_id] = WeChatMessageCrypt(
                    token=config['wechat_token'],
                    encoding_aes_key=config['wechat_encoding_aes_key'],
                    receive_id=config['wechat_corp_id']
                )
                logger.debug(f"为机器人 {bot_id} 创建加解密器")
            return self._crypts[bot_id]
    
    def get_features(self, bot_id: str) -> List[str]:
        """
        获取机器人的功能列表
        
        Args:
            bot_id: 机器人ID
            
        Returns:
            功能列表
        """
        config = self.get_bot_config(bot_id)
        return config.get('features', [])
    
    def get_all_bot_ids(self) -> List[str]:
        """
        获取所有机器人ID
        
        Returns:
            机器人ID列表
        """
        with self._lock:
            return list(self._bots.keys())
    
    def reload_config(self):
        """重新加载配置文件（支持热重载）"""
        logger.info("重新加载机器人配置...")
        with self._lock:
            self._crypts.clear()  # 清空加解密器缓存
        self._load_config()
        logger.info("机器人配置重新加载完成")


# 全局机器人管理器实例
bot_manager = BotManager()

