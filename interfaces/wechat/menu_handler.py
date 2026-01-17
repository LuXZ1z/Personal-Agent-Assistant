"""
菜单处理器
处理主菜单显示和业务选择
使用统一的菜单配置，与CLI保持一致
"""
from typing import Dict, Any
from shared.utils import setup_logger
from typing import List, Optional
from shared.menu_config import (
    get_business_by_id,
    get_business_by_id_filtered,
    get_all_businesses,
    generate_menu_text,
    is_business_choice as check_business_choice
)

logger = setup_logger(__name__)


class MenuHandler:
    """菜单处理器"""
    
    @staticmethod
    def show_menu(
        user_id: str = None,
        allowed_features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        显示主菜单
        使用统一的菜单配置，与CLI保持一致
        
        Args:
            user_id: 用户ID（可选）
            allowed_features: 允许的功能列表（可选），如果提供则只显示这些功能
        
        Returns:
            包含菜单文本的字典
        """
        menu_text = generate_menu_text(
            user_id=user_id, 
            include_status=True,
            allowed_features=allowed_features
        )
        
        return {
            "type": "menu",
            "message": menu_text,
            "action": "show_menu"
        }
    
    @staticmethod
    def select_business(
        choice: str,
        allowed_features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        处理业务选择
        使用统一的菜单配置，与CLI保持一致
        
        Args:
            choice: 用户选择的数字（"1", "2", "3"等）
            allowed_features: 允许的功能列表（可选），如果提供则使用过滤后的编号
        
        Returns:
            包含业务类型和提示信息的字典
        """
        businesses = get_all_businesses()
        if allowed_features:
            businesses = [
                b for b in businesses 
                if b['business_type'] in allowed_features
            ]
        
        # 计算"查看系统状态"的编号
        status_num = len(businesses) + 1
        
        # 检查是否为"查看系统状态"
        if choice == str(status_num):
            return {
                "type": "show_status",
                "message": "✓ 正在查看系统状态..."
            }
        
        # 从统一配置获取业务信息（使用过滤后的编号）
        if allowed_features:
            business_info = get_business_by_id_filtered(choice, allowed_features)
        else:
            business_info = get_business_by_id(choice)
        
        if not business_info:
            max_choice = len(businesses) + 1
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
    def is_business_choice(
        content: str,
        allowed_features: Optional[List[str]] = None
    ) -> bool:
        """
        判断是否为业务选择
        使用统一的菜单配置，与CLI保持一致
        
        Args:
            content: 消息内容
            allowed_features: 允许的功能列表（可选），如果提供则根据过滤后的数量判断
        
        Returns:
            是否为业务选择
        """
        return check_business_choice(
            content, 
            include_status=True,
            allowed_features=allowed_features
        )

