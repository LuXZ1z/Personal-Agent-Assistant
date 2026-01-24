"""
员工业务管理界面
交互式员工管理，支持增删改查和统计分析
使用 core.database 和 core.llm 基础功能
"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
import json
from collections import defaultdict
from typing import Optional

from core.database import get_database_manager
from core.llm import LLMClient
from business.employee.prompts import EMPLOYEE_PROMPT_TEMPLATE
from shared.utils import setup_logger

logger = setup_logger(__name__)


class EmployeeManager:
    """员工管理器 - 使用 core 基础功能"""
    
    def __init__(self, user_id: Optional[str] = None, bot_id: Optional[str] = None, debug: bool = False):
        """
        初始化员工管理器
        
        Args:
            user_id: 用户ID，如果为None则使用单数据库模式
            bot_id: 机器人ID，如果提供则使用 bot_id_user_id 格式的数据库路径
            debug: 是否为调试模式
        """
        self.user_id = user_id
        self.bot_id = bot_id
        self.debug = debug
        self.db = get_database_manager(user_id, bot_id)
        # 确保数据库被创建（通过获取会话来触发数据库创建）
        if user_id:
            try:
                _ = self.db.get_session(user_id=user_id, bot_id=bot_id)
                logger.info(f"员工管理器初始化成功: user_id={user_id}, bot_id={bot_id}")
            except Exception as e:
                logger.error(f"初始化数据库失败: {e}", exc_info=True)
        self.llm_client = LLMClient()
        self.table_name = "员工"  # 默认表名
    
    def show_main_menu(self):
        """显示主菜单"""
        print("\n" + "="*60)
        print("员工工作情况管理系统")
        print("="*60)
        if self.user_id:
            print(f"用户: {self.user_id}")
        print(f"当前表/目录: {self.table_name}")
        print("\n请选择操作：")
        print("  1. 添加员工工作记录（输入自然语言）")
        print("  2. 查询员工记录")
        print("  3. 修改员工记录")
        print("  4. 删除员工记录")
        print("  5. 切换表/目录")
        print("  6. 查看所有表/目录")
        print("  7. 统计分析")
        print("  0. 退出")
        print("="*60)
    
    def add_record(self):
        """添加员工工作记录"""
        print("\n" + "-"*60)
        print("添加员工工作记录")
        print("-"*60)
        print("请输入员工工作信息（自然语言），例如：")
        print("  - 今天张三完成了项目文档编写，工作态度积极，完成度90%")
        print("  - 李四正在进行代码审查，状态正常")
        print("\n输入 'back' 返回主菜单")
        
        text = input("\n> ").strip()
        if text.lower() == 'back':
            return
        
        if not text:
            print("输入不能为空")
            return
        
        try:
            print("\n正在处理...")
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt_template_with_date = EMPLOYEE_PROMPT_TEMPLATE.replace("{current_date}", current_date)
            
            structured_data = self.llm_client.structure_text(
                text=text,
                prompt_template=prompt_template_with_date
            )
            
            print(f"\n✓ 结构化成功:")
            print(f"  类型: {structured_data.get('type')}")
            print(f"  摘要: {structured_data.get('summary')}")
            print(f"  字段: {json.dumps(structured_data.get('fields', {}), ensure_ascii=False, indent=2)}")
            
            confirm = input("\n是否保存？(y/n): ").strip().lower()
            if confirm == 'y':
                record = self.db.create_record(
                    original_text=text,
                    structured_data=structured_data,
                    record_type=structured_data.get('type', '员工'),
                    table_name=self.table_name,
                    metadata=None,
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
                print(f"\n✓ 保存成功！记录ID: {record.id}")
            else:
                print("已取消保存")
        
        except Exception as e:
            print(f"\n✗ 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    def query_records(self):
        """查询员工记录"""
        print("\n" + "-"*60)
        print("查询员工记录")
        print("-"*60)
        print("请选择查询方式：")
        print("  1. 查询所有记录")
        print("  2. 按员工姓名查询")
        print("  3. 按日期查询（单日）")
        print("  4. 按时间段查询（日期范围）")
        print("  5. 按状态查询")
        print("  6. 按关键词搜索")
        print("  0. 返回")
        
        choice = input("\n> ").strip()
        
        try:
            filters = {
                "record_type": "员工",
                "table_name": self.table_name
            }
            
            if choice == "1":
                records = self.db.query_records(
                    filters=filters,
                    limit=50,
                    order_by="-created_at",
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
            elif choice == "2":
                name = input("请输入员工姓名: ").strip()
                all_records = self.db.query_records(
                    filters=filters,
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
                records = [r for r in all_records if r.structured_data.get('fields', {}).get('name', '').find(name) >= 0]
            elif choice == "3":
                date_str = input("请输入日期 (YYYY-MM-DD): ").strip()
                filters["date_from"] = date_str
                filters["date_to"] = date_str
                records = self.db.query_records(
                    filters=filters,
                    order_by="-created_at",
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
            elif choice == "4":
                start_date_str = input("请输入开始日期 (YYYY-MM-DD): ").strip()
                end_date_str = input("请输入结束日期 (YYYY-MM-DD): ").strip()
                filters["date_from"] = start_date_str
                filters["date_to"] = end_date_str
                records = self.db.query_records(
                    filters=filters,
                    order_by="-created_at",
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
            elif choice == "6":
                keyword = input("请输入关键词: ").strip()
                filters["keyword"] = keyword
                records = self.db.query_records(
                    filters=filters,
                    order_by="-created_at",
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
            else:
                return
            
            if records:
                print(f"\n找到 {len(records)} 条记录：")
                print("-"*60)
                for i, record in enumerate(records, 1):
                    fields = record.structured_data.get('fields', {})
                    name = fields.get('name', '未知')
                    task = fields.get('task', '')
                    status = fields.get('status', '未知')
                    date_str = fields.get('date', '')
                    work_attitude = fields.get('work_attitude', '未记录')
                    work_state = fields.get('work_state', '未记录')
                    completion = fields.get('completion', '')
                    summary = record.structured_data.get('summary', '')
                    
                    print(f"\n[{i}] ID: {record.id}")
                    print(f"    员工: {name} | 任务: {task}")
                    print(f"    状态: {status} | 日期: {date_str}")
                    print(f"    工作态度: {work_attitude} | 工作状态: {work_state}")
                    if completion:
                        print(f"    完成度: {completion}%")
                    print(f"    摘要: {summary}")
                    print(f"    创建时间: {record.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print("\n未找到记录")
        
        except Exception as e:
            print(f"\n✗ 查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def statistics_analysis(self):
        """统计分析员工记录"""
        print("\n" + "-"*60)
        print("统计分析")
        print("-"*60)
        print("请选择统计范围：")
        print("  1. 统计所有记录")
        print("  2. 按时间段统计")
        print("  3. 按员工统计")
        print("  0. 返回")
        
        choice = input("\n> ").strip()
        
        try:
            filters = {
                "record_type": "员工",
                "table_name": self.table_name
            }
            
            records = []
            
            if choice == "1":
                records = self.db.query_records(
                    filters=filters,
                    order_by="-created_at",
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
            elif choice == "2":
                start_date_str = input("请输入开始日期 (YYYY-MM-DD): ").strip()
                end_date_str = input("请输入结束日期 (YYYY-MM-DD): ").strip()
                filters["date_from"] = start_date_str
                filters["date_to"] = end_date_str
                records = self.db.query_records(
                    filters=filters,
                    order_by="-created_at",
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
            elif choice == "3":
                name = input("请输入员工姓名（留空统计所有员工）: ").strip()
                all_records = self.db.query_records(
                    filters=filters,
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
                if name:
                    records = [r for r in all_records if name in r.structured_data.get('fields', {}).get('name', '')]
                else:
                    records = all_records
            else:
                return
            
            if not records:
                print("\n未找到记录")
                input("\n按回车键继续...")
                return
            
            # 统计分析
            print("\n" + "="*60)
            print("统计分析结果")
            print("="*60)
            
            employee_stats = defaultdict(lambda: {
                "count": 0,
                "tasks": [],
                "statuses": defaultdict(int),
                "attitudes": defaultdict(int),
                "work_states": defaultdict(int),
                "completions": [],
            })
            
            for record in records:
                fields = record.structured_data.get('fields', {})
                name = fields.get('name', '未知')
                task = fields.get('task', '')
                status = fields.get('status', '未知')
                work_attitude = fields.get('work_attitude', '未记录')
                work_state = fields.get('work_state', '未记录')
                completion = fields.get('completion', None)
                
                employee_stats[name]["count"] += 1
                employee_stats[name]["tasks"].append(task)
                employee_stats[name]["statuses"][status] += 1
                employee_stats[name]["attitudes"][work_attitude] += 1
                employee_stats[name]["work_states"][work_state] += 1
                if completion is not None:
                    employee_stats[name]["completions"].append(completion)
            
            record_count = len(records)
            
            # 显示总体统计
            print(f"\n【总体概况】")
            print(f"  记录总数: {record_count} 条")
            print(f"  员工数量: {len(employee_stats)} 人")
            
            # 按员工统计
            print(f"\n【按员工统计】")
            if employee_stats:
                sorted_employees = sorted(employee_stats.items(), key=lambda x: x[1]["count"], reverse=True)
                for name, stats in sorted_employees:
                    print(f"\n  {name}:")
                    print(f"    记录数: {stats['count']} 条")
                    print(f"    任务数: {len(stats['tasks'])} 个")
                    
                    if stats['statuses']:
                        status_str = ", ".join([f"{k}({v})" for k, v in stats['statuses'].items()])
                        print(f"    状态分布: {status_str}")
                    
                    if stats['completions']:
                        avg_completion = sum(stats['completions']) / len(stats['completions'])
                        print(f"    平均完成度: {avg_completion:.1f}%")
            
            print("="*60)
        
        except Exception as e:
            print(f"\n✗ 统计失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def update_record(self):
        """修改员工记录"""
        print("\n" + "-"*60)
        print("修改员工记录")
        print("-"*60)
        
        record_id = input("请输入要修改的记录ID: ").strip()
        if not record_id.isdigit():
            print("ID格式错误")
            return
        
        try:
            record = self.db.get_record(int(record_id), user_id=self.user_id)
            if not record:
                print("记录不存在")
                return
            
            print(f"\n当前记录:")
            print(f"  原始文本: {record.original_text}")
            print(f"  结构化数据: {json.dumps(record.structured_data, ensure_ascii=False, indent=2)}")
            
            print("\n请输入新的员工工作信息（自然语言）:")
            new_text = input("> ").strip()
            
            if not new_text:
                print("输入不能为空")
                return
            
            print("\n正在处理...")
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt_template_with_date = EMPLOYEE_PROMPT_TEMPLATE.replace("{current_date}", current_date)
            structured_data = self.llm_client.structure_text(
                text=new_text,
                prompt_template=prompt_template_with_date
            )
            
            self.db.update_record(
                record_id=int(record_id),
                original_text=new_text,
                structured_data=structured_data,
                user_id=self.user_id
            )
            print(f"\n✓ 更新成功！")
        
        except Exception as e:
            print(f"\n✗ 更新失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def delete_record(self):
        """删除员工记录"""
        print("\n" + "-"*60)
        print("删除员工记录")
        print("-"*60)
        
        record_id = input("请输入要删除的记录ID: ").strip()
        if not record_id.isdigit():
            print("ID格式错误")
            return
        
        confirm = input(f"确认删除记录 {record_id}？(y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return
        
        try:
            success = self.db.delete_record(int(record_id), user_id=self.user_id)
            if success:
                print(f"\n✓ 删除成功！")
            else:
                print("\n记录不存在")
        
        except Exception as e:
            print(f"\n✗ 删除失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def switch_table(self):
        """切换表/目录"""
        print("\n" + "-"*60)
        print("切换表/目录")
        print("-"*60)
        
        try:
            stats = self.db.get_statistics(
                filters={"record_type": "员工"},
                user_id=self.user_id
            )
            table_list = list(stats.get('by_table', {}).keys())
            
            if table_list:
                print("\n可用的表/目录（仅员工业务）：")
                for i, table in enumerate(table_list, 1):
                    marker = " ← 当前" if table == self.table_name else ""
                    print(f"  {i}. {table}{marker}")
            
            print(f"\n当前表: {self.table_name}")
            new_table = input("请输入新表名（直接回车保持当前）: ").strip()
            
            if new_table:
                if new_table in table_list:
                    self.table_name = new_table
                    print(f"\n✓ 已切换到: {self.table_name}")
                else:
                    print(f"\n✗ 表 '{new_table}' 不存在或不属于员工业务")
            else:
                print("保持当前表")
        
        except Exception as e:
            print(f"\n✗ 切换失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def list_tables(self):
        """查看所有表/目录"""
        print("\n" + "-"*60)
        print("所有表/目录（仅员工业务）")
        print("-"*60)
        
        try:
            stats = self.db.get_statistics(
                filters={"record_type": "员工"},
                user_id=self.user_id
            )
            by_table = stats.get('by_table', {})
            
            if by_table:
                print(f"\n{'表名':<20} {'记录数':<10}")
                print("-"*30)
                for table_name, count in by_table.items():
                    marker = " ← 当前" if table_name == self.table_name else ""
                    print(f"{table_name:<20} {count:<10}{marker}")
            else:
                print("\n暂无表/目录")
        
        except Exception as e:
            print(f"\n✗ 查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def run(self):
        """运行主循环"""
        while True:
            try:
                self.show_main_menu()
                choice = input("\n请选择 (0-7): ").strip()
                
                if choice == "0":
                    print("\n再见！")
                    break
                elif choice == "1":
                    self.add_record()
                elif choice == "2":
                    self.query_records()
                elif choice == "3":
                    self.update_record()
                elif choice == "4":
                    self.delete_record()
                elif choice == "5":
                    self.switch_table()
                elif choice == "6":
                    self.list_tables()
                elif choice == "7":
                    self.statistics_analysis()
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
    parser = argparse.ArgumentParser(description='员工业务管理系统')
    parser.add_argument('--debug', action='store_true', help='调试模式（本地测试）')
    parser.add_argument('--user-id', type=str, default=None, help='用户ID（多用户模式）')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("员工工作情况管理系统")
    if args.debug:
        print("调试模式")
    print("="*60)
    
    manager = EmployeeManager(user_id=args.user_id, debug=args.debug)
    manager.run()


if __name__ == "__main__":
    main()
