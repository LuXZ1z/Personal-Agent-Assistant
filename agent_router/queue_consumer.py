"""
消息路由Agent的队列消费者
主入口文件
"""
from agent_router.message_router import MessageRouter
from shared.utils import setup_logger

logger = setup_logger(__name__)


def main():
    """主函数"""
    try:
        router = MessageRouter()
        router.run()
    except Exception as e:
        logger.error(f"消息路由器启动失败: {e}")
        raise


if __name__ == "__main__":
    main()

