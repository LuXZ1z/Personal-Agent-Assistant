"""
命令行界面主入口
完全本地运行，通过数字菜单选择业务，直接调用业务管理器
支持两种模式：
1. 交互式模式（默认）：用于本地测试
2. 服务端模式（--server）：从Redis队列消费消息，处理业务逻辑
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Optional
import redis
from redis.exceptions import RedisError
from core.database import get_database_manager
from shared.models import StructuredRecord
from shared.utils import setup_logger
from shared.config import settings
from shared.menu_config import get_all_businesses, generate_menu_text, get_business_by_id_filtered, BUSINESS_CONFIG
from shared.message_types import BusinessRequest, BusinessResponse
from interfaces.cli.service_adapter import ServiceAdapter
from interfaces.wechat.message_router import message_router
from interfaces.wechat.session_manager import session_manager
import importlib

logger = setup_logger(__name__)


class CLIMain:
    """CLI主系统页面"""
    
    def __init__(self, bot_id: Optional[str] = None):
        """
        初始化CLI
        
        Args:
            bot_id: 机器人ID（可选），如果指定则只显示该机器人的功能
        """
        self.bot_id = bot_id or "default"
        self.user_id = f"local_test_user_{self.bot_id}"
        
        # 加载机器人配置（如果指定了bot_id）
        self.allowed_features = None
        self.bot_name = "默认（全功能）"
        
        if bot_id:
            try:
                from interfaces.wechat.bot_manager import bot_manager
                bot_config = bot_manager.get_bot_config(bot_id)
                self.allowed_features = bot_config.get('features')
                self.bot_name = bot_config.get('name', bot_id)
                print(f"\n🤖 当前测试机器人: {self.bot_name}")
                print(f"📋 可用功能: {', '.join(self.allowed_features)}")
            except ValueError as e:
                print(f"\n❌ 错误: {e}")
                print(f"💡 可用的机器人ID请查看 config/bots.yaml")
                raise
    
    def show_menu(self):
        """显示主菜单（使用动态过滤）"""
        menu_text = generate_menu_text(
            user_id=self.user_id, 
            include_status=True,
            allowed_features=self.allowed_features
        )
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
            adapter = ServiceAdapter(bot_id=self.bot_id, user_id=self.user_id, business_type=business_type)
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
                
                # 获取过滤后的业务列表
                businesses = get_all_businesses()
                if self.allowed_features:
                    businesses = [
                        b for b in businesses 
                        if b['business_type'] in self.allowed_features
                    ]
                    # 重新编号
                    for idx, business in enumerate(businesses, start=1):
                        business['id'] = str(idx)
                
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
                    # 动态查找业务（支持过滤后的编号）
                    if self.allowed_features:
                        business_info = get_business_by_id_filtered(choice, self.allowed_features)
                    else:
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


class CLIServer:
    """CLI服务端：从Redis队列消费消息，处理业务逻辑，返回结果"""
    
    def __init__(self):
        """初始化CLI服务端"""
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"CLI服务端初始化成功，Redis连接: {settings.redis_url}")
        except RedisError as e:
            logger.error(f"CLI服务端Redis连接失败: {e}")
            raise
    
    def _restore_session(self, session_dict: dict):
        """
        恢复会话状态
        
        Args:
            session_dict: 会话状态字典
        """
        bot_id = session_dict.get("bot_id")
        user_id = session_dict.get("user_id")
        if not bot_id or not user_id:
            return
        
        # 获取或创建会话
        session = session_manager.get_session(bot_id, user_id)
        
        # 恢复会话状态
        session.business_type = session_dict.get("business_type", "menu")
        session.sub_menu = session_dict.get("sub_menu")
        session.table_name = session_dict.get("table_name")
        session.context = session_dict.get("context", {})
        
        logger.debug(f"恢复会话状态: bot_id={bot_id}, user_id={user_id}, business_type={session.business_type}")
    
    def _process_message(self, request: BusinessRequest) -> BusinessResponse:
        """
        处理业务消息
        
        Args:
            request: 业务请求
            
        Returns:
            业务响应
        """
        try:
            logger.info(f"[CLI服务端] 处理消息: request_id={request.request_id}, bot_id={request.bot_id}, user_id={request.user_id}, content={request.content[:50]}")
            
            # 恢复会话状态
            self._restore_session(request.session)
            
            # 调用消息路由器处理消息
            result = message_router.route_message(
                bot_id=request.bot_id,
                user_id=request.user_id,
                content=request.content
            )
            
            # 获取当前会话状态（处理后的状态）
            session = session_manager.get_session(request.bot_id, request.user_id)
            session_dict = session.to_dict()
            session_dict.pop('last_activity', None)
            session_dict.pop('expire_at', None)
            
            # 在结果中包含bot_id和user_id，以便Server知道发送给谁
            result_with_metadata = {
                **result,
                "bot_id": request.bot_id,
                "user_id": request.user_id,
                "session": session_dict  # 更新后的会话状态
            }
            
            # 创建响应
            response = BusinessResponse(
                request_id=request.request_id,
                result=result_with_metadata
            )
            
            logger.info(f"[CLI服务端] 处理完成: request_id={request.request_id}, type={result.get('type')}")
            return response
            
        except Exception as e:
            logger.error(f"[CLI服务端] 处理消息失败: request_id={request.request_id}, error={e}", exc_info=True)
            # 返回错误响应
            return BusinessResponse(
                request_id=request.request_id,
                result={
                    "type": "error",
                    "message": f"处理消息时发生错误: {str(e)}",
                    "bot_id": request.bot_id,
                    "user_id": request.user_id
                }
            )
    
    def run(self):
        """运行服务端主循环"""
        logger.info("CLI服务端开始运行，等待消息...")
        logger.info("队列名称: wechat_messages")
        
        try:
            while True:
                try:
                    # 从队列右侧弹出消息（FIFO，阻塞等待）
                    message_data = self.redis_client.brpop("wechat_messages", timeout=1)
                    
                    if message_data:
                        # message_data 是 (queue_name, message_json) 元组
                        message_json = message_data[1]
                        
                        try:
                            # 解析消息
                            request = BusinessRequest.model_validate_json(message_json)
                            
                            # 处理消息
                            response = self._process_message(request)
                            
                            # 发送响应到响应队列
                            response_json = response.model_dump_json()
                            self.redis_client.lpush("wechat_responses", response_json)
                            
                            logger.info(f"[CLI服务端] 响应已发送: request_id={request.request_id}")
                            
                        except Exception as e:
                            logger.error(f"[CLI服务端] 处理消息异常: {e}", exc_info=True)
                            # 如果是BusinessRequest解析失败，可能是其他类型的消息，忽略
                            if "BusinessRequest" not in str(e):
                                logger.warning(f"[CLI服务端] 跳过非业务消息: {message_json[:100]}")
                
                except KeyboardInterrupt:
                    logger.info("收到中断信号，停止CLI服务端")
                    break
                except Exception as e:
                    logger.error(f"[CLI服务端] 循环异常: {e}", exc_info=True)
                    time.sleep(1)  # 出错后短暂休眠
                    
        except Exception as e:
            logger.error(f"[CLI服务端] 运行异常: {e}", exc_info=True)
        finally:
            logger.info("CLI服务端已停止")


def main():
    """主函数，支持命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description='本地业务测试')
    parser.add_argument('--bot', type=str, help='指定机器人ID (如: test, prod, hr)')
    parser.add_argument('--server', action='store_true', help='启动服务端模式（从队列消费消息）')
    args = parser.parse_args()
    
    # 服务端模式
    if args.server:
        try:
            print("\n" + "="*60)
            print("CLI服务端模式")
            print("="*60)
            print("从Redis队列消费消息，处理业务逻辑")
            print("按 Ctrl+C 停止服务端\n")
            
            server = CLIServer()
            server.run()
        except KeyboardInterrupt:
            print("\n\n服务端已停止")
        except Exception as e:
            print(f"\n❌ 服务端启动失败: {e}")
            import traceback
            traceback.print_exc()
        return
    
    # 交互式模式（默认）
    try:
        cli = CLIMain(bot_id=args.bot)
        cli.run()
    except ValueError:
        # 已经在 CLIMain.__init__ 中打印了错误信息
        return
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

