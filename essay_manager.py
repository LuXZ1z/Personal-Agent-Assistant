"""
随笔业务管理界面
交互式随笔管理，支持增删改查和AI分析
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.config import settings
from shared.models import StructuredRecord
from agent_storage.database import db
from agent_structurizer.llm_client import LLMClient
from agent_structurizer.prompt_templates import ESSAY_PROMPT_TEMPLATE, ESSAY_ANALYSIS_PROMPT
from shared.utils import setup_logger
from datetime import datetime, timedelta
import json

logger = setup_logger(__name__)


class EssayManager:
    """随笔管理器"""
    
    def __init__(self):
        """初始化随笔管理器"""
        self.db = db
        self.llm_client = LLMClient()
        self.table_name = "随笔"  # 默认表名
    
    def show_main_menu(self):
        """显示主菜单"""
        print("\n" + "="*60)
        print("随笔管理系统")
        print("="*60)
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
        print("  - 2024-01-15 今天发生了一件有趣的事...")
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
            prompt_template_with_date = ESSAY_PROMPT_TEMPLATE.replace("{current_date}", current_date)
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
                        record_type=structured_data.get('type', '随笔'),
                        table_name=self.table_name,
                        metadata=None
                    )
                    session.add(record)
                    session.commit()
                    session.refresh(record)
                    print(f"\n✓ 保存成功！记录ID: {record.id}")
                    
                    # 保存后自动进行AI分析
                    analyze_choice = input("\n是否立即进行AI分析？(y/n): ").strip().lower()
                    if analyze_choice == 'y':
                        self._analyze_essay(record)
                    
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
            
            # 调用LLM分析
            response = self.llm_client.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个温暖、专业的心理和内容分析助手，能够对随笔进行深入分析并给出有温度的回应。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            print("\n" + "="*60)
            print("AI分析回应")
            print("="*60)
            print(analysis_text)
            print("="*60)
            
            # 可选：将分析结果保存到extra_metadata
            save_analysis = input("\n是否保存分析结果到记录？(y/n): ").strip().lower()
            if save_analysis == 'y':
                session = self.db.get_session()
                try:
                    db_record = session.query(StructuredRecord).filter(
                        StructuredRecord.id == record.id
                    ).first()
                    if db_record:
                        if db_record.extra_metadata is None:
                            db_record.extra_metadata = {}
                        db_record.extra_metadata['ai_analysis'] = analysis_text
                        db_record.extra_metadata['analysis_date'] = datetime.now().isoformat()
                        session.commit()
                        print("\n✓ 分析结果已保存")
                except Exception as e:
                    session.rollback()
                    print(f"\n✗ 保存分析结果失败: {e}")
                finally:
                    session.close()
            
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
        
        session = self.db.get_session()
        try:
            query = session.query(StructuredRecord).filter(
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "随笔"
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
                # 按标签查询
                tag = input("请输入标签: ").strip()
                all_records = query.all()
                records = []
                for r in all_records:
                    tags = r.structured_data.get('fields', {}).get('tags', [])
                    if tag in tags:
                        records.append(r)
                records.sort(key=lambda x: x.created_at, reverse=True)
            
            elif choice == "5":
                # 按关键词搜索
                keyword = input("请输入关键词: ").strip()
                records = query.filter(
                    StructuredRecord.original_text.contains(keyword)
                ).order_by(StructuredRecord.created_at.desc()).all()
            
            elif choice == "6":
                # 按心情查询
                mood = input("请输入心情: ").strip()
                all_records = query.all()
                records = []
                for r in all_records:
                    record_mood = r.structured_data.get('fields', {}).get('mood', '')
                    if mood in record_mood:
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
        
        finally:
            session.close()
        
        input("\n按回车键继续...")
    
    def analyze_essay(self):
        """AI分析随笔（查看AI回应）"""
        print("\n" + "-"*60)
        print("AI分析随笔")
        print("-"*60)
        
        record_id = input("请输入要分析的记录ID: ").strip()
        if not record_id.isdigit():
            print("ID格式错误")
            return
        
        session = self.db.get_session()
        try:
            record = session.query(StructuredRecord).filter(
                StructuredRecord.id == int(record_id),
                StructuredRecord.table_name == self.table_name,
                StructuredRecord.record_type == "随笔"
            ).first()
            
            if not record:
                print("记录不存在")
                return
            
            # 显示记录信息
            fields = record.structured_data.get('fields', {})
            print(f"\n记录信息:")
            print(f"  ID: {record.id}")
            print(f"  日期: {fields.get('date', '')}")
            print(f"  标题: {fields.get('title', '无标题')}")
            print(f"  内容: {fields.get('content', record.original_text)[:100]}...")
            
            # 检查是否已有分析结果
            if record.extra_metadata and record.extra_metadata.get('ai_analysis'):
                print(f"\n已有分析结果（生成于: {record.extra_metadata.get('analysis_date', '未知')}）")
                show_existing = input("是否查看已有分析？(y/n): ").strip().lower()
                if show_existing == 'y':
                    print("\n" + "="*60)
                    print("已有AI分析回应")
                    print("="*60)
                    print(record.extra_metadata['ai_analysis'])
                    print("="*60)
                    regenerate = input("\n是否重新生成分析？(y/n): ").strip().lower()
                    if regenerate != 'y':
                        return
            
            # 进行AI分析
            self._analyze_essay(record)
        
        finally:
            session.close()
        
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
            
            print("\n请输入新的随笔内容（自然语言）:")
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
            prompt_template_with_date = ESSAY_PROMPT_TEMPLATE.replace("{current_date}", current_date)
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
    """主函数"""
    print("\n" + "="*60)
    print("随笔业务管理系统")
    print("="*60)
    
    manager = EssayManager()
    manager.run()


if __name__ == "__main__":
    main()

