# 消息接收问题修复说明

## 问题描述

1. **只接收到第一条消息**：发送多条消息后，服务器只收到了第一条，后续消息都没有收到
2. **机器人不回复消息**：消息处理后没有回复

## 根本原因

**企业微信的超时限制**：企业微信要求服务器在 **5秒内** 返回响应（返回 "success"），否则会认为服务器出问题，**停止发送后续消息**。

### 旧代码的问题

```python
# 旧代码（同步处理）
@app.post("/ai-bot/callback/{botid}")
async def handle_message(...):
    # 1. 解密消息
    # 2. 检查去重
    # 3. 调用消息路由器处理（可能耗时很长，特别是调用LLM）
    result = message_router.route_message(...)  # 可能需要几十秒
    # 4. 发送响应消息
    send_text_message(...)
    # 5. 最后才返回success
    return PlainTextResponse(content="success")  # 太晚了！可能已经超过5秒
```

如果消息处理（特别是调用LLM）超过5秒，企业微信就会认为服务器超时，不再发送后续消息。

## 修复方案

### 1. 立即返回响应 + 后台异步处理

```python
# 新代码（异步处理）
@app.post("/ai-bot/callback/{botid}")
async def handle_message(...):
    # 1. 解密消息
    # 2. 检查去重
    # 3. 立即创建后台任务处理消息
    asyncio.create_task(_process_message_async(...))
    # 4. 马上返回success（通常在几十毫秒内）
    return PlainTextResponse(content="success")  # ✓ 快速返回，不会超时

# 后台处理函数
async def _process_message_async(...):
    # 在后台慢慢处理消息，不会阻塞主请求
    result = await asyncio.to_thread(message_router.route_message, ...)
    await asyncio.to_thread(send_text_message, ...)
```

### 2. 修复消息去重器的误判问题

旧代码在没有 `msg_id` 时，只使用内容hash作为唯一标识，导致相同内容的不同消息被误判为重复。

```python
# 旧代码
if not msg_id:
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    message_key = f"{user_id}:{content_hash}"  # 问题：相同内容会被认为是重复

# 新代码
if not msg_id:
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    timestamp = int(time.time())  # 添加时间戳
    message_key = f"{user_id}:{timestamp}:{content_hash}"  # ✓ 不同时间的相同内容不会被误判
```

### 3. 添加详细日志

在关键步骤添加日志，便于调试：
- 消息接收
- 消息去重检查
- 会话状态获取
- 消息路由器调用
- 消息发送结果

## 修改的文件

1. `/home/Personal-Agent-Assistant/interfaces/wechat/server.py`
   - 将消息处理改为后台异步执行
   - 主请求立即返回响应
   - 添加详细日志

2. `/home/Personal-Agent-Assistant/interfaces/wechat/message_deduplicator.py`
   - 修复消息去重逻辑
   - 添加时间戳避免误判

## 测试验证

重启服务器后，应该能看到：

1. **每条消息都能收到**
   ```
   2026-01-17 22:47:34 - __main__ - INFO - 收到消息: botid=test, timestamp=...
   2026-01-17 22:47:36 - __main__ - INFO - 收到消息: botid=test, timestamp=...
   2026-01-17 22:47:38 - __main__ - INFO - 收到消息: botid=family, timestamp=...
   ```

2. **快速返回响应（几十毫秒内）**
   ```
   [后台任务] 开始处理消息: botid=test, user_id=xxx, content=测试
   [后台任务] ✓ 消息发送成功: botid=test, user_id=xxx
   ```

3. **机器人正常回复消息**

## 回调URL配置

你的配置是正确的：
- test机器人：`http://你的IP:8024/ai-bot/callback/test`
- family机器人：`http://你的IP:8024/ai-bot/callback/family`

服务器根据URL中的 `{botid}` 来区分不同的机器人，使用对应的加解密密钥和配置。

## 下一步

1. 重启服务器
2. 在两个不同的机器人中发送多条消息
3. 观察日志输出
4. 检查是否收到机器人的回复

如果还有问题，请查看日志中的 `[后台任务]` 标记的日志行。

