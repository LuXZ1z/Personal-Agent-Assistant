# 微信回调验证工具使用指南

## 概述

`minimal_callback_verify.py` 是一个**最简单的回调URL验证工具**，专门用于验证企业微信回调URL配置是否正确。

## 功能特点

- ✅ **极简代码**：约160行代码
- ✅ **仅URL验证**：只处理 GET 请求（URL验证）
- ✅ **使用 .env.test 配置**：适合快速测试
- ✅ **详细日志**：每一步都有日志输出
- ✅ **健康检查接口**：方便检查服务状态

## 适用场景

- 🎯 **首次配置**：第一次配置企业微信回调URL
- 🎯 **快速验证**：只需要验证URL是否正确，不需要测试消息收发
- 🎯 **单机器人测试**：测试单个机器人的配置

## 前置要求

### 1. 创建 .env.test 文件

在项目根目录创建 `.env.test` 文件：

```env
# 企业微信配置
WECHAT_TOKEN=你的Token
WECHAT_ENCODING_AES_KEY=你的EncodingAESKey
WECHAT_CORP_ID=你的企业ID
WECHAT_RECEIVE_ID=你的企业ID  # 与CORP_ID相同
WECHAT_CORP_SECRET=你的Secret  # 可选，此工具不需要
WECHAT_AGENT_ID=1000002  # 可选，此工具不需要

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8024
```

**注意**：`WECHAT_RECEIVE_ID` 应该与 `WECHAT_CORP_ID` 相同（对于普通应用）。

### 2. 获取企业微信配置信息

参考 `WECHAT_API_SETUP_GUIDE.md` 获取以下参数：
- **WECHAT_TOKEN**：在"接收消息"配置中生成
- **WECHAT_ENCODING_AES_KEY**：在"接收消息"配置中生成（43字符）
- **WECHAT_CORP_ID**：在"我的企业"页面底部
- **WECHAT_RECEIVE_ID**：与 CORP_ID 相同

## 启动方法

```bash
cd /home/Personal-Agent-Assistant
python minimal_callback_verify.py
```

**期望输出**：

```
============================================================
启动企业微信回调验证服务器
配置文件: .env.test
Token: Abc123Def4...
EncodingAESKey: abcdefghij...
receive_id: 'ww1234567890abcdef'
============================================================
服务器配置:
  地址: 0.0.0.0
  端口: 8024
============================================================
回调URL格式:
  http://你的域名或IP:8024/ai-bot/callback/你的botid
============================================================
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8024
```

## 使用步骤

### 步骤 1: 启动服务器

运行 `python minimal_callback_verify.py`，确保服务器正常运行。

### 步骤 2: 在企业微信后台配置回调URL

1. 进入企业微信管理后台
2. 进入应用详情页面
3. 找到 **"接收消息"** 部分
4. 点击 **"设置API接收"**
5. 填写以下信息：
   - **URL**：`http://你的服务器IP:8024/ai-bot/callback/{botid}`
     - 示例：`http://123.456.789.0:8024/ai-bot/callback/test`
   - **Token**：与 `.env.test` 中的 `WECHAT_TOKEN` 一致
   - **EncodingAESKey**：与 `.env.test` 中的 `WECHAT_ENCODING_AES_KEY` 一致
6. 点击 **"保存"**

### 步骤 3: 查看验证结果

点击"保存"后，企业微信会立即发送 GET 请求验证URL。

**查看服务器日志**，应该显示：

```
============================================================
收到URL验证请求
  botid: test
  msg_signature: 5c45ff5e21c57e6ad56bac8758b79b1d3ac18eb
  timestamp: 1705123456
  nonce: xxxxxx
  echostr: RypEvHKD8qQKFhvQ6QleEB...
✓ URL验证成功
  解密后的echostr: 1234567890123456789
============================================================
```

**企业微信后台显示**：
```
✅ 已保存并启用
```

🎉 **恭喜！URL验证成功！**

## API 端点

### GET `/ai-bot/callback/{botid}`

URL验证接口（企业微信自动调用）

**参数**（Query参数）：
- `msg_signature`: 消息签名
- `timestamp`: 时间戳
- `nonce`: 随机字符串
- `echostr`: 加密的随机字符串

**返回**：
- 成功：解密后的 echostr（明文）
- 失败：`"verify fail"`（状态码 400 或 500）

### GET `/health`

健康检查接口

**返回**：
```json
{
  "status": "ok",
  "service": "minimal_callback_verify"
}
```

