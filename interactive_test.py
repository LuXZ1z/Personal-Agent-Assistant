"""
交互式测试脚本
可以手动输入命令进行测试
"""
import time
import redis
import json
from shared.config import settings
from shared.message_types import WeChatMessage, QueryRequest, SummaryRequest
from shared.utils import setup_logger

logger = setup_logger(__name__)

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def check_queue_length(queue_name):
    """检查队列长度"""
    return redis_client.llen(queue_name)


def print_status():
    """打印系统状态"""
    print("\n" + "="*60)
    print("系统状态")
    print("="*60)
    queues = [
        "wechat_messages",
        "raw_text",
        "structured_data",
        "storage_result",
        "query_request",
        "query_result",
        "summary_request",
        "summary_result",
        "wechat_responses"
    ]
    for queue in queues:
        length = check_queue_length(queue)
        if length > 0:
            print(f"  {queue}: {length} 条消息")
    print("="*60)


def send_text(text):
    """发送文本消息"""
    message = WeChatMessage(
        text=text,
        msgtype="text",
        user_id="test_user"
    )
    redis_client.lpush("wechat_messages", message.model_dump_json())
    print(f"\n✓ 已发送文本消息: {message.message_id}")
    print(f"  内容: {text}")
    return message.message_id


def send_query(query_text):
    """发送查询请求"""
    from shared.rule_engine import rule_engine
    
    params = rule_engine.parse_query_params(query_text)
    query_type = rule_engine.determine_query_type(params)
    
    request = QueryRequest(
        query_type=query_type,
        params=params,
        user_id="test_user"
    )
    redis_client.lpush("query_request", request.model_dump_json())
    print(f"\n✓ 已发送查询请求: {request.request_id}")
    print(f"  类型: {query_type}, 参数: {params}")
    return request.request_id


def wait_for_response(message_id, timeout=30):
    """等待响应"""
    print(f"\n等待响应 (最多{timeout}秒)...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # 检查响应
        response = redis_client.rpop("wechat_responses")
        if response:
            resp_data = json.loads(response)
            if resp_data.get("message_id") == message_id:
                print(f"\n✓ 收到响应:")
                print(f"  {resp_data.get('text', '')}")
                return resp_data
        
        # 检查查询结果
        query_result = redis_client.rpop("query_result")
        if query_result:
            result = json.loads(query_result)
            if result.get("request_id") == message_id:
                print(f"\n✓ 收到查询结果:")
                print(f"  成功: {result.get('success')}")
                print(f"  记录数: {result.get('count', 0)}")
                if result.get('records'):
                    print(f"  前3条记录:")
                    for i, record in enumerate(result['records'][:3], 1):
                        print(f"    {i}. {record.get('structured_data', {}).get('summary', '')}")
                return result
        
        # 检查总结结果
        summary_result = redis_client.rpop("summary_result")
        if summary_result:
            result = json.loads(summary_result)
            if result.get("request_id") == message_id:
                print(f"\n✓ 收到总结结果:")
                print(f"  {result.get('summary', '')}")
                return result
        
        # 检查存储结果
        storage_result = redis_client.rpop("storage_result")
        if storage_result:
            result = json.loads(storage_result)
            if result.get("message_id") == message_id:
                print(f"\n✓ 收到存储结果:")
                print(f"  成功: {result.get('success')}")
                print(f"  记录ID: {result.get('record_id')}")
        
        time.sleep(0.5)
        if int(time.time() - start_time) % 5 == 0 and int(time.time() - start_time) > 0:
            elapsed = int(time.time() - start_time)
            print(f"  等待中... ({elapsed}/{timeout}秒)")
    
    print(f"\n✗ 超时，未收到响应")
    return None


def main():
    """主函数"""
    print("\n" + "="*60)
    print("交互式测试 - 个人助手系统")
    print("="*60)
    print("\n命令:")
    print("  1. text <内容>  - 发送文本消息")
    print("  2. query <查询> - 发送查询请求")
    print("  3. status      - 查看系统状态")
    print("  4. exit        - 退出")
    print("\n示例:")
    print("  text 今天花了50元买咖啡")
    print("  query 查询")
    print("  query 查询类型：记账")
    
    while True:
        try:
            cmd = input("\n> ").strip()
            if not cmd:
                continue
            
            if cmd == "exit":
                break
            elif cmd == "status":
                print_status()
            elif cmd.startswith("text "):
                text = cmd[5:].strip()
                if text:
                    message_id = send_text(text)
                    wait_for_response(message_id, timeout=60)
            elif cmd.startswith("query "):
                query_text = cmd[6:].strip()
                if query_text:
                    request_id = send_query(query_text)
                    wait_for_response(request_id, timeout=30)
            else:
                print("未知命令，请输入 help 查看帮助")
        
        except KeyboardInterrupt:
            print("\n\n退出...")
            break
        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n测试结束")


if __name__ == "__main__":
    main()

