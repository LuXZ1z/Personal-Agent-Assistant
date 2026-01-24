"""
FastAPI服务器
处理微信HTTP接口
"""
import sys
from pathlib import Path
# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import logging
import asyncio
import time
import requests
import xml.etree.ElementTree as ET
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Query, BackgroundTasks
from fastapi.responses import Response, PlainTextResponse
import uvicorn

from shared.config import settings
from shared.message_types import WeChatMessage, BusinessRequest, BusinessResponse
from interfaces.wechat.message_crypt import WeChatMessageCrypt, WeChatCryptError
from interfaces.wechat.queue_client import QueueClient
from interfaces.wechat.response_manager import ResponseManager
from interfaces.wechat.message_router import message_router
from interfaces.wechat.session_manager import session_manager
from interfaces.wechat.message_deduplicator import message_deduplicator
from interfaces.wechat.task_manager import task_manager
from interfaces.wechat.bot_manager import bot_manager
from shared.utils import setup_logger

logger = setup_logger(__name__)

# 创建FastAPI应用
app = FastAPI(title="Personal Assistant WeChat Agent", version="1.0.0")

# 初始化队列客户端
queue_client = QueueClient()

# 初始化响应管理器
response_manager = ResponseManager()

# Access Token 缓存（按机器人ID缓存）
access_token_cache: dict = {}


def get_access_token(bot_id: str) -> Optional[str]:
    """
    获取企业微信 access_token（带缓存）
    
    Args:
        bot_id: 机器人ID
        
    Returns:
        access_token 或 None
    """
    current_time = datetime.now().timestamp()
    
    # 获取机器人配置
    try:
        bot_config = bot_manager.get_bot_config(bot_id)
        corp_id = bot_config['wechat_corp_id']
        corp_secret = bot_config['wechat_corp_secret']
    except ValueError as e:
        logger.error(f"获取机器人配置失败: {e}")
        return None
    
    # 如果该机器人的 token 还没过期，直接返回
    if bot_id in access_token_cache:
        cache = access_token_cache[bot_id]
        if cache.get('token') and current_time < cache.get('expires_at', 0):
            return cache['token']
    
    # 请求新的 access_token
    try:
        url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if 'access_token' in result:
            # 缓存 token
            access_token_cache[bot_id] = {
                'token': result['access_token'],
                'expires_at': current_time + result.get('expires_in', 7200) - 300  # 提前 5 分钟过期
            }
            logger.info(f"✓ 获取机器人 {bot_id} access_token 成功")
            return access_token_cache[bot_id]['token']
        else:
            logger.error(f"✗ 获取机器人 {bot_id} access_token 失败: {result.get('errmsg')}")
            return None
    except Exception as e:
        logger.error(f"✗ 请求机器人 {bot_id} access_token 异常: {e}")
        return None


def send_text_message(bot_id: str, user_id: str, content: str) -> bool:
    """
    主动发送文本消息到企业微信（支持分批次发送）
    
    Args:
        bot_id: 机器人ID
        user_id: 用户 ID
        content: 消息内容
        
    Returns:
        是否所有消息都发送成功
    """
    raw_len = len(content) if content else 0

    # 美化 + 分割消息（分批发送）
    from shared.message_utils import format_message, split_message
    content = format_message(content)
    beautified_len = len(content) if content else 0
    messages = split_message(content, max_chars=750)
    
    if not messages:
        return True
    
    logger.info(
        f"[发送消息] 开始发送: bot_id={bot_id}, user_id={user_id}, "
        f"总消息数={len(messages)}, 原始长度={raw_len}, 美化后长度={beautified_len}"
    )
    
    # 获取 access_token 和 agent_id（所有消息共享）
    access_token = get_access_token(bot_id)
    if not access_token:
        logger.error(f"[发送消息] ✗ 无法获取机器人 {bot_id} access_token，消息发送失败")
        return False
    
    try:
        bot_config = bot_manager.get_bot_config(bot_id)
        agent_id = bot_config['wechat_agent_id']
    except ValueError as e:
        logger.error(f"[发送消息] ✗ 获取机器人配置失败: {e}")
        return False
    
    # 分批次发送
    all_success = True
    url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
    
    for i, message_content in enumerate(messages, 1):
        send_start_time = time.time()
        logger.info(f"[发送消息] 发送第 {i}/{len(messages)} 条消息，长度={len(message_content)}")
        
        try:
            data = {
                "touser": user_id,
                "msgtype": "text",
                "agentid": agent_id,
                "text": {
                    "content": message_content
                },
                "safe": 0,
                "enable_id_trans": 0,
                "enable_duplicate_check": 0,
            }
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('errcode') == 0:
                elapsed = time.time() - send_start_time
                logger.info(f"[发送消息] ✓ 第 {i}/{len(messages)} 条消息发送成功，耗时={elapsed:.3f}秒")
            else:
                logger.error(f"[发送消息] ✗ 第 {i}/{len(messages)} 条消息发送失败: errmsg={result.get('errmsg')}, errcode={result.get('errcode')}")
                all_success = False
                
        except requests.exceptions.Timeout as e:
            logger.error(f"[发送消息] ✗ 第 {i}/{len(messages)} 条消息请求超时: {e}")
            all_success = False
        except requests.exceptions.RequestException as e:
            logger.error(f"[发送消息] ✗ 第 {i}/{len(messages)} 条消息请求异常: {e}")
            all_success = False
        except Exception as e:
            logger.error(f"[发送消息] ✗ 第 {i}/{len(messages)} 条消息发送异常: {e}", exc_info=True)
            all_success = False
        
        # 在消息之间添加短暂延迟，避免发送过快
        if i < len(messages):
            import time as time_module
            time_module.sleep(0.5)  # 延迟0.5秒
    
    if all_success:
        logger.info(f"[发送消息] ✓ 所有 {len(messages)} 条消息发送成功")
    else:
        logger.warning(f"[发送消息] ⚠ 部分消息发送失败，共 {len(messages)} 条")
    
    return all_success


