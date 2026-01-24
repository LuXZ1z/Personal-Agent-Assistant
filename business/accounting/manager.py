"""
记账业务管理界面
交互式记账管理，支持增删改查
使用 core.database 和 core.llm 基础功能
"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime, timedelta
import json
from collections import defaultdict
from typing import Optional

from core.database import get_database_manager
from core.llm import LLMClient
from business.accounting.prompts import ACCOUNTING_PROMPT_TEMPLATE, ACCOUNTING_SUMMARY_PROMPT
from shared.utils import setup_logger

logger = setup_logger(__name__)


class AccountingManager:
    """记账管理器 - 使用 core 基础功能"""
    
    def __init__(self, user_id: Optional[str] = None, bot_id: Optional[str] = None, debug: bool = False):
        """
        初始化记账管理器
        
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
                logger.info(f"记账管理器初始化成功: user_id={user_id}, bot_id={bot_id}")
            except Exception as e:
                logger.error(f"初始化数据库失败: {e}", exc_info=True)
        self.llm_client = LLMClient()
        self.table_name = "记账"  # 默认表名
    
    def show_main_menu(self):
        """显示主菜单"""
        print("\n" + "="*60)
        print("记账管理系统")
        print("="*60)
        if self.user_id:
            print(f"用户: {self.user_id}")
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
            # 格式化prompt模板，保留 {text} 占位符供 structure_text 方法使用
            prompt_template_with_date = ACCOUNTING_PROMPT_TEMPLATE.format(current_date=current_date, text="{text}")
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
                # 使用 core.database 创建记录
                record = self.db.create_record(
                    original_text=text,
                    structured_data=structured_data,
                    record_type=structured_data.get('type', '记账'),
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
        
        try:
            filters = {
                "record_type": "记账",
                "table_name": self.table_name
            }
            
            if choice == "1":
                # 查询所有
                records = self.db.query_records(
                    filters=filters,
                    limit=50,
                    order_by="-created_at",
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
            
            elif choice == "2":
                # 按日期查询（单日）
                date_str = input("请输入日期 (YYYY-MM-DD): ").strip()
                try:
                    filters["date_from"] = date_str
                    filters["date_to"] = date_str
                    records = self.db.query_records(
                        filters=filters,
                        order_by="-created_at",
                        user_id=self.user_id,
                        bot_id=self.bot_id
                    )
                except ValueError:
                    print("日期格式错误")
                    return
            
            elif choice == "3":
                # 按时间段查询（日期范围）
                start_date_str = input("请输入开始日期 (YYYY-MM-DD): ").strip()
                end_date_str = input("请输入结束日期 (YYYY-MM-DD): ").strip()
                try:
                    filters["date_from"] = start_date_str
                    filters["date_to"] = end_date_str
                    records = self.db.query_records(
                        filters=filters,
                        order_by="-created_at",
                        user_id=self.user_id,
                        bot_id=self.bot_id
                    )
                except ValueError:
                    print("日期格式错误，请使用 YYYY-MM-DD 格式")
                    return
            
            elif choice == "4":
                # 按类别查询（需要手动过滤）
                category = input("请输入类别: ").strip()
                all_records = self.db.query_records(
                    filters=filters,
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
                records = []
                for r in all_records:
                    if r.structured_data.get('fields', {}).get('category') == category:
                        records.append(r)
            
            elif choice == "5":
                # 按金额范围查询
                min_amount = input("最小金额: ").strip()
                max_amount = input("最大金额: ").strip()
                try:
                    min_val = float(min_amount) if min_amount else 0
                    max_val = float(max_amount) if max_amount else float('inf')
                    all_records = self.db.query_records(
                        filters=filters,
                        user_id=self.user_id,
                        bot_id=self.bot_id
                    )
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
                filters["keyword"] = keyword
                records = self.db.query_records(
                    filters=filters,
                    order_by="-created_at",
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
            
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
        
        except Exception as e:
            print(f"\n✗ 查询失败: {e}")
            import traceback
            traceback.print_exc()
        
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
        
        try:
            filters = {
                "record_type": "记账",
                "table_name": self.table_name
            }
            
            records = []
            
            if choice == "1":
                records = self.db.query_records(
                    filters=filters,
                    limit=100,
                    order_by="-created_at",
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
            
            elif choice == "2":
                date_str = input("请输入日期 (YYYY-MM-DD): ").strip()
                try:
                    filters["date_from"] = date_str
                    filters["date_to"] = date_str
                    records = self.db.query_records(
                        filters=filters,
                        order_by="-created_at",
                        user_id=self.user_id,
                        bot_id=self.bot_id
                    )
                except ValueError:
                    print("日期格式错误")
                    return
            
            elif choice == "3":
                start_date_str = input("请输入开始日期 (YYYY-MM-DD): ").strip()
                end_date_str = input("请输入结束日期 (YYYY-MM-DD): ").strip()
                try:
                    filters["date_from"] = start_date_str
                    filters["date_to"] = end_date_str
                    records = self.db.query_records(
                        filters=filters,
                        order_by="-created_at",
                        user_id=self.user_id,
                        bot_id=self.bot_id
                    )
                except ValueError:
                    print("日期格式错误，请使用 YYYY-MM-DD 格式")
                    return
            
            elif choice == "4":
                category = input("请输入类别: ").strip()
                all_records = self.db.query_records(
                    filters=filters,
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
                records = [r for r in all_records if r.structured_data.get('fields', {}).get('category') == category]
            
            elif choice == "5":
                min_amount = input("最小金额: ").strip()
                max_amount = input("最大金额: ").strip()
                try:
                    min_val = float(min_amount) if min_amount else 0
                    max_val = float(max_amount) if max_amount else float('inf')
                    all_records = self.db.query_records(
                        filters=filters,
                        user_id=self.user_id,
                        bot_id=self.bot_id
                    )
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
                    
                    # 使用 core.llm 的 summarize 方法
                    summary_text = self.llm_client.summarize(
                        records=formatted_records[:50],
                        custom_prompt=ACCOUNTING_SUMMARY_PROMPT
                    )
                    
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
        
        except Exception as e:
            print(f"\n✗ 查询失败: {e}")
            import traceback
            traceback.print_exc()
        
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
        
        try:
            filters = {
                "record_type": "记账",
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
                try:
                    filters["date_from"] = start_date_str
                    filters["date_to"] = end_date_str
                    records = self.db.query_records(
                        filters=filters,
                        order_by="-created_at",
                        user_id=self.user_id,
                        bot_id=self.bot_id
                    )
                except ValueError:
                    print("日期格式错误，请使用 YYYY-MM-DD 格式")
                    return
            
            elif choice == "3":
                category = input("请输入类别: ").strip()
                all_records = self.db.query_records(
                    filters=filters,
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
                records = [r for r in all_records if r.structured_data.get('fields', {}).get('category') == category]
            
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
        
        except Exception as e:
            print(f"\n✗ 统计失败: {e}")
            import traceback
            traceback.print_exc()
        
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
        
        try:
            record = self.db.get_record(int(record_id), user_id=self.user_id)
            
            if not record:
                print("记录不存在")
                return
            
            if record.table_name != self.table_name:
                print("记录不属于当前表")
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
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt_template_with_date = ACCOUNTING_PROMPT_TEMPLATE.format(current_date=current_date, text="{text}")
            structured_data = self.llm_client.structure_text(
                text=new_text,
                prompt_template=prompt_template_with_date
            )
            
            # 更新记录
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
            # 获取所有表
            stats = self.db.get_statistics(
                filters={"record_type": "记账"},
                user_id=self.user_id
            )
            table_list = list(stats.get('by_table', {}).keys())
            
            if table_list:
                print("\n可用的表/目录（仅记账业务）：")
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
                    print(f"\n✗ 表 '{new_table}' 不存在或不属于记账业务")
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
        print("所有表/目录（仅记账业务）")
        print("-"*60)
        
        try:
            stats = self.db.get_statistics(
                filters={"record_type": "记账"},
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
    """主函数 - 支持 --debug 参数"""
    parser = argparse.ArgumentParser(description='记账业务管理系统')
    parser.add_argument('--debug', action='store_true', help='调试模式（本地测试）')
    parser.add_argument('--user-id', type=str, default=None, help='用户ID（多用户模式）')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("记账业务管理系统")
    if args.debug:
        print("调试模式")
    print("="*60)
    
    manager = AccountingManager(user_id=args.user_id, debug=args.debug)
    manager.run()


if __name__ == "__main__":
    main()
