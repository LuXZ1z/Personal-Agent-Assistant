"""
塔罗牌核心功能
提供塔罗牌抽取和牌阵功能
"""
import random
from typing import List, Dict, Any
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
    
    def _shuffle_deck(self) -> List[Dict[str, Any]]:
        """
        洗牌（创建牌组的副本并打乱顺序）
        
        Returns:
            打乱后的牌组副本
        """
        shuffled = self.deck.copy()
        random.shuffle(shuffled)
        return shuffled
    
    def draw_card(self, available_deck: List[Dict[str, Any]] = None) -> tuple:
        """
        从可用牌组中抽取一张牌（不放回）
        
        Args:
            available_deck: 可用的牌组（如果为None，则从完整牌组中随机抽取，不修改牌组）
        
        Returns:
            如果 available_deck 为 None，返回 (牌, None)
            如果 available_deck 不为 None，返回 (牌, 剩余牌组)
        """
        if available_deck is None:
            # 向后兼容：从完整牌组中随机抽取（不修改牌组）
            card = random.choice(self.deck)
            is_upright = random.choice([True, False])
            return {
                **card,
                "upright": is_upright,
                "position": "正位" if is_upright else "逆位"
            }, None
        
        # 从指定牌组中抽取（不放回）
        if not available_deck:
            # 如果牌组为空，重新创建
            available_deck = self._create_deck()
            random.shuffle(available_deck)
        
        card = available_deck.pop(0)  # 从牌组中移除第一张牌
        is_upright = random.choice([True, False])
        
        return {
            **card,
            "upright": is_upright,
            "position": "正位" if is_upright else "逆位"
        }, available_deck
    
    def draw_spread(self, spread_type: str = "single") -> List[Dict[str, Any]]:
        """
        抽取牌阵（确保同一牌阵中不会重复）
        
        Args:
            spread_type: 牌阵类型 (single, three_card, five_card)
            
        Returns:
            抽取的牌列表（确保不重复）
        """
        # 确定需要抽取的牌数
        if spread_type == "single":
            num_cards = 1
        elif spread_type == "three_card":
            num_cards = 3
        elif spread_type == "five_card":
            num_cards = 5
        else:
            num_cards = 1
        
        # 洗牌，创建可用牌组
        available_deck = self._shuffle_deck()
        
        # 抽取指定数量的牌（不放回）
        drawn_cards = []
        for _ in range(num_cards):
            card, available_deck = self.draw_card(available_deck)
            drawn_cards.append(card)
        
        return drawn_cards
    
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