@app.get("/ai-bot/callback/{botid}")
async def verify_url(
    request: Request,
    botid: str,
    msg_signature: str = Query(..., alias="msg_signature"),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """微信URL验证接口（GET请求）"""
    try:
        logger.info(f"收到URL验证请求: botid={botid}")
        
        # 获取机器人的加解密器
        try:
            wxcpt = bot_manager.get_crypt(botid)
        except ValueError as e:
            logger.error(f"无效的botid: {botid}, {e}")
            return PlainTextResponse(content="invalid bot", status_code=404)
        
        # 验证URL
        decrypted_echostr = wxcpt.verify_url(
            msg_signature=msg_signature,
            timestamp=timestamp,
            nonce=nonce,
            echostr=echostr
        )
        
        logger.info(f"URL验证成功: botid={botid}")
        return PlainTextResponse(content=decrypted_echostr)
    except WeChatCryptError as e:
        logger.error(f"URL验证失败: {e}")
        return PlainTextResponse(content="verify fail", status_code=400)
    except Exception as e:
        logger.error(f"URL验证异常: {e}")
        return PlainTextResponse(content="verify fail", status_code=500)


@app.post("/ai-bot/callback/{botid}")
async def handle_message(
    request: Request,
    botid: str,
    msg_signature: str = Query(..., alias="msg_signature"),
    timestamp: str = Query(...),
    nonce: str = Query(...)
):
    """处理微信消息（POST请求）"""
    request_start_time = time.time()
    try:
        logger.info(f"======== 收到消息请求 ========")
        logger.info(f"botid={botid}, timestamp={timestamp}, nonce={nonce}")
        logger.info(f"msg_signature={msg_signature[:20]}...")
        
        # 获取机器人的加解密器
        try:
            wxcpt = bot_manager.get_crypt(botid)
            logger.info(f"✓ 成功获取机器人 {botid} 的加解密器")
        except ValueError as e:
            logger.error(f"✗ 无效的botid: {botid}, {e}")
            return PlainTextResponse(content="invalid bot", status_code=404)
        except Exception as e:
            logger.error(f"✗ 获取加解密器失败: {e}", exc_info=True)
            return PlainTextResponse(content="invalid bot", status_code=500)
        
        # 读取POST数据
        try:
            post_data = await request.body()
            logger.info(f"✓ POST数据读取成功: {len(post_data)} 字节")
        except Exception as e:
            logger.error(f"✗ 读取POST数据失败: {e}", exc_info=True)
            return PlainTextResponse(content="success", status_code=200)
        
        # 检查POST数据是否为空
        if not post_data:
            logger.error("✗ POST数据为空，忽略此请求")
            return PlainTextResponse(content="success", status_code=200)
        
        # 解密消息
        try:
            logger.info(f"开始解密消息...")
            decrypted_msg = wxcpt.decrypt_msg(
                post_data=post_data,
                msg_signature=msg_signature,
                timestamp=timestamp,
                nonce=nonce
            )
            logger.info(f"✓ 消息解密成功，长度: {len(decrypted_msg)} 字符")
            logger.debug(f"解密后的消息前100字符: {decrypted_msg[:100] if decrypted_msg else 'None'}")
        except WeChatCryptError as e:
            logger.error(f"✗ 消息解密失败 (WeChatCryptError): {e}", exc_info=True)
            return PlainTextResponse(content="success", status_code=200)
        except Exception as e:
            logger.error(f"✗ 消息解密异常: {e}", exc_info=True)
            return PlainTextResponse(content="success", status_code=200)
        
        # 解析消息（支持JSON和XML）
        msg_data = None
        msgtype = None
        content = ""
        user_id = ""
        msg_id = ""
        try:
            logger.info(f"开始解析消息...")
            try:
                msg_data = json.loads(decrypted_msg)
                msgtype = msg_data.get("msgtype")
                content = msg_data.get("text", {}).get("content", "")
                user_id = msg_data.get("from", {}).get("userid", "")
                msg_id = str(msg_data.get("msgid") or msg_data.get("MsgId") or "")
                logger.info(f"✓ 使用JSON格式解析消息成功")
                logger.info(f"  msgtype={msgtype}, user_id={user_id}, msg_id={msg_id}, content={content[:50]}")
            except json.JSONDecodeError:
                # 解析XML格式
                logger.info(f"尝试使用XML格式解析...")
                xml_tree = ET.fromstring(decrypted_msg)
                msgtype_elem = xml_tree.find("MsgType")
                if msgtype_elem is not None:
                    msgtype = msgtype_elem.text
                from_elem = xml_tree.find("FromUserName")
                if from_elem is not None:
                    user_id = from_elem.text
                if msgtype == "text":
                    content_elem = xml_tree.find("Content")
                    if content_elem is not None:
                        content = content_elem.text
                msg_id_elem = xml_tree.find("MsgId")
                if msg_id_elem is not None:
                    msg_id = msg_id_elem.text
                logger.info(f"✓ 使用XML格式解析消息成功")
                logger.info(f"  msgtype={msgtype}, user_id={user_id}, msg_id={msg_id}, content={content[:50]}")
        except ET.ParseError as e:
            logger.error(f"✗ XML解析失败: {e}", exc_info=True)
            return PlainTextResponse(content="success", status_code=200)
        except Exception as e:
            logger.error(f"✗ 消息解析失败: {e}", exc_info=True)
            return PlainTextResponse(content="success", status_code=200)
        
        # 检查消息类型
        logger.info(f"消息类型: {msgtype}")
        if msgtype not in ["text", "stream"]:
            logger.info(f"✗ 不支持的消息类型: {msgtype}，忽略")
            return PlainTextResponse(content="success", status_code=200)
        
        # 处理文本消息
        if msgtype == "text":
            
            if not content:
                logger.warning("消息内容为空")
                return PlainTextResponse(content="success", status_code=200)
            
            if not user_id:
                logger.warning("用户ID为空")
                return PlainTextResponse(content="success", status_code=200)
            
            # 检查消息是否重复（微信重试机制）
            logger.info(f"检查消息去重: user_id={user_id}, msg_id={msg_id}, content={content[:30]}")
            is_dup = message_deduplicator.is_duplicate(user_id, msg_id, content)
            if is_dup:
                logger.warning(f"⚠ 检测到重复消息，跳过处理: user_id={user_id}, msg_id={msg_id}, content={content[:30]}")
                elapsed = time.time() - request_start_time
                logger.info(f"请求处理完成（重复消息），耗时: {elapsed:.3f}秒")
                return PlainTextResponse(content="success", status_code=200)
            logger.info(f"✓ 消息未重复，继续处理")
            
            try:
                logger.info(f"准备处理消息: botid={botid}, user_id={user_id}, content={content[:50]}")
                
                # 【关键修复】立即启动后台任务处理消息，然后马上返回success给微信
                # 这样可以确保在5秒内返回响应，避免微信认为服务器超时
                logger.info(f"创建后台任务...")
                task = asyncio.create_task(
                    _process_message_async(botid, user_id, content, msg_id)
                )
                logger.info(f"✓ 后台任务已创建: {task}")
                
                elapsed = time.time() - request_start_time
                logger.info(f"✓ 立即返回响应，耗时: {elapsed:.3f}秒")
                # 立即返回 success 告诉企业微信我们已经收到消息
                return PlainTextResponse(content="success", status_code=200)
                
            except Exception as e:
                logger.error(f"处理文本消息失败: botid={botid}, user_id={user_id}, content={content[:30]}, error={e}", exc_info=True)
                # 即使失败也要返回success，避免微信重试
                return PlainTextResponse(content="success", status_code=200)
        
        # 处理stream消息（用于获取处理进度）
        elif msgtype == "stream":
            if not msg_data:
                logger.info("stream消息缺少JSON结构，忽略")
                return PlainTextResponse(content="success", status_code=200)
            stream_id = msg_data.get("stream", {}).get("id", "")
            if stream_id:
                try:
                    logger.info(f"收到stream轮询: stream_id={stream_id}")
                    
                    # 处理响应队列（检查是否有新的响应）
                    response_manager.process_response_queue()
                    
                    # 获取stream当前状态
                    stream_info = response_manager.get_stream(stream_id)
                    if stream_info:
                        stream_json = _make_text_stream(
                            stream_id, 
                            stream_info["content"], 
                            finish=stream_info["finish"]
                        )
                        encrypted_response = wxcpt.encrypt_msg(stream_json, nonce=nonce, timestamp=timestamp)
                        return PlainTextResponse(content=encrypted_response, media_type="text/plain")
                    else:
                        # stream不存在或已过期，返回完成状态
                        stream_json = _make_text_stream(stream_id, "处理完成", finish=True)
                        encrypted_response = wxcpt.encrypt_msg(stream_json, nonce=nonce, timestamp=timestamp)
                        return PlainTextResponse(content=encrypted_response, media_type="text/plain")
                except Exception as e:
                    logger.error(f"处理stream消息失败: {e}", exc_info=True)
                    # 返回完成状态，避免微信继续轮询
                    try:
                        stream_json = _make_text_stream(stream_id, "处理完成", finish=True)
                        encrypted_response = wxcpt.encrypt_msg(stream_json, nonce=nonce, timestamp=timestamp)
                        return PlainTextResponse(content=encrypted_response, media_type="text/plain")
                    except:
                        return PlainTextResponse(content="success", status_code=200)
        
        elapsed = time.time() - request_start_time
        logger.info(f"请求处理完成，总耗时: {elapsed:.3f}秒")
        return PlainTextResponse(content="success", status_code=200)
        
    except WeChatCryptError as e:
        elapsed = time.time() - request_start_time
        logger.error(f"✗ 消息处理失败 (WeChatCryptError): {e}, 耗时: {elapsed:.3f}秒", exc_info=True)
        return PlainTextResponse(content="success", status_code=200)  # 微信要求返回success
    except Exception as e:
        elapsed = time.time() - request_start_time
        logger.error(f"✗ 消息处理异常: {e}, 耗时: {elapsed:.3f}秒", exc_info=True)
        return PlainTextResponse(content="success", status_code=200)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "wechat_agent"}


