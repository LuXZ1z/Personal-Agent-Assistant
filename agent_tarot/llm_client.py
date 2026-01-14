"""
塔罗牌LLM客户端
专门用于塔罗牌解读
"""
import time
from typing import Optional, List, Dict, Any
from openai import OpenAI, APIError

from shared.config import settings
from shared.utils import setup_logger
from agent_tarot.prompt_templates import (
    TAROT_SYSTEM_MESSAGE,
    SINGLE_CARD_PROMPT,
    THREE_CARD_PROMPT,
    FIVE_CARD_PROMPT
)

logger = setup_logger(__name__)


class TarotLLMClient:
    """塔罗牌LLM客户端"""
    
    def __init__(self):
        """初始化LLM客户端"""
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        self.max_retries = 3
        self.retry_delay = 1  # 秒
    
    def interpret_tarot(
        self,
        cards: List[Dict[str, Any]],
        spread_type: str = "single",
        question: Optional[str] = None
    ) -> str:
        """
        解读塔罗牌
        
        Args:
            cards: 抽取的牌列表
            spread_type: 牌阵类型
            question: 用户的问题（可选）
            
        Returns:
            解读文本
        """
        # 构建牌信息字符串
        card_info_lines = []
        for i, card in enumerate(cards):
            position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
            card_info_lines.append(
                f"{card['name']} ({card['name_en']}) - {card.get('position', '正位')} {position_emoji}"
            )
        card_info = "\n".join(card_info_lines)
        
        # 根据牌阵类型选择prompt模板
        if spread_type == "single":
            card = cards[0]
            position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
            prompt = SINGLE_CARD_PROMPT.format(
                card_info=card_info,
                question=question or "无",
                card_name=card['name'],
                position_emoji=position_emoji
            )
        elif spread_type == "three_card":
            prompt = THREE_CARD_PROMPT.format(
                cards_info=card_info,
                question=question or "无",
                past_card=cards[0]['name'] if len(cards) > 0 else "",
                present_card=cards[1]['name'] if len(cards) > 1 else "",
                future_card=cards[2]['name'] if len(cards) > 2 else ""
            )
        elif spread_type == "five_card":
            prompt = FIVE_CARD_PROMPT.format(
                cards_info=card_info,
                question=question or "无",
                position1=cards[0]['name'] if len(cards) > 0 else "",
                position2=cards[1]['name'] if len(cards) > 1 else "",
                position3=cards[2]['name'] if len(cards) > 2 else "",
                position4=cards[3]['name'] if len(cards) > 3 else "",
                position5=cards[4]['name'] if len(cards) > 4 else ""
            )
        else:
            card = cards[0] if cards else {"name": "未知"}
            prompt = SINGLE_CARD_PROMPT.format(
                card_info=card_info,
                question=question or "无",
                card_name=card['name'],
                position_emoji="⬆️"
            )
        
        # 调用LLM生成解读
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"调用LLM生成塔罗牌解读 (尝试 {attempt + 1}/{self.max_retries})")
                
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": TAROT_SYSTEM_MESSAGE},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,  # 稍高的温度，让解读更有创造性
                    max_tokens=1500
                )
                
                interpretation = response.choices[0].message.content.strip()
                logger.info(f"塔罗牌解读生成成功: {len(interpretation)} 字符")
                return interpretation
                
            except APIError as e:
                logger.error(f"OpenAI API错误 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    return "🔮 抱歉，解读生成失败，请稍后再试。"
                time.sleep(self.retry_delay * (attempt + 1))
            
            except Exception as e:
                logger.error(f"解读生成失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    return "🔮 抱歉，解读生成失败，请稍后再试。"
                time.sleep(self.retry_delay * (attempt + 1))
        
        return "🔮 抱歉，解读生成失败，请稍后再试。"

