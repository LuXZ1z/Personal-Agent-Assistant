"""
记账服务 - 微信平台适配器
调用 AccountingManager 的业务逻辑，适配微信消息驱动模式
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json

from business.accounting.manager import AccountingManager
from business.accounting.prompts import ACCOUNTING_PROMPT_TEMPLATE, ACCOUNTING_SUMMARY_PROMPT
from shared.utils import setup_logger
from shared.message_utils import format_message
from datetime import timedelta

# 延迟导入，避免循环依赖
from interfaces.wechat.session_manager import session_manager

logger = setup_logger(__name__)


class AccountingService:
    """记账服务 - 微信适配器，调用 Manager 的业务逻辑"""
    
    def __init__(self, user_id: str, bot_id: str = "default"):
        """
        初始化记账服务
        
        Args:
            user_id: 用户ID
            bot_id: 机器人ID（可选，默认为"default"）
        """
        self.user_id = user_id
        self.bot_id = bot_id
        # 使用 Manager 层，Manager 使用 core 的基础能力
        self.manager = AccountingManager(user_id=user_id, debug=False)
    
    def show_sub_menu(self) -> Dict[str, Any]:
        """显示记账管理子菜单"""
        session = session_manager.get_session(self.bot_id, self.user_id)
        table_name = session.table_name or self.manager.table_name
        
        menu_text = f"""💰 记账管理系统 💰

📁 当前表/目录: {table_name}

✨ 请选择操作：
  1. ➕ 添加记账记录
  2. 🔍 查询记账记录
  3. ✏️ 修改记账记录
  4. 🗑️ 删除记账记录
  5. 🔄 切换表/目录
  6. 📋 查看所有表/目录
  7. 📊 查询并总结
  8. 📈 统计分析
  0. 🚪 退出

