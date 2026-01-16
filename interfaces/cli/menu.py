"""
CLI菜单管理
"""
from typing import Dict, Any
from shared.utils import setup_logger

logger = setup_logger(__name__)


class MenuHandler:
    """菜单处理器"""
    
    @staticmethod
    def show_menu(user_id: str = None) -> Dict[str, Any]:
        """
        显示主菜单
        
        Args:
            user_id: 用户ID（可选）
        
        Returns:
            包含菜单文本的字典
        """
        user_info = f"\n当前用户: {user_id}\n" if user_id else "\n"
        menu_text = f"""============================================================
本地业务集成功能测试
============================================================{user_info}
请选择业务：
  1. 记账管理
  2. 随笔管理
  3. 员工管理
  4. 塔罗牌占卜
  5. 查看系统状态
  0. 退出
============================================================

请输入数字选择（0-5）"""
        
        return {
            "type": "menu",
            "message": menu_text,
            "action": "show_menu"
        }
    
    @staticmethod
    def is_menu_command(content: str) -> bool:
        """判断是否为菜单命令"""
        menu_commands = ["菜单", "menu", "返回", "back", "主菜单", "帮助", "help"]
        return content.strip().lower() in [cmd.lower() for cmd in menu_commands]
    
    @staticmethod
    def is_business_choice(content: str) -> bool:
        """判断是否为业务选择（数字1-5）"""
        return content.strip() in ["1", "2", "3", "4", "5"]

