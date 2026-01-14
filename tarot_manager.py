"""
塔罗牌交互式管理界面
提供塔罗牌占卜功能
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from agent_tarot.tarot_service import TarotService, SpreadType
from agent_tarot.llm_client import TarotLLMClient
from shared.utils import setup_logger

logger = setup_logger(__name__)


class TarotManager:
    """塔罗牌管理器"""
    
    def __init__(self):
        """初始化塔罗牌管理器"""
        self.tarot_service = TarotService()
        self.llm_client = TarotLLMClient()
    
    def show_main_menu(self):
        """显示主菜单"""
        print("\n" + "="*60)
        print("🔮 塔罗牌占卜系统 🔮")
        print("="*60)
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
            cards = self.tarot_service.draw_spread("single")
            card = cards[0]
            
            # 显示牌
            position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
            print("="*60)
            print(f"✨ 你抽到的牌 ✨")
            print("="*60)
            print(f"🔮 牌名：{card['name']}")
            print(f"📖 英文名：{card['name_en']}")
            print(f"🎴 花色：{card['suit']}")
            print(f"📍 位置：{card.get('position', '正位')} {position_emoji}")
            print("="*60)
            
            # 生成解读
            print("\n💫 正在生成解读...\n")
            interpretation = self.llm_client.interpret_tarot(
                cards=cards,
                spread_type="single",
                question=question
            )
            
            print("="*60)
            print("🌟 塔罗牌解读 🌟")
            print("="*60)
            print(interpretation)
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ 占卜失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def draw_three_card(self):
        """三张牌占卜"""
        print("\n" + "-"*60)
        print("📜 三张牌占卜（过去-现在-未来）")
        print("-"*60)
        print("三张牌占卜可以帮助你了解：")
        print("  📜 过去：影响当前状况的过去因素")
        print("  💫 现在：当前的状况和能量")
        print("  🔮 未来：可能的发展方向")
        print("\n你可以输入一个问题（可选），或直接按回车开始抽牌：")
        
        question = input("\n> ").strip()
        if not question:
            question = None
        
        try:
            print("\n" + "🔮"*30)
            print("正在为你抽取三张塔罗牌...")
            print("🔮"*30 + "\n")
            
            # 抽牌
            cards = self.tarot_service.draw_spread("three_card")
            positions = self.tarot_service.get_spread_positions("three_card")
            
            # 显示牌
            print("="*60)
            print(f"✨ 你抽到的三张牌 ✨")
            print("="*60)
            for i, card in enumerate(cards):
                position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
                print(f"\n📌 {positions[i] if i < len(positions) else f'位置{i+1}'}:")
                print(f"   🔮 牌名：{card['name']}")
                print(f"   📖 英文名：{card['name_en']}")
                print(f"   📍 位置：{card.get('position', '正位')} {position_emoji}")
            print("="*60)
            
            # 生成解读
            print("\n💫 正在生成解读...\n")
            interpretation = self.llm_client.interpret_tarot(
                cards=cards,
                spread_type="three_card",
                question=question
            )
            
            print("="*60)
            print("🌟 塔罗牌解读 🌟")
            print("="*60)
            print(interpretation)
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ 占卜失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def draw_five_card(self):
        """五张牌占卜"""
        print("\n" + "-"*60)
        print("⭐ 五张牌占卜（凯尔特十字简化版）")
        print("-"*60)
        print("五张牌占卜提供更全面的洞察：")
        print("  📍 现状：当前的情况")
        print("  ⚡ 挑战：面临的挑战或阻碍")
        print("  📜 过去：影响现状的过去因素")
        print("  🔮 未来：可能的发展方向")
        print("  🌟 结果：最终可能的结果")
        print("\n你可以输入一个问题（可选），或直接按回车开始抽牌：")
        
        question = input("\n> ").strip()
        if not question:
            question = None
        
        try:
            print("\n" + "🔮"*30)
            print("正在为你抽取五张塔罗牌...")
            print("🔮"*30 + "\n")
            
            # 抽牌
            cards = self.tarot_service.draw_spread("five_card")
            positions = self.tarot_service.get_spread_positions("five_card")
            
            # 显示牌
            print("="*60)
            print(f"✨ 你抽到的五张牌 ✨")
            print("="*60)
            for i, card in enumerate(cards):
                position_emoji = "⬆️" if card.get("upright", True) else "⬇️"
                print(f"\n📌 {positions[i] if i < len(positions) else f'位置{i+1}'}:")
                print(f"   🔮 牌名：{card['name']}")
                print(f"   📖 英文名：{card['name_en']}")
                print(f"   📍 位置：{card.get('position', '正位')} {position_emoji}")
            print("="*60)
            
            # 生成解读
            print("\n💫 正在生成解读...\n")
            interpretation = self.llm_client.interpret_tarot(
                cards=cards,
                spread_type="five_card",
                question=question
            )
            
            print("="*60)
            print("🌟 塔罗牌解读 🌟")
            print("="*60)
            print(interpretation)
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ 占卜失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def show_tarot_knowledge(self):
        """显示塔罗牌知识"""
        print("\n" + "-"*60)
        print("📖 塔罗牌知识")
        print("-"*60)
        print("""
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
        """)
        input("\n按回车键继续...")
    
    def run(self):
        """运行主循环"""
        while True:
            try:
                self.show_main_menu()
                choice = input("\n请选择 (0-4): ").strip()
                
                if choice == "0":
                    print("\n🔮 再见！愿塔罗牌指引你的道路！🔮")
                    break
                elif choice == "1":
                    self.draw_single_card()
                elif choice == "2":
                    self.draw_three_card()
                elif choice == "3":
                    self.draw_five_card()
                elif choice == "4":
                    self.show_tarot_knowledge()
                else:
                    print("\n❌ 无效选择，请重新输入")
            
            except KeyboardInterrupt:
                print("\n\n🔮 再见！愿塔罗牌指引你的道路！🔮")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                import traceback
                traceback.print_exc()
                input("\n按回车键继续...")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🔮 塔罗牌占卜系统 🔮")
    print("="*60)
    
    manager = TarotManager()
    manager.run()


if __name__ == "__main__":
    main()

