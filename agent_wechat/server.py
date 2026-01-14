"""
FastAPI服务器
处理微信HTTP接口
"""
import json
import logging
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import Response, PlainTextResponse
import uvicorn

from shared.config import settings
from shared.message_types import WeChatMessage
from agent_wechat.message_crypt import WeChatMessageCrypt, WeChatCryptError
from agent_wechat.queue_client import QueueClient
from shared.utils import setup_logger

logger = setup_logger(__name__)

# 创建FastAPI应用
app = FastAPI(title="Personal Assistant WeChat Agent", version="1.0.0")

# 初始化微信加解密器
wxcpt = WeChatMessageCrypt(
    token=settings.wechat_token,
    encoding_aes_key=settings.wechat_encoding_aes_key,
    receive_id=""  # 智能机器人的receive_id为空字符串
)

# 初始化队列客户端
queue_client = QueueClient()


@app.get("/ai-bot/callback/{botid}")
async def verify_url(
    request: Request,
    botid: str,
    msg_signature: str = Query(..., alias="msg_signature"),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """
    微信URL验证接口（GET请求）
    
    Args:
        botid: 机器人ID
        msg_signature: 消息签名
        timestamp: 时间戳
        nonce: 随机字符串
        echostr: 加密的随机字符串
        
    Returns:
        解密后的随机字符串
    """
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
    """
    处理微信消息（POST请求）
    
    Args:
        botid: 机器人ID
        msg_signature: 消息签名
        timestamp: 时间戳
        nonce: 随机字符串
        
    Returns:
        加密后的响应消息
    """
    try:
        logger.info(f"收到消息: botid={botid}, timestamp={timestamp}")
        
        # 读取POST数据
        post_data = await request.body()
        
        # 解密消息
        decrypted_msg = wxcpt.decrypt_msg(
            post_data=post_data,
            msg_signature=msg_signature,
            timestamp=timestamp,
            nonce=nonce
        )
        
        logger.debug(f"解密后的消息: {decrypted_msg}")
        
        # 解析消息JSON
        try:
            msg_data = json.loads(decrypted_msg)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return PlainTextResponse(content="success", status_code=200)
        
        # 检查消息类型
        msgtype = msg_data.get("msgtype")
        if msgtype not in ["text", "stream"]:
            logger.info(f"不支持的消息类型: {msgtype}")
            return PlainTextResponse(content="success", status_code=200)
        
        # 处理文本消息
        if msgtype == "text":
            content = msg_data.get("text", {}).get("content", "")
            if not content:
                logger.warning("消息内容为空")
                return PlainTextResponse(content="success", status_code=200)
            
            # 创建微信消息对象
            wechat_message = WeChatMessage(
                text=content,
                msgtype="text",
                user_id=msg_data.get("from", {}).get("userid", "")
            )
            
            # 发送到队列
            queue_client.send_wechat_message(wechat_message)
            logger.info(f"消息已发送到队列: {wechat_message.message_id}")
            
            # 等待响应（异步处理，这里先返回success）
            # 实际响应会通过stream消息返回
            return PlainTextResponse(content="success", status_code=200)
        
        # 处理stream消息（用于获取处理进度）
        elif msgtype == "stream":
            stream_id = msg_data.get("stream", {}).get("id", "")
            if stream_id:
                logger.info(f"收到stream消息: stream_id={stream_id}")
                # 这里可以处理stream消息，暂时返回success
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


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=80,
        log_level=settings.log_level.lower()
    )

