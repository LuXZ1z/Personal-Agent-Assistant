"""
Service适配器
让CLI通过Service层处理业务逻辑，与微信服务器使用完全相同的代码
将Service的消息驱动接口转换为交互式接口
"""
from typing import Dict, Any, Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.menu_config import BUSINESS_CONFIG
from interfaces.wechat.session_manager import session_manager
import importlib


class ServiceAdapter:
    """Service适配器 - 将消息驱动接口转换为交互式接口"""
    
    def __init__(self, user_id: str, business_type: str):
        """
        初始化适配器
        
        Args:
            user_id: 用户ID
            business_type: 业务类型
        """
        self.user_id = user_id
        self.business_type = business_type
        self.service = self._create_service()
        # 初始化会话状态
        session_manager.update_business_type(user_id, business_type)
        session_manager.set_sub_menu(user_id, None)
    
    def _create_service(self):
        """创建Service实例"""
        if self.business_type not in BUSINESS_CONFIG:
            raise ValueError(f"未知的业务类型: {self.business_type}")
        
        try:
            # 从统一配置获取Service类路径
            service_class_path = BUSINESS_CONFIG[self.business_type]["service_class"]
            module_path, class_name = service_class_path.rsplit(".", 1)
            
            # 动态导入
            module = importlib.import_module(module_path)
            service_class = getattr(module, class_name)
            
            # 创建实例
            return service_class(self.user_id)
        except Exception as e:
            raise RuntimeError(f"加载业务Service失败: {e}")
    
    def run(self):
        """运行交互式循环（使用Service层处理业务逻辑）"""
        print("\n" + "="*60)
        print("提示：输入 '0' 返回主菜单")
        print("="*60)
        
        # 首次显示菜单
        session = session_manager.get_session(self.user_id)
        result = self.service.process_message("", session.context)
        if result.get("type") == "sub_menu":
            print("\n" + result.get("message", ""))
        
        while True:
            try:
                # 获取用户输入
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                # 检查退出命令
                if user_input == "0":
                    print("\n返回主菜单...")
                    session_manager.reset_to_menu(self.user_id)
                    break
                
                # 处理用户输入（使用与微信服务器完全相同的Service层）
                session = session_manager.get_session(self.user_id)
                result = self.service.process_message(user_input, session.context)
                
                # 显示结果
                if result.get("type") == "sub_menu":
                    print("\n" + result.get("message", ""))
                elif result.get("type") == "prompt":
                    print("\n" + result.get("message", ""))
                elif result.get("type") == "info":
                    print("\n" + result.get("message", ""))
                elif result.get("type") == "success":
                    print("\n" + result.get("message", ""))
                    # 成功后可能需要显示菜单
                    if "返回" in result.get("message", "") or "菜单" in result.get("message", ""):
                        # 显示子菜单
                        session = session_manager.get_session(self.user_id)
                        menu_result = self.service.process_message("", session.context)
                        if menu_result.get("type") == "sub_menu":
                            print("\n" + menu_result.get("message", ""))
                elif result.get("type") == "error":
                    print("\n❌ " + result.get("message", "发生错误"))
                else:
                    # 其他类型，显示消息
                    if result.get("message"):
                        print("\n" + result.get("message", ""))
                
            except KeyboardInterrupt:
                print("\n\n返回主菜单...")
                session_manager.reset_to_menu(self.user_id)
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                import traceback
                traceback.print_exc()
                input("\n按回车键继续...")

