"""
塔罗牌服务 - 微信平台适配器
调用 TarotManager 的业务逻辑，适配微信消息驱动模式
"""
from typing import Dict, Any, Optional

from business.tarot.manager import TarotManager
from business.tarot.tarot_cards import TarotService as BaseTarotService, SpreadType
from core.llm import LLMClient
from business.tarot.prompts import (
    TAROT_SYSTEM_MESSAGE,
    SINGLE_CARD_PROMPT,
    THREE_CARD_PROMPT,
    FIVE_CARD_PROMPT
)
from shared.utils import setup_logger
from shared.message_utils import format_message

from interfaces.wechat.session_manager import session_manager
from interfaces.wechat.task_manager import task_manager

logger = setup_logger(__name__)


class TarotService:
    """塔罗牌服务 - 微信适配器，调用 Manager 的业务逻辑"""
    
    def __init__(self, user_id: str, bot_id: str = "default"):
        self.user_id = user_id
        self.bot_id = bot_id
        # 使用 Manager 层，Manager 使用 core 的基础能力
        self.manager = TarotManager(user_id=user_id, debug=False)
        # Manager 已经初始化了这些，直接使用
        self.tarot_service = self.manager.tarot_service
        self.llm_client = self.manager.llm_client
    
    def show_sub_menu(self) -> Dict[str, Any]:
        """显示塔罗牌占卜子菜单"""
        menu_text = """🔮 塔罗牌占卜系统 🔮

✨ 请选择操作：
  1. 🔮 单张牌占卜
  2. 📜 三张牌占卜
     （过去-现在-未来）
  3. ⭐ 五张牌占卜
     （凯尔特十字简化版）
  4. 📖 查看塔罗牌知识
  0. 🚪 退出

💡 请输入数字选择（0-4）"""
        
        return {
            "type": "sub_menu",
            "message": menu_text,
            "action": "show_sub_menu"
        }
    
    def process_message(self, content: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理塔罗牌消息"""
        session = session_manager.get_session(self.bot_id, self.user_id)
        sub_menu = session.sub_menu
        
        if sub_menu is None:
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
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
            session_manager.reset_to_menu(self.bot_id, self.user_id)
            try:
                from interfaces.wechat.menu_handler import MenuHandler
            except ImportError:
                from interfaces.cli.menu import MenuHandler
            return MenuHandler.show_menu()
        elif choice == "1":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "single")
            return {
                "type": "prompt",
                "message": "🔮 单张牌占卜\n\n单张牌占卜适合快速了解当前状况或某个问题的答案。\n\n你可以输入一个问题（可选），或直接发送\"抽牌\"开始抽牌\n\n发送\"0\"可返回子菜单"
            }
        elif choice == "2":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "three_card")
            return {
                "type": "prompt",
                "message": "📜 三张牌占卜（过去-现在-未来）\n\n你可以输入一个问题（可选），或直接发送\"抽牌\"开始抽牌\n\n发送\"0\"可返回子菜单"
            }
        elif choice == "3":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "five_card")
            return {
                "type": "prompt",
                "message": "⭐ 五张牌占卜（凯尔特十字简化版）\n\n你可以输入一个问题（可选），或直接发送\"抽牌\"开始抽牌\n\n发送\"0\"可返回子菜单"
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
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        question = content.strip() if content.strip() and content.strip() != "抽牌" else None
        
        # 检查是否已有任务在处理
        task = task_manager.get_task(self.bot_id, self.user_id)
        if task and task.status == "processing":
            elapsed = task.get_elapsed_time()
            return {
                "type": "processing",
                "message": f"⏳ 正在处理中...\n\n任务类型: {task.task_type}\n已处理时间: {elapsed:.1f}秒\n\n如需取消，请发送\"取消\""
            }
        
        # 启动任务
        task_manager.start_task(self.bot_id, self.user_id, "tarot_single", question or "单张牌占卜")
        
        try:
            # 抽牌
            cards = self.tarot_service.draw_spread(SpreadType.SINGLE)
            card = cards[0]
            
            # 检查任务是否已取消
            task = task_manager.get_task(self.bot_id, self.user_id)
            if task and task.cancelled:
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 生成解读
            card_info = f"{card['name']} ({card.get('name_en', '')}) - {'正位' if card.get('upright', True) else '逆位'} {'⬆️' if card.get('upright', True) else '⬇️'}"
            prompt = SINGLE_CARD_PROMPT.format(
                card_info=card_info,
                question=question or "无",
                card_name=card['name'],
                position_emoji="⬆️" if card.get("upright", True) else "⬇️"
            )
            
            interpretation = self.llm_client.chat(
                messages=[
                    {"role": "system", "content": TAROT_SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1500
            )
            
            # 再次检查任务是否已取消
            task = task_manager.get_task(self.bot_id, self.user_id)
            if task and task.cancelled:
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 美化AI返回的解读结果
            interpretation = format_message(interpretation)
            
            # 构建消息
            position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
            message = f"✨ 你抽到的牌 ✨\n\n"
            message += f"🔮 牌名：{card['name']}\n"
            message += f"📖 英文名：{card.get('name_en', '')}\n"
            message += f"🎴 花色：{card.get('suit', '')}\n"
            message += f"📍 位置：{'正位' if card.get('upright', True) else '逆位'} {position_emoji}\n\n"
            
            if question:
                message += f"问题: {question}\n\n"
            
            message += f"🌟 塔罗牌解读 🌟\n\n{interpretation}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            task_manager.complete_task(self.bot_id, self.user_id, {
                "card": card,
                "question": question,
                "interpretation": interpretation
            })
            
            return {
                "type": "success",
                "message": message
            }
        
        except Exception as e:
            logger.error(f"单张牌占卜失败: {e}", exc_info=True)
            task_manager.complete_task(self.bot_id, self.user_id, None, error=str(e))
            return {
                "type": "error",
                "message": f"占卜失败: {str(e)}"
            }
    
    def _handle_three_card(self, content: str) -> Dict[str, Any]:
        """处理三张牌占卜"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        question = content.strip() if content.strip() and content.strip() != "抽牌" else None
        
        task = task_manager.get_task(self.bot_id, self.user_id)
        if task and task.status == "processing":
            elapsed = task.get_elapsed_time()
            return {
                "type": "processing",
                "message": f"⏳ 正在处理中...\n\n已处理时间: {elapsed:.1f}秒"
            }
        
        task_manager.start_task(self.bot_id, self.user_id, "tarot_three_card", question or "三张牌占卜")
        
        try:
            cards = self.tarot_service.draw_spread(SpreadType.THREE_CARD)
            
            task = task_manager.get_task(self.bot_id, self.user_id)
            if task and task.cancelled:
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 生成解读
            card_info_lines = []
            positions = ["过去", "现在", "未来"]
            for i, card in enumerate(cards):
                position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
                card_info_lines.append(
                    f"{positions[i]}：{card['name']} ({card.get('name_en', '')}) - {position_emoji}"
                )
            card_info = "\n".join(card_info_lines)
            
            prompt = THREE_CARD_PROMPT.format(
                cards_info=card_info,
                question=question or "无",
                past_card=cards[0]['name'],
                present_card=cards[1]['name'],
                future_card=cards[2]['name']
            )
            
            interpretation = self.llm_client.chat(
                messages=[
                    {"role": "system", "content": TAROT_SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2000
            )
            
            task = task_manager.get_task(self.bot_id, self.user_id)
            if task and task.cancelled:
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 美化AI返回的解读结果
            interpretation = format_message(interpretation)
            
            message = f"✨ 你抽到的三张牌 ✨\n\n"
            message += f"📜 过去：{cards[0]['name']} {'⬆️' if cards[0].get('upright', True) else '⬇️'}\n"
            message += f"💫 现在：{cards[1]['name']} {'⬆️' if cards[1].get('upright', True) else '⬇️'}\n"
            message += f"🔮 未来：{cards[2]['name']} {'⬆️' if cards[2].get('upright', True) else '⬇️'}\n\n"
            
            if question:
                message += f"问题: {question}\n\n"
            
            message += f"🌟 塔罗牌解读 🌟\n\n{interpretation}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            task_manager.complete_task(self.bot_id, self.user_id, {
                "cards": cards,
                "question": question,
                "interpretation": interpretation
            })
            
            return {
                "type": "success",
                "message": message
            }
        
        except Exception as e:
            logger.error(f"三张牌占卜失败: {e}", exc_info=True)
            task_manager.complete_task(self.bot_id, self.user_id, None, error=str(e))
            return {
                "type": "error",
                "message": f"占卜失败: {str(e)}"
            }
    
    def _handle_five_card(self, content: str) -> Dict[str, Any]:
        """处理五张牌占卜"""
        if content.strip() == "0":
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            return self.show_sub_menu()
        
        question = content.strip() if content.strip() and content.strip() != "抽牌" else None
        
        task = task_manager.get_task(self.bot_id, self.user_id)
        if task and task.status == "processing":
            elapsed = task.get_elapsed_time()
            return {
                "type": "processing",
                "message": f"⏳ 正在处理中...\n\n已处理时间: {elapsed:.1f}秒"
            }
        
        task_manager.start_task(self.bot_id, self.user_id, "tarot_five_card", question or "五张牌占卜")
        
        try:
            cards = self.tarot_service.draw_spread(SpreadType.FIVE_CARD)
            
            task = task_manager.get_task(self.bot_id, self.user_id)
            if task and task.cancelled:
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 生成解读
            card_info_lines = []
            positions = ["现状", "挑战", "过去", "未来", "结果"]
            for i, card in enumerate(cards):
                position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
                card_info_lines.append(
                    f"{positions[i]}：{card['name']} ({card.get('name_en', '')}) - {position_emoji}"
                )
            card_info = "\n".join(card_info_lines)
            
            prompt = FIVE_CARD_PROMPT.format(
                cards_info=card_info,
                question=question or "无",
                position1=cards[0]['name'],
                position2=cards[1]['name'],
                position3=cards[2]['name'],
                position4=cards[3]['name'],
                position5=cards[4]['name']
            )
            
            interpretation = self.llm_client.chat(
                messages=[
                    {"role": "system", "content": TAROT_SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2500
            )
            
            task = task_manager.get_task(self.bot_id, self.user_id)
            if task and task.cancelled:
                return {
                    "type": "info",
                    "message": "❌ 任务已取消\n\n发送\"0\"返回子菜单"
                }
            
            # 美化AI返回的解读结果
            interpretation = format_message(interpretation)
            
            message = f"✨ 你抽到的五张牌 ✨\n\n"
            positions = ["现状", "挑战", "过去", "未来", "结果"]
            emojis = ["📍", "⚡", "📜", "🔮", "🌟"]
            for i, card in enumerate(cards):
                message += f"{emojis[i]} {positions[i]}：{card['name']} {'⬆️' if card.get('upright', True) else '⬇️'}\n"
            message += "\n"
            
            if question:
                message += f"问题: {question}\n\n"
            
            message += f"🌟 塔罗牌解读 🌟\n\n{interpretation}\n\n"
            message += f"发送\"0\"返回子菜单"
            
            session_manager.set_sub_menu(self.bot_id, self.user_id, "main")
            task_manager.complete_task(self.bot_id, self.user_id, {
                "cards": cards,
                "question": question,
                "interpretation": interpretation
            })
            
            return {
                "type": "success",
                "message": message
            }
        
        except Exception as e:
            logger.error(f"五张牌占卜失败: {e}", exc_info=True)
            task_manager.complete_task(self.bot_id, self.user_id, None, error=str(e))
            return {
                "type": "error",
                "message": f"占卜失败: {str(e)}"
            }
    
    def _handle_knowledge(self) -> Dict[str, Any]:
        """处理查看塔罗牌知识"""
        knowledge_text = """📖 塔罗牌知识

塔罗牌（Tarot）是一套用于占卜和灵性指导的卡牌系统。

**牌组构成：**
- 大阿卡纳（Major Arcana）：22张，代表人生的重要阶段和主题
- 小阿卡纳（Minor Arcana）：56张，分为四个花色
  - 权杖（Wands）：代表行动、创造、热情
  - 圣杯（Cups）：代表情感、直觉、关系
  - 宝剑（Swords）：代表思想、沟通、冲突
  - 星币（Pentacles）：代表物质、金钱、实际

**正位与逆位：**
- 正位（⬆️）：牌的正常含义，通常代表积极或直接的能量
- 逆位（⬇️）：牌的相反含义，可能表示阻碍、延迟或需要反思

**牌阵类型：**
- 单张牌：快速了解当前状况
- 三张牌（过去-现在-未来）：了解时间线上的发展
- 五张牌（凯尔特十字简化版）：提供更全面的洞察

**使用建议：**
- 保持开放和专注的心态
- 可以针对具体问题提问
- 将解读作为参考和启发，而非绝对预言

发送\"0\"返回子菜单"""
        
        session_manager.set_sub_menu(self.user_id, "main")
        return {
            "type": "info",
            "message": knowledge_text
        }
