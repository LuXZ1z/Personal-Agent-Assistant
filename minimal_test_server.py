"""
最小化测试服务器
用于验证与企业微信的基础通信是否正常
"""
import json
import logging
import asyncio
import requests
import yaml
import xml.etree.ElementTree as ET
from datetime import datetime
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse
import uvicorn

from interfaces.wechat.message_crypt import WeChatMessageCrypt, WeChatCryptError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="Minimal WeChat Test")

# 加载机器人配置
with open('/home/Personal-Agent-Assistant/config/bots.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
    BOTS_CONFIG = config['bots']

# 为每个机器人创建加解密器
# 注意：根据实际测试，需要使用 wechat_corp_id 作为 receive_id
CRYPTS = {}
for bot_id, bot_config in BOTS_CONFIG.items():
    if bot_config.get('enabled', True):
        # 使用 corp_id 作为 receive_id（根据实际测试结果）
        receive_id = bot_config['wechat_corp_id']
        
        CRYPTS[bot_id] = WeChatMessageCrypt(
            token=bot_config['wechat_token'],
            encoding_aes_key=bot_config['wechat_encoding_aes_key'],
            receive_id=receive_id
        )
        logger.info(f"✓ 加载机器人: {bot_id} - {bot_config['name']} (receive_id='{receive_id}')")

# Access Token 缓存
access_token_cache = {}


def get_access_token(bot_id: str) -> str:
    """获取 access_token"""
    current_time = datetime.now().timestamp()
    
    # 检查缓存
    if bot_id in access_token_cache:
        cache = access_token_cache[bot_id]
        if cache.get('token') and current_time < cache.get('expires_at', 0):
            return cache['token']
    
    # 请求新的 token
    bot_config = BOTS_CONFIG[bot_id]
    corp_id = bot_config['wechat_corp_id']
    corp_secret = bot_config['wechat_corp_secret']
    
    try:
        url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}'
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if 'access_token' in result:
            access_token_cache[bot_id] = {
                'token': result['access_token'],
                'expires_at': current_time + result.get('expires_in', 7200) - 300
            }
            logger.info(f"✓ 获取 {bot_id} access_token 成功")
            return access_token_cache[bot_id]['token']
        else:
            logger.error(f"✗ 获取 {bot_id} access_token 失败: {result.get('errmsg')}")
            return None
    except Exception as e:
        logger.error(f"✗ 请求 {bot_id} access_token 异常: {e}")
        return None


def send_message(bot_id: str, user_id: str, content: str) -> bool:
    """发送消息"""
    access_token = get_access_token(bot_id)
    if not access_token:
        logger.error(f"✗ 无法获取 access_token: {bot_id}")
        return False
    
    bot_config = BOTS_CONFIG[bot_id]
    agent_id = bot_config['wechat_agent_id']
    
    try:
        url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
        data = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": agent_id,
            "text": {"content": content},
            "safe": 0
        }
        
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get('errcode') == 0:
            logger.info(f"✓ 发送成功: {bot_id} -> {user_id}")
            return True
        else:
            logger.error(f"✗ 发送失败: {result.get('errmsg')}, errcode={result.get('errcode')}")
            return False
    except Exception as e:
        logger.error(f"✗ 发送异常: {e}")
        return False


@app.get("/ai-bot/callback/{botid}")
async def verify_url(
    botid: str,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """URL验证"""
    logger.info(f"======== URL验证: {botid} ========")
    
    if botid not in CRYPTS:
        logger.error(f"✗ 无效的 botid: {botid}")
        return PlainTextResponse(content="invalid bot", status_code=404)
    
    try:
        wxcpt = CRYPTS[botid]
        decrypted = wxcpt.verify_url(msg_signature, timestamp, nonce, echostr)
        logger.info(f"✓ URL验证成功: {botid}")
        return PlainTextResponse(content=decrypted)
    except Exception as e:
        logger.error(f"✗ URL验证失败: {e}")
        return PlainTextResponse(content="verify fail", status_code=400)


@app.post("/ai-bot/callback/{botid}")
async def handle_message(
    request: Request,
    botid: str,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...)
):
    """处理消息"""
    logger.info(f"======== 收到消息: {botid} ========")
    
    if botid not in CRYPTS:
        logger.error(f"✗ 无效的 botid: {botid}")
        return PlainTextResponse(content="success", status_code=200)
    
    try:
        # 读取并解密消息
        post_data = await request.body()
        wxcpt = CRYPTS[botid]
        decrypted_msg = wxcpt.decrypt_msg(post_data, msg_signature, timestamp, nonce)
        logger.info(f"✓ 解密成功")
        
        # 解析XML
        xml_tree = ET.fromstring(decrypted_msg)
        msg_type = xml_tree.find("MsgType").text
        
        if msg_type != "text":
            logger.info(f"忽略非文本消息: {msg_type}")
            return PlainTextResponse(content="success", status_code=200)
        
        # 提取信息
        content = xml_tree.find("Content").text
        user_id = xml_tree.find("FromUserName").text
        
        logger.info(f"用户: {user_id}")
        logger.info(f"内容: {content}")
        
        # 【关键】立即启动后台任务，马上返回success
        asyncio.create_task(process_and_reply(botid, user_id, content))
        
        logger.info(f"✓ 已创建后台任务，立即返回响应")
        return PlainTextResponse(content="success", status_code=200)
        
    except Exception as e:
        logger.error(f"✗ 处理失败: {e}", exc_info=True)
        return PlainTextResponse(content="success", status_code=200)


async def process_and_reply(bot_id: str, user_id: str, content: str):
    """后台处理并回复"""
    try:
        logger.info(f"[后台] 开始处理: {bot_id}, {user_id}, {content}")
        
        # 构造回复消息
        bot_name = BOTS_CONFIG[bot_id]['name']
        reply = f"✅ {bot_name}收到消息\n\n你发送的内容：{content}\n\n时间：{datetime.now().strftime('%H:%M:%S')}"
        
        # 在线程池中发送（避免阻塞）
        success = await asyncio.to_thread(send_message, bot_id, user_id, reply)
        
        if success:
            logger.info(f"[后台] ✓ 回复成功: {bot_id}")
        else:
            logger.error(f"[后台] ✗ 回复失败: {bot_id}")
            
    except Exception as e:
        logger.error(f"[后台] ✗ 异常: {e}", exc_info=True)


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "bots": list(CRYPTS.keys()),
        "time": datetime.now().isoformat()
    }


if __name__ == "__main__":
    print("=" * 60)
    print("最小化测试服务器")
    print("=" * 60)
    print(f"已加载 {len(CRYPTS)} 个机器人:", list(CRYPTS.keys()))
    print("端口: 8024")
    print("=" * 60)
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8024,
        log_level="info"
    )