💡 请输入数字选择（0-8）"""
        
        return {
            "type": "sub_menu",
            "message": menu_text,
            "action": "show_sub_menu"
        }
    
    def process_message(self, content: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理记账消息
        
        Args:
            content: 用户输入
            session_context: 会话上下文
            
        Returns:
            处理结果字典
        """
        session = session_manager.get_session(self.bot_id, self.user_id)
        sub_menu = session.sub_menu
        
        # 如果没有子菜单状态，显示子菜单
        if sub_menu is None:
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        # 处理子菜单选择
        if sub_menu == "main":
            # 如果输入不是有效的数字选择（0-8），显示错误提示
            choice = content.strip()
            if choice and not choice.isdigit():
                return {
                    "type": "error",
                    "message": f"❌ 无效输入：{content}\n\n请输入数字选择（0-8），或发送\"0\"返回主菜单"
                }
            return self._handle_sub_menu_choice(content)
        elif sub_menu == "add":
            return self._handle_add(content)
        elif sub_menu == "query":
            return self._handle_query(content)
        elif sub_menu == "update":
            return self._handle_update(content)
        elif sub_menu == "delete":
            return self._handle_delete(content)
        elif sub_menu == "switch":
            return self._handle_switch_table(content)
        elif sub_menu == "list":
            return self._handle_list_tables()
        elif sub_menu == "summarize":
            return self._handle_summarize(content)
        elif sub_menu == "statistics":
            return self._handle_statistics()
        else:
            return {
                "type": "error",
                "message": f"未知的子菜单状态: {sub_menu}"
            }
    
    def _handle_sub_menu_choice(self, content: str) -> Dict[str, Any]:
        """处理子菜单选择"""
        choice = content.strip()
        
        if choice == "0":
            session_manager.reset_to_menu(self.bot_id, self.user_id)
            # 延迟导入避免循环依赖
            try:
                from interfaces.wechat.menu_handler import MenuHandler
                from interfaces.wechat.bot_manager import bot_manager
                # 获取机器人的功能列表，确保只显示允许的功能
                allowed_features = bot_manager.get_features(self.bot_id)
                return MenuHandler.show_menu(self.user_id, allowed_features=allowed_features)
            except ImportError:
                from interfaces.cli.menu import MenuHandler
                return MenuHandler.show_menu()
        elif choice == "1":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "add")
            return {
                "type": "prompt",
                "message": "✓ 已进入添加记账模式\n\n请直接发送记账信息（自然语言），例如：\n- 今天花了50元买了一杯咖啡\n- 在超市购物花费200元\n\n发送\"0\"可返回子菜单"
            }
        elif choice == "2":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "query")
            return self._show_query_menu()
        elif choice == "3":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "update")
            return {
                "type": "prompt",
                "message": "✓ 已进入修改记账模式\n\n请先发送要修改的记录ID，或发送\"0\"返回子菜单"
            }
        elif choice == "4":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "delete")
            return {
                "type": "prompt",
                "message": "✓ 已进入删除记账模式\n\n请先发送要删除的记录ID，或发送\"0\"返回子菜单"
            }
        elif choice == "5":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "switch")
            return {
                "type": "prompt",
                "message": "✓ 已进入切换表/目录模式\n\n请发送新的表/目录名称，或发送\"0\"返回子菜单"
            }
        elif choice == "6":
            return self._handle_list_tables()
        elif choice == "7":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "summarize")
            return self._show_summarize_menu()
        elif choice == "8":
            return self._handle_statistics()
        else:
            return {
                "type": "error",
                "message": f"无效选择：{choice}，请输入 0-8 之间的数字"
            }
    
    def _handle_add(self, content: str) -> Dict[str, Any]:
        """处理添加记账"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        if not content or not content.strip():
            return {
                "type": "error",
                "message": "记账信息不能为空"
            }
        
        try:
            # 获取当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")
            # 先格式化 current_date，保留 {text} 占位符供 structure_text 方法使用
            # 使用 format 方法，同时传入 current_date 和 text（text 会被 structure_text 再次替换，但这里先传入避免 KeyError）
            prompt_template_with_date = ACCOUNTING_PROMPT_TEMPLATE.format(current_date=current_date, text="{text}")
            
            # 调用LLM进行结构化
            structured_data = self.manager.llm_client.structure_text(
                text=content,
                prompt_template=prompt_template_with_date
            )
            
            # 保存到用户数据库
            record = self.manager.db.create_record(
                original_text=content,
                structured_data=structured_data,
                record_type=structured_data.get('type', '记账'),
                table_name=self.manager.table_name,
                metadata=None,
                user_id=self.user_id
            )
            
            # 构建成功消息
            fields = structured_data.get('fields', {})
            summary = structured_data.get('summary', '')
            amount = fields.get('amount', 0)
            category = fields.get('category', '未分类')
            date_str = fields.get('date', current_date)
            payment_method = fields.get('payment_method', '未指定')
            
            message = f"✓ 记账保存成功！\n\n"
            message += f"💰 金额: ¥{amount}\n"
            message += f"📂 类别: {category}\n"
            message += f"📅 日期: {date_str}\n"
            message += f"💳 支付方式: {payment_method}\n"
            message += f"📝 摘要: {summary}\n"
            message += f"🆔 记录ID: {record.id}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            # 重置到主菜单状态
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            
            return {
                "type": "success",
                "message": message,
                "data": {
                    "record_id": record.id,
                    "structured_data": structured_data
                }
            }
        
        except Exception as e:
            logger.error(f"处理记账消息失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"处理失败: {str(e)}"
            }
    
    def _show_query_menu(self) -> Dict[str, Any]:
        """显示查询菜单"""
        menu_text = """【查询记账记录】

请选择查询方式：
  1. 查询所有记录
  2. 按日期查询（单日）
  3. 按时间段查询（日期范围）
  4. 按类别查询
  5. 按金额范围查询
  6. 按关键词搜索
  0. 返回

