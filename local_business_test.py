"""
本地业务集成功能测试脚本
完全本地运行，通过数字菜单选择业务，直接调用业务管理器
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from accounting_manager import AccountingManager
from essay_manager import EssayManager
from employee_manager import EmployeeManager
from tarot_manager import TarotManager
from shared.models import StructuredRecord
from agent_storage.database import db
from shared.utils import setup_logger

logger = setup_logger(__name__)


class LocalBusinessTester:
    """本地业务测试器 - 主入口页面"""
    
    def __init__(self):
        """初始化测试器"""
        self.user_id = "local_test_user"
    
    def show_menu(self):
        """显示主菜单"""
        print("\n" + "="*60)
        print("本地业务集成功能测试")
        print("="*60)
        print(f"当前用户: {self.user_id}")
        print("\n请选择业务：")
        print("  1. 记账管理")
        print("  2. 随笔管理")
        print("  3. 员工管理")
        print("  4. 塔罗牌占卜")
        print("  5. 查看系统状态")
        print("  0. 退出")
        print("="*60)
    
    def show_status(self):
        """显示当前状态"""
        print("\n" + "-"*60)
        print("系统状态")
        print("-"*60)
        
        # 检查数据库连接
        try:
            session = db.get_session()
            try:
                # 统计各业务类型的记录数量
                from sqlalchemy import func
                
                print("\n数据库连接: ✓ 正常")
                print("\n各业务记录统计:")
                print("-"*60)
                
                business_types = ["记账", "随笔", "员工", "塔罗牌"]
                for business_type in business_types:
                    count = session.query(func.count(StructuredRecord.id)).filter(
                        StructuredRecord.record_type == business_type
                    ).scalar()
                    print(f"  {business_type}: {count} 条记录")
                
                # 统计总记录数
                total_count = session.query(func.count(StructuredRecord.id)).scalar()
                print(f"\n  总计: {total_count} 条记录")
                
                # 统计表/目录数量
                table_count = session.query(func.count(func.distinct(StructuredRecord.table_name))).filter(
                    StructuredRecord.table_name.isnot(None)
                ).scalar()
                print(f"  表/目录数: {table_count} 个")
                
            finally:
                session.close()
        except Exception as e:
            print(f"\n数据库连接: ✗ 异常")
            print(f"  错误: {e}")
        
        print("-"*60)
        input("\n按回车键返回主菜单...")
    
    def enter_accounting(self):
        """进入记账管理"""
        print("\n" + "="*60)
        print("进入记账管理系统")
        print("="*60)
        manager = AccountingManager()
        manager.run()
    
    def enter_essay(self):
        """进入随笔管理"""
        print("\n" + "="*60)
        print("进入随笔管理系统")
        print("="*60)
        manager = EssayManager()
        manager.run()
    
    def enter_employee(self):
        """进入员工管理"""
        print("\n" + "="*60)
        print("进入员工管理系统")
        print("="*60)
        manager = EmployeeManager()
        manager.run()
    
    def enter_tarot(self):
        """进入塔罗牌占卜"""
        print("\n" + "="*60)
        print("进入塔罗牌占卜系统")
        print("="*60)
        manager = TarotManager()
        manager.run()
    
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
                choice = input("\n请选择 (0-5): ").strip()
                
                if not choice:
                    continue
                
                if choice == "0":
                    print("\n退出测试...")
                    break
                
                elif choice == "1":
                    self.enter_accounting()
                
                elif choice == "2":
                    self.enter_essay()
                
                elif choice == "3":
                    self.enter_employee()
                
                elif choice == "4":
                    self.enter_tarot()
                
                elif choice == "5":
                    self.show_status()
                
                else:
                    print("\n无效选择，请输入 0-5 之间的数字")
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
    tester = LocalBusinessTester()
    tester.run()


if __name__ == "__main__":
    main()
