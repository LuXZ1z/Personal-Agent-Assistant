"""
塔罗牌服务
提供塔罗牌抽取和牌阵功能
"""
import random
from typing import List, Dict, Any, Optional
from enum import Enum


class SpreadType(str, Enum):
    """牌阵类型"""
    SINGLE = "single"  # 单张牌
    THREE_CARD = "three_card"  # 三张牌（过去-现在-未来）
    FIVE_CARD = "five_card"  # 五张牌（凯尔特十字简化版）


class TarotService:
    """塔罗牌服务类"""
    
    # 大阿卡纳（22张）
    MAJOR_ARCANA = [
        {"id": 0, "name": "愚者", "name_en": "The Fool", "suit": "大阿卡纳"},
        {"id": 1, "name": "魔术师", "name_en": "The Magician", "suit": "大阿卡纳"},
        {"id": 2, "name": "女祭司", "name_en": "The High Priestess", "suit": "大阿卡纳"},
        {"id": 3, "name": "皇后", "name_en": "The Empress", "suit": "大阿卡纳"},
        {"id": 4, "name": "皇帝", "name_en": "The Emperor", "suit": "大阿卡纳"},
        {"id": 5, "name": "教皇", "name_en": "The Hierophant", "suit": "大阿卡纳"},
        {"id": 6, "name": "恋人", "name_en": "The Lovers", "suit": "大阿卡纳"},
        {"id": 7, "name": "战车", "name_en": "The Chariot", "suit": "大阿卡纳"},
        {"id": 8, "name": "力量", "name_en": "Strength", "suit": "大阿卡纳"},
        {"id": 9, "name": "隐者", "name_en": "The Hermit", "suit": "大阿卡纳"},
        {"id": 10, "name": "命运之轮", "name_en": "Wheel of Fortune", "suit": "大阿卡纳"},
        {"id": 11, "name": "正义", "name_en": "Justice", "suit": "大阿卡纳"},
        {"id": 12, "name": "倒吊人", "name_en": "The Hanged Man", "suit": "大阿卡纳"},
        {"id": 13, "name": "死神", "name_en": "Death", "suit": "大阿卡纳"},
        {"id": 14, "name": "节制", "name_en": "Temperance", "suit": "大阿卡纳"},
        {"id": 15, "name": "恶魔", "name_en": "The Devil", "suit": "大阿卡纳"},
        {"id": 16, "name": "塔", "name_en": "The Tower", "suit": "大阿卡纳"},
        {"id": 17, "name": "星星", "name_en": "The Star", "suit": "大阿卡纳"},
        {"id": 18, "name": "月亮", "name_en": "The Moon", "suit": "大阿卡纳"},
        {"id": 19, "name": "太阳", "name_en": "The Sun", "suit": "大阿卡纳"},
        {"id": 20, "name": "审判", "name_en": "Judgement", "suit": "大阿卡纳"},
        {"id": 21, "name": "世界", "name_en": "The World", "suit": "大阿卡纳"},
    ]
    
    # 小阿卡纳花色
    SUITS = ["权杖", "圣杯", "宝剑", "星币"]
    SUITS_EN = ["Wands", "Cups", "Swords", "Pentacles"]
    
    # 小阿卡纳牌面
    MINOR_RANKS = ["Ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "侍从", "骑士", "王后", "国王"]
    MINOR_RANKS_CN = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "侍从", "骑士", "王后", "国王"]
    
    def __init__(self):
        """初始化塔罗牌服务"""
        self.deck = self._create_deck()
    
    def _create_deck(self) -> List[Dict[str, Any]]:
        """创建完整的78张塔罗牌牌组"""
        deck = []
        
        # 添加大阿卡纳
        for card in self.MAJOR_ARCANA:
            deck.append({
                "id": card["id"],
                "name": card["name"],
                "name_en": card["name_en"],
                "suit": card["suit"],
                "arcana": "major"
            })
        
        # 添加小阿卡纳
        card_id = 22  # 从22开始编号
        for suit_idx, suit in enumerate(self.SUITS):
            for rank_idx, rank in enumerate(self.MINOR_RANKS):
                deck.append({
                    "id": card_id,
                    "name": f"{suit}{self.MINOR_RANKS_CN[rank_idx]}",
                    "name_en": f"{self.MINOR_RANKS[rank_idx]} of {self.SUITS_EN[suit_idx]}",
                    "suit": suit,
                    "rank": self.MINOR_RANKS_CN[rank_idx],
                    "arcana": "minor"
                })
                card_id += 1
        
        return deck
    
    def draw_card(self) -> Dict[str, Any]:
        """
        抽取一张牌
        
        Returns:
            抽取的牌（包含正位/逆位信息）
        """
        card = random.choice(self.deck)
        is_upright = random.choice([True, False])
        
        return {
            **card,
            "upright": is_upright,
            "position": "正位" if is_upright else "逆位"
        }
    
    def draw_spread(self, spread_type: str = "single") -> List[Dict[str, Any]]:
        """
        抽取牌阵
        
        Args:
            spread_type: 牌阵类型 (single, three_card, five_card)
            
        Returns:
            抽取的牌列表
        """
        if spread_type == "single":
            return [self.draw_card()]
        elif spread_type == "three_card":
            # 三张牌：过去-现在-未来
            return [self.draw_card() for _ in range(3)]
        elif spread_type == "five_card":
            # 五张牌：凯尔特十字简化版
            return [self.draw_card() for _ in range(5)]
        else:
            return [self.draw_card()]
    
    def get_spread_positions(self, spread_type: str) -> List[str]:
        """
        获取牌阵位置说明
        
        Args:
            spread_type: 牌阵类型
            
        Returns:
            位置说明列表
        """
        if spread_type == "single":
            return ["单张牌"]
        elif spread_type == "three_card":
            return ["过去", "现在", "未来"]
        elif spread_type == "five_card":
            return ["现状", "挑战", "过去", "未来", "结果"]
        else:
            return ["单张牌"]
    
    def format_cards_for_interpretation(self, cards: List[Dict[str, Any]], spread_type: str) -> str:
        """
        格式化牌信息用于LLM解读
        
        Args:
            cards: 抽取的牌列表
            spread_type: 牌阵类型
            
        Returns:
            格式化后的字符串
        """
        positions = self.get_spread_positions(spread_type)
        lines = []
        
        for i, card in enumerate(cards):
            position = positions[i] if i < len(positions) else f"位置{i+1}"
            lines.append(f"{position}: {card['name']} ({card['name_en']}) - {card['position']}")
        
        return "\n".join(lines)

