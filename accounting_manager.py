"""
记账业务管理界面
交互式记账管理，支持增删改查
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.config import settings
from shared.models import StructuredRecord
from agent_storage.database import db
from agent_structurizer.llm_client import LLMClient
from agent_structurizer.prompt_templates import ACCOUNTING_PROMPT_TEMPLATE
from shared.utils import setup_logger
from datetime import datetime
import json

logger = setup_logger(__name__)


class AccountingManager:
    """记账管理器"""
    
    def __init__(self):
        """初始化记账管理器"""
        self.db = db
        self.llm_client = LLMClient()
        self.table_name = "记账"  # 默认表名
    
    def show_main_menu(self):
        """显示主菜单"""
        print("\n" + "="*60)
        print("记账管理系统")
        print("="*60)
        print(f"当前表/目录: {self.table_name}")
        print("\n请选择操作：")
        print("  1. 添加记账记录（输入自然语言）")
        print("  2. 查询记账记录")
        print("  3. 修改记账记录")
        print("  4. 删除记账记录")
        print("  5. 切换表/目录")
        print("  6. 查看所有表/目录")
        print("  0. 退出")
        print("="*60)
    
    def add_record(self):
        """添加记账记录"""
        print("\n" + "-"*60)
        print("添加记账记录")
        print("-"*60)
        print("请输入记账信息（自然语言），例如：")
        print("  - 今天花了50元买了一杯咖啡")
        print("  - 在超市购物花费200元，用微信支付")
        print("  - 2024-01-15 打车花费30元")
        print("\n输入 'back' 返回主菜单")
        
        text = input("\n> ").strip()
        if text.lower() == 'back':
            return
        
        if not text:
            print("输入不能为空")
            return
        
        try:
            print("\n正在处理...")
            # 调用LLM进行结构化
            structured_data = self.llm_client.structure_text(
                text=text,
                prompt_template=ACCOUNTING_PROMPT_TEMPLATE
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
                        record_type=structured_data.get('type', '记账'),
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
        """查询记账记录"""
        print("\n" + "-"*60)
        print("查询记账记录")
        print("-"*60)
        print("请选择查询方式：")
        print("  1. 查询所有记录")
        print("  2. 按日期查询")
        print("  3. 按类别查询")
        print("  4. 按金额范围查询")
        print("  5. 按关键词搜索")
        print("  0. 返回")
        
        choice = input("\n> ").strip()
        
        session = self.db.get_session()
        try:
            query = session.query(StructuredRecord).filter(
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "记账"
            )
            
            if choice == "1":
                # 查询所有
                records = query.order_by(StructuredRecord.created_at.desc()).limit(50).all()
            
            elif choice == "2":
                # 按日期查询
                date_str = input("请输入日期 (YYYY-MM-DD): ").strip()
                try:
                    query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    from datetime import timedelta
                    records = query.filter(
                        StructuredRecord.created_at >= datetime.combine(query_date, datetime.min.time()),
                        StructuredRecord.created_at < datetime.combine(query_date, datetime.max.time()) + timedelta(days=1)
                    ).order_by(StructuredRecord.created_at.desc()).all()
                except ValueError:
                    print("日期格式错误")
                    return
            
            elif choice == "3":
                # 按类别查询
                category = input("请输入类别: ").strip()
                records = query.filter(
                    StructuredRecord.structured_data.contains({"fields": {"category": category}})
                ).order_by(StructuredRecord.created_at.desc()).all()
            
            elif choice == "4":
                # 按金额范围查询
                min_amount = input("最小金额: ").strip()
                max_amount = input("最大金额: ").strip()
                try:
                    min_val = float(min_amount) if min_amount else 0
                    max_val = float(max_amount) if max_amount else float('inf')
                    # 这里简化处理，实际应该用JSON查询
                    all_records = query.all()
                    records = []
                    for r in all_records:
                        amount = r.structured_data.get('fields', {}).get('amount', 0)
                        if min_val <= amount <= max_val:
                            records.append(r)
                    records.sort(key=lambda x: x.created_at, reverse=True)
                except ValueError:
                    print("金额格式错误")
                    return
            
            elif choice == "5":
                # 按关键词搜索
                keyword = input("请输入关键词: ").strip()
                records = query.filter(
                    StructuredRecord.original_text.contains(keyword)
                ).order_by(StructuredRecord.created_at.desc()).all()
            
            else:
                return
            
            # 显示结果
            if records:
                print(f"\n找到 {len(records)} 条记录：")
                print("-"*60)
                for i, record in enumerate(records, 1):
                    fields = record.structured_data.get('fields', {})
                    amount = fields.get('amount', 0)
                    category = fields.get('category', '未知')
                    date_str = fields.get('date', '')
                    summary = record.structured_data.get('summary', '')
                    
                    print(f"\n[{i}] ID: {record.id}")
                    print(f"    金额: {amount}元 | 类别: {category} | 日期: {date_str}")
                    print(f"    摘要: {summary}")
                    print(f"    创建时间: {record.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print("\n未找到记录")
        
        finally:
            session.close()
        
        input("\n按回车键继续...")
    
    def update_record(self):
        """修改记账记录"""
        print("\n" + "-"*60)
        print("修改记账记录")
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
            
            print("\n请输入新的记账信息（自然语言）:")
            new_text = input("> ").strip()
            
            if not new_text:
                print("输入不能为空")
                return
            
            # 重新结构化
            print("\n正在处理...")
            structured_data = self.llm_client.structure_text(
                text=new_text,
                prompt_template=ACCOUNTING_PROMPT_TEMPLATE
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
        """删除记账记录"""
        print("\n" + "-"*60)
        print("删除记账记录")
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
                choice = input("\n请选择 (0-6): ").strip()
                
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
    print("记账业务管理系统")
    print("="*60)
    
    manager = AccountingManager()
    manager.run()


if __name__ == "__main__":
    main()