def _make_text_stream(stream_id: str, content: str, finish: bool) -> str:
    """创建文本stream消息格式"""
    stream_data = {
        "msgtype": "stream",
        "stream": {
            "id": stream_id,
            "finish": finish,
            "content": content
        }
    }
    return json.dumps(stream_data, ensure_ascii=False)


async def _process_message_async(bot_id: str, user_id: str, content: str, msg_id: str):
    """
    后台异步处理消息
    将消息发送到队列，由CLI服务端处理业务逻辑
    """
    process_start_time = time.time()
    try:
        logger.info(f"[后台任务] ======== 开始处理消息 ========")
        logger.info(f"[后台任务] botid={bot_id}, user_id={user_id}, content={content[:50]}, msg_id={msg_id}")
        
        # 获取会话状态
        logger.info(f"[后台任务] 步骤1: 获取会话状态...")
        session = session_manager.get_session(bot_id, user_id)
        logger.info(f"[后台任务] ✓ 会话状态: business_type={session.business_type}, sub_menu={session.sub_menu}")
        
        # 将会话状态序列化
        session_dict = session.to_dict()
        # 移除不能序列化的字段
        session_dict.pop('last_activity', None)
        session_dict.pop('expire_at', None)
        
        # 创建业务请求
        request = BusinessRequest(
            bot_id=bot_id,
            user_id=user_id,
            content=content,
            msg_id=msg_id,
            session=session_dict
        )
        
        # 发送到队列
        logger.info(f"[后台任务] 步骤2: 发送业务请求到队列...")
        logger.info(f"[后台任务] request_id={request.request_id}")
        await asyncio.to_thread(queue_client.send_business_message, request)
        logger.info(f"[后台任务] ✓ 业务请求已发送到队列，等待CLI服务端处理")
        
        elapsed = time.time() - process_start_time
        logger.info(f"[后台任务] ======== 消息已转发到队列，耗时: {elapsed:.3f}秒 ========")
        
    except Exception as e:
        elapsed = time.time() - process_start_time
        logger.error(f"[后台任务] ✗ 转发消息失败: botid={bot_id}, user_id={user_id}, content={content[:30]}, error={e}, 耗时={elapsed:.3f}秒", exc_info=True)
        # 发送错误消息给用户
        try:
            error_message = f"❌ 处理消息时发生错误: {str(e)}"
            logger.info(f"[后台任务] 尝试发送错误消息给用户...")
            await asyncio.to_thread(send_text_message, bot_id, user_id, error_message)
            logger.info(f"[后台任务] ✓ 错误消息已发送")
        except Exception as send_error:
            logger.error(f"[后台任务] ✗ 发送错误消息失败: {send_error}", exc_info=True)


