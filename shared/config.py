"""
配置管理模块
使用pydantic-settings管理环境变量配置
"""
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# 加载.env文件
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Settings(BaseSettings):
    """应用配置类"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # 微信配置
    wechat_token: str = ""
    wechat_encoding_aes_key: str = ""
    
    # OpenAI配置
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    
    # Redis配置
    redis_url: str = "redis://localhost:6379/0"
    
    # 数据库配置
    database_path: str = "./data/assistant.db"
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # 服务器配置
    server_host: str = "0.0.0.0"
    server_port: int = 80
    server_workers: int = 1  # 生产环境建议设置为CPU核心数
    
    def __init__(self, **kwargs):
        """初始化配置，确保目录存在"""
        super().__init__(**kwargs)
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
        if not self.wechat_token:
            raise ValueError("WECHAT_TOKEN is required")
        if not self.wechat_encoding_aes_key:
            raise ValueError("WECHAT_ENCODING_AES_KEY is required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")


# 全局配置实例
settings = Settings()

