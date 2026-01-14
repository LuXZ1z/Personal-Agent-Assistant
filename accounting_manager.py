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
from agent_structurizer.prompt_templates import ACCOUNTING_PROMPT_TEMPLATE, ACCOUNTING_SUMMARY_PROMPT
from shared.utils import setup_logger
from datetime import datetime, timedelta
import json
from collections import defaultdict

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
        print("  7. 查询并总结")
        print("  8. 统计分析")
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
            # 获取当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")
            # 格式化prompt模板，传入当前日期（text会在structure_text中格式化）
            prompt_template_with_date = ACCOUNTING_PROMPT_TEMPLATE.format(current_date=current_date)
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
        print("  2. 按日期查询（单日）")
        print("  3. 按时间段查询（日期范围）")
        print("  4. 按类别查询")
        print("  5. 按金额范围查询")
        print("  6. 按关键词搜索")
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
            
            elif choice == "3":
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
            
            elif choice == "4":
                # 按类别查询
                category = input("请输入类别: ").strip()
                records = query.filter(
                    StructuredRecord.structured_data.contains({"fields": {"category": category}})
                ).order_by(StructuredRecord.created_at.desc()).all()
            
            elif choice == "5":
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
            
            elif choice == "6":
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
    
    def _format_records_for_summary(self, records):
        """格式化记录用于总结"""
        formatted_records = []
        for record in records:
            fields = record.structured_data.get('fields', {})
            formatted_record = {
                "id": record.id,
                "日期": fields.get('date', record.created_at.strftime('%Y-%m-%d')),
                "金额": fields.get('amount', 0),
                "类别": fields.get('category', '未知'),
                "摘要": record.structured_data.get('summary', ''),
                "支付方式": fields.get('payment_method', '未知'),
                "地点": fields.get('location', '')
            }
            formatted_records.append(formatted_record)
        return formatted_records
    
    def query_and_summarize(self):
        """查询并总结记账记录"""
        print("\n" + "-"*60)
        print("查询并总结记账记录")
        print("-"*60)
        print("请选择查询方式：")
        print("  1. 查询所有记录并总结")
        print("  2. 按日期查询并总结（单日）")
        print("  3. 按时间段查询并总结（日期范围）")
        print("  4. 按类别查询并总结")
        print("  5. 按金额范围查询并总结")
        print("  6. 按关键词搜索并总结")
        print("  0. 返回")
        
        choice = input("\n> ").strip()
        
        session = self.db.get_session()
        try:
            query = session.query(StructuredRecord).filter(
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "记账"
            )
            
            records = []
            
            if choice == "1":
                # 查询所有
                records = query.order_by(StructuredRecord.created_at.desc()).limit(100).all()
            
            elif choice == "2":
                # 按日期查询
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
            
            elif choice == "3":
                # 按时间段查询
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
            
            elif choice == "4":
                # 按类别查询
                category = input("请输入类别: ").strip()
                records = query.filter(
                    StructuredRecord.structured_data.contains({"fields": {"category": category}})
                ).order_by(StructuredRecord.created_at.desc()).all()
            
            elif choice == "5":
                # 按金额范围查询
                min_amount = input("最小金额: ").strip()
                max_amount = input("最大金额: ").strip()
                try:
                    min_val = float(min_amount) if min_amount else 0
                    max_val = float(max_amount) if max_amount else float('inf')
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
            
            elif choice == "6":
                # 按关键词搜索
                keyword = input("请输入关键词: ").strip()
                records = query.filter(
                    StructuredRecord.original_text.contains(keyword)
                ).order_by(StructuredRecord.created_at.desc()).all()
            
            else:
                return
            
            # 显示查询结果
            if records:
                print(f"\n找到 {len(records)} 条记录")
                print("-"*60)
                
                # 显示前10条记录预览
                preview_count = min(10, len(records))
                print(f"\n前 {preview_count} 条记录预览：")
                for i, record in enumerate(records[:preview_count], 1):
                    fields = record.structured_data.get('fields', {})
                    amount = fields.get('amount', 0)
                    category = fields.get('category', '未知')
                    date_str = fields.get('date', '')
                    summary = record.structured_data.get('summary', '')
                    
                    print(f"\n[{i}] ID: {record.id}")
                    print(f"    金额: {amount}元 | 类别: {category} | 日期: {date_str}")
                    print(f"    摘要: {summary}")
                
                if len(records) > preview_count:
                    print(f"\n... 还有 {len(records) - preview_count} 条记录")
                
                # 调用LLM进行总结
                print("\n" + "-"*60)
                print("正在生成总结...")
                print("-"*60)
                
                try:
                    # 格式化记录
                    formatted_records = self._format_records_for_summary(records)
                    records_text = "\n".join([
                        f"记录{i+1}: {json.dumps(r, ensure_ascii=False)}"
                        for i, r in enumerate(formatted_records[:50])  # 最多50条
                    ])
                    
                    # 构建总结prompt
                    prompt = ACCOUNTING_SUMMARY_PROMPT.format(records_data=records_text)
                    
                    # 调用LLM总结
                    response = self.llm_client.client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "你是一个专业的记账分析助手，能够对多条记账记录进行总结和分析。"},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.5,
                        max_tokens=1000
                    )
                    
                    summary_text = response.choices[0].message.content.strip()
                    
                    print("\n" + "="*60)
                    print("总结分析结果")
                    print("="*60)
                    print(summary_text)
                    print("="*60)
                    
                except Exception as e:
                    print(f"\n✗ 总结生成失败: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("\n未找到记录")
        
        finally:
            session.close()
        
        input("\n按回车键继续...")
    
    def statistics_analysis(self):
        """统计分析记账记录"""
        print("\n" + "-"*60)
        print("统计分析")
        print("-"*60)
        print("请选择统计范围：")
        print("  1. 统计所有记录")
        print("  2. 按时间段统计")
        print("  3. 按类别统计")
        print("  0. 返回")
        
        choice = input("\n> ").strip()
        
        session = self.db.get_session()
        try:
            query = session.query(StructuredRecord).filter(
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "记账"
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
                # 按类别统计
                category = input("请输入类别: ").strip()
                records = query.filter(
                    StructuredRecord.structured_data.contains({"fields": {"category": category}})
                ).order_by(StructuredRecord.created_at.desc()).all()
            
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
            total_amount = 0
            category_stats = defaultdict(lambda: {"count": 0, "amount": 0})
            payment_method_stats = defaultdict(lambda: {"count": 0, "amount": 0})
            date_list = []
            
            for record in records:
                fields = record.structured_data.get('fields', {})
                amount = float(fields.get('amount', 0))
                category = fields.get('category', '未知')
                payment_method = fields.get('payment_method', '未知')
                date_str = fields.get('date', record.created_at.strftime('%Y-%m-%d'))
                
                total_amount += amount
                category_stats[category]["count"] += 1
                category_stats[category]["amount"] += amount
                payment_method_stats[payment_method]["count"] += 1
                payment_method_stats[payment_method]["amount"] += amount
                date_list.append(date_str)
            
            record_count = len(records)
            avg_amount = total_amount / record_count if record_count > 0 else 0
            
            # 显示总体统计
            print(f"\n【总体概况】")
            print(f"  记录总数: {record_count} 条")
            print(f"  总支出: {total_amount:.2f} 元")
            print(f"  平均支出: {avg_amount:.2f} 元")
            
            if date_list:
                min_date = min(date_list)
                max_date = max(date_list)
                print(f"  时间范围: {min_date} 至 {max_date}")
            
            # 按类别统计
            print(f"\n【按类别统计】")
            if category_stats:
                # 按金额排序
                sorted_categories = sorted(category_stats.items(), key=lambda x: x[1]["amount"], reverse=True)
                for category, stats in sorted_categories:
                    percentage = (stats["amount"] / total_amount * 100) if total_amount > 0 else 0
                    print(f"  {category}: {stats['count']} 笔, {stats['amount']:.2f} 元 ({percentage:.1f}%)")
            else:
                print("  暂无类别数据")
            
            # 按支付方式统计
            print(f"\n【按支付方式统计】")
            if payment_method_stats:
                sorted_payment = sorted(payment_method_stats.items(), key=lambda x: x[1]["amount"], reverse=True)
                for payment_method, stats in sorted_payment:
                    percentage = (stats["amount"] / total_amount * 100) if total_amount > 0 else 0
                    print(f"  {payment_method}: {stats['count']} 笔, {stats['amount']:.2f} 元 ({percentage:.1f}%)")
            else:
                print("  暂无支付方式数据")
            
            # 支出趋势（按日期统计）
            print(f"\n【支出趋势】")
            date_amount_map = defaultdict(float)
            for record in records:
                fields = record.structured_data.get('fields', {})
                amount = float(fields.get('amount', 0))
                date_str = fields.get('date', record.created_at.strftime('%Y-%m-%d'))
                date_amount_map[date_str] += amount
            
            if date_amount_map:
                sorted_dates = sorted(date_amount_map.items())
                print(f"  共 {len(date_amount_map)} 个日期有支出记录")
                if len(sorted_dates) <= 10:
                    for date_str, amount in sorted_dates:
                        print(f"    {date_str}: {amount:.2f} 元")
                else:
                    print(f"  前5天:")
                    for date_str, amount in sorted_dates[:5]:
                        print(f"    {date_str}: {amount:.2f} 元")
                    print(f"  ...")
                    print(f"  后5天:")
                    for date_str, amount in sorted_dates[-5:]:
                        print(f"    {date_str}: {amount:.2f} 元")
            
            print("="*60)
        
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
            # 获取当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")
            # 格式化prompt模板，传入当前日期（text会在structure_text中格式化）
            prompt_template_with_date = ACCOUNTING_PROMPT_TEMPLATE.format(current_date=current_date)
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
                choice = input("\n请选择 (0-8): ").strip()
                
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
                    self.query_and_summarize()
                elif choice == "8":
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
    print("记账业务管理系统")
    print("="*60)
    
    manager = AccountingManager()
    manager.run()


if __name__ == "__main__":
    main()