@app.on_event("startup")
async def startup_event():
    """应用启动时的后台任务"""
    logger.info("启动响应队列处理后台任务")
    asyncio.create_task(background_response_processor())
    logger.info("启动业务响应队列监听任务")
    asyncio.create_task(background_business_response_processor())
    logger.info("启动任务清理后台任务")
    asyncio.create_task(background_task_cleanup())


async def background_response_processor():
    """后台处理响应队列的任务"""
    while True:
        try:
            response_manager.process_response_queue()
            await asyncio.sleep(0.5)  # 每0.5秒检查一次
        except Exception as e:
            logger.error(f"后台响应处理异常: {e}")
            await asyncio.sleep(1)


async def background_business_response_processor():
    """后台处理业务响应队列的任务（从CLI服务端接收结果并发送回微信）"""
    import redis
    from redis.exceptions import RedisError
    
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        redis_client.ping()
        logger.info("业务响应队列监听器初始化成功")
    except RedisError as e:
        logger.error(f"业务响应队列监听器Redis连接失败: {e}")
        return
    
    while True:
        try:
            # 从队列右侧弹出消息（FIFO）
            message_json = redis_client.rpop("wechat_responses")
            if message_json:
                try:
                    response = BusinessResponse.model_validate_json(message_json)
                    logger.info(f"[业务响应] 收到响应: request_id={response.request_id}")
                    
                    # 从响应中提取信息
                    result = response.result
                    bot_id = result.get("bot_id")
                    user_id = result.get("user_id")
                    response_type = result.get("type")
                    response_message = result.get("message", "")
                    
                    if not bot_id or not user_id:
                        logger.warning(f"[业务响应] 响应缺少bot_id或user_id，跳过: request_id={response.request_id}")
                        continue
                    
                    # 处理响应消息
                    if response_type == "error":
                        final_message = f"❌ {response_message}"
                    elif response_type == "processing":
                        # 处理中，发送"正在处理"消息
                        final_message = response_message
                    else:
                        final_message = response_message
                    
                    # 发送消息回微信
                    logger.info(f"[业务响应] 发送响应消息到用户: bot_id={bot_id}, user_id={user_id}, type={response_type}")
                    success = await asyncio.to_thread(send_text_message, bot_id, user_id, final_message)
                    
                    if success:
                        logger.info(f"[业务响应] ✓ 响应消息发送成功: request_id={response.request_id}")
                    else:
                        logger.error(f"[业务响应] ✗ 响应消息发送失败: request_id={response.request_id}")
                    
                except Exception as e:
                    logger.error(f"[业务响应] 处理响应消息失败: {e}", exc_info=True)
            
            # 短暂休眠避免CPU占用过高
            await asyncio.sleep(0.1)
            
        except KeyboardInterrupt:
            logger.info("收到中断信号，停止业务响应队列监听器")
            break
        except Exception as e:
            logger.error(f"业务响应队列监听异常: {e}")
            await asyncio.sleep(1)


async def background_task_cleanup():
    """后台清理已完成的任务"""
    while True:
        try:
            task_manager.cleanup_completed_tasks(max_age=300)  # 清理5分钟前的任务
            await asyncio.sleep(60)  # 每60秒清理一次
        except Exception as e:
            logger.error(f"后台任务清理异常: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower(),
        workers=settings.server_workers
    )

