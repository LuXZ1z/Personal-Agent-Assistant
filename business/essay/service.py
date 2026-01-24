"""
随笔服务 - 微信平台适配器
调用 EssayManager 的业务逻辑，适配微信消息驱动模式
"""
from typing import Dict, Any
from datetime import datetime

from business.essay.manager import EssayManager
from business.essay.prompts import ESSAY_PROMPT_TEMPLATE, ESSAY_ANALYSIS_PROMPT
from shared.utils import setup_logger

from interfaces.wechat.session_manager import session_manager

logger = setup_logger(__name__)


class EssayService:
    """随笔服务 - 微信适配器，调用 Manager 的业务逻辑"""
    
    def __init__(self, user_id: str, bot_id: str = "default"):
        self.user_id = user_id
        self.bot_id = bot_id
        # 使用 Manager 层，Manager 使用 core 的基础能力
        self.manager = EssayManager(user_id=user_id, bot_id=bot_id, debug=False)
    
    def show_sub_menu(self) -> Dict[str, Any]:
        """显示随笔管理子菜单"""
        session = session_manager.get_session(self.bot_id, self.user_id)
        table_name = session.table_name or self.manager.table_name
        
        menu_text = f"""📝 随笔管理系统 📝

📁 当前表/目录: {table_name}

✨ 请选择操作：
  1. ➕ 添加随笔记录
  2. 🔍 查询随笔记录
  3. ✏️ 修改随笔记录
  4. 🗑️ 删除随笔记录
  5. 🔄 切换表/目录
  6. 📋 查看所有表/目录
  7. 🤖 AI分析随笔
  0. 🚪 退出

💡 请输入数字选择（0-7）"""
        
        return {
            "type": "sub_menu",
            "message": menu_text,
            "action": "show_sub_menu"
        }
    
    def process_message(self, content: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理随笔消息"""
        session = session_manager.get_session(self.bot_id, self.user_id)
        sub_menu = session.sub_menu
        
        if sub_menu is None:
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
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
        elif sub_menu == "analysis":
            return self._handle_analysis(content)
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
                "message": "✅ 已进入添加随笔模式\n\n💬 请直接发送随笔内容（自然语言）\n\n发送\"0\"可返回子菜单"
            }
        elif choice == "2":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "query")
            return self._show_query_menu()
        elif choice == "3":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "update")
            return {
                "type": "prompt",
                "message": "✅ 已进入修改随笔模式\n\n请先发送要修改的记录ID，或发送\"0\"返回子菜单"
            }
        elif choice == "4":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "delete")
            return {
                "type": "prompt",
                "message": "✅ 已进入删除随笔模式\n\n请先发送要删除的记录ID，或发送\"0\"返回子菜单"
            }
        elif choice == "5":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "switch")
            return {
                "type": "prompt",
                "message": "✅ 已进入切换表/目录模式\n\n请发送新的表/目录名称，或发送\"0\"返回子菜单"
            }
        elif choice == "6":
            return self._handle_list_tables()
        elif choice == "7":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "analysis")
            return self._show_analysis_menu()
        else:
            return {
                "type": "error",
                "message": f"无效选择：{choice}，请输入 0-7 之间的数字"
            }
    
    def _handle_add(self, content: str) -> Dict[str, Any]:
        """处理添加随笔"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        if not content or not content.strip():
            return {
                "type": "error",
                "message": "随笔内容不能为空"
            }
        
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt_template_with_date = ESSAY_PROMPT_TEMPLATE.replace("{current_date}", current_date)
            
            structured_data = self.manager.llm_client.structure_text(
                text=content,
                prompt_template=prompt_template_with_date
            )
            
            record = self.manager.db.create_record(
                original_text=content,
                structured_data=structured_data,
                record_type=structured_data.get('type', '随笔'),
                table_name=self.manager.table_name,
                metadata=None,
                user_id=self.user_id,
                bot_id=self.bot_id
            )
            
            fields = structured_data.get('fields', {})
            message = f"✅ 随笔保存成功！\n\n"
            message += f"📝 摘要: {structured_data.get('summary', '')}\n"
            if fields.get('tags'):
                tags_text = "、".join(fields.get('tags', []))
                message += f"🏷️ 标签: {tags_text}\n"
            if fields.get('mood'):
                message += f"😊 心情: {fields.get('mood')}\n"
            message += f"🆔 记录ID: {record.id}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return {
                "type": "success",
                "message": message
            }
        except Exception as e:
            logger.error(f"处理随笔消息失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"处理失败: {str(e)}"
            }
    
    def _show_query_menu(self) -> Dict[str, Any]:
        """显示查询菜单"""
        menu_text = """🔍 【查询随笔记录】

请选择查询方式：
  1. 📋 查询所有记录
  2. 📅 按日期查询（单日）
  3. 🏷️ 按标签查询
  4. 😊 按心情查询
  5. 🔍 按关键词搜索
  0. 🔙 返回

💡 请输入数字选择（0-5）"""
        
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
                    "message": "📅 请输入日期 (YYYY-MM-DD)，或发送\"0\"返回"
                }
            elif choice == "3":
                session.context["query_mode"] = "tag"
                return {
                    "type": "prompt",
                    "message": "🏷️ 请输入标签，或发送\"0\"返回"
                }
            elif choice == "4":
                session.context["query_mode"] = "mood"
                return {
                    "type": "prompt",
                    "message": "😊 请输入心情，或发送\"0\"返回"
                }
            elif choice == "5":
                session.context["query_mode"] = "keyword"
                return {
                    "type": "prompt",
                    "message": "🔍 请输入关键词，或发送\"0\"返回"
                }
            else:
                return {
                    "type": "error",
                    "message": f"查询方式 {choice} 暂未实现，请选择 1-5"
                }
        else:
            # 执行具体查询
            return self._execute_query(content, query_mode)
    
    def _query_all(self) -> Dict[str, Any]:
        """查询所有记录"""
        try:
            filters = {
                "record_type": "随笔",
                "table_name": self.manager.table_name
            }
            records = self.manager.db.query_records(
                filters=filters,
                limit=20,
                order_by="-created_at",
                user_id=self.user_id,
                bot_id=self.bot_id
            )
            
            if not records:
                return {
                    "type": "info",
                    "message": "📭 暂无随笔记录\n\n发送\"0\"返回子菜单"
                }
            
            message = f"📋 找到 {len(records)} 条记录：\n\n"
            for i, record in enumerate(records, 1):
                fields = record.structured_data.get('fields', {})
                summary = record.structured_data.get('summary', '')
                date_str = fields.get('date', '')
                tags = fields.get('tags', [])
                message += f"[{i}] 🆔 ID: {record.id}\n"
                message += f"    📝 {summary}\n"
                message += f"    📅 {date_str}"
                if tags:
                    tags_text = "、".join(tags[:3])
                    message += f" | 🏷️ {tags_text}"
                message += "\n\n"
            
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
                "record_type": "随笔",
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
                            "message": f"📭 未找到 {content} 的记录\n\n发送\"0\"返回子菜单"
                        }
                    
                    message = f"📅 {content} 的记录（{len(records)} 条）：\n\n"
                    for i, record in enumerate(records, 1):
                        summary = record.structured_data.get('summary', '')
                        message += f"[{i}] 🆔 ID: {record.id}\n"
                        message += f"    📝 {summary}\n\n"
                    
                    message += "发送\"0\"返回子菜单"
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
            elif query_mode == "tag":
                tag = content.strip()
                all_records = self.manager.db.query_records(
                    filters=filters,
                    user_id=self.user_id
                )
                records = [
                    r for r in all_records 
                    if tag in r.structured_data.get('fields', {}).get('tags', [])
                ]
                
                if not records:
                    return {
                        "type": "info",
                        "message": f"📭 未找到标签为\"{tag}\"的记录\n\n发送\"0\"返回子菜单"
                    }
                
                message = f"🏷️ 标签\"{tag}\"的记录（{len(records)} 条）：\n\n"
                for i, record in enumerate(records[:15], 1):
                    summary = record.structured_data.get('summary', '')
                    date_str = record.structured_data.get('fields', {}).get('date', '')
                    message += f"[{i}] 🆔 ID: {record.id}\n"
                    message += f"    📝 {summary}\n"
                    message += f"    📅 {date_str}\n\n"
                
                if len(records) > 15:
                    message += f"... 还有 {len(records) - 15} 条记录\n\n"
                
                message += "发送\"0\"返回子菜单"
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return {
                    "type": "success",
                    "message": message
                }
            elif query_mode == "mood":
                mood = content.strip()
                all_records = self.manager.db.query_records(
                    filters=filters,
                    user_id=self.user_id
                )
                records = [
                    r for r in all_records 
                    if r.structured_data.get('fields', {}).get('mood') == mood
                ]
                
                if not records:
                    return {
                        "type": "info",
                        "message": f"📭 未找到心情为\"{mood}\"的记录\n\n发送\"0\"返回子菜单"
                    }
                
                message = f"😊 心情\"{mood}\"的记录（{len(records)} 条）：\n\n"
                for i, record in enumerate(records[:15], 1):
                    summary = record.structured_data.get('summary', '')
                    date_str = record.structured_data.get('fields', {}).get('date', '')
                    message += f"[{i}] 🆔 ID: {record.id}\n"
                    message += f"    📝 {summary}\n"
                    message += f"    📅 {date_str}\n\n"
                
                if len(records) > 15:
                    message += f"... 还有 {len(records) - 15} 条记录\n\n"
                
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
                        "message": f"📭 未找到包含\"{content}\"的记录\n\n发送\"0\"返回子菜单"
                    }
                
                message = f"🔍 找到 {len(records)} 条记录：\n\n"
                for i, record in enumerate(records, 1):
                    summary = record.structured_data.get('summary', '')
                    date_str = record.structured_data.get('fields', {}).get('date', '')
                    message += f"[{i}] 🆔 ID: {record.id}\n"
                    message += f"    📝 {summary}\n"
                    message += f"    📅 {date_str}\n\n"
                
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
        """处理修改随笔"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        return {
            "type": "info",
            "message": "✏️ 修改功能暂未实现，请使用删除+添加的方式\n\n发送\"0\"返回子菜单"
        }
    
    def _handle_delete(self, content: str) -> Dict[str, Any]:
        """处理删除随笔"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        try:
            record_id = int(content.strip())
            success = self.manager.db.delete_record(record_id, user_id=self.user_id, bot_id=self.bot_id)
            
            if success:
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return {
                    "type": "success",
                    "message": f"✅ 记录 ID {record_id} 已删除\n\n发送\"0\"返回子菜单"
                }
            else:
                return {
                    "type": "error",
                    "message": f"❌ 记录 ID {record_id} 不存在\n\n发送\"0\"返回子菜单"
                }
        except ValueError:
            return {
                "type": "error",
                "message": "❌ 请输入有效的记录ID（数字）"
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
                "message": f"✅ 已切换到表/目录: {new_table}\n\n发送\"0\"返回子菜单"
            }
        
        return {
            "type": "error",
            "message": "❌ 表/目录名称不能为空"
        }
    
    def _handle_list_tables(self) -> Dict[str, Any]:
        """处理查看所有表/目录"""
        try:
            stats = self.manager.db.get_statistics(
                filters={"record_type": "随笔"},
                user_id=self.user_id,
                bot_id=self.bot_id
            )
            by_table = stats.get('by_table', {})
            
            if not by_table:
                return {
                    "type": "info",
                    "message": "📭 暂无表/目录\n\n发送\"0\"返回子菜单"
                }
            
            message = "📋 所有表/目录：\n\n"
            for table_name, count in by_table.items():
                marker = " ← 当前" if table_name == self.manager.table_name else ""
                message += f"  📁 {table_name}: {count} 条记录{marker}\n"
            
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
    
    def _show_analysis_menu(self) -> Dict[str, Any]:
        """显示AI分析菜单"""
        menu_text = """🤖 【AI分析随笔】

请选择分析方式：
  1. 📋 分析所有记录
  2. 📅 按日期分析（单日）
  3. 🆔 按记录ID分析
  0. 🔙 返回

💡 请输入数字选择（0-3）"""
        
        session_manager.get_session(self.bot_id, self.user_id).context["analysis_mode"] = "menu"
        return {
            "type": "sub_menu",
            "message": menu_text
        }
    
    def _handle_analysis(self, content: str) -> Dict[str, Any]:
        """处理AI分析"""
        session = session_manager.get_session(self.bot_id, self.user_id)
        analysis_mode = session.context.get("analysis_mode", "menu")
        
        if content.strip() == "0":
            if analysis_mode == "menu":
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return self.show_sub_menu()
            else:
                session.context["analysis_mode"] = "menu"
                return self._show_analysis_menu()
        
        if analysis_mode == "menu":
            choice = content.strip()
            if choice == "1":
                return self._analyze_all()
            elif choice == "2":
                session.context["analysis_mode"] = "date"
                return {
                    "type": "prompt",
                    "message": "📅 请输入日期 (YYYY-MM-DD)，或发送\"0\"返回"
                }
            elif choice == "3":
                session.context["analysis_mode"] = "id"
                return {
                    "type": "prompt",
                    "message": "🆔 请输入记录ID，或发送\"0\"返回"
                }
            else:
                return {
                    "type": "error",
                    "message": f"分析方式 {choice} 暂未实现，请选择 1-3"
                }
        else:
            # 执行具体分析
            return self._execute_analysis(content, analysis_mode)
    
    def _analyze_all(self) -> Dict[str, Any]:
        """分析所有记录"""
        try:
            filters = {
                "record_type": "随笔",
                "table_name": self.manager.table_name
            }
            records = self.manager.db.query_records(
                filters=filters,
                limit=10,
                order_by="-created_at",
                user_id=self.user_id,
                bot_id=self.bot_id
            )
            
            if not records:
                return {
                    "type": "info",
                    "message": "📭 暂无随笔记录\n\n发送\"0\"返回子菜单"
                }
            
            # 格式化记录用于分析
            formatted_essays = []
            for record in records:
                fields = record.structured_data.get('fields', {})
                formatted_essays.append({
                    "id": record.id,
                    "content": fields.get('content', record.original_text),
                    "date": fields.get('date', record.created_at.strftime('%Y-%m-%d')),
                    "tags": "、".join(fields.get('tags', [])),
                    "mood": fields.get('mood', ''),
                    "location": fields.get('location', '')
                })
            
            # 格式化随笔内容用于分析
            essays_text = "\n\n".join([
                f"随笔 {essay['id']} ({essay['date']}):\n{essay['content'][:500]}"
                for essay in formatted_essays
            ])
            
            # 使用LLM分析
            analysis_text = self.manager.llm_client.analyze(
                content=essays_text,
                custom_prompt=ESSAY_ANALYSIS_PROMPT.format(
                    essay_content=essays_text,
                    essay_date="、".join([essay['date'] for essay in formatted_essays]),
                    essay_tags="、".join([essay['tags'] for essay in formatted_essays if essay['tags']]),
                    essay_mood="、".join([essay['mood'] for essay in formatted_essays if essay['mood']]),
                    essay_location="、".join([essay['location'] for essay in formatted_essays if essay['location']])
                )
            )
            
            message = f"📊 分析了 {len(records)} 条记录\n\n"
            message += f"【AI分析结果】\n\n{analysis_text}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return {
                "type": "success",
                "message": message
            }
        except Exception as e:
            logger.error(f"分析失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"分析失败: {str(e)}"
            }
    
    def _execute_analysis(self, content: str, analysis_mode: str) -> Dict[str, Any]:
        """执行分析"""
        try:
            if analysis_mode == "id":
                try:
                    record_id = int(content.strip())
                    record = self.manager.db.get_record(record_id, user_id=self.user_id, bot_id=self.bot_id)
                    
                    if not record or record.record_type != "随笔":
                        return {
                            "type": "error",
                            "message": f"❌ 记录 ID {record_id} 不存在或不是随笔记录\n\n发送\"0\"返回"
                        }
                    
                    fields = record.structured_data.get('fields', {})
                    essay_content = fields.get('content', record.original_text)
                    essay_date = fields.get('date', record.created_at.strftime('%Y-%m-%d'))
                    essay_tags = "、".join(fields.get('tags', []))
                    essay_mood = fields.get('mood', '')
                    essay_location = fields.get('location', '')
                    
                    # 构建分析prompt
                    analysis_prompt = ESSAY_ANALYSIS_PROMPT.format(
                        essay_content=essay_content,
                        essay_date=essay_date,
                        essay_tags=essay_tags or "无",
                        essay_mood=essay_mood or "未指定",
                        essay_location=essay_location or "未指定"
                    )
                    
                    # 使用LLM分析
                    analysis_text = self.manager.llm_client.analyze(
                        content=essay_content,
                        custom_prompt=analysis_prompt
                    )
                    
                    message = f"📊 记录 ID {record_id} 的分析结果：\n\n"
                    message += f"{analysis_text}\n\n"
                    message += f"发送\"0\"返回子菜单"
                    
                    session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                    return {
                        "type": "success",
                        "message": message
                    }
                except ValueError:
                    return {
                        "type": "error",
                        "message": "❌ 请输入有效的记录ID（数字）"
                    }
            elif analysis_mode == "date":
                filters = {
                    "record_type": "随笔",
                    "table_name": self.manager.table_name,
                    "date_from": content.strip(),
                    "date_to": content.strip()
                }
                records = self.manager.db.query_records(
                    filters=filters,
                    user_id=self.user_id
                )
                
                if not records:
                    return {
                        "type": "info",
                        "message": f"📭 未找到 {content} 的记录\n\n发送\"0\"返回子菜单"
                    }
                
                # 格式化记录用于分析
                formatted_essays = []
                for record in records:
                    fields = record.structured_data.get('fields', {})
                    formatted_essays.append({
                        "id": record.id,
                        "content": fields.get('content', record.original_text),
                        "date": fields.get('date', record.created_at.strftime('%Y-%m-%d')),
                        "tags": "、".join(fields.get('tags', [])),
                        "mood": fields.get('mood', ''),
                        "location": fields.get('location', '')
                    })
                
                # 格式化随笔内容用于分析
                essays_text = "\n\n".join([
                    f"随笔 {essay['id']} ({essay['date']}):\n{essay['content'][:500]}"
                    for essay in formatted_essays
                ])
                
                # 使用LLM分析
                analysis_text = self.manager.llm_client.analyze(
                    content=essays_text,
                    custom_prompt=ESSAY_ANALYSIS_PROMPT.format(
                        essay_content=essays_text,
                        essay_date="、".join([essay['date'] for essay in formatted_essays]),
                        essay_tags="、".join([essay['tags'] for essay in formatted_essays if essay['tags']]),
                        essay_mood="、".join([essay['mood'] for essay in formatted_essays if essay['mood']]),
                        essay_location="、".join([essay['location'] for essay in formatted_essays if essay['location']])
                    )
                )
                
                message = f"📊 {content} 的记录分析（{len(records)} 条）：\n\n"
                message += f"【AI分析结果】\n\n{analysis_text}\n\n"
                message += f"发送\"0\"返回子菜单"
                
                session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
                return {
                    "type": "success",
                    "message": message
                }
        
        except Exception as e:
            logger.error(f"分析失败: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"分析失败: {str(e)}"
            }
        
        return {
            "type": "error",
            "message": f"分析模式 {analysis_mode} 暂未实现"
        }
