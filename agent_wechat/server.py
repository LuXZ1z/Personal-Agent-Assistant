"""
FastAPI服务器
处理微信HTTP接口
"""
import json
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException, Query, BackgroundTasks
from fastapi.responses import Response, PlainTextResponse
import uvicorn

from shared.config import settings
from shared.message_types import WeChatMessage
from agent_wechat.message_crypt import WeChatMessageCrypt, WeChatCryptError
from agent_wechat.queue_client import QueueClient
from agent_wechat.response_manager import ResponseManager
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

# 初始化响应管理器
response_manager = ResponseManager()


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
            
            try:
                # 创建微信消息对象
                wechat_message = WeChatMessage(
                    text=content,
                    msgtype="text",
                    user_id=msg_data.get("from", {}).get("userid", "")
                )
                
                # 创建stream
                stream_id = response_manager.create_stream(wechat_message.message_id)
                # 建立message_id到stream_id的映射
                response_manager.link_message_to_stream(wechat_message.message_id, stream_id)
                
                # 发送到队列
                queue_client.send_wechat_message(wechat_message)
                logger.info(f"消息已发送到队列: {wechat_message.message_id}, stream_id={stream_id}")
                
                # 立即返回stream消息（微信要求）
                stream_content = "正在处理您的消息..."
                stream_json = _make_text_stream(stream_id, stream_content, finish=False)
                encrypted_response = wxcpt.encrypt_msg(stream_json, nonce=nonce, timestamp=timestamp)
                
                return PlainTextResponse(content=encrypted_response, media_type="text/plain")
            except Exception as e:
                logger.error(f"处理文本消息失败: {e}", exc_info=True)
                # 即使失败也要返回success，避免微信重试
                return PlainTextResponse(content="success", status_code=200)
        
        # 处理stream消息（用于获取处理进度）
        elif msgtype == "stream":
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
    """
    创建文本stream消息格式
    
    Args:
        stream_id: stream ID
        content: 消息内容
        finish: 是否完成
        
    Returns:
        JSON字符串
    """
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

