"""
员工服务 - 微信平台适配器
调用 EmployeeManager 的业务逻辑，适配微信消息驱动模式
"""
from typing import Dict, Any
from datetime import datetime

from business.employee.manager import EmployeeManager
from business.employee.prompts import EMPLOYEE_PROMPT_TEMPLATE
from shared.utils import setup_logger

from interfaces.wechat.session_manager import session_manager

logger = setup_logger(__name__)


class EmployeeService:
    """员工服务 - 微信适配器，调用 Manager 的业务逻辑"""
    
    def __init__(self, user_id: str, bot_id: str = "default"):
        self.user_id = user_id
        self.bot_id = bot_id
        # 使用 Manager 层，Manager 使用 core 的基础能力
        self.manager = EmployeeManager(user_id=user_id, debug=False)
    
    def show_sub_menu(self) -> Dict[str, Any]:
        """显示员工管理子菜单"""
        session = session_manager.get_session(self.bot_id, self.user_id)
        table_name = session.table_name or self.manager.table_name
        
        menu_text = f"""👥 员工工作情况管理系统 👥

📁 当前表/目录: {table_name}

✨ 请选择操作：
  1. ➕ 添加员工工作记录
  2. 🔍 查询员工记录
  3. ✏️ 修改员工记录
  4. 🗑️ 删除员工记录
  5. 🔄 切换表/目录
  6. 📋 查看所有表/目录
  7. 📊 统计分析
  0. 🚪 退出

💡 请输入数字选择（0-7）"""
        
        return {
            "type": "sub_menu",
            "message": menu_text,
            "action": "show_sub_menu"
        }
    
    def process_message(self, content: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理员工消息"""
        session = session_manager.get_session(self.bot_id, self.user_id)
        sub_menu = session.sub_menu
        
        if sub_menu is None:
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        if sub_menu == "main":
            choice = content.strip()
            if choice == "0":
                session_manager.reset_to_menu(self.bot_id, self.user_id)
                try:
                    from interfaces.wechat.menu_handler import MenuHandler
                except ImportError:
                    from interfaces.cli.menu import MenuHandler
                return MenuHandler.show_menu()
            elif choice == "1":
                session_manager.set_sub_menu(self.bot_id, self.user_id, "add")
                return {
                    "type": "prompt",
                    "message": "✓ 已进入添加员工工作记录模式\n\n请直接发送员工工作信息（自然语言）\n\n发送\"0\"可返回子菜单"
                }
            # 其他选项简化处理
            else:
                return {
                    "type": "info",
                    "message": "功能开发中，请选择 1 添加记录\n\n发送\"0\"返回子菜单"
                }
        
        elif sub_menu == "add":
            if content.strip() == "0":
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return self.show_sub_menu()
            
            try:
                current_date = datetime.now().strftime("%Y-%m-%d")
                prompt_template_with_date = EMPLOYEE_PROMPT_TEMPLATE.replace("{current_date}", current_date)
                
                structured_data = self.manager.llm_client.structure_text(
                    text=content,
                    prompt_template=prompt_template_with_date
                )
                
                record = self.manager.db.create_record(
                    original_text=content,
                    structured_data=structured_data,
                    record_type=structured_data.get('type', '员工'),
                    table_name=self.manager.table_name,
                    metadata=None,
                    user_id=self.user_id
                )
                
                fields = structured_data.get('fields', {})
                message = f"✓ 员工工作记录保存成功！\n\n"
                message += f"👤 员工: {fields.get('name', '')}\n"
                message += f"📋 任务: {fields.get('task', '')}\n"
                message += f"📊 状态: {fields.get('status', '')}\n"
                message += f"🆔 记录ID: {record.id}\n\n"
                message += f"发送\"0\"返回子菜单"
                
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return {
                    "type": "success",
                    "message": message
                }
            except Exception as e:
                logger.error(f"处理员工消息失败: {e}", exc_info=True)
                return {
                    "type": "error",
                    "message": f"处理失败: {str(e)}"
                }
        
        return {
            "type": "error",
            "message": f"未知的子菜单状态: {sub_menu}"
        }
