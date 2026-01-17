"""
FastAPI服务器
处理微信HTTP接口
"""
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
from shared.message_types import WeChatMessage
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
    主动发送文本消息到企业微信
    
    Args:
        bot_id: 机器人ID
        user_id: 用户 ID
        content: 消息内容
        
    Returns:
        是否发送成功
    """
    access_token = get_access_token(bot_id)
    if not access_token:
        logger.error(f"✗ 无法获取机器人 {bot_id} access_token，消息发送失败")
        return False
    
    # 获取机器人配置
    try:
        bot_config = bot_manager.get_bot_config(bot_id)
        agent_id = bot_config['wechat_agent_id']
    except ValueError as e:
        logger.error(f"获取机器人配置失败: {e}")
        return False
    
    try:
        url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
        data = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": agent_id,
            "text": {
                "content": content
            },
            "safe": 0,
            "enable_id_trans": 0,
            "enable_duplicate_check": 0,
        }
        
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get('errcode') == 0:
            logger.info(f"✓ 消息发送成功: bot_id={bot_id}, user_id={user_id}, content_length={len(content)}")
            return True
        else:
            logger.error(f"✗ 消息发送失败: {result.get('errmsg')}, errcode={result.get('errcode')}")
            return False
    except Exception as e:
        logger.error(f"✗ 发送消息异常: {e}")
        return False


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
    try:
        logger.info(f"收到消息: botid={botid}, timestamp={timestamp}")
        
        # 获取机器人的加解密器
        try:
            wxcpt = bot_manager.get_crypt(botid)
        except ValueError as e:
            logger.error(f"无效的botid: {botid}, {e}")
            return PlainTextResponse(content="invalid bot", status_code=404)
        
        # 读取POST数据
        post_data = await request.body()
        logger.info(f"POST数据长度: {len(post_data)} 字节")
        
        # 检查POST数据是否为空
        if not post_data:
            logger.error("POST数据为空，忽略此请求")
            return PlainTextResponse(content="success", status_code=200)
        
        # 解密消息
        decrypted_msg = wxcpt.decrypt_msg(
            post_data=post_data,
            msg_signature=msg_signature,
            timestamp=timestamp,
            nonce=nonce
        )
        
        logger.debug(f"解密后的消息: {decrypted_msg}")
        
        # 解析消息（支持JSON和XML）
        msg_data = None
        msgtype = None
        content = ""
        user_id = ""
        msg_id = ""
        try:
            try:
                msg_data = json.loads(decrypted_msg)
                msgtype = msg_data.get("msgtype")
                content = msg_data.get("text", {}).get("content", "")
                user_id = msg_data.get("from", {}).get("userid", "")
                msg_id = str(msg_data.get("msgid") or msg_data.get("MsgId") or "")
                logger.debug("使用JSON格式解析消息")
            except json.JSONDecodeError:
                # 解析XML格式
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
                logger.debug("使用XML格式解析消息")
        except ET.ParseError as e:
            logger.error(f"XML解析失败: {e}")
            return PlainTextResponse(content="success", status_code=200)
        except Exception as e:
            logger.error(f"消息解析失败: {e}")
            return PlainTextResponse(content="success", status_code=200)
        
        # 检查消息类型
        if msgtype not in ["text", "stream"]:
            logger.info(f"不支持的消息类型: {msgtype}")
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
            if message_deduplicator.is_duplicate(user_id, msg_id, content):
                logger.info(f"检测到重复消息，跳过处理: user_id={user_id}, msg_id={msg_id}")
                return PlainTextResponse(content="success", status_code=200)
            
            try:
                logger.info(f"处理消息: botid={botid}, user_id={user_id}, content={content[:50]}")
                
                # 检查是否需要调用LLM（通过检查业务类型和内容）
                session = session_manager.get_session(botid, user_id)
                needs_llm = False
                task_type = None
                
                if session.business_type == "tarot":
                    # 检查是否在占卜状态（不是主菜单）
                    if session.sub_menu in ["single", "three_card", "five_card"]:
                        # 检查内容不是"0"（返回菜单）
                        if content.strip() != "0":
                            needs_llm = True
                            task_type = f"tarot_{session.sub_menu}"
                
                # 如果需要调用LLM，先发送"正在处理"消息
                if needs_llm:
                    processing_message = f"⏳ 正在调用大模型处理中...\n\n任务类型: {task_type}\n内容: {content[:50]}\n\n请稍候，处理完成后会立即返回结果"
                    send_text_message(botid, user_id, processing_message)
                    logger.info(f"已发送正在处理消息: botid={botid}, user_id={user_id}")
                
                # 使用消息路由器处理消息（会检查任务状态）
                result = message_router.route_message(botid, user_id, content)
                
                # 获取响应消息
                if result.get("type") == "error":
                    response_message = f"❌ {result.get('message', '处理失败')}"
                elif result.get("type") == "processing":
                    # 如果返回processing类型，说明任务正在处理中
                    response_message = result.get("message", "正在处理中...")
                else:
                    response_message = result.get("message", "处理完成")
                
                logger.info(f"路由结果: type={result.get('type')}, message长度={len(response_message)}")
                logger.debug(f"响应消息内容: {response_message[:200]}")
                
                # 如果之前已经发送了"正在处理"消息，且现在返回的是最终结果，直接发送结果
                # 如果返回的是processing类型，说明任务还在处理中，不发送（因为之前已经发送了）
                if needs_llm and result.get("type") == "processing":
                    # 任务正在处理中，不发送重复消息
                    logger.info(f"任务正在处理中，跳过发送: botid={botid}, user_id={user_id}")
                else:
                    # 使用主动发送 API 发送消息（企业微信推荐方式）
                    success = send_text_message(botid, user_id, response_message)
                    
                    if success:
                        logger.info(f"✓ 消息发送成功: botid={botid}, user_id={user_id}, response_length={len(response_message)}")
                    else:
                        logger.error(f"✗ 消息发送失败: botid={botid}, user_id={user_id}")
                
                # 返回 success 告诉企业微信我们已经处理了
                return PlainTextResponse(content="success", status_code=200)
                
            except Exception as e:
                logger.error(f"处理文本消息失败: {e}", exc_info=True)
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
        
        return PlainTextResponse(content="success", status_code=200)
        
    except WeChatCryptError as e:
        logger.error(f"消息处理失败: {e}")
        return PlainTextResponse(content="success", status_code=200)  # 微信要求返回success
    except Exception as e:
        logger.error(f"消息处理异常: {e}")
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


@app.on_event("startup")
async def startup_event():
    """应用启动时的后台任务"""
    logger.info("启动响应队列处理后台任务")
    asyncio.create_task(background_response_processor())
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

