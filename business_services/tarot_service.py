"""
塔罗牌服务
处理塔罗牌占卜业务逻辑，适配微信消息驱动模式，支持完整子菜单
"""
from typing import Dict, Any, Optional

from agent_tarot.tarot_service import TarotService as BaseTarotService, SpreadType
from agent_tarot.llm_client import TarotLLMClient
from shared.utils import setup_logger
from agent_wechat.session_manager import session_manager
from agent_wechat.task_manager import task_manager

logger = setup_logger(__name__)


class TarotService:
    """塔罗牌服务"""
    
    def __init__(self, user_id: str):
        """
        初始化塔罗牌服务
        
        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.tarot_service = BaseTarotService()
        self.llm_client = TarotLLMClient()
    
    def show_sub_menu(self) -> Dict[str, Any]:
        """显示塔罗牌占卜子菜单"""
        menu_text = """============================================================
🔮 塔罗牌占卜系统 🔮
============================================================

请选择操作：
  1. 🔮 单张牌占卜
  2. 📜 三张牌占卜（过去-现在-未来）
  3. ⭐ 五张牌占卜（凯尔特十字简化版）
  4. 📖 查看塔罗牌知识
  0. 退出
============================================================

请输入数字选择（0-4）"""
        
        return {
            "type": "sub_menu",
            "message": menu_text,
            "action": "show_sub_menu"
        }
    
    def process_message(self, content: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理塔罗牌消息
        
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
        elif sub_menu == "single":
            return self._handle_single_card(content)
        elif sub_menu == "three_card":
            return self._handle_three_card(content)
        elif sub_menu == "five_card":
            return self._handle_five_card(content)
        elif sub_menu == "knowledge":
            return self._handle_knowledge()
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
            session_manager.set_sub_menu(self.user_id, "single")
            return {
                "type": "prompt",
                "message": "🔮 单张牌占卜\n\n单张牌占卜适合快速了解当前状况或某个问题的答案。\n\n你可以输入一个问题（可选），或直接发送\"抽牌\"开始抽牌\n\n发送\"0\"可返回子菜单"
            }
        elif choice == "2":
            session_manager.set_sub_menu(self.user_id, "three_card")
            return {
                "type": "prompt",
                "message": "📜 三张牌占卜（过去-现在-未来）\n\n三张牌占卜可以帮助你了解：\n  📜 过去：影响当前状况的过去因素\n  💫 现在：当前的状况和能量\n  🔮 未来：可能的发展方向\n\n你可以输入一个问题（可选），或直接发送\"抽牌\"开始抽牌\n\n发送\"0\"可返回子菜单"
            }
        elif choice == "3":
            session_manager.set_sub_menu(self.user_id, "five_card")
            return {
                "type": "prompt",
                "message": "⭐ 五张牌占卜（凯尔特十字简化版）\n\n五张牌占卜提供更全面的洞察：\n  📍 现状：当前的情况\n  ⚡ 挑战：面临的挑战或阻碍\n  📜 过去：影响现状的过去因素\n  🔮 未来：可能的发展方向\n  🌟 结果：最终可能的结果\n\n你可以输入一个问题（可选），或直接发送\"抽牌\"开始抽牌\n\n发送\"0\"可返回子菜单"
            }
        elif choice == "4":
            return self._handle_knowledge()
        else:
            return {
                "type": "error",
                "message": f"无效选择：{choice}，请输入 0-4 之间的数字"
            }
    
    def _handle_single_card(self, content: str) -> Dict[str, Any]:
        """处理单张牌占卜"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.user_id, "main")
            return self.show_sub_menu()
        
        question = content.strip() if content.strip() and content.strip() != "抽牌" else None
        
        # 检查是否已有任务在处理
        task = task_manager.get_task(self.user_id)
        if task and task.status == "processing":
            # 如果任务正在处理，返回处理中状态
            elapsed = task.get_elapsed_time()
            return {
                "type": "processing",
                "message": f"⏳ 正在处理中...\n\n任务类型: {task.task_type}\n已处理时间: {elapsed:.1f}秒\n\n如需取消，请发送\"取消\""
            }
        
        # 启动任务
        task_manager.start_task(self.user_id, "tarot_single", question or "单张牌占卜")
        
        try:
            # 抽牌
            cards = self.tarot_service.draw_spread("single")
            card = cards[0]
            
            # 在调用LLM前检查任务是否已取消
            task = task_manager.get_task(self.user_id)
            if task and task.cancelled:
                logger.info(f"任务已取消，停止处理: user_id={self.user_id}")
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 生成解读（这里会调用LLM，可能需要较长时间）
            interpretation = self.llm_client.interpret_tarot(
                cards=cards,
                spread_type="single",
                question=question
            )
            
            # 调用LLM后再次检查任务是否已取消
            task = task_manager.get_task(self.user_id)
            if task and task.cancelled:
                logger.info(f"任务在处理过程中被取消: user_id={self.user_id}")
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 构建消息
            position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
            message = f"✨ 你抽到的牌 ✨\n\n"
            message += f"🔮 牌名：{card['name']}\n"
            message += f"📖 英文名：{card.get('name_en', '')}\n"
            message += f"🎴 花色：{card.get('suit', '')}\n"
            message += f"📍 位置：{card.get('position', '正位')} {position_emoji}\n\n"
            
            if question:
                message += f"问题: {question}\n\n"
            
            message += f"🌟 塔罗牌解读 🌟\n\n{interpretation}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            # 重置到主菜单状态
            session_manager.set_sub_menu(self.user_id, "main")
            
            # 完成任务
            task_manager.complete_task(self.user_id, {
                "card": card,
                "question": question,
                "interpretation": interpretation
            })
            
            return {
                "type": "success",
                "message": message,
                "data": {
                    "card": card,
                    "question": question,
                    "interpretation": interpretation
                }
            }
            
        except Exception as e:
            logger.error(f"单张牌占卜失败: {e}", exc_info=True)
            # 取消任务
            task_manager.cancel_task(self.user_id)
            return {
                "type": "error",
                "message": f"占卜失败: {str(e)}\n\n发送\"0\"返回子菜单"
            }
    
    def _handle_three_card(self, content: str) -> Dict[str, Any]:
        """处理三张牌占卜"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.user_id, "main")
            return self.show_sub_menu()
        
        question = content.strip() if content.strip() and content.strip() != "抽牌" else None
        
        # 检查是否已有任务在处理
        task = task_manager.get_task(self.user_id)
        if task and task.status == "processing":
            elapsed = task.get_elapsed_time()
            return {
                "type": "processing",
                "message": f"⏳ 正在处理中...\n\n任务类型: {task.task_type}\n已处理时间: {elapsed:.1f}秒\n\n如需取消，请发送\"取消\""
            }
        
        # 启动任务
        task_manager.start_task(self.user_id, "tarot_three_card", question or "三张牌占卜")
        
        try:
            # 抽牌
            cards = self.tarot_service.draw_spread("three_card")
            positions = self.tarot_service.get_spread_positions("three_card")
            
            # 在调用LLM前检查任务是否已取消
            task = task_manager.get_task(self.user_id)
            if task and task.cancelled:
                logger.info(f"任务已取消，停止处理: user_id={self.user_id}")
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 生成解读（这里会调用LLM，可能需要较长时间）
            interpretation = self.llm_client.interpret_tarot(
                cards=cards,
                spread_type="three_card",
                question=question
            )
            
            # 调用LLM后再次检查任务是否已取消
            task = task_manager.get_task(self.user_id)
            if task and task.cancelled:
                logger.info(f"任务在处理过程中被取消: user_id={self.user_id}")
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 构建消息
            message = f"✨ 你抽到的三张牌 ✨\n\n"
            for i, card in enumerate(cards):
                position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
                pos_name = positions[i] if i < len(positions) else f'位置{i+1}'
                message += f"📌 {pos_name}:\n"
                message += f"   🔮 牌名：{card['name']}\n"
                message += f"   📖 英文名：{card.get('name_en', '')}\n"
                message += f"   📍 位置：{card.get('position', '正位')} {position_emoji}\n\n"
            
            if question:
                message += f"问题: {question}\n\n"
            
            message += f"🌟 塔罗牌解读 🌟\n\n{interpretation}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            # 重置到主菜单状态
            session_manager.set_sub_menu(self.user_id, "main")
            
            # 完成任务
            task_manager.complete_task(self.user_id, {
                "cards": cards,
                "question": question,
                "interpretation": interpretation
            })
            
            return {
                "type": "success",
                "message": message,
                "data": {
                    "cards": cards,
                    "question": question,
                    "interpretation": interpretation
                }
            }
            
        except Exception as e:
            logger.error(f"三张牌占卜失败: {e}", exc_info=True)
            # 取消任务
            task_manager.cancel_task(self.user_id)
            return {
                "type": "error",
                "message": f"占卜失败: {str(e)}\n\n发送\"0\"返回子菜单"
            }
    
    def _handle_five_card(self, content: str) -> Dict[str, Any]:
        """处理五张牌占卜"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.user_id, "main")
            return self.show_sub_menu()
        
        question = content.strip() if content.strip() and content.strip() != "抽牌" else None
        
        # 检查是否已有任务在处理
        task = task_manager.get_task(self.user_id)
        if task and task.status == "processing":
            elapsed = task.get_elapsed_time()
            return {
                "type": "processing",
                "message": f"⏳ 正在处理中...\n\n任务类型: {task.task_type}\n已处理时间: {elapsed:.1f}秒\n\n如需取消，请发送\"取消\""
            }
        
        # 启动任务
        task_manager.start_task(self.user_id, "tarot_five_card", question or "五张牌占卜")
        
        try:
            # 抽牌
            cards = self.tarot_service.draw_spread("five_card")
            positions = self.tarot_service.get_spread_positions("five_card")
            
            # 在调用LLM前检查任务是否已取消
            task = task_manager.get_task(self.user_id)
            if task and task.cancelled:
                logger.info(f"任务已取消，停止处理: user_id={self.user_id}")
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 生成解读（这里会调用LLM，可能需要较长时间）
            interpretation = self.llm_client.interpret_tarot(
                cards=cards,
                spread_type="five_card",
                question=question
            )
            
            # 调用LLM后再次检查任务是否已取消
            task = task_manager.get_task(self.user_id)
            if task and task.cancelled:
                logger.info(f"任务在处理过程中被取消: user_id={self.user_id}")
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 构建消息
            message = f"✨ 你抽到的五张牌 ✨\n\n"
            for i, card in enumerate(cards):
                position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
                pos_name = positions[i] if i < len(positions) else f'位置{i+1}'
                message += f"📌 {pos_name}:\n"
                message += f"   🔮 牌名：{card['name']}\n"
                message += f"   📖 英文名：{card.get('name_en', '')}\n"
                message += f"   📍 位置：{card.get('position', '正位')} {position_emoji}\n\n"
            
            if question:
                message += f"问题: {question}\n\n"
            
            message += f"🌟 塔罗牌解读 🌟\n\n{interpretation}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            # 重置到主菜单状态
            session_manager.set_sub_menu(self.user_id, "main")
            
            # 完成任务
            task_manager.complete_task(self.user_id, {
                "cards": cards,
                "question": question,
                "interpretation": interpretation
            })
            
            return {
                "type": "success",
                "message": message,
                "data": {
                    "cards": cards,
                    "question": question,
                    "interpretation": interpretation
                }
            }
            
        except Exception as e:
            logger.error(f"五张牌占卜失败: {e}", exc_info=True)
            # 取消任务
            task_manager.cancel_task(self.user_id)
            return {
                "type": "error",
                "message": f"占卜失败: {str(e)}\n\n发送\"0\"返回子菜单"
            }
    
    def _handle_knowledge(self) -> Dict[str, Any]:
        """显示塔罗牌知识"""
        knowledge_text = """📖 塔罗牌知识

🔮 **塔罗牌简介**
塔罗牌是一套78张的占卜工具，分为：
  • 大阿卡纳（22张）：代表人生的重要阶段和重大事件
  • 小阿卡纳（56张）：代表日常生活中的各种情况
    - 权杖（Wands）：代表行动、创造、热情
    - 圣杯（Cups）：代表情感、直觉、关系
    - 宝剑（Swords）：代表思想、沟通、挑战
    - 星币（Pentacles）：代表物质、工作、财富

📌 **正位与逆位**
  • 正位（⬆️）：牌的正常含义，通常代表正面或直接的能量
  • 逆位（⬇️）：牌的反向含义，可能代表阻碍、延迟或内在的挑战

💫 **牌阵类型**
  • 单张牌：快速了解当前状况或某个问题的答案
  • 三张牌（过去-现在-未来）：了解时间线上的发展
  • 五张牌（凯尔特十字简化版）：提供更全面的洞察

🌟 **使用建议**
  • 保持开放和专注的心态
  • 可以针对具体问题提问，也可以进行开放式占卜
  • 塔罗牌是引导和启发，最终的选择权在你手中

发送"0"返回子菜单"""
        
        session_manager.set_sub_menu(self.user_id, "main")
        return {
            "type": "info",
            "message": knowledge_text
        }
