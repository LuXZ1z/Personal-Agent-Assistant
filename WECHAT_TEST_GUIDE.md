# 微信最小测试单元使用指南

## 概述

`minimal_wechat_test.py` 是一个最小化的微信交互测试单元，用于快速验证微信消息的收发功能。

## 功能特点

- ✅ 接收微信消息（支持URL验证）
- ✅ 消息解密（使用企业微信加密库）
- ✅ 简单的Echo回复（收到什么回复什么）
- ✅ 详细的日志输出（方便调试）
- ✅ 健康检查接口

## 前置要求 

### 1. 企业微信配置

需要在企业微信后台获取以下信息：

- **WECHAT_TOKEN**: 应用Token（随机生成）
- **WECHAT_ENCODING_AES_KEY**: Base64编码的AES密钥（随机生成）
- **WECHAT_CORP_ID**: 企业ID
- **WECHAT_CORP_SECRET**: 应用Secret
- **WECHAT_AGENT_ID**: 应用AgentID

### 2. 服务器要求

- 公网可访问的服务器或使用内网穿透工具（如ngrok）
- Python 3.11+
- 已安装项目依赖

## 配置步骤

### 1. 配置 .env 文件

在项目根目录的 `.env` 文件中添加或修改以下配置：

```env
# 微信配置（必填）
WECHAT_TOKEN=your_token_here
WECHAT_ENCODING_AES_KEY=your_base64_aes_key_here

# 企业微信配置（用于发送消息，必填）
WECHAT_CORP_ID=your_corp_id_here
WECHAT_CORP_SECRET=your_corp_secret_here
WECHAT_AGENT_ID=1000002

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

### 2. 获取企业微信配置信息

#### 步骤 1: 进入企业微信管理后台

访问 [https://work.weixin.qq.com/](https://work.weixin.qq.com/) 并登录

#### 步骤 2: 创建应用

1. 进入「应用管理」
2. 点击「创建应用」
3. 填写应用信息并创建

#### 步骤 3: 获取配置参数

在应用详情页面：

- **AgentID**: 直接显示在页面上 → `WECHAT_AGENT_ID`
- **Secret**: 点击「查看」→ `WECHAT_CORP_SECRET`

在「接收消息」配置中：

- **Token**: 随机生成 → `WECHAT_TOKEN`
- **EncodingAESKey**: 随机生成 → `WECHAT_ENCODING_AES_KEY`

在「我的企业」页面：

- **企业ID**: 页面底部 → `WECHAT_CORP_ID`

## 启动测试

### 1. 本地启动

```bash
python minimal_wechat_test.py
```

启动后会显示配置检查和服务器信息：

```
============================================================
微信最小测试单元启动
============================================================

配置检查:
  WECHAT_TOKEN: ✓
  WECHAT_ENCODING_AES_KEY: ✓
  CORP_ID: ✓
  CORP_SECRET: ✓
  AGENT_ID: ✓

服务器配置:
  地址: 0.0.0.0
  端口: 8000
  回调URL: http://your-domain.com/ai-bot/callback/{botid}

使用说明:
  1. 确保配置了 .env 文件中的所有参数
  2. 在微信后台配置回调URL
  3. 在微信中发送消息测试
  4. 查看日志输出了解消息处理流程

============================================================
服务器启动中...
============================================================
```

### 2. 使用内网穿透（本地测试）

如果在本地测试，可以使用 ngrok 等工具：

```bash
# 安装 ngrok
brew install ngrok

# 启动内网穿透
ngrok http 8000
```

ngrok 会提供一个公网URL，如：`https://xxxx.ngrok.io`

### 3. 配置微信回调URL

在企业微信应用后台：

1. 进入「接收消息」配置
2. 填写 **URL**: `https://your-domain.com/ai-bot/callback/test`
   - 本地测试使用 ngrok URL: `https://xxxx.ngrok.io/ai-bot/callback/test`
3. 填写 **Token** 和 **EncodingAESKey**（与.env中一致）
4. 点击「保存」

**重要**: 保存时微信会发送GET请求验证URL，确保服务器正在运行。

## 测试流程

### 1. URL验证测试

保存回调URL时，查看日志应该显示：

