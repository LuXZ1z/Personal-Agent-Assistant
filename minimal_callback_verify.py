#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最简单的企业微信回调验证脚本
只处理GET请求进行URL验证，用于注册回调URL

使用方法:
1. 复制 .env.test.example 为 .env.test 并填写配置
2. 运行此脚本: python minimal_callback_verify.py
3. 在企业微信后台配置回调URL: http://你的域名或IP:端口/ai-bot/callback/{botid}
4. 点击保存，企业微信会自动发送GET请求验证URL
5. 查看日志确认验证是否成功
"""
import logging
import os
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse
import uvicorn
from dotenv import load_dotenv

from interfaces.wechat.message_crypt import WeChatMessageCrypt, WeChatCryptError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载测试环境变量文件
# 注意：使用 override=True 强制覆盖已存在的环境变量
# 这样可以确保 .env.test 中的配置优先于 .env 文件
test_env_path = Path("./.env.test")
if test_env_path.exists():
    load_dotenv(test_env_path, override=True)
    logger.info(f"✓ 已加载测试配置文件: {test_env_path}")
else:
    logger.warning(f"⚠ 未找到测试配置文件: {test_env_path}")
    logger.warning("请创建 .env.test 文件或复制 .env.test.example")

# 从环境变量读取配置
WECHAT_TOKEN = os.getenv("WECHAT_TOKEN", "")
WECHAT_ENCODING_AES_KEY = os.getenv("WECHAT_ENCODING_AES_KEY", "")
WECHAT_RECEIVE_ID = os.getenv("WECHAT_RECEIVE_ID", "")  # 智能机器人使用空字符串
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8024"))

# 创建FastAPI应用
app = FastAPI(title="Minimal WeChat Callback Verify", version="1.0.0")

# 初始化微信加解密器
# 注意：对于智能机器人，receive_id 使用空字符串
# 如果验证失败，可以尝试使用企业微信的CorpID
wxcpt = WeChatMessageCrypt(
    token=WECHAT_TOKEN,
    encoding_aes_key=WECHAT_ENCODING_AES_KEY,
    receive_id=WECHAT_RECEIVE_ID  # 智能机器人使用空字符串
)


@app.get("/ai-bot/callback/{botid}")
async def verify_url(
    botid: str,
    msg_signature: str = Query(..., alias="msg_signature"),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """
    企业微信URL验证接口（GET请求）
    
    这是企业微信验证回调URL时的第一步。
    企业微信会发送GET请求到配置的回调URL，携带以下参数：
    - msg_signature: 消息签名
    - timestamp: 时间戳
    - nonce: 随机字符串
    - echostr: 加密的随机字符串
    
    服务器需要：
    1. 验证签名
    2. 解密echostr
    3. 返回解密后的echostr（明文）
    """
    try:
        logger.info("=" * 60)
        logger.info("收到URL验证请求")
        logger.info(f"  botid: {botid}")
        logger.info(f"  msg_signature: {msg_signature}")
        logger.info(f"  timestamp: {timestamp}")
        logger.info(f"  nonce: {nonce}")
        logger.info(f"  echostr: {echostr[:50]}...")  # 只打印前50个字符
        
        # 验证URL并解密echostr
        decrypted_echostr = wxcpt.verify_url(
            msg_signature=msg_signature,
            timestamp=timestamp,
            nonce=nonce,
            echostr=echostr
        )
        
        logger.info("✓ URL验证成功")
        logger.info(f"  解密后的echostr: {decrypted_echostr}")
        logger.info("=" * 60)
        
        # 返回解密后的echostr（必须是明文，不能加引号）
        return PlainTextResponse(content=decrypted_echostr)
        
    except WeChatCryptError as e:
        logger.error(f"✗ URL验证失败: {e}")
        logger.error("可能的原因：")
        logger.error("  1. Token配置不一致（检查.env.test文件中的WECHAT_TOKEN）")
        logger.error("  2. EncodingAESKey配置不一致（检查.env.test文件中的WECHAT_ENCODING_AES_KEY）")
        logger.error("  3. receive_id不正确（如果是智能机器人应使用空字符串）")
        return PlainTextResponse(content="verify fail", status_code=400)
        
    except Exception as e:
        logger.error(f"✗ URL验证异常: {e}", exc_info=True)
        return PlainTextResponse(content="verify fail", status_code=500)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "minimal_callback_verify"}


if __name__ == "__main__":
    # 检查必要的配置
    if not WECHAT_TOKEN:
        logger.error("错误: 未配置 WECHAT_TOKEN，请在.env.test文件中设置")
        logger.error(f"请创建 .env.test 文件或复制 .env.test.example 并填写配置")
        exit(1)
    
    if not WECHAT_ENCODING_AES_KEY:
        logger.error("错误: 未配置 WECHAT_ENCODING_AES_KEY，请在.env.test文件中设置")
        logger.error(f"请创建 .env.test 文件或复制 .env.test.example 并填写配置")
        exit(1)
    
    logger.info("=" * 60)
    logger.info("启动企业微信回调验证服务器")
    logger.info(f"配置文件: {test_env_path}")
    logger.info(f"Token: {WECHAT_TOKEN[:10]}...")
    logger.info(f"EncodingAESKey: {WECHAT_ENCODING_AES_KEY[:10]}...")
    logger.info(f"receive_id: '{WECHAT_RECEIVE_ID}'")
    logger.info("=" * 60)
    logger.info("服务器配置:")
    logger.info(f"  地址: {SERVER_HOST}")
    logger.info(f"  端口: {SERVER_PORT}")
    logger.info("=" * 60)
    logger.info("回调URL格式:")
    logger.info(f"  http://你的域名或IP:{SERVER_PORT}/ai-bot/callback/你的botid")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info"
    )

