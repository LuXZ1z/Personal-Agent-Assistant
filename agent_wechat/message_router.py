"""
消息路由器
根据用户消息和会话状态，路由到对应的业务处理器
"""
from typing import Dict, Any, Optional
from shared.utils import setup_logger
from agent_wechat.session_manager import session_manager
from agent_wechat.task_manager import task_manager
from business_services.menu_handler import MenuHandler
from business_services.essay_service import EssayService
from business_services.accounting_service import AccountingService
from business_services.employee_service import EmployeeService
from business_services.tarot_service import TarotService

logger = setup_logger(__name__)


class MessageRouter:
    """消息路由器"""
    
    def __init__(self):
        """初始化路由器"""
        self.menu_handler = MenuHandler()
    
    def route_message(self, user_id: str, content: str) -> Dict[str, Any]:
        """
        路由消息到对应的业务处理器
        
        Args:
            user_id: 用户ID
            content: 消息内容
            
        Returns:
            处理结果字典
        """
        if not user_id or not content:
            return {
                "type": "error",
                "message": "用户ID或消息内容不能为空"
            }
        
        # 检查是否有正在处理的任务
        task = task_manager.get_task(user_id)
        if task and task.status == "processing":
            # 检查是否为取消命令
            if content.strip() in ["取消", "cancel", "停止", "stop"]:
                cancelled = task_manager.cancel_task(user_id)
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
        session = session_manager.get_session(user_id)
        business_type = session.business_type
        
        logger.debug(f"路由消息: user_id={user_id}, business_type={business_type}, content={content[:50]}")
        
        # 1. 检查是否为菜单命令（优先级最高）
        if self.menu_handler.is_menu_command(content):
            # 如果用户有正在处理的任务，先取消
            if task and task.status == "processing":
                task_manager.cancel_task(user_id)
            session_manager.reset_to_menu(user_id)
            return self.menu_handler.show_menu(user_id)
        
        # 2. 如果在菜单状态，检查是否为业务选择
        if business_type == "menu":
            if content.strip() == "0":
                return {
                    "type": "info",
                    "message": "退出系统\n\n感谢使用！"
                }
            elif content.strip() == "5":
                # 查看系统状态
                return self._show_system_status(user_id)
            elif self.menu_handler.is_business_choice(content):
                result = self.menu_handler.select_business(content)
                if result["type"] == "business_selected":
                    # 更新会话状态
                    session_manager.update_business_type(
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
                return self.menu_handler.show_menu()
        
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
        获取业务服务实例
        
        Args:
            user_id: 用户ID
            business_type: 业务类型
            
        Returns:
            业务服务实例
        """
        if business_type == "essay":
            return EssayService(user_id)
        elif business_type == "accounting":
            return AccountingService(user_id)
        elif business_type == "employee":
            return EmployeeService(user_id)
        elif business_type == "tarot":
            return TarotService(user_id)
        else:
            return None
    
    def _show_system_status(self, user_id: str) -> Dict[str, Any]:
        """显示系统状态"""
        from shared.models import StructuredRecord
        from shared.user_database_manager import user_db_manager
        from sqlalchemy import func
        
        try:
            db = user_db_manager.get_user_db(user_id)
            session = db.get_session()
            try:
                message = "系统状态\n"
                message += "-" * 60 + "\n\n"
                message += "数据库连接: ✓ 正常\n\n"
                message += "各业务记录统计:\n"
                message += "-" * 60 + "\n"
                
                business_types = ["记账", "随笔", "员工", "塔罗牌"]
                for business_type in business_types:
                    count = session.query(func.count(StructuredRecord.id)).filter(
                        StructuredRecord.record_type == business_type
                    ).scalar()
                    message += f"  {business_type}: {count} 条记录\n"
                
                # 统计总记录数
                total_count = session.query(func.count(StructuredRecord.id)).scalar()
                message += f"\n  总计: {total_count} 条记录\n"
                
                # 统计表/目录数量
                table_count = session.query(func.count(func.distinct(StructuredRecord.table_name))).filter(
                    StructuredRecord.table_name.isnot(None)
                ).scalar()
                message += f"  表/目录数: {table_count} 个\n"
                
                message += "-" * 60 + "\n\n"
                message += "发送\"菜单\"返回主菜单"
                
                return {
                    "type": "info",
                    "message": message
                }
            finally:
                session.close()
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"获取系统状态失败: {str(e)}"
            }


# 全局消息路由器实例
message_router = MessageRouter()

