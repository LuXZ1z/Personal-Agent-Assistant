"""
员工工作情况管理界面
交互式员工管理，支持增删改查和统计分析
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.config import settings
from shared.models import StructuredRecord
from agent_storage.database import db
from agent_structurizer.llm_client import LLMClient
from agent_structurizer.prompt_templates import EMPLOYEE_PROMPT_TEMPLATE
from shared.utils import setup_logger
from datetime import datetime, timedelta
import json
from collections import defaultdict

logger = setup_logger(__name__)


class EmployeeManager:
    """员工管理器"""
    
    def __init__(self):
        """初始化员工管理器"""
        self.db = db
        self.llm_client = LLMClient()
        self.table_name = "员工"  # 默认表名
    
    def show_main_menu(self):
        """显示主菜单"""
        print("\n" + "="*60)
        print("员工工作情况管理系统")
        print("="*60)
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
        print("  - 2024-01-15 王五暂停了当前任务，需要关注")
        print("\n输入 'back' 返回主菜单")
        
        text = input("\n> ").strip()
        if text.lower() == 'back':
            return
        
        if not text:
            print("输入不能为空")
            return
        
        try:
            print("\n正在处理...")
            # 获取当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")
            # 格式化prompt模板，传入当前日期
            # 直接在模板中替换占位符，避免format方法误解JSON示例中的字符串
            prompt_template_with_date = EMPLOYEE_PROMPT_TEMPLATE.replace("{current_date}", current_date)
            # 调用LLM进行结构化
            structured_data = self.llm_client.structure_text(
                text=text,
                prompt_template=prompt_template_with_date
            )
            
            print(f"\n✓ 结构化成功:")
            print(f"  类型: {structured_data.get('type')}")
            print(f"  摘要: {structured_data.get('summary')}")
            print(f"  字段: {json.dumps(structured_data.get('fields', {}), ensure_ascii=False, indent=2)}")
            
            # 确认保存
            confirm = input("\n是否保存？(y/n): ").strip().lower()
            if confirm == 'y':
                session = self.db.get_session()
                try:
                    record = StructuredRecord(
                        original_text=text,
                        structured_data=structured_data,
                        record_type=structured_data.get('type', '员工'),
                        table_name=self.table_name,
                        metadata=None
                    )
                    session.add(record)
                    session.commit()
                    session.refresh(record)
                    print(f"\n✓ 保存成功！记录ID: {record.id}")
                except Exception as e:
                    session.rollback()
                    print(f"\n✗ 保存失败: {e}")
                finally:
                    session.close()
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
        print("  6. 按工作态度查询")
        print("  7. 按工作状态查询")
        print("  0. 返回")
        
        choice = input("\n> ").strip()
        
        session = self.db.get_session()
        try:
            query = session.query(StructuredRecord).filter(
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "员工"
            )
            
            if choice == "1":
                # 查询所有
                records = query.order_by(StructuredRecord.created_at.desc()).limit(50).all()
            
            elif choice == "2":
                # 按员工姓名查询
                name = input("请输入员工姓名: ").strip()
                all_records = query.all()
                records = []
                for r in all_records:
                    record_name = r.structured_data.get('fields', {}).get('name', '')
                    if name in record_name:
                        records.append(r)
                records.sort(key=lambda x: x.created_at, reverse=True)
            
            elif choice == "3":
                # 按日期查询（单日）
                date_str = input("请输入日期 (YYYY-MM-DD): ").strip()
                try:
                    query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    records = query.filter(
                        StructuredRecord.created_at >= datetime.combine(query_date, datetime.min.time()),
                        StructuredRecord.created_at < datetime.combine(query_date, datetime.max.time()) + timedelta(days=1)
                    ).order_by(StructuredRecord.created_at.desc()).all()
                except ValueError:
                    print("日期格式错误")
                    return
            
            elif choice == "4":
                # 按时间段查询（日期范围）
                start_date_str = input("请输入开始日期 (YYYY-MM-DD): ").strip()
                end_date_str = input("请输入结束日期 (YYYY-MM-DD): ").strip()
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    if start_date > end_date:
                        print("开始日期不能晚于结束日期")
                        return
                    records = query.filter(
                        StructuredRecord.created_at >= datetime.combine(start_date, datetime.min.time()),
                        StructuredRecord.created_at <= datetime.combine(end_date, datetime.max.time())
                    ).order_by(StructuredRecord.created_at.desc()).all()
                except ValueError:
                    print("日期格式错误，请使用 YYYY-MM-DD 格式")
                    return
            
            elif choice == "5":
                # 按状态查询
                status = input("请输入状态（进行中/已完成/已暂停/已取消）: ").strip()
                all_records = query.all()
                records = []
                for r in all_records:
                    record_status = r.structured_data.get('fields', {}).get('status', '')
                    if status in record_status:
                        records.append(r)
                records.sort(key=lambda x: x.created_at, reverse=True)
            
            elif choice == "6":
                # 按工作态度查询
                attitude = input("请输入工作态度（积极/一般/消极/需改进）: ").strip()
                all_records = query.all()
                records = []
                for r in all_records:
                    record_attitude = r.structured_data.get('fields', {}).get('work_attitude', '')
                    if attitude in record_attitude:
                        records.append(r)
                records.sort(key=lambda x: x.created_at, reverse=True)
            
            elif choice == "7":
                # 按工作状态查询
                work_state = input("请输入工作状态（正常/异常/需关注/优秀）: ").strip()
                all_records = query.all()
                records = []
                for r in all_records:
                    record_work_state = r.structured_data.get('fields', {}).get('work_state', '')
                    if work_state in record_work_state:
                        records.append(r)
                records.sort(key=lambda x: x.created_at, reverse=True)
            
            else:
                return
            
            # 显示结果
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
        
        finally:
            session.close()
        
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
        print("  4. 按状态统计")
        print("  0. 返回")
        
        choice = input("\n> ").strip()
        
        session = self.db.get_session()
        try:
            query = session.query(StructuredRecord).filter(
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "员工"
            )
            
            records = []
            
            if choice == "1":
                # 统计所有记录
                records = query.order_by(StructuredRecord.created_at.desc()).all()
            
            elif choice == "2":
                # 按时间段统计
                start_date_str = input("请输入开始日期 (YYYY-MM-DD): ").strip()
                end_date_str = input("请输入结束日期 (YYYY-MM-DD): ").strip()
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    if start_date > end_date:
                        print("开始日期不能晚于结束日期")
                        return
                    records = query.filter(
                        StructuredRecord.created_at >= datetime.combine(start_date, datetime.min.time()),
                        StructuredRecord.created_at <= datetime.combine(end_date, datetime.max.time())
                    ).order_by(StructuredRecord.created_at.desc()).all()
                except ValueError:
                    print("日期格式错误，请使用 YYYY-MM-DD 格式")
                    return
            
            elif choice == "3":
                # 按员工统计
                name = input("请输入员工姓名（留空统计所有员工）: ").strip()
                all_records = query.all()
                if name:
                    records = [r for r in all_records if name in r.structured_data.get('fields', {}).get('name', '')]
                else:
                    records = all_records
                records.sort(key=lambda x: x.created_at, reverse=True)
            
            elif choice == "4":
                # 按状态统计
                status = input("请输入状态（留空统计所有状态）: ").strip()
                all_records = query.all()
                if status:
                    records = [r for r in all_records if status in r.structured_data.get('fields', {}).get('status', '')]
                else:
                    records = all_records
                records.sort(key=lambda x: x.created_at, reverse=True)
            
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
            
            # 提取数据
            employee_stats = defaultdict(lambda: {
                "count": 0,
                "tasks": [],
                "statuses": defaultdict(int),
                "attitudes": defaultdict(int),
                "work_states": defaultdict(int),
                "completions": [],
                "dates": []
            })
            
            status_stats = defaultdict(int)
            attitude_stats = defaultdict(int)
            work_state_stats = defaultdict(int)
            date_list = []
            total_completion = 0
            completion_count = 0
            
            for record in records:
                fields = record.structured_data.get('fields', {})
                name = fields.get('name', '未知')
                task = fields.get('task', '')
                status = fields.get('status', '未知')
                work_attitude = fields.get('work_attitude', '未记录')
                work_state = fields.get('work_state', '未记录')
                completion = fields.get('completion', None)
                date_str = fields.get('date', record.created_at.strftime('%Y-%m-%d'))
                
                # 员工统计
                employee_stats[name]["count"] += 1
                employee_stats[name]["tasks"].append(task)
                employee_stats[name]["statuses"][status] += 1
                employee_stats[name]["attitudes"][work_attitude] += 1
                employee_stats[name]["work_states"][work_state] += 1
                if completion is not None:
                    employee_stats[name]["completions"].append(completion)
                employee_stats[name]["dates"].append(date_str)
                
                # 全局统计
                status_stats[status] += 1
                attitude_stats[work_attitude] += 1
                work_state_stats[work_state] += 1
                date_list.append(date_str)
                if completion is not None:
                    total_completion += completion
                    completion_count += 1
            
            record_count = len(records)
            avg_completion = total_completion / completion_count if completion_count > 0 else 0
            
            # 显示总体统计
            print(f"\n【总体概况】")
            print(f"  记录总数: {record_count} 条")
            print(f"  员工数量: {len(employee_stats)} 人")
            if completion_count > 0:
                print(f"  平均完成度: {avg_completion:.1f}%")
            if date_list:
                min_date = min(date_list)
                max_date = max(date_list)
                print(f"  时间范围: {min_date} 至 {max_date}")
            
            # 按员工统计
            print(f"\n【按员工统计】")
            if employee_stats:
                sorted_employees = sorted(employee_stats.items(), key=lambda x: x[1]["count"], reverse=True)
                for name, stats in sorted_employees:
                    print(f"\n  {name}:")
                    print(f"    记录数: {stats['count']} 条")
                    print(f"    任务数: {len(stats['tasks'])} 个")
                    
                    # 状态分布
                    if stats['statuses']:
                        status_str = ", ".join([f"{k}({v})" for k, v in stats['statuses'].items()])
                        print(f"    状态分布: {status_str}")
                    
                    # 工作态度分布
                    if stats['attitudes'] and '未记录' not in stats['attitudes']:
                        attitude_str = ", ".join([f"{k}({v})" for k, v in stats['attitudes'].items() if k != '未记录'])
                        if attitude_str:
                            print(f"    工作态度: {attitude_str}")
                    
                    # 工作状态分布
                    if stats['work_states'] and '未记录' not in stats['work_states']:
                        work_state_str = ", ".join([f"{k}({v})" for k, v in stats['work_states'].items() if k != '未记录'])
                        if work_state_str:
                            print(f"    工作状态: {work_state_str}")
                    
                    # 平均完成度
                    if stats['completions']:
                        avg_emp_completion = sum(stats['completions']) / len(stats['completions'])
                        print(f"    平均完成度: {avg_emp_completion:.1f}%")
            else:
                print("  暂无员工数据")
            
            # 按状态统计
            print(f"\n【按状态统计】")
            if status_stats:
                sorted_statuses = sorted(status_stats.items(), key=lambda x: x[1], reverse=True)
                for status, count in sorted_statuses:
                    percentage = (count / record_count * 100) if record_count > 0 else 0
                    print(f"  {status}: {count} 条 ({percentage:.1f}%)")
            else:
                print("  暂无状态数据")
            
            # 按工作态度统计
            print(f"\n【按工作态度统计】")
            if attitude_stats:
                sorted_attitudes = sorted(attitude_stats.items(), key=lambda x: x[1], reverse=True)
                for attitude, count in sorted_attitudes:
                    if attitude != '未记录':
                        percentage = (count / record_count * 100) if record_count > 0 else 0
                        print(f"  {attitude}: {count} 条 ({percentage:.1f}%)")
            else:
                print("  暂无工作态度数据")
            
            # 按工作状态统计
            print(f"\n【按工作状态统计】")
            if work_state_stats:
                sorted_work_states = sorted(work_state_stats.items(), key=lambda x: x[1], reverse=True)
                for work_state, count in sorted_work_states:
                    if work_state != '未记录':
                        percentage = (count / record_count * 100) if record_count > 0 else 0
                        print(f"  {work_state}: {count} 条 ({percentage:.1f}%)")
            else:
                print("  暂无工作状态数据")
            
            # 工作状态趋势（按日期统计）
            print(f"\n【工作记录趋势】")
            date_count_map = defaultdict(int)
            for record in records:
                date_str = record.structured_data.get('fields', {}).get('date', record.created_at.strftime('%Y-%m-%d'))
                date_count_map[date_str] += 1
            
            if date_count_map:
                sorted_dates = sorted(date_count_map.items())
                print(f"  共 {len(date_count_map)} 个日期有工作记录")
                if len(sorted_dates) <= 10:
                    for date_str, count in sorted_dates:
                        print(f"    {date_str}: {count} 条记录")
                else:
                    print(f"  前5天:")
                    for date_str, count in sorted_dates[:5]:
                        print(f"    {date_str}: {count} 条记录")
                    print(f"  ...")
                    print(f"  后5天:")
                    for date_str, count in sorted_dates[-5:]:
                        print(f"    {date_str}: {count} 条记录")
            
            print("="*60)
        
        finally:
            session.close()
        
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
        
        session = self.db.get_session()
        try:
            record = session.query(StructuredRecord).filter(
                StructuredRecord.id == int(record_id),
                StructuredRecord.table_name == self.table_name
            ).first()
            
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
            
            # 重新结构化
            print("\n正在处理...")
            # 获取当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")
            # 格式化prompt模板，传入当前日期
            # 直接在模板中替换占位符，避免format方法误解JSON示例中的字符串
            prompt_template_with_date = EMPLOYEE_PROMPT_TEMPLATE.replace("{current_date}", current_date)
            structured_data = self.llm_client.structure_text(
                text=new_text,
                prompt_template=prompt_template_with_date
            )
            
            # 更新记录
            record.original_text = new_text
            record.structured_data = structured_data
            record.updated_at = datetime.utcnow()
            
            session.commit()
            print(f"\n✓ 更新成功！")
        
        except Exception as e:
            session.rollback()
            print(f"\n✗ 更新失败: {e}")
        finally:
            session.close()
        
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
        
        session = self.db.get_session()
        try:
            record = session.query(StructuredRecord).filter(
                StructuredRecord.id == int(record_id),
                StructuredRecord.table_name == self.table_name
            ).first()
            
            if not record:
                print("记录不存在")
                return
            
            session.delete(record)
            session.commit()
            print(f"\n✓ 删除成功！")
        
        except Exception as e:
            session.rollback()
            print(f"\n✗ 删除失败: {e}")
        finally:
            session.close()
        
        input("\n按回车键继续...")
    
    def switch_table(self):
        """切换表/目录"""
        print("\n" + "-"*60)
        print("切换表/目录")
        print("-"*60)
        
        # 获取所有表
        session = self.db.get_session()
        try:
            tables = session.query(StructuredRecord.table_name).distinct().all()
            table_list = [t[0] for t in tables if t[0]]
            
            if table_list:
                print("\n可用的表/目录：")
                for i, table in enumerate(table_list, 1):
                    marker = " ← 当前" if table == self.table_name else ""
                    print(f"  {i}. {table}{marker}")
            
            print(f"\n当前表: {self.table_name}")
            new_table = input("请输入新表名（直接回车保持当前）: ").strip()
            
            if new_table:
                self.table_name = new_table
                print(f"\n✓ 已切换到: {self.table_name}")
            else:
                print("保持当前表")
        
        finally:
            session.close()
        
        input("\n按回车键继续...")
    
    def list_tables(self):
        """查看所有表/目录"""
        print("\n" + "-"*60)
        print("所有表/目录")
        print("-"*60)
        
        session = self.db.get_session()
        try:
            # 获取所有表及其记录数
            from sqlalchemy import func
            result = session.query(
                StructuredRecord.table_name,
                func.count(StructuredRecord.id).label('count')
            ).filter(
                StructuredRecord.table_name.isnot(None)
            ).group_by(StructuredRecord.table_name).all()
            
            if result:
                print(f"\n{'表名':<20} {'记录数':<10}")
                print("-"*30)
                for table_name, count in result:
                    marker = " ← 当前" if table_name == self.table_name else ""
                    print(f"{table_name:<20} {count:<10}{marker}")
            else:
                print("\n暂无表/目录")
        
        finally:
            session.close()
        
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
    """主函数"""
    print("\n" + "="*60)
    print("员工工作情况管理系统")
    print("="*60)
    
    manager = EmployeeManager()
    manager.run()


if __name__ == "__main__":
    main()
