"""
随笔业务管理界面
交互式随笔管理，支持增删改查和AI分析
使用 core.database 和 core.llm 基础功能
"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
import json
from typing import Optional

from core.database import get_database_manager
from core.llm import LLMClient
from business.essay.prompts import ESSAY_PROMPT_TEMPLATE, ESSAY_ANALYSIS_PROMPT
from shared.utils import setup_logger

logger = setup_logger(__name__)


class EssayManager:
    """随笔管理器 - 使用 core 基础功能"""
    
    def __init__(self, user_id: Optional[str] = None, bot_id: Optional[str] = None, debug: bool = False):
        """
        初始化随笔管理器
        
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
                logger.info(f"随笔管理器初始化成功: user_id={user_id}, bot_id={bot_id}")
            except Exception as e:
                logger.error(f"初始化数据库失败: {e}", exc_info=True)
        self.llm_client = LLMClient()
        self.table_name = "随笔"  # 默认表名
    
    def show_main_menu(self):
        """显示主菜单"""
        print("\n" + "="*60)
        print("随笔管理系统")
        print("="*60)
        if self.user_id:
            print(f"用户: {self.user_id}")
        print(f"当前表/目录: {self.table_name}")
        print("\n请选择操作：")
        print("  1. 添加随笔记录（输入自然语言）")
        print("  2. 查询随笔记录")
        print("  3. 修改随笔记录")
        print("  4. 删除随笔记录")
        print("  5. 切换表/目录")
        print("  6. 查看所有表/目录")
        print("  7. AI分析随笔（查看AI回应）")
        print("  0. 退出")
        print("="*60)
    
    def add_record(self):
        """添加随笔记录"""
        print("\n" + "-"*60)
        print("添加随笔记录")
        print("-"*60)
        print("请输入随笔内容（自然语言），例如：")
        print("  - 今天心情很好，在咖啡厅写下了这些想法...")
        print("  - 关于工作的思考：我觉得...")
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
            prompt_template_with_date = ESSAY_PROMPT_TEMPLATE.replace("{current_date}", current_date)
            
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
                    record_type=structured_data.get('type', '随笔'),
                    table_name=self.table_name,
                    metadata=None,
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
                print(f"\n✓ 保存成功！记录ID: {record.id}")
                
                analyze_choice = input("\n是否立即进行AI分析？(y/n): ").strip().lower()
                if analyze_choice == 'y':
                    self._analyze_essay(record)
            else:
                print("已取消保存")
        
        except Exception as e:
            print(f"\n✗ 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _analyze_essay(self, record):
        """分析随笔并显示AI回应"""
        print("\n" + "-"*60)
        print("正在生成AI分析...")
        print("-"*60)
        
        try:
            fields = record.structured_data.get('fields', {})
            essay_content = fields.get('content', record.original_text)
            essay_date = fields.get('date', record.created_at.strftime('%Y-%m-%d'))
            essay_tags = ', '.join(fields.get('tags', [])) if fields.get('tags') else '无'
            essay_mood = fields.get('mood', '未记录')
            essay_location = fields.get('location', '未记录')
            
            # 构建分析prompt
            prompt = ESSAY_ANALYSIS_PROMPT.format(
                essay_content=essay_content,
                essay_date=essay_date,
                essay_tags=essay_tags,
                essay_mood=essay_mood,
                essay_location=essay_location
            )
            
            # 使用 core.llm 的 analyze 方法
            analysis_text = self.llm_client.analyze(
                content=essay_content,
                custom_prompt=prompt
            )
            
            print("\n" + "="*60)
            print("AI分析回应")
            print("="*60)
            print(analysis_text)
            print("="*60)
            
            save_analysis = input("\n是否保存分析结果到记录？(y/n): ").strip().lower()
            if save_analysis == 'y':
                self.db.update_record(
                    record_id=record.id,
                    metadata={'ai_analysis': analysis_text, 'analysis_date': datetime.now().isoformat()},
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
                print("\n✓ 分析结果已保存")
        
        except Exception as e:
            print(f"\n✗ AI分析失败: {e}")
            import traceback
            traceback.print_exc()
    
    def query_records(self):
        """查询随笔记录"""
        print("\n" + "-"*60)
        print("查询随笔记录")
        print("-"*60)
        print("请选择查询方式：")
        print("  1. 查询所有记录")
        print("  2. 按日期查询（单日）")
        print("  3. 按时间段查询（日期范围）")
        print("  4. 按标签查询")
        print("  5. 按关键词搜索")
        print("  6. 按心情查询")
        print("  0. 返回")
        
        choice = input("\n> ").strip()
        
        try:
            filters = {
                "record_type": "随笔",
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
                date_str = input("请输入日期 (YYYY-MM-DD): ").strip()
                filters["date_from"] = date_str
                filters["date_to"] = date_str
                records = self.db.query_records(
                    filters=filters,
                    order_by="-created_at",
                    user_id=self.user_id,
                    bot_id=self.bot_id
                )
            elif choice == "3":
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
            elif choice == "5":
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
                    title = fields.get('title', '无标题')
                    content_preview = fields.get('content', '')[:50] + '...' if len(fields.get('content', '')) > 50 else fields.get('content', '')
                    date_str = fields.get('date', '')
                    tags = ', '.join(fields.get('tags', [])) if fields.get('tags') else '无标签'
                    mood = fields.get('mood', '未记录')
                    summary = record.structured_data.get('summary', '')
                    
                    print(f"\n[{i}] ID: {record.id}")
                    print(f"    标题: {title}")
                    print(f"    日期: {date_str} | 心情: {mood} | 标签: {tags}")
                    print(f"    内容预览: {content_preview}")
                    print(f"    摘要: {summary}")
                    print(f"    创建时间: {record.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print("\n未找到记录")
        
        except Exception as e:
            print(f"\n✗ 查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        input("\n按回车键继续...")
    
    def update_record(self):
        """修改随笔记录"""
        print("\n" + "-"*60)
        print("修改随笔记录")
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
            
            print("\n请输入新的随笔内容（自然语言）:")
            new_text = input("> ").strip()
            
            if not new_text:
                print("输入不能为空")
                return
            
            print("\n正在处理...")
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt_template_with_date = ESSAY_PROMPT_TEMPLATE.replace("{current_date}", current_date)
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
        """删除随笔记录"""
        print("\n" + "-"*60)
        print("删除随笔记录")
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
    
    def analyze_essay(self):
        """AI分析随笔"""
        print("\n" + "-"*60)
        print("AI分析随笔")
        print("-"*60)
        
        record_id = input("请输入要分析的记录ID: ").strip()
        if not record_id.isdigit():
            print("ID格式错误")
            return
        
        try:
            record = self.db.get_record(int(record_id), user_id=self.user_id)
            if not record:
                print("记录不存在")
                return
            
            self._analyze_essay(record)
        
        except Exception as e:
            print(f"\n✗ 分析失败: {e}")
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
                filters={"record_type": "随笔"},
                user_id=self.user_id
            )
            table_list = list(stats.get('by_table', {}).keys())
            
            if table_list:
                print("\n可用的表/目录（仅随笔业务）：")
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
                    print(f"\n✗ 表 '{new_table}' 不存在或不属于随笔业务")
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
        print("所有表/目录（仅随笔业务）")
        print("-"*60)
        
        try:
            stats = self.db.get_statistics(
                filters={"record_type": "随笔"},
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
                    self.analyze_essay()
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
    parser = argparse.ArgumentParser(description='随笔业务管理系统')
    parser.add_argument('--debug', action='store_true', help='调试模式（本地测试）')
    parser.add_argument('--user-id', type=str, default=None, help='用户ID（多用户模式）')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("随笔业务管理系统")
    if args.debug:
        print("调试模式")
    print("="*60)
    
    manager = EssayManager(user_id=args.user_id, debug=args.debug)
    manager.run()


if __name__ == "__main__":
    main()
