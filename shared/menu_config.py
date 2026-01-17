"""
统一的菜单配置
让 CLI 和微信服务器共享同一个菜单配置，避免重复开发
"""
from typing import Dict, Any, List, Optional

# 业务配置：定义所有可用的业务
# Service层调用Manager层的业务逻辑，Manager层使用core的基础能力
BUSINESS_CONFIG = {
    "accounting": {
        "id": "1",
        "name": "记账管理",
        "manager_class": "business.accounting.manager.AccountingManager",
        "service_class": "business.accounting.service.AccountingService",
        "display_name": "记账管理"
    },
    "essay": {
        "id": "2",
        "name": "随笔管理",
        "manager_class": "business.essay.manager.EssayManager",
        "service_class": "business.essay.service.EssayService",
        "display_name": "随笔管理"
    },
    "employee": {
        "id": "3",
        "name": "员工管理",
        "manager_class": "business.employee.manager.EmployeeManager",
        "service_class": "business.employee.service.EmployeeService",
        "display_name": "员工管理"
    },
    "tarot": {
        "id": "4",
        "name": "塔罗牌占卜",
        "manager_class": "business.tarot.manager.TarotManager",
        "service_class": "business.tarot.service.TarotService",
        "display_name": "塔罗牌占卜"
    }
}

# 菜单选项顺序
MENU_ORDER = ["accounting", "essay", "employee", "tarot"]


def get_business_by_id(choice_id: str) -> Optional[Dict[str, Any]]:
    """
    根据选择ID获取业务配置
    
    Args:
        choice_id: 用户选择的数字（"1", "2", "3", "4"）
        
    Returns:
        业务配置字典，如果不存在则返回None
    """
    for business_type, config in BUSINESS_CONFIG.items():
        if config["id"] == choice_id:
            return {
                "business_type": business_type,
                **config
            }
    return None


def get_all_businesses() -> List[Dict[str, Any]]:
    """
    获取所有业务配置（按菜单顺序）
    
    Returns:
        业务配置列表
    """
    return [
        {
            "business_type": business_type,
            **BUSINESS_CONFIG[business_type]
        }
        for business_type in MENU_ORDER
        if business_type in BUSINESS_CONFIG
    ]


def generate_menu_text(
    user_id: Optional[str] = None, 
    include_status: bool = True,
    allowed_features: Optional[List[str]] = None
) -> str:
    """
    生成菜单文本，支持根据机器人功能过滤
    
    Args:
        user_id: 用户ID（可选）
        include_status: 是否包含"查看系统状态"选项
        allowed_features: 允许的功能列表（可选），如果提供则只显示这些功能
        
    Returns:
        菜单文本
    """
    user_info = f"\n当前用户: {user_id}\n" if user_id else "\n"
    
    menu_lines = ["请选择业务："]
    businesses = get_all_businesses()
    
    # 根据允许的功能过滤
    if allowed_features:
        businesses = [
            b for b in businesses 
            if b['business_type'] in allowed_features
        ]
    
    # 动态重新编号（重要！）
    for idx, business in enumerate(businesses, start=1):
        business['id'] = str(idx)
    
    for business in businesses:
        menu_lines.append(f"  {business['id']}. {business['display_name']}")
    
    status_num = len(businesses) + 1
    if include_status:
        menu_lines.append(f"  {status_num}. 查看系统状态")
    
    menu_lines.append("  0. 退出")
    
    max_choice = len(businesses) + (1 if include_status else 0)
    menu_text = f"""============================================================
本地业务集成功能测试
============================================================{user_info}
{chr(10).join(menu_lines)}
============================================================

请输入数字选择（0-{max_choice}）"""
    
    return menu_text


def is_business_choice(
    content: str, 
    include_status: bool = True,
    allowed_features: Optional[List[str]] = None
) -> bool:
    """
    判断是否为业务选择
    
    Args:
        content: 消息内容
        include_status: 是否包含"查看系统状态"选项
        allowed_features: 允许的功能列表（可选），如果提供则根据过滤后的数量判断
        
    Returns:
        是否为业务选择
    """
    if allowed_features:
        # 使用过滤后的业务数量
        businesses = [
            b for b in get_all_businesses()
            if b['business_type'] in allowed_features
        ]
        max_choice = len(businesses) + (1 if include_status else 0)
    else:
        # 使用全部业务数量
        max_choice = len(MENU_ORDER) + (1 if include_status else 0)
    
    return content.strip() in [str(i) for i in range(1, max_choice + 1)]


def get_business_by_id_filtered(
    choice_id: str, 
    allowed_features: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    根据选择ID获取业务配置（支持过滤）
    当有功能过滤时，需要重新编号
    
    Args:
        choice_id: 用户选择的数字（"1", "2", "3"等）
        allowed_features: 允许的功能列表（可选）
        
    Returns:
        业务配置字典，如果不存在则返回None
    """
    businesses = get_all_businesses()
    
    # 根据允许的功能过滤
    if allowed_features:
        businesses = [
            b for b in businesses 
            if b['business_type'] in allowed_features
        ]
    
    # 重新编号并查找
    for idx, business in enumerate(businesses, start=1):
        if str(idx) == choice_id:
            return {
                "business_type": business['business_type'],
                **business
            }
    
    return None

