# 企业微信API配置与测试完整指南

## 📋 目录

1. [概述](#概述)
2. [企业微信配置步骤](#企业微信配置步骤)
3. [配置文件说明](#配置文件说明)
4. [测试工具使用](#测试工具使用)
5. [多机器人部署](#多机器人部署)
6. [故障排查](#故障排查)
7. [常见问题](#常见问题)

---

## 🎯 概述

本指南将帮助你完成从零开始配置企业微信API的全过程，包括：
- ✅ 企业微信账号注册与应用创建
- ✅ 回调URL验证
- ✅ 消息收发测试
- ✅ 多机器人部署
- ✅ 故障排查

### 配置参数说明

| 参数名称 | YAML配置名 | ENV配置名 | 说明 |
|---------|-----------|----------|------|
| 企业ID | `wechat_corp_id` | `WECHAT_CORP_ID` / `WECHAT_RECEIVE_ID` | 企业微信企业唯一标识 |
| 应用AgentID | `wechat_agent_id` | `WECHAT_AGENT_ID` | 应用的唯一标识 |
| 应用Secret | `wechat_corp_secret` | `WECHAT_CORP_SECRET` | 应用密钥 |
| Token | `wechat_token` | `WECHAT_TOKEN` | 回调URL验证令牌 |
| EncodingAESKey | `wechat_encoding_aes_key` | `WECHAT_ENCODING_AES_KEY` | 消息加密密钥 |

**注意**：建议使用 YAML 配置方式（支持多机器人），ENV 方式主要用于单机器人快速测试。

---

## 📝 企业微信配置步骤

### 步骤 1: 注册企业微信

访问 [企业微信官网](https://work.weixin.qq.com/)，注册并创建一个企业。

**提示**：个人也可以注册企业微信，适合个人项目使用。

---

### 步骤 2: 获取企业ID

1. 用电脑登录[企业微信管理后台](https://work.weixin.qq.com/wework_admin/loginpage_wx)
2. 点击左侧菜单 **"我的企业"**
3. 滚动到页面底部，找到 **"企业ID"**
4. 复制企业ID（以 "ww" 开头）

**记录到配置**：
```yaml
wechat_corp_id: "ww1234567890abcdef"  # 你的企业ID
```

---

### 步骤 3: 创建应用

1. 点击左侧菜单 **"应用管理"**
2. 点击 **"创建应用"**
3. 填写应用信息：
   - **应用名称**：如"测试机器人"或"家庭助手"
   - **应用介绍**：简单描述应用功能
   - **应用logo**：上传图标（可选）
4. 点击 **"创建应用"**

---

### 步骤 4: 获取应用配置参数

进入刚创建的应用详情页面：

#### 4.1 获取 AgentID

在应用详情页面顶部直接显示：
```
AgentID: 1000002
```

**记录到配置**：
```yaml
wechat_agent_id: 1000002  # 你的AgentID
```

#### 4.2 获取 Secret

在应用详情页面：
1. 找到 **"Secret"** 字段
2. 点击 **"查看"**
3. 验证管理员身份（扫码）
4. 复制显示的Secret

**记录到配置**：
```yaml
wechat_corp_secret: "abc123def456ghi789jkl012mno345pq"  # 你的Secret
```

**⚠️ 重要**：Secret 是敏感信息，不要泄露或上传到公开仓库！

---

### 步骤 5: 配置接收消息

在应用详情页面：
1. 滚动到 **"接收消息"** 部分
2. 点击 **"设置API接收"**

#### 5.1 生成 Token 和 EncodingAESKey

在弹出的配置页面：
1. **URL**：先留空（稍后填写）
2. **Token**：点击 **"随机获取"** 按钮生成
3. **EncodingAESKey**：点击 **"随机获取"** 按钮生成

**记录到配置**：
```yaml
wechat_token: "Abc123Def456"  # 生成的Token
wechat_encoding_aes_key: "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG"  # 生成的Key（43字符）
```

**⚠️ 先不要点击"保存"**，我们需要先启动测试服务器！

---

### 步骤 6: 配置企业可信IP

在应用详情页面：
1. 找到 **"企业可信IP"** 部分
2. 点击 **"配置"**
3. 输入你的服务器公网IP地址
4. 点击 **"确定"**

**提示**：如果不配置可信IP，将无法主动发送消息（只能接收消息）。

---

### 步骤 7: 配置测试环境

根据你的需求选择配置方式：

#### 方式A：使用 YAML 配置（推荐，支持多机器人）

编辑 `/home/Personal-Agent-Assistant/config/bots.yaml`：

```yaml
bots:
  # 第一个机器人（用于测试）
  test:
    name: "测试机器人"
    enabled: true
    wechat_token: "你的Token"
    wechat_encoding_aes_key: "你的EncodingAESKey"
    wechat_corp_id: "你的企业ID"
    wechat_corp_secret: "你的Secret"
    wechat_agent_id: 1000002
    features:
      - tarot
      - essay
```

#### 方式B：使用 .env.test 文件（仅用于单机器人测试）

创建或编辑 `/home/Personal-Agent-Assistant/.env.test`：

```env
# 企业微信配置
WECHAT_TOKEN=你的Token
WECHAT_ENCODING_AES_KEY=你的EncodingAESKey
WECHAT_CORP_ID=你的企业ID
WECHAT_RECEIVE_ID=你的企业ID
WECHAT_CORP_SECRET=你的Secret
WECHAT_AGENT_ID=1000002

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8024
```

---

### 步骤 8: 启动测试服务器进行URL验证

我们提供了两个测试工具，选择其一使用：

#### 工具A：minimal_callback_verify.py（最简单，仅验证URL）

**适用场景**：第一次配置，只需要验证回调URL

```bash
cd /home/Personal-Agent-Assistant
python minimal_callback_verify.py
```

**详细用法**：参考 [WECHAT_TEST_GUIDE.md](./docs/WECHAT_TEST_GUIDE.md)

#### 工具B：minimal_test_server.py（完整测试，支持消息收发）

**适用场景**：验证URL + 测试消息收发

```bash
cd /home/Personal-Agent-Assistant
python minimal_test_server.py
```

**详细用法**：参考 [MINIMAL_TEST_GUIDE.md](./docs/MINIMAL_TEST_GUIDE.md)

---

### 步骤 9: 配置并验证回调URL

现在回到企业微信管理后台的 **"设置API接收"** 页面：

#### 9.1 填写回调URL

**URL格式**：
```
http://你的服务器IP:8024/ai-bot/callback/{bot_id}
```

**示例**（假设你的机器人叫 `test`）：
```
http://123.456.789.0:8024/ai-bot/callback/test
```

**多机器人示例**：
- 机器人 `test`：`http://123.456.789.0:8024/ai-bot/callback/test`
- 机器人 `family`：`http://123.456.789.0:8024/ai-bot/callback/family`

**⚠️ 重要**：
- `{bot_id}` 必须与 `bots.yaml` 中的键名一致
- 如果使用 `minimal_callback_verify.py`，bot_id 可以是任意值（因为单机器人）

#### 9.2 点击"保存"进行验证

点击 **"保存"** 按钮后，企业微信会立即发送 GET 请求验证URL。

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

---

### 步骤 10: 测试消息收发

#### 10.1 手机端访问应用

1. 在手机上打开 **企业微信APP**
2. 点击底部 **"工作台"**
3. 找到你创建的应用（如"测试机器人"）
4. 点击进入

#### 10.2 发送测试消息

在应用对话框中发送：
```
你好
```

#### 10.3 查看服务器日志

**如果使用 `minimal_test_server.py`**，日志应该显示：

```
======== 收到消息: test ========
✓ 解密成功
用户: YourUserID
内容: 你好
✓ 已创建后台任务，立即返回响应
[后台] 开始处理: test, YourUserID, 你好
✓ 获取 test access_token 成功
✓ 发送成功: test -> YourUserID
[后台] ✓ 回复成功: test
```

#### 10.4 接收回复消息

手机端应该收到回复：
```
✅ 测试机器人收到消息

你发送的内容：你好

时间：22:30:45
```

🎉 **测试成功！消息收发正常！**

---

## 📁 配置文件说明

### YAML 配置文件结构

路径：`/home/Personal-Agent-Assistant/config/bots.yaml`

```yaml
bots:
  # 机器人1的配置
  bot_id_1:
    name: "机器人显示名称"
    enabled: true  # 是否启用
    wechat_token: "Token"
    wechat_encoding_aes_key: "EncodingAESKey"
    wechat_corp_id: "企业ID"
    wechat_corp_secret: "应用Secret"
    wechat_agent_id: 应用AgentID
    features:  # 启用的功能模块
      - tarot
      - essay
      - accounting
  
  # 机器人2的配置
  bot_id_2:
    name: "另一个机器人"
    enabled: true
    # ... 其他配置
```

### ENV 配置文件（测试用）

路径：`/home/Personal-Agent-Assistant/.env.test`

```env
# 企业微信配置
WECHAT_TOKEN=你的Token
WECHAT_ENCODING_AES_KEY=你的EncodingAESKey
WECHAT_CORP_ID=你的企业ID
WECHAT_RECEIVE_ID=你的企业ID  # 与CORP_ID相同
WECHAT_CORP_SECRET=你的Secret
WECHAT_AGENT_ID=应用AgentID

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8024
```

---

## 🔧 测试工具使用

### 工具对比

| 特性 | minimal_callback_verify.py | minimal_test_server.py |
|------|---------------------------|------------------------|
| **用途** | 仅URL验证 | 完整消息收发测试 |
| **配置方式** | .env.test 文件 | config/bots.yaml |
| **支持多机器人** | ❌ 否 | ✅ 是 |
| **处理消息** | ❌ 否 | ✅ 是 |
| **代码行数** | ~160行 | ~240行 |
| **适用场景** | 首次配置验证 | 完整功能测试 |

### 工具1: minimal_callback_verify.py

**用途**：仅用于回调URL验证（不处理消息）

**特点**：
- ✅ 最简单（约160行代码）
- ✅ 只处理 GET 请求（URL验证）
- ✅ 使用 .env.test 配置
- ✅ 适合首次配置

**启动方式**：
```bash
python minimal_callback_verify.py
```

**详细文档**：参考 [WECHAT_TEST_GUIDE.md](./docs.WECHAT_TEST_GUIDE.md)

---

### 工具2: minimal_test_server.py

**用途**：完整的消息收发测试

**特点**：
- ✅ 支持多机器人
- ✅ 支持消息收发
- ✅ 使用 bots.yaml 配置
- ✅ 异步后台处理
- ✅ 详细日志输出

**启动方式**：
```bash
python minimal_test_server.py
```

**详细文档**：参考 [MINIMAL_TEST_GUIDE.md](./docs/MINIMAL_TEST_GUIDE.md)

---

## 🤖 多机器人部署

### 使用场景

- 🏠 **家庭机器人**：处理家庭账务、员工管理
- 📚 **个人机器人**：塔罗牌、随笔记录
- 💼 **工作机器人**：团队协作、任务管理

### 配置步骤

#### 1. 在企业微信中创建多个应用

按照"步骤3-6"为每个机器人创建独立的应用，每个应用会有不同的：
- AgentID
- Secret
- Token
- EncodingAESKey

#### 2. 在 bots.yaml 中配置多个机器人

```yaml
bots:
  test:
    name: "测试机器人"
    enabled: true
    wechat_token: "Token_1"
    wechat_encoding_aes_key: "Key_1"
    wechat_corp_id: "ww1234567890abcdef"  # 相同企业ID
    wechat_corp_secret: "Secret_1"
    wechat_agent_id: 1000002
    features:
      - tarot
      - essay
  
  family:
    name: "家庭助手"
    enabled: true
    wechat_token: "Token_2"
    wechat_encoding_aes_key: "Key_2"
    wechat_corp_id: "ww1234567890abcdef"  # 相同企业ID
    wechat_corp_secret: "Secret_2"
    wechat_agent_id: 1000003  # 不同AgentID
    features:
      - accounting
      - employee
```

#### 3. 配置不同的回调URL

- test: `http://123.456.789.0:8024/ai-bot/callback/test`
- family: `http://123.456.789.0:8024/ai-bot/callback/family`

#### 4. 启动服务器

```bash
python minimal_test_server.py
```

或启动完整服务：
```bash
python interfaces/wechat/server.py
```

### 机器人路由机制

系统通过回调URL的最后一段 `{bot_id}` 来区分不同机器人：

```python
# 示例：用户向 family 机器人发消息
# 企业微信调用：POST http://your-ip:8024/ai-bot/callback/family
# 
# 服务器识别：
#   - bot_id = "family"
#   - 加载 bots.yaml 中 family 的配置
#   - 使用 family 的 token/key 解密消息
#   - 使用 family 的 agent_id/secret 发送回复
#   - 根据 family.features 决定可用功能
```

---

## 🔍 故障排查

### 问题1: URL验证失败

**日志显示**：
```
✗ URL验证失败: 签名验证失败
```

**可能原因**：
1. Token 配置错误
2. EncodingAESKey 配置错误
3. receive_id 不正确

**解决方法**：
1. 检查配置文件中的 `wechat_token` 是否与企业微信后台一致
2. 检查 `wechat_encoding_aes_key` 是否完整（43个字符）
3. 确认 `wechat_corp_id` 填写正确（以 "ww" 开头）
4. 确保没有多余的空格或换行符

---

### 问题2: 收不到消息

**症状**：URL验证成功，但发送消息后服务器没有日志

**可能原因**：
1. 回调URL配置错误
2. 服务器防火墙阻止
3. 企业微信后台API未启用

**解决方法**：
1. 检查企业微信后台 "接收消息" 状态是否为 "已启用"
2. 确认回调URL的 bot_id 与配置一致
3. 检查服务器防火墙：
   ```bash
   # 开放端口
   sudo ufw allow 8024
   ```
4. 查看服务器是否正常运行：
   ```bash
   curl http://localhost:8024/health
   ```

---

### 问题3: 无法发送回复

**日志显示**：
```
✗ 获取 test access_token 失败: invalid secret
```

**可能原因**：
1. Corp Secret 配置错误
2. Corp ID 配置错误
3. 企业可信IP未配置

**解决方法**：
1. 重新获取并检查 `wechat_corp_secret`
2. 检查 `wechat_corp_id` 是否正确
3. 在企业微信后台配置 "企业可信IP"
4. 检查 `wechat_agent_id` 是否正确

---

### 问题4: 只收到第一条消息，后续消息不响应

**可能原因**：
1. 消息处理超时（超过5秒未返回）
2. 同步阻塞导致死锁

**解决方法**：
1. 使用异步后台处理：
   ```python
   # ✅ 正确：立即返回
   asyncio.create_task(process_message(...))
   return PlainTextResponse("success")
   
   # ❌ 错误：等待处理完成
   result = process_message(...)
   return PlainTextResponse("success")
   ```

2. 参考 `minimal_test_server.py` 的实现方式

---

### 问题5: 消息内容乱码或解密失败

**日志显示**：
```
✗ 解密失败: receive_id不匹配
```

**可能原因**：
1. receive_id 配置错误
2. EncodingAESKey 不匹配

**解决方法**：
1. 确保 `receive_id` 使用企业ID（与 `wechat_corp_id` 相同）
2. 重新生成并更新 `wechat_encoding_aes_key`
3. 确保密钥是Base64格式（43字符，不包含空格）

---

### 问题6: 多个机器人配置冲突

**症状**：发送给机器人A的消息，机器人B也收到了

**可能原因**：
1. 回调URL的 bot_id 配置错误
2. bots.yaml 中的键名与URL不一致

**解决方法**：
1. 检查每个应用的回调URL：
   ```
   test:  http://your-ip:8024/ai-bot/callback/test
   family: http://your-ip:8024/ai-bot/callback/family
   ```

2. 确保 bots.yaml 的键名与URL一致：
   ```yaml
   bots:
     test:    # 必须与URL中的bot_id一致
       name: "测试机器人"
       # ...
     family:  # 必须与URL中的bot_id一致
       name: "家庭助手"
       # ...
   ```

---

## ❓ 常见问题

### Q1: 个人可以注册企业微信吗？

**答**：可以！企业微信支持个人注册，适合个人项目使用。

---

### Q2: 一个企业可以创建多少个应用？

**答**：企业微信允许创建多个自建应用，通常足够个人使用。

---

### Q3: Token 和 Secret 有什么区别？

**答**：
- **Token**：用于回调URL签名验证（企业微信→你的服务器）
- **Secret**：用于获取access_token（你的服务器→企业微信API）

---

### Q4: EncodingAESKey 可以自己生成吗？

**答**：建议使用企业微信后台的 "随机获取" 功能生成，确保安全性和兼容性。

---

### Q5: 为什么要配置企业可信IP？

**答**：企业微信要求主动调用API（如发送消息）的服务器IP必须在可信IP列表中，否则会返回权限错误。

---

### Q6: 本地开发如何测试？

**答**：可以使用内网穿透工具（如 ngrok）：
```bash
# 安装 ngrok
brew install ngrok  # macOS
# 或从官网下载：https://ngrok.com/

# 启动穿透
ngrok http 8024

# 使用生成的公网URL配置回调
# 例如：https://abc123.ngrok.io/ai-bot/callback/test
```

---

### Q7: 如何查看完整的企业微信API文档？

**答**：访问[企业微信API文档](https://developer.work.weixin.qq.com/document/)

---

### Q8: 消息加密是必须的吗？

**答**：是的。企业微信强制要求使用加密模式，所有消息必须加解密。

---

### Q9: 如何调试消息内容？

**答**：查看服务器日志，所有解密后的消息都会打印：
```bash
tail -f logs/assistant_*.log | grep "内容:"
```

---

### Q10: 多机器人是否需要多个企业？

**答**：不需要！同一个企业可以创建多个应用，每个应用就是一个独立的机器人。

---

## 📚 参考资料

- [企业微信API官方文档](https://developer.work.weixin.qq.com/document/)
- [消息加密解密说明](https://developer.work.weixin.qq.com/document/path/90968)
- [发送应用消息API](https://developer.work.weixin.qq.com/document/path/90236)
- [接收消息与事件](https://developer.work.weixin.qq.com/document/path/90239)
- [WECHAT_TEST_GUIDE.md](./WECHAT_TEST_GUIDE.md) - 回调验证工具详细说明
- [MINIMAL_TEST_GUIDE.md](./docs/MINIMAL_TEST_GUIDE.md) - 消息收发测试详细说明

---

## 🎉 完成！

按照本指南操作后，你应该已经成功：
- ✅ 配置了企业微信应用
- ✅ 验证了回调URL
- ✅ 测试了消息收发
- ✅ 部署了多机器人（可选）

**下一步**：
1. 启动完整服务：`python interfaces/wechat/server.py`
2. 体验各种业务功能（塔罗牌、随笔、账务等）
3. 根据需要调整 `bots.yaml` 中的功能配置

祝使用愉快！🚀
