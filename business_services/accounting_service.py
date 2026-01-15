"""
记账服务
处理记账业务逻辑，适配微信消息驱动模式，支持完整子菜单
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
from collections import defaultdict

from shared.models import StructuredRecord
from shared.user_database_manager import user_db_manager
from agent_structurizer.llm_client import LLMClient
from agent_structurizer.prompt_templates import ACCOUNTING_PROMPT_TEMPLATE, ACCOUNTING_SUMMARY_PROMPT
from shared.utils import setup_logger
from agent_wechat.session_manager import session_manager

logger = setup_logger(__name__)


class AccountingService:
    """记账服务"""
    
    def __init__(self, user_id: str):
        """
        初始化记账服务
        
        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.db = user_db_manager.get_user_db(user_id)
        self.llm_client = LLMClient()
        self.table_name = "记账"  # 默认表名
    
    def show_sub_menu(self) -> Dict[str, Any]:
        """显示记账管理子菜单"""
        session = session_manager.get_session(self.user_id)
        table_name = session.table_name or self.table_name
        
        menu_text = f"""
记账管理系统
当前表/目录: {table_name}
========
请选择操作：
  1. 添加记账记录（输入自然语言）
  2. 查询记账记录
  3. 修改记账记录
  4. 删除记账记录
  5. 切换表/目录
  6. 查看所有表/目录
  7. 查询并总结
  8. 统计分析
  0. 退出
========

请输入数字选择（0-8）"""
        
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
        session = session_manager.get_session(self.user_id)
        sub_menu = session.sub_menu
        
        # 如果没有子菜单状态，显示子菜单
        if sub_menu is None:
            session_manager.set_sub_menu(self.user_id, "main")
            return self.show_sub_menu()
        
        # 处理子菜单选择
        if sub_menu == "main":
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
            session_manager.reset_to_menu(self.user_id)
            from business_services.menu_handler import MenuHandler
            return MenuHandler.show_menu()
        elif choice == "1":
            session_manager.set_sub_menu(self.user_id, "add")
            return {
                "type": "prompt",
                "message": "✓ 已进入添加记账模式\n\n请直接发送记账信息（自然语言），例如：\n- 今天花了50元买了一杯咖啡\n- 在超市购物花费200元\n\n发送\"0\"可返回子菜单"
            }
        elif choice == "2":
            session_manager.set_sub_menu(self.user_id, "query")
            return self._show_query_menu()
        elif choice == "3":
            session_manager.set_sub_menu(self.user_id, "update")
            return {
                "type": "prompt",
                "message": "✓ 已进入修改记账模式\n\n请先发送要修改的记录ID，或发送\"0\"返回子菜单"
            }
        elif choice == "4":
            session_manager.set_sub_menu(self.user_id, "delete")
            return {
                "type": "prompt",
                "message": "✓ 已进入删除记账模式\n\n请先发送要删除的记录ID，或发送\"0\"返回子菜单"
            }
        elif choice == "5":
            session_manager.set_sub_menu(self.user_id, "switch")
            return {
                "type": "prompt",
                "message": "✓ 已进入切换表/目录模式\n\n请发送新的表/目录名称，或发送\"0\"返回子菜单"
            }
        elif choice == "6":
            return self._handle_list_tables()
        elif choice == "7":
            session_manager.set_sub_menu(self.user_id, "summarize")
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
            session_manager.set_sub_menu(self.user_id, "main")
            return self.show_sub_menu()
        
        if not content or not content.strip():
            return {
                "type": "error",
                "message": "记账信息不能为空"
            }
        
        try:
            # 获取当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt_template_with_date = ACCOUNTING_PROMPT_TEMPLATE.replace("{current_date}", current_date)
            
            # 调用LLM进行结构化
            structured_data = self.llm_client.structure_text(
                text=content,
                prompt_template=prompt_template_with_date
            )
            
            # 保存到用户数据库
            session = self.db.get_session()
            try:
                record = StructuredRecord(
                    original_text=content,
                    structured_data=structured_data,
                    record_type=structured_data.get('type', '记账'),
                    table_name=self.table_name,
                    extra_metadata=None
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                
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
                session_manager.set_sub_menu(self.user_id, "main")
                
                return {
                    "type": "success",
                    "message": message,
                    "data": {
                        "record_id": record.id,
                        "structured_data": structured_data
                    }
                }
                
            except Exception as e:
                session.rollback()
                logger.error(f"保存记账记录失败: {e}", exc_info=True)
                return {
                    "type": "error",
                    "message": f"保存失败: {str(e)}"
                }
            finally:
                session.close()
        
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
        
        session_manager.get_session(self.user_id).context["query_mode"] = "menu"
        return {
            "type": "sub_menu",
            "message": menu_text
        }
    
    def _handle_query(self, content: str) -> Dict[str, Any]:
        """处理查询"""
        session = session_manager.get_session(self.user_id)
        query_mode = session.context.get("query_mode", "menu")
        
        if content.strip() == "0":
            if query_mode == "menu":
                session_manager.set_sub_menu(self.user_id, "main")
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
        session = self.db.get_session()
        try:
            records = session.query(StructuredRecord).filter(
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "记账"
            ).order_by(StructuredRecord.created_at.desc()).limit(20).all()
            
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
            session_manager.set_sub_menu(self.user_id, "main")
            return {
                "type": "success",
                "message": message
            }
        finally:
            session.close()
    
    def _execute_query(self, content: str, query_mode: str) -> Dict[str, Any]:
        """执行查询"""
        session = self.db.get_session()
        try:
            query = session.query(StructuredRecord).filter(
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "记账"
            )
            
            if query_mode == "date":
                try:
                    query_date = datetime.strptime(content.strip(), "%Y-%m-%d").date()
                    records = query.filter(
                        StructuredRecord.created_at >= datetime.combine(query_date, datetime.min.time()),
                        StructuredRecord.created_at < datetime.combine(query_date, datetime.max.time()) + timedelta(days=1)
                    ).order_by(StructuredRecord.created_at.desc()).all()
                    
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
                    session_manager.set_sub_menu(self.user_id, "main")
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
                all_records = query.all()
                records = []
                for r in all_records:
                    record_category = r.structured_data.get('fields', {}).get('category', '')
                    if category in record_category:
                        records.append(r)
                records.sort(key=lambda x: x.created_at, reverse=True)
                
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
                session_manager.set_sub_menu(self.user_id, "main")
                return {
                    "type": "success",
                    "message": message
                }
            elif query_mode == "keyword":
                keyword = content.strip()
                records = query.filter(
                    StructuredRecord.original_text.contains(keyword)
                ).order_by(StructuredRecord.created_at.desc()).limit(20).all()
                
                if not records:
                    return {
                        "type": "info",
                        "message": f"未找到包含\"{keyword}\"的记录\n\n发送\"0\"返回子菜单"
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
                session_manager.set_sub_menu(self.user_id, "main")
                return {
                    "type": "success",
                    "message": message
                }
        
        finally:
            session.close()
        
        return {
            "type": "error",
            "message": f"查询模式 {query_mode} 暂未实现"
        }
    
    def _handle_update(self, content: str) -> Dict[str, Any]:
        """处理修改记账"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.user_id, "main")
            return self.show_sub_menu()
        
        # 简化实现
        return {
            "type": "info",
            "message": "修改功能暂未实现，请使用删除+添加的方式\n\n发送\"0\"返回子菜单"
        }
    
    def _handle_delete(self, content: str) -> Dict[str, Any]:
        """处理删除记账"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.user_id, "main")
            return self.show_sub_menu()
        
        try:
            record_id = int(content.strip())
            session = self.db.get_session()
            try:
                record = session.query(StructuredRecord).filter(
                    StructuredRecord.id == record_id,
                    StructuredRecord.table_name == self.table_name,
                    StructuredRecord.record_type == "记账"
                ).first()
                
                if not record:
                    return {
                        "type": "error",
                        "message": f"记录 ID {record_id} 不存在\n\n发送\"0\"返回子菜单"
                    }
                
                session.delete(record)
                session.commit()
                
                session_manager.set_sub_menu(self.user_id, "main")
                return {
                    "type": "success",
                    "message": f"✓ 记录 ID {record_id} 已删除\n\n发送\"0\"返回子菜单"
                }
            finally:
                session.close()
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
            session_manager.set_sub_menu(self.user_id, "main")
            return self.show_sub_menu()
        
        new_table = content.strip()
        if new_table:
            self.table_name = new_table
            session = session_manager.get_session(self.user_id)
            session.table_name = new_table
            session.update_activity()
            
            session_manager.set_sub_menu(self.user_id, "main")
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
        session = self.db.get_session()
        try:
            from sqlalchemy import func
            result = session.query(
                StructuredRecord.table_name,
                func.count(StructuredRecord.id).label('count')
            ).filter(
                StructuredRecord.table_name.isnot(None),
                StructuredRecord.record_type == "记账"
            ).group_by(StructuredRecord.table_name).all()
            
            if not result:
                return {
                    "type": "info",
                    "message": "暂无表/目录\n\n发送\"0\"返回子菜单"
                }
            
            message = "所有表/目录：\n\n"
            for table_name, count in result:
                marker = " ← 当前" if table_name == self.table_name else ""
                message += f"  {table_name}: {count} 条记录{marker}\n"
            
            message += "\n发送\"0\"返回子菜单"
            session_manager.set_sub_menu(self.user_id, "main")
            return {
                "type": "success",
                "message": message
            }
        finally:
            session.close()
    
    def _show_summarize_menu(self) -> Dict[str, Any]:
        """显示总结菜单"""
        menu_text = """【查询并总结记账记录】

请选择查询方式：
  1. 查询所有记录并总结
  2. 按日期查询并总结（单日）
  3. 按时间段查询并总结（日期范围）
  4. 按类别查询并总结
  0. 返回

请输入数字选择（0-4）"""
        
        session_manager.get_session(self.user_id).context["summarize_mode"] = "menu"
        return {
            "type": "sub_menu",
            "message": menu_text
        }
    
    def _handle_summarize(self, content: str) -> Dict[str, Any]:
        """处理查询并总结"""
        session = session_manager.get_session(self.user_id)
        summarize_mode = session.context.get("summarize_mode", "menu")
        
        if content.strip() == "0":
            if summarize_mode == "menu":
                session_manager.set_sub_menu(self.user_id, "main")
                return self.show_sub_menu()
            else:
                session.context["summarize_mode"] = "menu"
                return self._show_summarize_menu()
        
        # 简化实现：只实现查询所有并总结
        if summarize_mode == "menu":
            if content.strip() == "1":
                return self._summarize_all()
            else:
                return {
                    "type": "info",
                    "message": "暂只支持查询所有记录并总结，请选择 1\n\n发送\"0\"返回"
                }
        
        return {
            "type": "error",
            "message": "总结功能暂未完全实现"
        }
    
    def _summarize_all(self) -> Dict[str, Any]:
        """总结所有记录"""
        session = self.db.get_session()
        try:
            records = session.query(StructuredRecord).filter(
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "记账"
            ).order_by(StructuredRecord.created_at.desc()).limit(100).all()
            
            if not records:
                return {
                    "type": "info",
                    "message": "暂无记账记录\n\n发送\"0\"返回子菜单"
                }
            
            # 格式化记录
            formatted_records = []
            for record in records:
                fields = record.structured_data.get('fields', {})
                formatted_record = {
                    "id": record.id,
                    "日期": fields.get('date', record.created_at.strftime('%Y-%m-%d')),
                    "金额": fields.get('amount', 0),
                    "类别": fields.get('category', '未知'),
                    "摘要": record.structured_data.get('summary', ''),
                }
                formatted_records.append(formatted_record)
            
            records_text = "\n".join([
                f"记录{i+1}: {json.dumps(r, ensure_ascii=False)}"
                for i, r in enumerate(formatted_records[:50])
            ])
            
            # 调用LLM总结
            prompt = ACCOUNTING_SUMMARY_PROMPT.format(records_data=records_text)
            response = self.llm_client.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的记账分析助手，能够对多条记账记录进行总结和分析。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            
            summary_text = response.choices[0].message.content.strip()
            
            message = f"找到 {len(records)} 条记录\n\n"
            message += f"【总结分析结果】\n\n{summary_text}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            session_manager.set_sub_menu(self.user_id, "main")
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
        finally:
            session.close()
    
    def _handle_statistics(self) -> Dict[str, Any]:
        """处理统计分析"""
        session = self.db.get_session()
        try:
            records = session.query(StructuredRecord).filter(
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "记账"
            ).all()
            
            if not records:
                return {
                    "type": "info",
                    "message": "暂无记账记录\n\n发送\"0\"返回子菜单"
                }
            
            # 统计分析
            total_amount = 0
            category_stats = defaultdict(lambda: {"count": 0, "amount": 0})
            
            for record in records:
                fields = record.structured_data.get('fields', {})
                amount = fields.get('amount', 0)
                category = fields.get('category', '未知')
                total_amount += amount
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
            session_manager.set_sub_menu(self.user_id, "main")
            return {
                "type": "success",
                "message": message
            }
        finally:
            session.close()
