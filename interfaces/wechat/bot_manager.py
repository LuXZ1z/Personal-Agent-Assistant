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
        # 注意：get_crypt() 内部会调用 get_bot_config()，两者都会尝试获取同一把锁；
        # 使用不可重入的 Lock 会导致死锁（表现为“只收到第一条消息，后续都收不到/不回复”）。
        self._lock = threading.RLock()
        
        # 加载配置
        try:
            self._load_config()
            logger.info(f"机器人管理器初始化成功，加载了 {len(self._bots)} 个机器人")
            if len(self._bots) == 0:
                logger.warning("⚠ 警告: 没有加载到任何机器人配置，请检查 config/bots.yaml 文件")
        except Exception as e:
            logger.error(f"机器人管理器初始化失败: {e}", exc_info=True)
            raise
    
    def _load_config(self):
        """加载机器人配置"""
        # 使用 settings.bot_config_path（已经是绝对路径）
        # 如果 settings.bot_config_path 是字符串，转换为 Path
        config_path = Path(settings.bot_config_path)
        
        # 如果仍然是相对路径（虽然不应该），基于项目根目录解析
        if not config_path.is_absolute():
            project_root = Path(__file__).parent.parent.parent
            config_path = (project_root / config_path).resolve()
        
        logger.info(f"加载机器人配置文件: {config_path}")
        
        if not config_path.exists():
            logger.error(f"机器人配置文件不存在: {config_path}，使用空配置")
            logger.error(f"请检查配置文件路径是否正确")
            return
        
        try:
            # 使用与 minimal_test_server.py 完全相同的加载方式
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                logger.error(f"配置文件为空或格式错误: {config_path}")
                return
            
            bots_config = config_data.get('bots', {})
            if not bots_config:
                logger.warning(f"配置文件中没有找到 'bots' 配置项: {config_path}")
                return
            
            logger.info(f"从配置文件读取到 {len(bots_config)} 个机器人配置")
            
            with self._lock:
                self._bots = {}
                for bot_id, bot_config in bots_config.items():
                    if bot_config.get('enabled', True):
                        # 确保所有必需的字段都存在
                        required_fields = ['wechat_token', 'wechat_encoding_aes_key', 'wechat_corp_id']
                        missing_fields = [f for f in required_fields if f not in bot_config]
                        if missing_fields:
                            logger.error(f"机器人 {bot_id} 缺少必需字段: {missing_fields}")
                            continue
                        
                        self._bots[bot_id] = bot_config.copy()
                        logger.info(f"✓ 加载机器人: {bot_id} - {bot_config.get('name', '未知')} (receive_id='{bot_config.get('wechat_corp_id')}')")
                    else:
                        logger.debug(f"跳过禁用的机器人: {bot_id}")
            
            if len(self._bots) == 0:
                logger.error("没有加载到任何启用的机器人，请检查配置文件")
                
        except FileNotFoundError:
            logger.error(f"配置文件不存在: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"YAML解析失败: {e}")
            raise
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
    
    def get_all_bots(self) -> Dict[str, Dict]:
        """
        获取所有机器人配置（与 minimal_test_server.py 的 BOTS_CONFIG 格式一致）
        
        Returns:
            所有机器人配置字典
        """
        with self._lock:
            return self._bots.copy()
    
    def reload_config(self):
        """重新加载配置文件（支持热重载）"""
        logger.info("重新加载机器人配置...")
        with self._lock:
            self._crypts.clear()  # 清空加解密器缓存
        self._load_config()
        logger.info("机器人配置重新加载完成")


# 全局机器人管理器实例
bot_manager = BotManager()

