"""
消息路由器
根据用户消息和会话状态，路由到对应的业务处理器
"""
from typing import Dict, Any, Optional, List
from shared.utils import setup_logger
from interfaces.wechat.session_manager import session_manager
from interfaces.wechat.task_manager import task_manager
from interfaces.wechat.menu_handler import MenuHandler
from interfaces.wechat.bot_manager import bot_manager
# 动态导入业务服务，使用统一配置
from shared.menu_config import BUSINESS_CONFIG
import importlib

logger = setup_logger(__name__)


class MessageRouter:
    """消息路由器"""
    
    def __init__(self):
        """初始化路由器"""
        self.menu_handler = MenuHandler()
    
    def route_message(self, bot_id: str, user_id: str, content: str) -> Dict[str, Any]:
        """
        路由消息到对应的业务处理器
        
        Args:
            bot_id: 机器人ID
            user_id: 用户ID
            content: 消息内容
            
        Returns:
            处理结果字典
        """
        if not bot_id or not user_id or not content:
            return {
                "type": "error",
                "message": "机器人ID、用户ID或消息内容不能为空"
            }
        
        # 获取机器人的功能列表
        try:
            allowed_features = bot_manager.get_features(bot_id)
        except ValueError as e:
            logger.error(f"获取机器人功能失败: {e}")
            allowed_features = None  # 默认全功能
        
        # 检查是否有正在处理的任务
        task = task_manager.get_task(bot_id, user_id)
        if task and task.status == "processing":
            # 检查是否为取消命令
            if content.strip() in ["取消", "cancel", "停止", "stop"]:
                cancelled = task_manager.cancel_task(bot_id, user_id)
                if cancelled:
                    return {
                        "type": "info",
                        "message": f"✅ 已取消正在处理的任务\n\n任务类型: {task.task_type}\n已处理时间: {task.get_elapsed_time():.1f}秒\n\n发送\"菜单\"返回主菜单"
                    }
                else:
                    return {
                        "type": "info",
                        "message": "没有正在处理的任务"
                    }
            else:
                # 有任务正在处理，提示用户
                elapsed = task.get_elapsed_time()
                return {
                    "type": "info",
                    "message": f"⏳ 正在处理中...\n\n任务类型: {task.task_type}\n已处理时间: {elapsed:.1f}秒\n\n如需取消，请发送\"取消\""
                }
        
        # 获取会话状态
        session = session_manager.get_session(bot_id, user_id)
        business_type = session.business_type
        
        logger.debug(f"路由消息: bot_id={bot_id}, user_id={user_id}, business_type={business_type}, content={content[:50]}")
        
        # 1. 检查是否为菜单命令（优先级最高）
        if self.menu_handler.is_menu_command(content):
            # 如果用户有正在处理的任务，先取消
            if task and task.status == "processing":
                task_manager.cancel_task(bot_id, user_id)
            session_manager.reset_to_menu(bot_id, user_id)
            return self.menu_handler.show_menu(user_id, allowed_features=allowed_features)
        
        # 2. 如果在菜单状态，检查是否为业务选择
        if business_type == "menu":
            if content.strip() == "0":
                return {
                    "type": "info",
                    "message": "退出系统\n\n感谢使用！"
                }
            elif self.menu_handler.is_business_choice(content, allowed_features=allowed_features):
                result = self.menu_handler.select_business(content, allowed_features=allowed_features)
                if result["type"] == "show_status":
                    # 查看系统状态
                    return self._show_system_status(bot_id, user_id)
                elif result["type"] == "business_selected":
                    # 更新会话状态
                    session_manager.update_business_type(
                        bot_id,
                        user_id,
                        result["business_type"]
                    )
                    # 进入业务后，先显示进入提示，然后显示子菜单
                    business_name = result.get("business_name", "")
                    enter_message = f"""============================================================
进入{business_name}系统
============================================================

"""
                    # 获取子菜单
                    service = self._get_business_service(user_id, result["business_type"])
                    if service:
                        sub_menu_result = service.process_message("", session.context)
                        # 合并消息
                        enter_message += sub_menu_result.get("message", "")
                        return {
                            "type": sub_menu_result.get("type", "sub_menu"),
                            "message": enter_message
                        }
                return result
            else:
                # 在菜单状态但输入不是数字，显示菜单
                logger.info(f"用户在菜单状态但输入了非数字内容，显示菜单")
                return self.menu_handler.show_menu(user_id, allowed_features=allowed_features)
        
        # 3. 路由到对应的业务服务
        try:
            service = self._get_business_service(user_id, business_type)
            if service is None:
                return {
                    "type": "error",
                    "message": f"未知的业务类型: {business_type}"
                }
            
            # 处理业务消息
            result = service.process_message(content, session.context)
            return result
            
        except Exception as e:
            logger.error(f"路由消息失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"处理消息时发生错误: {str(e)}"
            }
    
    def _get_business_service(self, user_id: str, business_type: str):
        """
        获取业务服务实例（动态加载，使用统一配置）
        注意：Service层已经包装了Manager，并复用了Manager的核心业务逻辑
        这样可以确保wechat.server和cli.main使用相同的业务逻辑
        
        Args:
            user_id: 用户ID
            business_type: 业务类型
            
        Returns:
            业务服务实例
        """
        if business_type not in BUSINESS_CONFIG:
            return None
        
        try:
            # 从统一配置获取Service类路径
            service_class_path = BUSINESS_CONFIG[business_type]["service_class"]
            module_path, class_name = service_class_path.rsplit(".", 1)
            
            # 动态导入
            module = importlib.import_module(module_path)
            service_class = getattr(module, class_name)
            
            # 创建实例
            return service_class(user_id)
        except Exception as e:
            logger.error(f"加载业务服务失败: business_type={business_type}, error={e}", exc_info=True)
            return None
    
    def _get_business_manager(self, user_id: str, business_type: str):
        """
        获取业务Manager实例（动态加载，使用统一配置）
        用于独立测试业务逻辑
        
        Args:
            user_id: 用户ID
            business_type: 业务类型
            
        Returns:
            Manager实例
        """
        if business_type not in BUSINESS_CONFIG:
            return None
        
        try:
            # 从统一配置获取Manager类路径
            manager_class_path = BUSINESS_CONFIG[business_type]["manager_class"]
            module_path, class_name = manager_class_path.rsplit(".", 1)
            
            # 动态导入
            module = importlib.import_module(module_path)
            manager_class = getattr(module, class_name)
            
            # 创建实例
            return manager_class(user_id=user_id, debug=False)
        except Exception as e:
            logger.error(f"加载业务Manager失败: business_type={business_type}, error={e}", exc_info=True)
            return None
    
    def _show_system_status(self, bot_id: str, user_id: str) -> Dict[str, Any]:
        """显示系统状态"""
        from core.database import get_database_manager
        
        try:
            db = get_database_manager(user_id=user_id)
            stats = db.get_statistics(user_id=user_id)
            
            message = "系统状态\n"
            message += "-" * 60 + "\n\n"
            message += "数据库连接: ✓ 正常\n\n"
            message += "各业务记录统计:\n"
            message += "-" * 60 + "\n"
            
            by_type = stats.get('by_type', {})
            business_types = ["记账", "随笔", "员工", "塔罗牌"]
            for business_type in business_types:
                count = by_type.get(business_type, 0)
                message += f"  {business_type}: {count} 条记录\n"
            
            # 统计总记录数
            total_count = stats.get('total_count', 0)
            message += f"\n  总计: {total_count} 条记录\n"
            
            # 统计表/目录数量
            by_table = stats.get('by_table', {})
            table_count = len(by_table)
            message += f"  表/目录数: {table_count} 个\n"
            
            message += "-" * 60 + "\n\n"
            message += "发送\"菜单\"返回主菜单"
            
            return {
                "type": "info",
                "message": message
            }
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"获取系统状态失败: {str(e)}"
            }


# 全局消息路由器实例
message_router = MessageRouter()

