"""
随笔服务
处理随笔业务逻辑，适配微信消息驱动模式，支持完整子菜单
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

from shared.models import StructuredRecord
from shared.user_database_manager import user_db_manager
from agent_structurizer.llm_client import LLMClient
from agent_structurizer.prompt_templates import ESSAY_PROMPT_TEMPLATE, ESSAY_ANALYSIS_PROMPT
from shared.utils import setup_logger
from agent_wechat.session_manager import session_manager

logger = setup_logger(__name__)


class EssayService:
    """随笔服务"""
    
    def __init__(self, user_id: str):
        """
        初始化随笔服务
        
        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.db = user_db_manager.get_user_db(user_id)
        self.llm_client = LLMClient()
        self.table_name = "随笔"  # 默认表名
    
    def show_sub_menu(self) -> Dict[str, Any]:
        """显示随笔管理子菜单"""
        session = session_manager.get_session(self.user_id)
        table_name = session.table_name or self.table_name
        
        menu_text = f"""============================================================
随笔管理系统
============================================================
当前表/目录: {table_name}

请选择操作：
  1. 添加随笔记录（输入自然语言）
  2. 查询随笔记录
  3. 修改随笔记录
  4. 删除随笔记录
  5. 切换表/目录
  6. 查看所有表/目录
  7. AI分析随笔（查看AI回应）
  0. 退出
============================================================

请输入数字选择（0-7）"""
        
        return {
            "type": "sub_menu",
            "message": menu_text,
            "action": "show_sub_menu"
        }
    
    def process_message(self, content: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理随笔消息
        
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
        elif sub_menu == "analyze":
            return self._handle_analyze(content)
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
                "message": "✓ 已进入添加随笔模式\n\n请直接发送随笔内容（自然语言），例如：\n- 今天心情很好，在咖啡厅写下了这些想法...\n- 关于工作的思考：我觉得...\n\n发送\"0\"可返回子菜单"
            }
        elif choice == "2":
            session_manager.set_sub_menu(self.user_id, "query")
            return self._show_query_menu()
        elif choice == "3":
            session_manager.set_sub_menu(self.user_id, "update")
            return {
                "type": "prompt",
                "message": "✓ 已进入修改随笔模式\n\n请先发送要修改的记录ID，或发送\"0\"返回子菜单"
            }
        elif choice == "4":
            session_manager.set_sub_menu(self.user_id, "delete")
            return {
                "type": "prompt",
                "message": "✓ 已进入删除随笔模式\n\n请先发送要删除的记录ID，或发送\"0\"返回子菜单"
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
            session_manager.set_sub_menu(self.user_id, "analyze")
            return {
                "type": "prompt",
                "message": "✓ 已进入AI分析模式\n\n请发送要分析的记录ID，或发送\"0\"返回子菜单"
            }
        else:
            return {
                "type": "error",
                "message": f"无效选择：{choice}，请输入 0-7 之间的数字"
            }
    
    def _handle_add(self, content: str) -> Dict[str, Any]:
        """处理添加随笔"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.user_id, "main")
            return self.show_sub_menu()
        
        if not content or not content.strip():
            return {
                "type": "error",
                "message": "随笔内容不能为空"
            }
        
        try:
            # 获取当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt_template_with_date = ESSAY_PROMPT_TEMPLATE.replace("{current_date}", current_date)
            
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
                    record_type=structured_data.get('type', '随笔'),
                    table_name=self.table_name,
                    extra_metadata=None
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                
                # 构建成功消息
                fields = structured_data.get('fields', {})
                summary = structured_data.get('summary', '')
                date_str = fields.get('date', current_date)
                mood = fields.get('mood', '未记录')
                tags = ', '.join(fields.get('tags', [])) if fields.get('tags') else '无标签'
                
                message = f"✓ 随笔保存成功！\n\n"
                message += f"📅 日期: {date_str}\n"
                message += f"😊 心情: {mood}\n"
                message += f"🏷️ 标签: {tags}\n"
                message += f"📝 摘要: {summary}\n"
                message += f"🆔 记录ID: {record.id}\n\n"
                message += f"发送\"0\"返回子菜单"
                
                # 重置到主菜单状态，等待下次操作
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
                logger.error(f"保存随笔记录失败: {e}", exc_info=True)
                return {
                    "type": "error",
                    "message": f"保存失败: {str(e)}"
                }
            finally:
                session.close()
        
        except Exception as e:
            logger.error(f"处理随笔消息失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"处理失败: {str(e)}"
            }
    
    def _show_query_menu(self) -> Dict[str, Any]:
        """显示查询菜单"""
        menu_text = """【查询随笔记录】

请选择查询方式：
  1. 查询所有记录
  2. 按日期查询（单日）
  3. 按时间段查询（日期范围）
  4. 按标签查询
  5. 按关键词搜索
  6. 按心情查询
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
                # 查询所有
                return self._query_all()
            elif choice == "2":
                session.context["query_mode"] = "date"
                return {
                    "type": "prompt",
                    "message": "请输入日期 (YYYY-MM-DD)，或发送\"0\"返回"
                }
            elif choice == "3":
                session.context["query_mode"] = "date_range"
                session.context["query_step"] = "start"
                return {
                    "type": "prompt",
                    "message": "请输入开始日期 (YYYY-MM-DD)，或发送\"0\"返回"
                }
            elif choice == "4":
                session.context["query_mode"] = "tag"
                return {
                    "type": "prompt",
                    "message": "请输入标签，或发送\"0\"返回"
                }
            elif choice == "5":
                session.context["query_mode"] = "keyword"
                return {
                    "type": "prompt",
                    "message": "请输入关键词，或发送\"0\"返回"
                }
            elif choice == "6":
                session.context["query_mode"] = "mood"
                return {
                    "type": "prompt",
                    "message": "请输入心情，或发送\"0\"返回"
                }
            else:
                return {
                    "type": "error",
                    "message": f"无效选择：{choice}"
                }
        else:
            # 处理具体查询
            return self._execute_query(content, query_mode)
    
    def _query_all(self) -> Dict[str, Any]:
        """查询所有记录"""
        session = self.db.get_session()
        try:
            records = session.query(StructuredRecord).filter(
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "随笔"
            ).order_by(StructuredRecord.created_at.desc()).limit(20).all()
            
            if not records:
                return {
                    "type": "info",
                    "message": "暂无随笔记录\n\n发送\"0\"返回子菜单"
                }
            
            message = f"找到 {len(records)} 条记录：\n\n"
            for i, record in enumerate(records, 1):
                fields = record.structured_data.get('fields', {})
                title = fields.get('title', '无标题')
                date_str = fields.get('date', '')
                summary = record.structured_data.get('summary', '')
                message += f"[{i}] ID: {record.id}\n"
                message += f"    标题: {title}\n"
                message += f"    日期: {date_str}\n"
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
        # 简化实现，只实现按日期查询
        if query_mode == "date":
            try:
                query_date = datetime.strptime(content.strip(), "%Y-%m-%d").date()
                session = self.db.get_session()
                try:
                    records = session.query(StructuredRecord).filter(
                        StructuredRecord.table_name == self.table_name,
                        StructuredRecord.record_type == "随笔",
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
                        title = fields.get('title', '无标题')
                        summary = record.structured_data.get('summary', '')
                        message += f"[{i}] ID: {record.id}\n"
                        message += f"    标题: {title}\n"
                        message += f"    摘要: {summary}\n\n"
                    
                    message += "发送\"0\"返回子菜单"
                    session_manager.set_sub_menu(self.user_id, "main")
                    return {
                        "type": "success",
                        "message": message
                    }
                finally:
                    session.close()
            except ValueError:
                return {
                    "type": "error",
                    "message": "日期格式错误，请使用 YYYY-MM-DD 格式"
                }
        
        return {
            "type": "error",
            "message": f"查询模式 {query_mode} 暂未实现"
        }
    
    def _handle_update(self, content: str) -> Dict[str, Any]:
        """处理修改随笔"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.user_id, "main")
            return self.show_sub_menu()
        
        # 简化实现：直接修改
        return {
            "type": "info",
            "message": "修改功能暂未实现，请使用删除+添加的方式\n\n发送\"0\"返回子菜单"
        }
    
    def _handle_delete(self, content: str) -> Dict[str, Any]:
        """处理删除随笔"""
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
                    StructuredRecord.record_type == "随笔"
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
                StructuredRecord.record_type == "随笔"
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
    
    def _handle_analyze(self, content: str) -> Dict[str, Any]:
        """处理AI分析"""
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
                    StructuredRecord.record_type == "随笔"
                ).first()
                
                if not record:
                    return {
                        "type": "error",
                        "message": f"记录 ID {record_id} 不存在"
                    }
                
                # 进行AI分析
                fields = record.structured_data.get('fields', {})
                essay_content = fields.get('content', record.original_text)
                essay_date = fields.get('date', record.created_at.strftime('%Y-%m-%d'))
                essay_tags = ', '.join(fields.get('tags', [])) if fields.get('tags') else '无'
                essay_mood = fields.get('mood', '未记录')
                essay_location = fields.get('location', '未记录')
                
                prompt = ESSAY_ANALYSIS_PROMPT.format(
                    essay_content=essay_content,
                    essay_date=essay_date,
                    essay_tags=essay_tags,
                    essay_mood=essay_mood,
                    essay_location=essay_location
                )
                
                response = self.llm_client.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个温暖、专业的心理和内容分析助手，能够对随笔进行深入分析并给出有温度的回应。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
                
                analysis_text = response.choices[0].message.content.strip()
                
                message = f"【AI分析回应】\n\n{analysis_text}\n\n发送\"0\"返回子菜单"
                
                session_manager.set_sub_menu(self.user_id, "main")
                return {
                    "type": "success",
                    "message": message
                }
            finally:
                session.close()
        except ValueError:
            return {
                "type": "error",
                "message": "请输入有效的记录ID（数字）"
            }
        except Exception as e:
            logger.error(f"AI分析失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"AI分析失败: {str(e)}"
            }
