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
from shared.utils import setup_logger

logger = setup_logger(__name__)

# 创建FastAPI应用
app = FastAPI(title="Personal Assistant WeChat Agent", version="1.0.0")

# 初始化微信加解密器
wxcpt = WeChatMessageCrypt(
    token=settings.wechat_token,
    encoding_aes_key=settings.wechat_encoding_aes_key,
    receive_id=settings.wechat_corp_id  # 使用企业微信CorpID
)

# 初始化队列客户端
queue_client = QueueClient()

# 初始化响应管理器
response_manager = ResponseManager()

# Access Token 缓存
access_token_cache = {
    'token': None,
    'expires_at': 0
}

# 企业微信配置
CORP_ID = settings.wechat_corp_id
CORP_SECRET = settings.wechat_corp_secret
AGENT_ID = settings.wechat_agent_id


def get_access_token() -> Optional[str]:
    """获取企业微信 access_token（带缓存）"""
    current_time = datetime.now().timestamp()
    
    # 如果 token 还没过期，直接返回
    if access_token_cache['token'] and current_time < access_token_cache['expires_at']:
        return access_token_cache['token']
    
    # 请求新的 access_token
    try:
        url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if 'access_token' in result:
            access_token_cache['token'] = result['access_token']
            # 提前 5 分钟过期，避免边界问题
            access_token_cache['expires_at'] = current_time + result.get('expires_in', 7200) - 300
            logger.info(f"✓ 获取 access_token 成功")
            return access_token_cache['token']
        else:
            logger.error(f"✗ 获取 access_token 失败: {result.get('errmsg')}")
            return None
    except Exception as e:
        logger.error(f"✗ 请求 access_token 异常: {e}")
        return None


def send_text_message(user_id: str, content: str) -> bool:
    """
    主动发送文本消息到企业微信
    
    Args:
        user_id: 用户 ID
        content: 消息内容
        
    Returns:
        是否发送成功
    """
    access_token = get_access_token()
    if not access_token:
        logger.error("✗ 无法获取 access_token，消息发送失败")
        return False
    
    try:
        url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
        data = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": AGENT_ID,
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
            logger.info(f"✓ 消息发送成功: user_id={user_id}, content_length={len(content)}")
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
            
            try:
                logger.info(f"处理消息: user_id={user_id}, content={content[:50]}")
                
                # 使用消息路由器处理消息
                result = message_router.route_message(user_id, content)
                
                # 获取响应消息
                if result.get("type") == "error":
                    response_message = f"❌ {result.get('message', '处理失败')}"
                else:
                    response_message = result.get("message", "处理完成")
                
                logger.info(f"路由结果: type={result.get('type')}, message长度={len(response_message)}")
                logger.debug(f"响应消息内容: {response_message[:200]}")
                
                # 使用主动发送 API 发送消息（企业微信推荐方式）
                success = send_text_message(user_id, response_message)
                
                if success:
                    logger.info(f"✓ 消息发送成功: user_id={user_id}, response_length={len(response_message)}")
                else:
                    logger.error(f"✗ 消息发送失败: user_id={user_id}")
                
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


async def background_response_processor():
    """后台处理响应队列的任务"""
    while True:
        try:
            response_manager.process_response_queue()
            await asyncio.sleep(0.5)  # 每0.5秒检查一次
        except Exception as e:
            logger.error(f"后台响应处理异常: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower(),
        workers=settings.server_workers
    )

