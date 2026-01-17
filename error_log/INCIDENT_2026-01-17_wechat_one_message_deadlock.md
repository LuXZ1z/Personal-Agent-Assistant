# 事故复盘：企业微信回调“只能收到第一条消息 + 机器人不回复”

日期：2026-01-17  
项目：Personal-Agent-Assistant（企业微信回调 + 多机器人）  

## 现象（Symptoms）

- **只收到第一条消息**：企业微信能推送第一条回调，但后续消息完全不再触发服务端日志。
- **机器人不回复**：即便第一条消息到达，也看不到发送回复的日志，用户端无任何回复。
- **最小化程序正常**：`minimal_test_server.py` 能稳定收多条、也能发消息回复，说明网络/企业微信配置/Token/EncodingAESKey/CorpID/CorpSecret 等基础通信是可用的。

## 影响（Impact）

- 企业微信侧会认为回调服务不可用/超时，导致后续消息不再投递。
- 用户端体验：机器人“失联”。

## 根因（Root Cause）

**死锁（Deadlock）发生在机器人配置管理器 `BotManager` 的锁使用上。**

在 `interfaces/wechat/bot_manager.py` 中，`get_crypt()` 在持有 `self._lock` 的情况下调用 `get_bot_config()`，而 `get_bot_config()` 同样会尝试获取 `self._lock`：

- 旧实现使用 `threading.Lock()`（不可重入）
- 同一线程再次获取同一把 Lock 会**永久阻塞**
- 于是第一条回调请求在“获取加解密器”阶段卡死，HTTP handler 无法继续打印后续日志，也无法尽快返回 `success`
- 企业微信收到超时后，会停止投递后续消息，因此表现为“只收到第一条”

修复：将 `self._lock` 改为 **`threading.RLock()`（可重入锁）**，避免嵌套加锁死锁。

相关修复文件：

- `interfaces/wechat/bot_manager.py`：`self._lock = threading.RLock()`

## 为什么最小化程序没问题？

最小化程序 `minimal_test_server.py` 不使用 `BotManager` 这套“缓存 crypt + 读取 yaml + 锁”的逻辑，所以不会触发这把锁的嵌套获取，自然不会死锁。

## 修复内容（Fix）

### 1) 消除死锁

- 将 `BotManager` 的实例锁从 `threading.Lock()` 改为 `threading.RLock()`。

### 2) 让日志“必定可用”（落盘）

为了避免只在 screen/控制台上看日志导致排查困难，做了日志落盘默认化：

- `shared/utils.py` 的 `setup_logger()` 默认使用 `settings.log_file` 写文件（默认 `./logs/assistant.log`）。
- 设置 `logger.propagate = False`，避免与 root logger（例如 uvicorn）重复输出造成噪音。

### 3) 增强关键链路日志

在 `interfaces/wechat/server.py` 增加了“收到回调 → 解密 → 解析 → 去重 → 创建后台任务 → 发送消息”全链路日志，便于快速定位卡点：

- `======== 收到消息请求 ========`
- `✓ 成功获取机器人 X 的加解密器`
- `✓ POST数据读取成功`
- `✓ 消息解密成功`
- `✓ 使用XML/JSON解析消息成功`
- `✓ 后台任务已创建`
- `[发送消息]` 分步日志（token/agent_id/http 状态码/errcode/errmsg）

## 验证（Verification）

修复后应当看到：

- 同一机器人连续两条消息均出现 `======== 收到消息请求 ========`
- 后台任务继续打印 `[后台任务] ...`
- 发送消息出现 `errcode: 0, errmsg: ok`，并输出 “✓ 消息发送成功”

日志文件：

- `logs/assistant.log`

常用命令：

```bash
tail -f /home/Personal-Agent-Assistant/logs/assistant.log
curl -sS http://127.0.0.1:8024/health
lsof -i:8024 -nP
```

## 防再犯（Prevention）

### 1) 锁设计规范

- **不要在持有同一把不可重入锁时再调用可能获取该锁的函数**。
- 如果确实需要“同一线程嵌套加锁”，应使用 `threading.RLock()`，并在代码注释说明原因。

建议对这类模块做一个简单的“锁递归调用”自检（代码 review checklist）：

- `with lock:` 作用域内是否调用了其它同样 `with lock:` 的方法？

### 2) 进程存活与端口巡检

“只收到第一条”非常常见的另一类原因是服务没跑/端口不通/进程退出。

当出现异常时先做 30 秒体检：

```bash
# 1) 服务是否监听端口
lsof -i:8024 -nP

# 2) /health 是否可访问
curl -sS -m 2 http://127.0.0.1:8024/health || echo "health失败"

# 3) 看日志是否有新回调
tail -n 200 /home/Personal-Agent-Assistant/logs/assistant.log
```

### 3) 回调超时原则（企业微信 5 秒）

- 回调 handler 必须**尽快返回** `success`（通常 < 100ms）
- 耗时逻辑必须丢到后台任务/队列（你现在的 `asyncio.create_task(_process_message_async(...))` 就是正确方向）

### 4) 发送失败快速定位

如果“能收到但不回复”，直接看 `[发送消息] 响应结果`：

- `errcode=0`：发送成功
- `errcode!=0`：按 `errmsg` 定位（常见：token 失效、agentid 错、userid 不在通讯录/无权限等）

## 如果以后又犯了，按这个 Runbook 做

### Step A：确认服务真的在跑

```bash
lsof -i:8024 -nP
curl -sS -m 2 http://127.0.0.1:8024/health
```

### Step B：确认企业微信回调有没有打到服务

```bash
grep -n "收到消息请求" -n /home/Personal-Agent-Assistant/logs/assistant.log | tail -n 20
```

- 没有新增：企业微信没投递（可能配置/网络/域名/端口/超时/服务挂了）
- 有新增但卡住：看最后一条日志停在哪一步

### Step C：若再出现“只打印到 msg_signature 就停”

高度怀疑再次出现“锁/阻塞”问题（类似本次死锁）。重点检查：

- `BotManager` / `SessionManager` / `TaskManager` 等是否有不可重入锁嵌套调用
- 是否有同步阻塞调用在主 handler 内执行（网络请求/LLM/数据库）

## 相关代码位置（便于快速跳转）

- 死锁修复：`interfaces/wechat/bot_manager.py`
- 回调入口：`interfaces/wechat/server.py` 的 `handle_message()`
- 日志落盘：`shared/utils.py` 的 `setup_logger()`


