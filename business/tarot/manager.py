"""
塔罗牌交互式管理界面
提供塔罗牌占卜功能
使用 core.llm 基础功能
"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Optional, List, Dict, Any
from enum import Enum
import random

from business.tarot.tarot_cards import TarotService as BaseTarotService, SpreadType
from core.llm import LLMClient
from business.tarot.prompts import (
    TAROT_SYSTEM_MESSAGE,
    SINGLE_CARD_PROMPT,
    THREE_CARD_PROMPT,
    FIVE_CARD_PROMPT
)   
from shared.utils import setup_logger

logger = setup_logger(__name__)


class TarotManager:
    """塔罗牌管理器 - 使用 core.llm 基础功能"""
    
    def __init__(self, user_id: Optional[str] = None, debug: bool = False):
        """
        初始化塔罗牌管理器
        
        Args:
            user_id: 用户ID（可选）
            debug: 是否为调试模式
        """
        self.user_id = user_id
        self.debug = debug
        self.tarot_service = BaseTarotService()
        self.llm_client = LLMClient()
    
    def show_main_menu(self):
        """显示主菜单"""
        print("\n" + "="*60)
        print("🔮 塔罗牌占卜系统 🔮")
        print("="*60)
        if self.user_id:
            print(f"用户: {self.user_id}")
        print("\n请选择操作：")
        print("  1. 🔮 单张牌占卜")
        print("  2. 📜 三张牌占卜（过去-现在-未来）")
        print("  3. ⭐ 五张牌占卜（凯尔特十字简化版）")
        print("  4. 📖 查看塔罗牌知识")
        print("  0. 退出")
        print("="*60)
    
    def draw_single_card(self):
        """单张牌占卜"""
        print("\n" + "-"*60)
        print("🔮 单张牌占卜")
        print("-"*60)
        print("单张牌占卜适合快速了解当前状况或某个问题的答案。")
        print("\n你可以输入一个问题（可选），或直接按回车开始抽牌：")
        
        question = input("\n> ").strip()
        if not question:
            question = None
        
        try:
            print("\n" + "🔮"*30)
            print("正在为你抽取塔罗牌...")
            print("🔮"*30 + "\n")
            
            # 抽牌
            card = self.tarot_service.draw_card()
            
            # 显示牌信息
            position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
            position_text = "正位" if card.get("upright", True) else "逆位"
            
            print(f"🔮 抽取的牌：{card['name']} ({card['name_en']})")
            print(f"📊 位置：{position_text} {position_emoji}")
            print(f"🎴 花色：{card.get('suit', '大阿卡纳')}")
            print("\n" + "-"*60)
            print("正在生成AI解读...")
            print("-"*60 + "\n")
            
            # 生成解读
            card_info = f"{card['name']} ({card['name_en']}) - {position_text} {position_emoji}"
            prompt = SINGLE_CARD_PROMPT.format(
                card_info=card_info,
                question=question or "无",
                card_name=card['name'],
                position_emoji=position_emoji
            )
            
            interpretation = self.llm_client.chat(
                messages=[
                    {"role": "system", "content": TAROT_SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1500
            )
            
            print("\n" + "="*60)
            print("🔮 AI解读结果")
            print("="*60)
            print(interpretation)
            print("="*60)
        
        except Exception as e:
            print(f"\n✗ 占卜失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def draw_three_card(self):
        """三张牌占卜"""
        print("\n" + "-"*60)
        print("📜 三张牌占卜（过去-现在-未来）")
        print("-"*60)
        print("三张牌占卜可以帮助你了解时间线上的发展。")
        print("\n你可以输入一个问题（可选），或直接按回车开始抽牌：")
        
        question = input("\n> ").strip()
        if not question:
            question = None
        
        try:
            print("\n" + "🔮"*30)
            print("正在为你抽取三张塔罗牌...")
            print("🔮"*30 + "\n")
            
            # 抽三张牌
            cards = self.tarot_service.draw_spread(SpreadType.THREE_CARD)
            
            # 显示牌信息
            print("📜 过去：", cards[0]['name'], "⬆️" if cards[0].get("upright", True) else "⬇️")
            print("💫 现在：", cards[1]['name'], "⬆️" if cards[1].get("upright", True) else "⬇️")
            print("🔮 未来：", cards[2]['name'], "⬆️" if cards[2].get("upright", True) else "⬇️")
            print("\n" + "-"*60)
            print("正在生成AI解读...")
            print("-"*60 + "\n")
            
            # 生成解读
            card_info_lines = []
            for i, card in enumerate(cards):
                position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
                positions = ["过去", "现在", "未来"]
                card_info_lines.append(
                    f"{positions[i]}：{card['name']} ({card['name_en']}) - {position_emoji}"
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
            
            print("\n" + "="*60)
            print("🔮 AI解读结果")
            print("="*60)
            print(interpretation)
            print("="*60)
        
        except Exception as e:
            print(f"\n✗ 占卜失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def draw_five_card(self):
        """五张牌占卜"""
        print("\n" + "-"*60)
        print("⭐ 五张牌占卜（凯尔特十字简化版）")
        print("-"*60)
        print("五张牌占卜提供更全面的洞察。")
        print("\n你可以输入一个问题（可选），或直接按回车开始抽牌：")
        
        question = input("\n> ").strip()
        if not question:
            question = None
        
        try:
            print("\n" + "🔮"*30)
            print("正在为你抽取五张塔罗牌...")
            print("🔮"*30 + "\n")
            
            # 抽五张牌
            cards = self.tarot_service.draw_spread(SpreadType.FIVE_CARD)
            
            # 显示牌信息
            positions = ["现状", "挑战", "过去", "未来", "结果"]
            for i, card in enumerate(cards):
                emoji = ["📍", "⚡", "📜", "🔮", "🌟"][i]
                position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
                print(f"{emoji} {positions[i]}：{card['name']} {position_emoji}")
            
            print("\n" + "-"*60)
            print("正在生成AI解读...")
            print("-"*60 + "\n")
            
            # 生成解读
            card_info_lines = []
            for i, card in enumerate(cards):
                position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
                positions = ["现状", "挑战", "过去", "未来", "结果"]
                card_info_lines.append(
                    f"{positions[i]}：{card['name']} ({card['name_en']}) - {position_emoji}"
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
            
            print("\n" + "="*60)
            print("🔮 AI解读结果")
            print("="*60)
            print(interpretation)
            print("="*60)
        
        except Exception as e:
            print(f"\n✗ 占卜失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def show_knowledge(self):
        """显示塔罗牌知识"""
        print("\n" + "="*60)
        print("📖 塔罗牌知识")
        print("="*60)
        print("""
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
        """)
        print("="*60)
        input("\n按回车键继续...")
    
    def run(self):
        """运行主循环"""
        while True:
            try:
                self.show_main_menu()
                choice = input("\n请选择 (0-4): ").strip()
                
                if choice == "0":
                    print("\n再见！")
                    break
                elif choice == "1":
                    self.draw_single_card()
                elif choice == "2":
                    self.draw_three_card()
                elif choice == "3":
                    self.draw_five_card()
                elif choice == "4":
                    self.show_knowledge()
                else:
                    print("\n无效选择，请重新输入")
            
            except KeyboardInterrupt:
                print("\n\n再见！")
                break
            except Exception as e:
                print(f"\n错误: {e}")
                import traceback
                traceback.print_exc()
                input("\n按回车键继续...")


def main():
    """主函数 - 支持 --debug 参数"""
    parser = argparse.ArgumentParser(description='塔罗牌占卜系统')
    parser.add_argument('--debug', action='store_true', help='调试模式（本地测试）')
    parser.add_argument('--user-id', type=str, default=None, help='用户ID（多用户模式）')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("🔮 塔罗牌占卜系统 🔮")
    if args.debug:
        print("调试模式")
    print("="*60)
    
    manager = TarotManager(user_id=args.user_id, debug=args.debug)
    manager.run()


if __name__ == "__main__":
    main()
