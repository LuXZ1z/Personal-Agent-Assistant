"""
菜单处理器
处理主菜单显示和业务选择
使用统一的菜单配置，与CLI保持一致
"""
from typing import Dict, Any
from shared.utils import setup_logger
from shared.menu_config import (
    get_business_by_id,
    get_all_businesses,
    generate_menu_text,
    is_business_choice as check_business_choice
)

logger = setup_logger(__name__)


class MenuHandler:
    """菜单处理器"""
    
    @staticmethod
    def show_menu(user_id: str = None) -> Dict[str, Any]:
        """
        显示主菜单
        使用统一的菜单配置，与CLI保持一致
        
        Args:
            user_id: 用户ID（可选）
        
        Returns:
            包含菜单文本的字典
        """
        menu_text = generate_menu_text(user_id=user_id, include_status=True)
        
        return {
            "type": "menu",
            "message": menu_text,
            "action": "show_menu"
        }
    
    @staticmethod
    def select_business(choice: str) -> Dict[str, Any]:
        """
        处理业务选择
        使用统一的菜单配置，与CLI保持一致
        
        Args:
            choice: 用户选择的数字（"1", "2", "3", "4"等）
        
        Returns:
            包含业务类型和提示信息的字典
        """
        # 检查是否为"查看系统状态"
        if choice == "5":
            return {
                "type": "show_status",
                "message": "✓ 正在查看系统状态..."
            }
        
        # 从统一配置获取业务信息
        business_info = get_business_by_id(choice)
        
        if not business_info:
            max_choice = len(get_all_businesses())
            return {
                "type": "error",
                "message": f"无效选择：{choice}，请输入 1-{max_choice} 之间的数字"
            }
        
        return {
            "type": "business_selected",
            "business_type": business_info["business_type"],
            "business_name": business_info["display_name"],
            "message": f"✓ 正在进入{business_info['display_name']}..."
        }
    
    @staticmethod
    def is_menu_command(content: str) -> bool:
        """
        判断是否为菜单命令
        
        Args:
            content: 消息内容
        
        Returns:
            是否为菜单命令
        """
        menu_commands = ["菜单", "menu", "返回", "back", "主菜单", "帮助", "help"]
        return content.strip().lower() in [cmd.lower() for cmd in menu_commands]
    
    @staticmethod
    def is_business_choice(content: str) -> bool:
        """
        判断是否为业务选择
        使用统一的菜单配置，与CLI保持一致
        
        Args:
            content: 消息内容
        
        Returns:
            是否为业务选择
        """
        return check_business_choice(content, include_status=True)