```
============================================================
收到URL验证请求
  botid: test
  msg_signature: xxxxx
  timestamp: 1234567890
  nonce: xxxxx
  echostr: xxxxx...
✓ URL验证成功
  解密后的echostr: xxxxx
============================================================
```

### 2. 消息收发测试

在企业微信中向应用发送消息，如：`你好`

查看日志应该显示：

```
============================================================
收到消息回调
  botid: test
  timestamp: 1234567890
  POST数据长度: 256 字节
✓ 消息解密成功
  解密后的消息: {...}
  消息类型: text
  用户ID: YourUserID
  消息内容: 你好
获取access_token成功，有效期: 7200秒
✓ 回复发送成功
============================================================
```

应用会回复：

```
[Echo回复] 你说: 你好

收到时间: 2026-01-15 10:30:45
```

## API 端点

### 1. GET /ai-bot/callback/{botid}

URL验证接口

**参数：**
- `msg_signature`: 消息签名
- `timestamp`: 时间戳
- `nonce`: 随机字符串
- `echostr`: 加密的随机字符串

**返回：** 解密后的echostr

### 2. POST /ai-bot/callback/{botid}

消息处理接口

**参数：**
- `msg_signature`: 消息签名
- `timestamp`: 时间戳
- `nonce`: 随机字符串

**Body：** 加密的消息内容（XML格式）

**返回：** "success"

### 3. GET /health

健康检查接口

**返回：**
```json
{
  "status": "ok",
  "service": "minimal_wechat_test",
  "timestamp": "2026-01-15T10:30:45.123456"
}
```

### 4. GET /

根路径，显示服务信息

## 常见问题

### 1. URL验证失败

**可能原因：**
- Token 或 EncodingAESKey 配置错误
- 服务器未启动或无法访问
- 网络问题

**解决方法：**
- 检查 .env 配置是否正确
- 确保服务器正在运行
- 检查防火墙和网络设置

### 2. 收不到消息

**可能原因：**
- 回调URL配置错误
- 企业可信IP未配置
- 消息类型不支持

**解决方法：**
- 检查回调URL是否正确
- 在企业微信后台添加服务器IP到「企业可信IP」
- 查看日志确认消息是否到达

### 3. 无法发送回复

**可能原因：**
- CorpID 或 CorpSecret 错误
- AgentID 错误
- access_token 获取失败

**解决方法：**
- 检查企业微信配置参数
- 查看日志中的错误信息
- 确认企业微信应用状态正常

## 下一步

测试成功后，可以：

1. **集成到完整系统**: 将此测试单元的逻辑集成到 `agent_wechat/server.py`
2. **添加业务逻辑**: 替换echo回复为实际的业务处理（如调用LLM）
3. **连接消息队列**: 将收到的消息发送到Redis队列进行异步处理
4. **部署到生产**: 参考 [DEPLOYMENT.md](DEPLOYMENT.md) 部署到生产服务器

## 代码说明

### 核心流程

```python
# 1. 接收消息
post_data = await request.body()

# 2. 解密消息
decrypted_msg = wxcpt.decrypt_msg(post_data, msg_signature, timestamp, nonce)

# 3. 解析消息
msg_data = json.loads(decrypted_msg)
content = msg_data.get("text", {}).get("content", "")
user_id = msg_data.get("from", {}).get("userid", "")

# 4. 处理消息（这里是简单的echo）
reply_content = f"[Echo回复] 你说: {content}"

# 5. 发送回复
send_text_message(user_id, reply_content)
```

### 消息加密解密

使用 `WeChatMessageCrypt` 类进行消息的加解密：

```python
from agent_wechat.message_crypt import WeChatMessageCrypt

wxcpt = WeChatMessageCrypt(
    token=settings.wechat_token,
    encoding_aes_key=settings.wechat_encoding_aes_key,
    receive_id=""
)
```

### 发送消息到企业微信

```python
def send_text_message(user_id: str, content: str):
    access_token = get_access_token()
    url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
    data = {
        "touser": user_id,
        "msgtype": "text",
        "agentid": AGENT_ID,
        "text": {"content": content}
    }
    response = requests.post(url, json=data)
```

## 参考文档

- [企业微信API文档](https://developer.work.weixin.qq.com/document/)
- [消息加密解密说明](https://developer.work.weixin.qq.com/document/path/90968)
- [发送应用消息](https://developer.work.weixin.qq.com/document/path/90236)