请输入数字选择（0-6）"""
        
        session_manager.get_session(self.bot_id, self.user_id).context["query_mode"] = "menu"
        return {
            "type": "sub_menu",
            "message": menu_text
        }
    
    def _handle_query(self, content: str) -> Dict[str, Any]:
        """处理查询"""
        session = session_manager.get_session(self.bot_id, self.user_id)
        query_mode = session.context.get("query_mode", "menu")
        
        if content.strip() == "0":
            if query_mode == "menu":
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return self.show_sub_menu()
            else:
                session.context["query_mode"] = "menu"
                return self._show_query_menu()
        
        if query_mode == "menu":
            choice = content.strip()
            if choice == "1":
                return self._query_all()
            elif choice == "2":
                session.context["query_mode"] = "date"
                return {
                    "type": "prompt",
                    "message": "请输入日期 (YYYY-MM-DD)，或发送\"0\"返回"
                }
            elif choice == "4":
                session.context["query_mode"] = "category"
                return {
                    "type": "prompt",
                    "message": "请输入类别，或发送\"0\"返回"
                }
            elif choice == "6":
                session.context["query_mode"] = "keyword"
                return {
                    "type": "prompt",
                    "message": "请输入关键词，或发送\"0\"返回"
                }
            else:
                return {
                    "type": "error",
                    "message": f"查询方式 {choice} 暂未实现，请选择 1、2、4 或 6"
                }
        else:
            # 执行具体查询
            return self._execute_query(content, query_mode)
    
    def _query_all(self) -> Dict[str, Any]:
        """查询所有记录"""
        try:
            filters = {
                "record_type": "记账",
                "table_name": self.manager.table_name
            }
            records = self.manager.db.query_records(
                filters=filters,
                limit=20,
                order_by="-created_at",
                user_id=self.user_id
            )
            
            if not records:
                return {
                    "type": "info",
                    "message": "暂无记账记录\n\n发送\"0\"返回子菜单"
                }
            
            message = f"找到 {len(records)} 条记录：\n\n"
            for i, record in enumerate(records, 1):
                fields = record.structured_data.get('fields', {})
                amount = fields.get('amount', 0)
                category = fields.get('category', '未知')
                date_str = fields.get('date', '')
                summary = record.structured_data.get('summary', '')
                message += f"[{i}] ID: {record.id}\n"
                message += f"    金额: {amount}元 | 类别: {category} | 日期: {date_str}\n"
                message += f"    摘要: {summary}\n\n"
            
            message += "发送\"0\"返回子菜单"
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return {
                "type": "success",
                "message": message
            }
        except Exception as e:
            logger.error(f"查询失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"查询失败: {str(e)}"
            }
    
    def _execute_query(self, content: str, query_mode: str) -> Dict[str, Any]:
        """执行查询"""
        try:
            filters = {
                "record_type": "记账",
                "table_name": self.manager.table_name
            }
            
            if query_mode == "date":
                try:
                    filters["date_from"] = content.strip()
                    filters["date_to"] = content.strip()
                    records = self.manager.db.query_records(
                        filters=filters,
                        order_by="-created_at",
                        user_id=self.user_id
                    )
                    
                    if not records:
                        return {
                            "type": "info",
                            "message": f"未找到 {content} 的记录\n\n发送\"0\"返回子菜单"
                        }
                    
                    message = f"找到 {len(records)} 条记录：\n\n"
                    for i, record in enumerate(records, 1):
                        fields = record.structured_data.get('fields', {})
                        amount = fields.get('amount', 0)
                        category = fields.get('category', '未知')
                        summary = record.structured_data.get('summary', '')
                        message += f"[{i}] ID: {record.id}\n"
                        message += f"    金额: {amount}元 | 类别: {category}\n"
                        message += f"    摘要: {summary}\n\n"
                    
                    message += "发送\"0\"返回子菜单"
                    session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                    return {
                        "type": "success",
                        "message": message
                    }
                except ValueError:
                    return {
                        "type": "error",
                        "message": "日期格式错误，请使用 YYYY-MM-DD 格式"
                    }
            elif query_mode == "category":
                category = content.strip()
                all_records = self.manager.db.query_records(
                    filters=filters,
                    user_id=self.user_id
                )
                records = [r for r in all_records if r.structured_data.get('fields', {}).get('category') == category]
                
                if not records:
                    return {
                        "type": "info",
                        "message": f"未找到类别为\"{category}\"的记录\n\n发送\"0\"返回子菜单"
                    }
                
                message = f"找到 {len(records)} 条记录：\n\n"
                for i, record in enumerate(records[:10], 1):
                    fields = record.structured_data.get('fields', {})
                    amount = fields.get('amount', 0)
                    date_str = fields.get('date', '')
                    summary = record.structured_data.get('summary', '')
                    message += f"[{i}] ID: {record.id}\n"
                    message += f"    金额: {amount}元 | 日期: {date_str}\n"
                    message += f"    摘要: {summary}\n\n"
                
                if len(records) > 10:
                    message += f"... 还有 {len(records) - 10} 条记录\n\n"
                
                message += "发送\"0\"返回子菜单"
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return {
                    "type": "success",
                    "message": message
                }
            elif query_mode == "keyword":
                filters["keyword"] = content.strip()
                records = self.manager.db.query_records(
                    filters=filters,
                    limit=20,
                    order_by="-created_at",
                    user_id=self.user_id
                )
                
                if not records:
                    return {
                        "type": "info",
                        "message": f"未找到包含\"{content}\"的记录\n\n发送\"0\"返回子菜单"
                    }
                
                message = f"找到 {len(records)} 条记录：\n\n"
                for i, record in enumerate(records, 1):
                    fields = record.structured_data.get('fields', {})
                    amount = fields.get('amount', 0)
                    category = fields.get('category', '未知')
                    date_str = fields.get('date', '')
                    message += f"[{i}] ID: {record.id}\n"
                    message += f"    金额: {amount}元 | 类别: {category} | 日期: {date_str}\n\n"
                
                message += "发送\"0\"返回子菜单"
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return {
                    "type": "success",
                    "message": message
                }
        
        except Exception as e:
            logger.error(f"查询失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"查询失败: {str(e)}"
            }
        
        return {
            "type": "error",
            "message": f"查询模式 {query_mode} 暂未实现"
        }
    
    def _handle_update(self, content: str) -> Dict[str, Any]:
        """处理修改记账"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        return {
            "type": "info",
            "message": "修改功能暂未实现，请使用删除+添加的方式\n\n发送\"0\"返回子菜单"
        }
    
    def _handle_delete(self, content: str) -> Dict[str, Any]:
        """处理删除记账"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        try:
            record_id = int(content.strip())
            success = self.manager.db.delete_record(record_id, user_id=self.user_id)
            
            if success:
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return {
                    "type": "success",
                    "message": f"✓ 记录 ID {record_id} 已删除\n\n发送\"0\"返回子菜单"
                }
            else:
                return {
                    "type": "error",
                    "message": f"记录 ID {record_id} 不存在\n\n发送\"0\"返回子菜单"
                }
        except ValueError:
            return {
                "type": "error",
                "message": "请输入有效的记录ID（数字）"
            }
        except Exception as e:
            logger.error(f"删除记录失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"删除失败: {str(e)}"
            }
    
    def _handle_switch_table(self, content: str) -> Dict[str, Any]:
        """处理切换表/目录"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        new_table = content.strip()
        if new_table:
            self.manager.table_name = new_table
            session = session_manager.get_session(self.bot_id, self.user_id)
            session.table_name = new_table
            session.update_activity()
            
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return {
                "type": "success",
                "message": f"✓ 已切换到表/目录: {new_table}\n\n发送\"0\"返回子菜单"
            }
        
        return {
            "type": "error",
            "message": "表/目录名称不能为空"
        }
    
    def _handle_list_tables(self) -> Dict[str, Any]:
        """处理查看所有表/目录"""
        try:
            stats = self.manager.db.get_statistics(
                filters={"record_type": "记账"},
                user_id=self.user_id
            )
            by_table = stats.get('by_table', {})
            
            if not by_table:
                return {
                    "type": "info",
                    "message": "暂无表/目录\n\n发送\"0\"返回子菜单"
                }
            
            message = "所有表/目录：\n\n"
            for table_name, count in by_table.items():
                marker = " ← 当前" if table_name == self.manager.table_name else ""
                message += f"  {table_name}: {count} 条记录{marker}\n"
            
            message += "\n发送\"0\"返回子菜单"
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return {
                "type": "success",
                "message": message
            }
        except Exception as e:
            logger.error(f"查询表列表失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"查询失败: {str(e)}"
            }
    
    def _show_summarize_menu(self) -> Dict[str, Any]:
        """显示总结菜单"""
        menu_text = """📊 【查询并总结记账记录】

请选择总结方式：
  1. 📋 查询所有记录并总结
  2. 📅 按日期查询并总结（单日）
  3. 📆 按时间段查询并总结（日期范围）
  4. 📈 生成周报（最近7天）
  5. 📅 生成月报（最近30天）
  6. 🏷️ 按类别查询并总结
  0. 🔙 返回

💡 请输入数字选择（0-6）"""
        
        session_manager.get_session(self.bot_id, self.user_id).context["summarize_mode"] = "menu"
        return {
            "type": "sub_menu",
            "message": menu_text
        }
    
    def _handle_summarize(self, content: str) -> Dict[str, Any]:
        """处理查询并总结"""
        session = session_manager.get_session(self.bot_id, self.user_id)
        summarize_mode = session.context.get("summarize_mode", "menu")
        
        if content.strip() == "0":
            if summarize_mode == "menu":
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return self.show_sub_menu()
            else:
                session.context["summarize_mode"] = "menu"
                return self._show_summarize_menu()
        
        if summarize_mode == "menu":
            choice = content.strip()
            if choice == "1":
                return self._summarize_all()
            elif choice == "2":
                session.context["summarize_mode"] = "date"
                return {
                    "type": "prompt",
                    "message": "📅 请输入日期 (YYYY-MM-DD)，或发送\"0\"返回"
                }
            elif choice == "3":
                session.context["summarize_mode"] = "date_range"
                return {
                    "type": "prompt",
                    "message": "📆 请输入日期范围，格式：YYYY-MM-DD 至 YYYY-MM-DD\n例如：2024-01-01 至 2024-01-31\n\n或发送\"0\"返回"
                }
            elif choice == "4":
                return self._summarize_weekly()
            elif choice == "5":
                return self._summarize_monthly()
            elif choice == "6":
                session.context["summarize_mode"] = "category"
                return {
                    "type": "prompt",
                    "message": "🏷️ 请输入类别，或发送\"0\"返回"
                }
            else:
                return {
                    "type": "error",
                    "message": f"无效选择：{choice}，请输入 0-6 之间的数字"
                }
        else:
            # 执行具体总结
            return self._execute_summarize(content, summarize_mode)
    
    def _summarize_all(self) -> Dict[str, Any]:
        """总结所有记录"""
        try:
            filters = {
                "record_type": "记账",
                "table_name": self.manager.table_name
            }
            records = self.manager.db.query_records(
                filters=filters,
                limit=100,
                order_by="-created_at",
                user_id=self.user_id
            )
            
            if not records:
                return {
                    "type": "info",
                    "message": "暂无记账记录\n\n发送\"0\"返回子菜单"
                }
            
            # 格式化记录
            formatted_records = self._format_records_for_summary(records)
            
            # 使用 core.llm 的 summarize 方法
            summary_text = self.manager.llm_client.summarize(
                records=formatted_records[:50],
                custom_prompt=ACCOUNTING_SUMMARY_PROMPT
            )
            
            # 美化消息
            summary_text = format_message(summary_text)
            
            message = f"📊 找到 {len(records)} 条记录\n\n"
            message += f"【总结分析结果】\n\n{summary_text}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return {
                "type": "success",
                "message": message
            }
        except Exception as e:
            logger.error(f"总结失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"总结失败: {str(e)}"
            }
    
    def _summarize_weekly(self) -> Dict[str, Any]:
        """生成周报（最近7天）"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            filters = {
                "record_type": "记账",
                "table_name": self.manager.table_name,
                "date_from": start_date.strftime("%Y-%m-%d"),
                "date_to": end_date.strftime("%Y-%m-%d")
            }
            records = self.manager.db.query_records(
                filters=filters,
                limit=200,
                order_by="-created_at",
                user_id=self.user_id
            )
            
            if not records:
                return {
                    "type": "info",
                    "message": f"📭 最近7天暂无记账记录\n\n发送\"0\"返回子菜单"
                }
            
            # 格式化记录
            formatted_records = self._format_records_for_summary(records)
            
            # 使用 core.llm 的 summarize 方法
            summary_text = self.manager.llm_client.summarize(
                records=formatted_records,
                custom_prompt=ACCOUNTING_SUMMARY_PROMPT
            )
            
            # 美化消息
            summary_text = format_message(summary_text)
            
            message = f"📈 【周报】最近7天记账总结\n"
            message += f"📅 时间范围：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}\n"
            message += f"📊 记录数：{len(records)} 条\n\n"
            message += f"{summary_text}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return {
                "type": "success",
                "message": message
            }
        except Exception as e:
            logger.error(f"生成周报失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"生成周报失败: {str(e)}"
            }
    
    def _summarize_monthly(self) -> Dict[str, Any]:
        """生成月报（最近30天）"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            filters = {
                "record_type": "记账",
                "table_name": self.manager.table_name,
                "date_from": start_date.strftime("%Y-%m-%d"),
                "date_to": end_date.strftime("%Y-%m-%d")
            }
            records = self.manager.db.query_records(
                filters=filters,
                limit=500,
                order_by="-created_at",
                user_id=self.user_id
            )
            
            if not records:
                return {
                    "type": "info",
                    "message": f"📭 最近30天暂无记账记录\n\n发送\"0\"返回子菜单"
                }
            
            # 格式化记录
            formatted_records = self._format_records_for_summary(records)
            
            # 使用 core.llm 的 summarize 方法
            summary_text = self.manager.llm_client.summarize(
                records=formatted_records,
                custom_prompt=ACCOUNTING_SUMMARY_PROMPT
            )
            
            # 美化消息
            summary_text = format_message(summary_text)
            
            message = f"📅 【月报】最近30天记账总结\n"
            message += f"📅 时间范围：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}\n"
            message += f"📊 记录数：{len(records)} 条\n\n"
            message += f"{summary_text}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return {
                "type": "success",
                "message": message
            }
        except Exception as e:
            logger.error(f"生成月报失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"生成月报失败: {str(e)}"
            }
    
    def _execute_summarize(self, content: str, summarize_mode: str) -> Dict[str, Any]:
        """执行具体总结"""
        try:
            filters = {
                "record_type": "记账",
                "table_name": self.manager.table_name
            }
            
            if summarize_mode == "date":
                try:
                    date_str = content.strip()
                    filters["date_from"] = date_str
                    filters["date_to"] = date_str
                    records = self.manager.db.query_records(
                        filters=filters,
                        order_by="-created_at",
                        user_id=self.user_id
                    )
                    
                    if not records:
                        return {
                            "type": "info",
                            "message": f"📭 {date_str} 暂无记账记录\n\n发送\"0\"返回子菜单"
                        }
                    
                    formatted_records = self._format_records_for_summary(records)
                    summary_text = self.manager.llm_client.summarize(
                        records=formatted_records,
                        custom_prompt=ACCOUNTING_SUMMARY_PROMPT
                    )
                    summary_text = format_message(summary_text)
                    
                    message = f"📅 {date_str} 记账总结\n"
                    message += f"📊 记录数：{len(records)} 条\n\n"
                    message += f"{summary_text}\n\n"
                    message += f"发送\"0\"返回子菜单"
                    
                    session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                    return {
                        "type": "success",
                        "message": message
                    }
                except ValueError:
                    return {
                        "type": "error",
                        "message": "❌ 日期格式错误，请使用 YYYY-MM-DD 格式"
                    }
            elif summarize_mode == "date_range":
                try:
                    # 解析日期范围，格式：YYYY-MM-DD 至 YYYY-MM-DD
                    if "至" in content or "到" in content:
                        separator = "至" if "至" in content else "到"
                        parts = content.split(separator)
                        if len(parts) != 2:
                            raise ValueError("日期范围格式错误")
                        start_date = parts[0].strip()
                        end_date = parts[1].strip()
                    else:
                        # 尝试空格分隔
                        parts = content.strip().split()
                        if len(parts) != 2:
                            raise ValueError("日期范围格式错误")
                        start_date = parts[0]
                        end_date = parts[1]
                    
                    filters["date_from"] = start_date
                    filters["date_to"] = end_date
                    records = self.manager.db.query_records(
                        filters=filters,
                        limit=500,
                        order_by="-created_at",
                        user_id=self.user_id
                    )
                    
                    if not records:
                        return {
                            "type": "info",
                            "message": f"📭 {start_date} 至 {end_date} 暂无记账记录\n\n发送\"0\"返回子菜单"
                        }
                    
                    formatted_records = self._format_records_for_summary(records)
                    summary_text = self.manager.llm_client.summarize(
                        records=formatted_records,
                        custom_prompt=ACCOUNTING_SUMMARY_PROMPT
                    )
                    summary_text = format_message(summary_text)
                    
                    message = f"📆 {start_date} 至 {end_date} 记账总结\n"
                    message += f"📊 记录数：{len(records)} 条\n\n"
                    message += f"{summary_text}\n\n"
                    message += f"发送\"0\"返回子菜单"
                    
                    session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                    return {
                        "type": "success",
                        "message": message
                    }
                except ValueError as e:
                    return {
                        "type": "error",
                        "message": f"❌ 日期范围格式错误，请使用：YYYY-MM-DD 至 YYYY-MM-DD\n错误：{str(e)}"
                    }
            elif summarize_mode == "category":
                category = content.strip()
                all_records = self.manager.db.query_records(
                    filters=filters,
                    user_id=self.user_id
                )
                records = [
                    r for r in all_records 
                    if r.structured_data.get('fields', {}).get('category') == category
                ]
                
                if not records:
                    return {
                        "type": "info",
                        "message": f"📭 类别\"{category}\"暂无记账记录\n\n发送\"0\"返回子菜单"
                    }
                
                formatted_records = self._format_records_for_summary(records)
                summary_text = self.manager.llm_client.summarize(
                    records=formatted_records,
                    custom_prompt=ACCOUNTING_SUMMARY_PROMPT
                )
                summary_text = format_message(summary_text)
                
                message = f"🏷️ 类别\"{category}\"记账总结\n"
                message += f"📊 记录数：{len(records)} 条\n\n"
                message += f"{summary_text}\n\n"
                message += f"发送\"0\"返回子菜单"
                
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return {
                    "type": "success",
                    "message": message
                }
        
        except Exception as e:
            logger.error(f"总结失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"总结失败: {str(e)}"
            }
        
        return {
            "type": "error",
            "message": f"总结模式 {summarize_mode} 暂未实现"
        }
    
    def _handle_statistics(self) -> Dict[str, Any]:
        """处理统计分析"""
        try:
            filters = {
                "record_type": "记账",
                "table_name": self.manager.table_name
            }
            records = self.manager.db.query_records(
                filters=filters,
                user_id=self.user_id
            )
            
            if not records:
                return {
                    "type": "info",
                    "message": "暂无记账记录\n\n发送\"0\"返回子菜单"
                }
            
            # 统计分析
            total_amount = 0
            category_stats = {}
            
            for record in records:
                fields = record.structured_data.get('fields', {})
                amount = fields.get('amount', 0)
                category = fields.get('category', '未知')
                total_amount += amount
                if category not in category_stats:
                    category_stats[category] = {"count": 0, "amount": 0}
                category_stats[category]["count"] += 1
                category_stats[category]["amount"] += amount
            
            message = f"【统计分析结果】\n\n"
            message += f"总记录数: {len(records)} 条\n"
            message += f"总支出: ¥{total_amount:.2f}\n"
            message += f"平均支出: ¥{total_amount/len(records):.2f}\n\n"
            message += f"按类别统计:\n"
            message += "-" * 60 + "\n"
            
            sorted_categories = sorted(category_stats.items(), key=lambda x: x[1]["amount"], reverse=True)
            for category, stats in sorted_categories[:10]:
                percentage = (stats["amount"] / total_amount * 100) if total_amount > 0 else 0
                message += f"  {category}: {stats['count']} 条, ¥{stats['amount']:.2f} ({percentage:.1f}%)\n"
            
            message += "\n发送\"0\"返回子菜单"
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return {
                "type": "success",
                "message": message
            }
        except Exception as e:
            logger.error(f"统计失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"统计失败: {str(e)}"
            }
    
    def _format_records_for_summary(self, records):
        """格式化记录用于总结"""
        formatted_records = []
        for record in records:
            fields = record.structured_data.get('fields', {})
            formatted_record = {
                "id": record.id,
                "日期": fields.get('date', record.created_at.strftime('%Y-%m-%d')),
                "金额": fields.get('amount', 0),
                "类别": fields.get('category', '未知'),
                "摘要": record.structured_data.get('summary', ''),
                "支付方式": fields.get('payment_method', '未知'),
                "地点": fields.get('location', '')
            }
            formatted_records.append(formatted_record)
        return formatted_records
