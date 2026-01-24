"""
模板卡片构建器
根据企业微信模板卡片API构建美观的菜单卡片
参考文档：https://developer.work.weixin.qq.com/document/path/101032
"""
from typing import Dict, Any, List, Optional
from shared.menu_config import get_all_businesses, BUSINESS_CONFIG


def build_main_menu_card(
    user_id: Optional[str] = None,
    allowed_features: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    构建主菜单模板卡片（text_notice类型）
    
    Args:
        user_id: 用户ID（可选）
        allowed_features: 允许的功能列表（可选）
        
    Returns:
        模板卡片字典
    """
    # 业务emoji映射
    business_emojis = {
        "accounting": "💰",
        "essay": "📝",
        "employee": "👥",
        "tarot": "🔮"
    }
    
    # 获取业务列表
    businesses = get_all_businesses()
    if allowed_features:
        businesses = [
            b for b in businesses 
            if b['business_type'] in allowed_features
        ]
    
    # 动态重新编号
    for idx, business in enumerate(businesses, start=1):
        business['id'] = str(idx)
    
    # 构建horizontal_content_list（业务选项）
    horizontal_content_list = []
    for business in businesses:
        emoji = business_emojis.get(business['business_type'], "📌")
        horizontal_content_list.append({
            "keyname": business['id'],
            "value": f"{emoji} {business['display_name']}",
            "type": 0  # 普通文本
        })
    
    # 添加"查看系统状态"选项
    status_num = len(businesses) + 1
    horizontal_content_list.append({
        "keyname": str(status_num),
        "value": "📊 查看系统状态",
        "type": 0
    })
    
    # 添加"退出"选项
    horizontal_content_list.append({
        "keyname": "0",
        "value": "🚪 退出",
        "type": 0
    })
    
    # 构建主标题
    main_title = {
        "title": "个人助手系统",
        "desc": "请选择业务功能" + (f"（用户：{user_id}）" if user_id else "")
    }
    
    # 构建模板卡片
    # 注意：text_notice类型的card_action.type必须是1或2，不能是0
    # 我们使用type=1（跳转URL），提供一个占位符URL
    card = {
        "card_type": "text_notice",
        "main_title": main_title,
        "sub_title_text": "💡 请输入数字选择对应功能",
        "horizontal_content_list": horizontal_content_list,
        "card_action": {
            "type": 1,  # 跳转URL（必填，text_notice类型只能是1或2）
            "url": "https://work.weixin.qq.com/"  # 占位符URL，实际不会跳转（用户通过输入数字选择）
        }
    }
    
    return card


def build_sub_menu_card(
    business_type: str,
    menu_text: str,
    table_name: Optional[str] = None,
    page: int = 1
) -> Dict[str, Any]:
    """
    构建子菜单模板卡片（text_notice类型）
    
    Args:
        business_type: 业务类型（accounting, essay, employee, tarot）
        menu_text: 子菜单文本内容（用于解析选项）
        table_name: 当前表/目录名称（可选）
        page: 页码（1=第一页，2=第二页）
        
    Returns:
        模板卡片字典
    """
    # 业务名称映射
    business_names = {
        "accounting": "记账管理",
        "essay": "随笔管理",
        "employee": "员工管理",
        "tarot": "塔罗牌占卜"
    }
    
    business_name = business_names.get(business_type, "业务管理")
    
    # 解析菜单文本，提取选项
    lines = menu_text.strip().split('\n')
    horizontal_content_list = []
    
    # 查找"请选择操作："之后的行
    in_options = False
    for line in lines:
        line = line.strip()
        if "请选择操作" in line or "请选择" in line:
            in_options = True
            continue
        if in_options and line and (line.startswith(('0.', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.'))):
            # 提取选项编号和内容
            parts = line.split('.', 1)
            if len(parts) == 2:
                option_num = parts[0].strip()
                option_text = parts[1].strip()
                # 如果是退出选项（0），改为"返回主菜单"
                if option_num == "0" and ("退出" in option_text or "🚪" in option_text):
                    option_text = "返回主菜单"
                horizontal_content_list.append({
                    "keyname": option_num,
                    "value": option_text,
                    "type": 0
                })
    
    # 如果解析失败，使用默认选项
    if not horizontal_content_list:
        # 根据业务类型提供默认选项
        # 注意：horizontal_content_list最多只能有6个选项
        default_options = {
            "accounting": [
                {"keyname": "1", "value": "添加记账", "type": 0},
                {"keyname": "2", "value": "查询记账", "type": 0},
                {"keyname": "3", "value": "修改记账", "type": 0},
                {"keyname": "4", "value": "删除记账", "type": 0},
                {"keyname": "5", "value": "切换表/目录", "type": 0},
                {"keyname": "0", "value": "返回主菜单", "type": 0}
            ],
            "essay": [
                {"keyname": "1", "value": "添加随笔", "type": 0},
                {"keyname": "2", "value": "查询随笔", "type": 0},
                {"keyname": "3", "value": "修改随笔", "type": 0},
                {"keyname": "4", "value": "删除随笔", "type": 0},
                {"keyname": "5", "value": "切换表/目录", "type": 0},
                {"keyname": "6", "value": "查看所有表/目录", "type": 0},
                {"keyname": "0", "value": "返回主菜单", "type": 0}
            ],
            "employee": [
                {"keyname": "1", "value": "添加员工记录", "type": 0},
                {"keyname": "2", "value": "查询员工记录", "type": 0},
                {"keyname": "3", "value": "修改员工记录", "type": 0},
                {"keyname": "4", "value": "删除员工记录", "type": 0},
                {"keyname": "5", "value": "切换表/目录", "type": 0},
                {"keyname": "0", "value": "返回主菜单", "type": 0}
            ],
            "tarot": [
                {"keyname": "1", "value": "单张牌占卜", "type": 0},
                {"keyname": "2", "value": "三张牌占卜", "type": 0},
                {"keyname": "3", "value": "五张牌占卜", "type": 0},
                {"keyname": "4", "value": "塔罗知识", "type": 0},
                {"keyname": "0", "value": "返回主菜单", "type": 0}
            ]
        }
        horizontal_content_list = default_options.get(business_type, [])
    
    # 分离退出选项和其他选项
    exit_option = None
    other_options = []
    for item in horizontal_content_list:
        if item.get("keyname") == "0":
            exit_option = item
        else:
            other_options.append(item)
    
    # 限制horizontal_content_list最多6个选项（企业微信API限制）
    # 实现翻页功能：当选项超过6个时，第一页显示前5个+更多选项，第二页显示剩余选项
    total_options_count = len(other_options)
    has_more_options = total_options_count > 5
    
    if page == 1:
        # 第一页：显示前5个选项 + "更多选项" + "返回主菜单"
        if has_more_options:
            horizontal_content_list = other_options[:5]
            # 添加"更多选项"按钮（使用特殊key "99"）
            horizontal_content_list.append({
                "keyname": "99",
                "value": "📄 更多选项",
                "type": 0
            })
        else:
            # 如果选项不超过5个，直接显示所有选项
            horizontal_content_list = other_options[:6]
        
        # 添加返回主菜单选项
        if exit_option:
            horizontal_content_list.append(exit_option)
    else:
        # 第二页：显示剩余选项 + "返回上一页" + "返回主菜单"
        if has_more_options:
            remaining_options = other_options[5:]
            horizontal_content_list = remaining_options[:5]  # 最多再显示5个
            # 添加"返回上一页"按钮（使用特殊key "98"）
            horizontal_content_list.append({
                "keyname": "98",
                "value": "⬅️ 返回上一页",
                "type": 0
            })
        else:
            horizontal_content_list = other_options[:6]
        
        # 添加返回主菜单选项
        if exit_option:
            horizontal_content_list.append(exit_option)
    
    # 构建主标题
    title_desc = business_name
    if table_name:
        title_desc += f"（当前表/目录：{table_name}）"
    if page == 2:
        title_desc += " - 第2页"
    
    main_title = {
        "title": business_name + "系统",
        "desc": title_desc
    }
    
    # 构建副标题文本
    if page == 1:
        sub_title = "💡 请输入数字选择对应操作"
    else:
        sub_title = "💡 请输入数字选择对应操作（第2页）"
    
    # 构建模板卡片
    # 注意：text_notice类型的card_action.type必须是1或2，不能是0
    # 我们使用type=1（跳转URL），提供一个占位符URL
    card = {
        "card_type": "text_notice",
        "main_title": main_title,
        "sub_title_text": sub_title,
        "horizontal_content_list": horizontal_content_list,
        "card_action": {
            "type": 1,  # 跳转URL（必填，text_notice类型只能是1或2）
            "url": "https://work.weixin.qq.com/"  # 占位符URL，实际不会跳转（用户通过输入数字选择）
        }
    }
    
    return card
