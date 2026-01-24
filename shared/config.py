"""
配置管理模块
从 system.yaml 文件读取配置，统一管理所有配置项
"""
import yaml
from pathlib import Path
from typing import Optional


def load_config_from_yaml(config_path: Optional[Path] = None) -> dict:
    """
    从 YAML 文件加载配置
    
    Args:
        config_path: 配置文件路径，如果为 None 则使用默认路径
        
    Returns:
        配置字典
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "system.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config or {}


class Settings:
    """应用配置类 - 从 YAML 文件读取配置"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径，如果为 None 则使用默认路径
        """
        # 加载 YAML 配置
        config = load_config_from_yaml(config_path)
        
        # OpenAI配置
        openai_config = config.get("openai", {})
        self.openai_api_key: str = openai_config.get("api_key", "")
        self.openai_base_url: str = openai_config.get("base_url", "https://api.openai.com/v1")
        
        # Redis配置
        redis_config = config.get("redis", {})
        self.redis_url: str = redis_config.get("url", "redis://localhost:6379/0")
        
        # 数据库配置
        database_config = config.get("database", {})
        self.database_path: str = database_config.get("path", "./data/assistant.db")
        self.user_database_dir: str = database_config.get("user_database_dir", "./data/users")
        
        # 日志配置
        log_config = config.get("log", {})
        self.log_level: str = log_config.get("level", "INFO")
        self.log_file: Optional[str] = log_config.get("file")
        
        # 服务器配置
        server_config = config.get("server", {})
        self.server_host: str = server_config.get("host", "0.0.0.0")
        self.server_port: int = server_config.get("port", 80)
        self.server_workers: int = server_config.get("workers", 1)
        
        # 微信配置（已移除，实际使用时会从 bots.yaml 中读取各机器人的配置）
        self.wechat_token: str = ""
        self.wechat_encoding_aes_key: str = ""
        self.wechat_corp_id: str = ""
        self.wechat_corp_secret: str = ""
        self.wechat_agent_id: int = 0
        
        # 机器人配置路径（处理相对路径，转换为绝对路径）
        bot_config_path = config.get("bot_config_path", "./config/bots.yaml")
        if not Path(bot_config_path).is_absolute():
            # 如果是相对路径，基于项目根目录解析
            project_root = Path(__file__).parent.parent
            self.bot_config_path: str = str((project_root / bot_config_path).resolve())
        else:
            self.bot_config_path: str = bot_config_path
        
        # 确保数据库目录存在
        db_path = Path(self.database_path)
        if db_path.parent:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 确保日志目录存在
        if self.log_file:
            log_path = Path(self.log_file)
            if log_path.parent:
                log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> None:
        """验证必需的配置项"""
        # 注意：微信配置已从 system.yaml 移除，实际使用时会从 bots.yaml 中读取各机器人的配置
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")


# 全局配置实例
settings = Settings()