## 代码结构

### 核心流程

```python
# 1. 加载 .env.test 配置
test_env_path = Path("./.env.test")
load_dotenv(test_env_path, override=True)

# 2. 从环境变量读取配置
WECHAT_TOKEN = os.getenv("WECHAT_TOKEN", "")
WECHAT_ENCODING_AES_KEY = os.getenv("WECHAT_ENCODING_AES_KEY", "")
WECHAT_RECEIVE_ID = os.getenv("WECHAT_RECEIVE_ID", "")

# 3. 初始化微信加解密器
wxcpt = WeChatMessageCrypt(
    token=WECHAT_TOKEN,
    encoding_aes_key=WECHAT_ENCODING_AES_KEY,
    receive_id=WECHAT_RECEIVE_ID  # 对于普通应用，使用企业ID
)

# 4. URL验证接口
@app.get("/ai-bot/callback/{botid}")
async def verify_url(botid, msg_signature, timestamp, nonce, echostr):
    # 验证URL并解密echostr
    decrypted_echostr = wxcpt.verify_url(
        msg_signature=msg_signature,
        timestamp=timestamp,
        nonce=nonce,
        echostr=echostr
    )
    # 返回解密后的echostr（必须是明文）
    return PlainTextResponse(content=decrypted_echostr)
```

## 故障排查

### 问题1: 配置文件未找到

**错误信息**：
```
⚠ 未找到测试配置文件: .env.test
```

**解决方法**：
1. 在项目根目录创建 `.env.test` 文件
2. 参考 `.env.test.example`（如果存在）
3. 填写必要的配置参数

### 问题2: URL验证失败

**日志显示**：
```
✗ URL验证失败: 签名验证失败
```

**可能原因**：
1. Token 配置不一致
2. EncodingAESKey 配置不一致
3. receive_id 不正确

**解决方法**：
1. 检查 `.env.test` 中的 `WECHAT_TOKEN` 是否与企业微信后台一致
2. 检查 `WECHAT_ENCODING_AES_KEY` 是否完整（43个字符）
3. 确认 `WECHAT_RECEIVE_ID` 与 `WECHAT_CORP_ID` 相同
4. 确保没有多余的空格或换行符

### 问题3: 服务器无法访问

**症状**：企业微信后台提示"验证失败"或"无法连接"

**检查项**：
1. 服务器是否正在运行：`curl http://localhost:8024/health`
2. 防火墙是否开放 8024 端口
3. 回调URL中的IP地址是否正确
4. 如果使用内网穿透，确保穿透服务正常运行

### 问题4: receive_id 配置错误

**日志显示**：
```
✗ URL验证失败: receive_id不匹配
```

**解决方法**：
1. 对于普通应用，`WECHAT_RECEIVE_ID` 应该与 `WECHAT_CORP_ID` 相同
2. 对于智能机器人，`WECHAT_RECEIVE_ID` 使用空字符串 `""`
3. 如果仍然失败，尝试使用企业ID（以 "ww" 开头）

## 与 minimal_test_server.py 的区别

| 特性 | minimal_callback_verify.py | minimal_test_server.py |
|------|---------------------------|------------------------|
| **用途** | 仅URL验证 | 完整消息收发测试 |
| **配置方式** | .env.test 文件 | config/bots.yaml |
| **支持多机器人** | ❌ 否 | ✅ 是 |
| **处理消息** | ❌ 否 | ✅ 是 |
| **代码行数** | ~160行 | ~240行 |
| **适用场景** | 首次配置验证 | 完整功能测试 |

## 下一步

URL验证成功后，可以：

1. **使用 minimal_test_server.py 测试消息收发**
   ```bash
   python minimal_test_server.py
   ```

2. **启动完整服务**
   ```bash
   python interfaces/wechat/server.py
   ```

3. **参考完整配置指南**
   - 查看 `WECHAT_API_SETUP_GUIDE.md` 了解详细配置步骤
   - 查看 `MINIMAL_TEST_GUIDE.md` 了解消息收发测试

## 参考文档

- [企业微信API文档](https://developer.work.weixin.qq.com/document/)
- [消息加密解密说明](https://developer.work.weixin.qq.com/document/path/90968)
- [WECHAT_API_SETUP_GUIDE.md](./WECHAT_API_SETUP_GUIDE.md) - 完整配置指南
- [MINIMAL_TEST_GUIDE.md](./docs/MINIMAL_TEST_GUIDE.md) - 消息收发测试指南
