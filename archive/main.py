"""
主程序
启动所有Agent并处理优雅关闭
"""
import signal
import sys
import multiprocessing
import time
from pathlib import Path

from shared.utils import setup_logger

logger = setup_logger(__name__)


class AgentManager:
    """Agent管理器"""
    
    def __init__(self):
        """初始化Agent管理器"""
        self.processes = []
        self.running = True
    
    def start_agent(self, agent_module: str, agent_name: str):
        """
        启动一个Agent进程
        
        Args:
            agent_module: Agent模块路径
            agent_name: Agent名称
        """
        try:
            # 使用multiprocessing启动Agent
            process = multiprocessing.Process(
                target=self._run_agent,
                args=(agent_module, agent_name),
                name=agent_name
            )
            process.start()
            self.processes.append(process)
            logger.info(f"Agent启动成功: {agent_name} (PID: {process.pid})")
            return process
        except Exception as e:
            logger.error(f"启动Agent失败: {agent_name}, {e}")
            raise
    
    @staticmethod
    def _run_agent(agent_module: str, agent_name: str):
        """
        运行Agent（在子进程中）
        
        Args:
            agent_module: Agent模块路径
            agent_name: Agent名称
        """
        try:
            # 动态导入并运行Agent
            module_parts = agent_module.split(".")
            module = __import__(agent_module, fromlist=[module_parts[-1]])
            if hasattr(module, "main"):
                module.main()
            else:
                logger.error(f"Agent模块 {agent_module} 没有main函数")
        except Exception as e:
            logger.error(f"运行Agent失败: {agent_name}, {e}")
            raise
    
    def start_all_agents(self):
        """启动所有Agent"""
        logger.info("开始启动所有Agent...")
        
        # Agent列表：模块路径和名称
        agents = [
            ("agent_router.queue_consumer", "Agent0-消息路由"),
            ("agent_structurizer.queue_consumer", "Agent2-文本结构化"),
            ("agent_storage.queue_consumer", "Agent3-数据存储"),
            ("agent_service.queue_consumer", "Agent4-数据服务"),
            ("agent_tarot.queue_consumer", "Agent5-塔罗牌服务"),
        ]
        
        for agent_module, agent_name in agents:
            try:
                self.start_agent(agent_module, agent_name)
                time.sleep(0.5)  # 短暂延迟，避免同时启动
            except Exception as e:
                logger.error(f"启动Agent失败: {agent_name}, {e}")
                # 继续启动其他Agent
        
        logger.info(f"所有Agent启动完成，共 {len(self.processes)} 个进程")
    
    def stop_all_agents(self):
        """停止所有Agent"""
        logger.info("开始停止所有Agent...")
        
        # 发送终止信号
        for process in self.processes:
            if process.is_alive():
                logger.info(f"终止Agent: {process.name} (PID: {process.pid})")
                process.terminate()
        
        # 等待进程结束
        for process in self.processes:
            process.join(timeout=5)
            if process.is_alive():
                logger.warning(f"强制终止Agent: {process.name} (PID: {process.pid})")
                process.kill()
                process.join()
        
        logger.info("所有Agent已停止")
    
    def wait(self):
        """等待所有Agent运行"""
        try:
            while self.running:
                # 检查进程状态
                for process in self.processes:
                    if not process.is_alive():
                        logger.warning(f"Agent进程已退出: {process.name} (PID: {process.pid})")
                        # 可以选择重启或退出
                        self.running = False
                        break
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到中断信号")
            self.running = False


def signal_handler(signum, frame):
    """信号处理函数"""
    logger.info(f"收到信号: {signum}")
    global agent_manager
    if agent_manager:
        agent_manager.running = False
        agent_manager.stop_all_agents()
    sys.exit(0)


# 全局Agent管理器
agent_manager = None


def main():
    """主函数"""
    global agent_manager
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 创建Agent管理器
        agent_manager = AgentManager()
        
        # 启动所有Agent
        agent_manager.start_all_agents()
        
        # 启动微信服务器（在主进程中运行）
        logger.info("启动微信服务器...")
        from agent_wechat.server import app
        import uvicorn
        from shared.config import settings
        
        # 在单独的线程中运行微信服务器
        import threading
        
        def run_server():
            uvicorn.run(
                app,
                host=settings.server_host,
                port=settings.server_port,
                log_level=settings.log_level.lower(),
                workers=settings.server_workers
            )
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        logger.info(f"微信服务器已启动: {settings.server_host}:{settings.server_port}")
        
        # 等待所有Agent运行
        agent_manager.wait()
        
    except Exception as e:
        logger.error(f"主程序运行失败: {e}")
        if agent_manager:
            agent_manager.stop_all_agents()
        raise
    finally:
        if agent_manager:
            agent_manager.stop_all_agents()
        logger.info("主程序已退出")


if __name__ == "__main__":
    main()

