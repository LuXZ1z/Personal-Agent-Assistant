"""
命令行界面主入口
完全本地运行，通过数字菜单选择业务，直接调用业务管理器
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.database import get_database_manager
from shared.models import StructuredRecord
from shared.utils import setup_logger
from shared.menu_config import get_all_businesses, generate_menu_text, BUSINESS_CONFIG
from interfaces.cli.service_adapter import ServiceAdapter
import importlib

logger = setup_logger(__name__)


class CLIMain:
    """CLI主系统页面"""
    
    def __init__(self):
        """初始化CLI"""
        self.user_id = "local_test_user"
    
    def show_menu(self):
        """显示主菜单（使用统一配置）"""
        menu_text = generate_menu_text(user_id=self.user_id, include_status=True)
        print(menu_text)
    
    def show_status(self):
        """显示当前状态"""
        print("\n" + "-"*60)
        print("系统状态")
        print("-"*60)
        
        # 检查数据库连接
        try:
            db = get_database_manager(user_id=self.user_id)
            stats = db.get_statistics(user_id=self.user_id)
            
            print("\n数据库连接: ✓ 正常")
            print("\n各业务记录统计:")
            print("-"*60)
            
            by_type = stats.get('by_type', {})
            business_types = ["记账", "随笔", "员工", "塔罗牌"]
            for business_type in business_types:
                count = by_type.get(business_type, 0)
                print(f"  {business_type}: {count} 条记录")
            
            # 统计总记录数
            total_count = stats.get('total_count', 0)
            print(f"\n  总计: {total_count} 条记录")
            
            # 统计表/目录数量
            by_table = stats.get('by_table', {})
            table_count = len(by_table)
            print(f"  表/目录数: {table_count} 个")
        except Exception as e:
            print(f"\n数据库连接: ✗ 异常")
            print(f"  错误: {e}")
        
        print("-"*60)
        input("\n按回车键返回主菜单...")
    
    def enter_business(self, business_type: str, business_name: str):
        """
        进入业务管理（使用Service层，与微信服务器完全相同的业务逻辑）
        
        Args:
            business_type: 业务类型（如 "accounting", "essay"）
            business_name: 业务名称（用于显示）
        """
        if business_type not in BUSINESS_CONFIG:
            print(f"错误：未知的业务类型: {business_type}")
            return
        
        try:
            # 使用Service适配器，确保与微信服务器使用完全相同的业务逻辑
            adapter = ServiceAdapter(user_id=self.user_id, business_type=business_type)
            adapter.run()
        except Exception as e:
            print(f"错误：加载业务Service失败: {e}")
            import traceback
            traceback.print_exc()
            input("\n按回车键返回主菜单...")
    
    def run(self):
        """运行交互式测试"""
        print("\n" + "="*60)
        print("本地业务集成功能测试")
        print("="*60)
        print("\n这是一个完全本地运行的测试工具")
        print("可以通过数字菜单选择不同的业务功能")
        print("\n提示:")
        print("- 选择业务后，会进入对应的业务管理界面")
        print("- 在业务管理界面选择 0 可以返回主菜单")
        print("- 按 Ctrl+C 可以随时退出程序")
        
        while True:
            try:
                self.show_menu()
                businesses = get_all_businesses()
                max_choice = len(businesses) + 1  # +1 for status option
                choice = input(f"\n请选择 (0-{max_choice}): ").strip()
                
                if not choice:
                    continue
                
                if choice == "0":
                    print("\n退出测试...")
                    break
                
                elif choice == str(max_choice):  # 查看系统状态
                    self.show_status()
                
                else:
                    # 动态查找业务
                    business_info = None
                    for business in businesses:
                        if business["id"] == choice:
                            business_info = business
                            break
                    
                    if business_info:
                        self.enter_business(
                            business_info["business_type"],
                            business_info["display_name"]
                        )
                    else:
                        print(f"\n无效选择，请输入 0-{max_choice} 之间的数字")
                        input("\n按回车键继续...")
            
            except KeyboardInterrupt:
                print("\n\n退出测试...")
                break
            except Exception as e:
                print(f"\n错误: {e}")
                import traceback
                traceback.print_exc()
                input("\n按回车键继续...")
        
        print("\n测试结束")


def main():
    """主函数"""
    cli = CLIMain()
    cli.run()


if __name__ == "__main__":
    main()

