# 最小化测试服务器使用说明

## 目的

`minimal_test_server.py` 是一个**最简单的测试程序**，用于验证：
1. ✅ 能否正确加载 yaml 配置
2. ✅ 能否接收微信消息
3. ✅ 能否发送回复消息
4. ✅ 多个机器人是否都能正常工作

## 特点

- **极简代码**：约240行代码
- **支持多机器人**：从 `config/bots.yaml` 加载配置
- **无复杂业务逻辑**：收到什么就回复什么
- **后台异步处理**：立即返回响应，不会超时
- **详细日志**：每一步都有日志输出

## 前置要求

1. 已配置 `config/bots.yaml` 文件（至少一个机器人）
2. 企业微信应用已创建并获取了所有必要参数

## 启动方法

```bash
cd /home/Personal-Agent-Assistant
python minimal_test_server.py
```

启动后会显示：
```
============================================================
最小化测试服务器
============================================================
已加载 2 个机器人: ['test', 'family']
端口: 8024
============================================================

✓ 加载机器人: test - 测试机器人 (receive_id='ww0b4c690c4b9e8ab1')
✓ 加载机器人: family - 家庭机器人 (receive_id='ww6f04ea15ec4caa93')
INFO:     Started server process [xxxxx]
INFO:     Uvicorn running on http://0.0.0.0:8024
```

## 测试步骤

### 1. 启动服务器

运行后应该看到：

```
============================================
最小化测试服务器
============================================
已加载 2 个机器人: ['test', 'family']
端口: 8024
============================================

✓ 加载机器人: test - 测试机器人
✓ 加载机器人: family - 家庭机器人
INFO:     Started server process [xxxxx]
INFO:     Uvicorn running on http://0.0.0.0:8024
```

### 2. 测试 test 机器人

在企业微信中向 **test 机器人** 发送消息：
```
测试1
```

**期望结果**：
- 日志显示：
  ```
  ======== 收到消息: test ========
  ✓ 解密成功
  用户: xxx
  内容: 测试1
  ✓ 已创建后台任务，立即返回响应
  [后台] 开始处理: test, xxx, 测试1
  ✓ 获取 test access_token 成功
  ✓ 发送成功: test -> xxx
  [后台] ✓ 回复成功: test
  ```

- 微信收到回复：
  ```
  ✅ 测试机器人收到消息
  
  你发送的内容：测试1
  
  时间：22:50:30
  ```

### 3. 测试连续消息

连续发送多条消息：
```
测试2
测试3
测试4
```

**期望结果**：
- 日志显示每条消息都被接收
- 每条消息都收到回复

### 4. 测试 family 机器人

在企业微信中向 **family 机器人** 发送消息：
```
家庭测试
```

**期望结果**：
- 日志显示：`收到消息: family`
- 微信收到回复：`✅ 家庭机器人收到消息`

## 代码结构

### 核心流程

```python
# 1. 加载 yaml 配置
with open('/home/Personal-Agent-Assistant/config/bots.yaml', 'r') as f:
    config = yaml.safe_load(f)
    BOTS_CONFIG = config['bots']

# 2. 为每个机器人创建加解密器（使用 corp_id 作为 receive_id）
for bot_id, bot_config in BOTS_CONFIG.items():
    receive_id = bot_config['wechat_corp_id']
    CRYPTS[bot_id] = WeChatMessageCrypt(
        token=bot_config['wechat_token'],
        encoding_aes_key=bot_config['wechat_encoding_aes_key'],
        receive_id=receive_id
    )

# 3. URL验证（GET请求）
@app.get("/ai-bot/callback/{botid}")
async def verify_url(...):
    decrypted = wxcpt.verify_url(msg_signature, timestamp, nonce, echostr)
    return PlainTextResponse(content=decrypted)

# 4. 接收消息（POST请求）
@app.post("/ai-bot/callback/{botid}")
async def handle_message(...):
    # 解密消息
    decrypted_msg = wxcpt.decrypt_msg(post_data, msg_signature, timestamp, nonce)
    # 解析XML
    xml_tree = ET.fromstring(decrypted_msg)
    # 【关键】立即启动后台任务
    asyncio.create_task(process_and_reply(botid, user_id, content))
    # 马上返回 success（不等待处理完成）
    return PlainTextResponse(content="success")

# 5. 后台处理并回复
async def process_and_reply(bot_id, user_id, content):
    # 构造回复
    reply = f"✅ {bot_name}收到消息\n\n你发送的内容：{content}\n\n时间：{datetime.now().strftime('%H:%M:%S')}"
    # 在线程池中发送（避免阻塞）
    success = await asyncio.to_thread(send_message, bot_id, user_id, reply)
```

## 关键点

### ✅ 立即返回响应

```python
# 立即创建后台任务
asyncio.create_task(process_and_reply(...))

# 马上返回（不等待）
return PlainTextResponse(content="success")
```

这样可以确保在 **几十毫秒内** 返回响应，远远小于企业微信的5秒超时限制。

### ✅ 异步发送消息

```python
# 在线程池中执行，避免阻塞事件循环
success = await asyncio.to_thread(send_message, bot_id, user_id, reply)
```

## 故障排查

### 问题1：服务器启动失败

**可能原因**：端口被占用

**解决方法**：
```bash
lsof -t -i:8024 | xargs kill -9
```

### 问题2：URL验证失败

**日志显示**：`✗ URL验证失败`

**检查项**：
1. yaml 配置中的 `wechat_token` 是否正确
2. yaml 配置中的 `wechat_encoding_aes_key` 是否正确
3. yaml 配置中的 `wechat_corp_id` 是否正确

### 问题3：收不到消息

**日志显示**：没有 `收到消息` 日志

**检查项**：
1. 企业微信后台的回调URL是否正确配置
   - test: `http://你的IP:8024/ai-bot/callback/test`
   - family: `http://你的IP:8024/ai-bot/callback/family`
2. 服务器防火墙是否开放 8024 端口
3. 企业微信是否提示 "接收消息服务器配置" 验证成功

### 问题4：收到消息但不回复

**日志显示**：`[后台] ✗ 回复失败`

**检查项**：
1. yaml 配置中的 `wechat_corp_secret` 是否正确
2. yaml 配置中的 `wechat_agent_id` 是否正确
3. 查看日志中的 `✗ 获取 access_token 失败` 或 `✗ 发送失败`

### 问题5：只收到第一条消息

**如果这个最小化程序也只收到第一条消息**：
- 说明不是代码问题
- 可能是网络问题或企业微信配置问题

**如果这个最小化程序能收到所有消息**：
- 说明基础通信正常
- 原来的程序可能有业务逻辑导致处理太慢

## 对比完整程序

如果最小化程序能正常工作，说明：
1. ✅ yaml 配置正确
2. ✅ 网络通信正常
3. ✅ 企业微信配置正确
4. ✅ 基础代码逻辑正常

那么完整程序的问题可能在于：
- 业务逻辑处理太慢
- 数据库查询太慢
- LLM 调用太慢
- 没有使用异步处理

## 下一步

如果最小化测试成功：
1. 逐步添加功能（会话管理、菜单等）
2. 确保每次添加后都测试是否仍然正常
3. 找出导致问题的具体模块

如果最小化测试失败：
1. 检查 yaml 配置
2. 检查企业微信后台配置
3. 检查网络和防火墙

