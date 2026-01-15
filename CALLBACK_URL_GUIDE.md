# 企业微信回调URL配置指南

## 📋 回调URL格式

在企业微信后台的"接收消息"配置中，需要填写以下格式的URL：

```
http://你的域名或IP:端口/ai-bot/callback/你的botid
```

### 示例

1. **本地测试（使用ngrok）**：
   ```
   https://xxxx.ngrok.io/ai-bot/callback/test
   ```

2. **服务器部署（使用域名）**：
   ```
   https://yourdomain.com/ai-bot/callback/test
   ```

3. **服务器部署（使用IP）**：
   ```
   http://123.456.789.0:8024/ai-bot/callback/test
   ```

## ⚠️ 重要要求

### 1. URL必须公网可访问
- ❌ **不能使用**：`localhost`、`127.0.0.1`、`192.168.x.x`（内网IP）
- ✅ **必须使用**：公网IP或域名

### 2. 路径必须完全匹配
- 路径格式：`/ai-bot/callback/{botid}`
- `{botid}` 可以是任意字符串，如：`test`、`bot1`、`mybot` 等
- 路径必须**完全一致**，不能多或少任何字符

### 3. 协议要求
- 支持 `http` 和 `https`
- 推荐使用 `https`（更安全）
- 如果使用 `https`，需要有效的SSL证书

### 4. 端口要求
- 如果使用标准端口（http:80, https:443），可以省略端口号
- 如果使用非标准端口（如8024），必须包含端口号

## 🔧 配置步骤

### 步骤1：启动服务器

确保服务器正在运行：

```bash
cd /home/Personal-Agent-Assistant
python minimal_wechat_test.py
```

服务器启动后会显示：
```
服务器配置:
  地址: 0.0.0.0
  端口: 8024
```

### 步骤2：确保服务器可访问

#### 方案A：使用ngrok（本地测试推荐）

```bash
# 安装ngrok
# 下载：https://ngrok.com/download

# 启动内网穿透
ngrok http 8024
```

ngrok会显示类似：
```
Forwarding  https://xxxx.ngrok.io -> http://localhost:8024
```

#### 方案B：服务器部署

确保：
- 服务器有公网IP
- 防火墙开放了8024端口
- 如果使用域名，DNS已正确解析

### 步骤3：在企业微信后台配置

1. 登录企业微信管理后台：https://work.weixin.qq.com/
2. 进入「应用管理」→ 选择你的应用
3. 进入「接收消息」配置
4. 填写以下信息：

   **URL**：
   ```
   https://xxxx.ngrok.io/ai-bot/callback/test
   ```
   （替换为你的实际URL）

   **Token**：
   ```
   你的WECHAT_TOKEN值（从.env文件）
   ```

   **EncodingAESKey**：
   ```
   你的WECHAT_ENCODING_AES_KEY值（从.env文件）
   ```

5. 点击「保存」

### 步骤4：查看验证结果

保存后，企业微信会立即发送GET请求验证URL。查看服务器日志：

**成功示例**：
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

**失败示例**：
```
✗ URL验证失败: 签名验证失败
```
或
```
✗ URL验证异常: ...
```

## 🔍 常见问题排查

### 问题1：URL验证失败 - 签名验证失败

**可能原因**：
- Token配置不一致（.env文件中的值与后台填写的不同）
- EncodingAESKey配置不一致

**解决方法**：
1. 检查 `.env` 文件中的 `WECHAT_TOKEN` 和 `WECHAT_ENCODING_AES_KEY`
2. 确保企业微信后台填写的值与 `.env` 文件中的值**完全一致**
3. 注意不要有多余的空格或换行符

### 问题2：无法访问URL

**可能原因**：
- 服务器未启动
- 防火墙阻止了端口
- URL格式错误
- 使用了内网地址

**解决方法**：
1. 确认服务器正在运行：`lsof -i :8024`
2. 测试URL是否可访问：
   ```bash
   curl http://your-domain.com:8024/health
   ```
3. 检查防火墙：
   ```bash
   # 开放端口
   sudo ufw allow 8024
   # 或
   sudo iptables -A INPUT -p tcp --dport 8024 -j ACCEPT
   ```

### 问题3：参数接收错误

**可能原因**：
- 参数名称不匹配
- FastAPI路由配置问题

**解决方法**：
代码中已正确配置了参数别名：
```python
msg_signature: str = Query(..., alias="msg_signature")
```

如果仍有问题，检查：
1. 企业微信发送的参数名称（应该是 `msg_signature`，不是 `msg-signature`）
2. 查看日志中的实际接收到的参数值

### 问题4：返回格式错误

**要求**：
- 返回解密后的明文内容
- **不能**加引号
- **不能**有BOM头
- **不能**有换行符
- 必须在1秒内响应

**当前实现**：
代码使用 `PlainTextResponse`，应该满足要求。如果失败，检查：
1. 响应时间是否超过1秒
2. 返回内容是否包含额外字符

## 📝 完整配置示例

### .env 文件配置
```env
# 微信配置（必填）
WECHAT_TOKEN=your_random_token_here_32_chars_max
WECHAT_ENCODING_AES_KEY=your_43_chars_base64_aes_key_here

# 企业微信配置（用于发送消息，必填）
WECHAT_CORP_ID=wwxxxxxxxxxxxxxxxx
WECHAT_CORP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
WECHAT_AGENT_ID=1000002

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8024
```

### 企业微信后台配置
- **URL**: `https://xxxx.ngrok.io/ai-bot/callback/test`
- **Token**: `your_random_token_here_32_chars_max`（与.env中的WECHAT_TOKEN一致）
- **EncodingAESKey**: `your_43_chars_base64_aes_key_here`（与.env中的WECHAT_ENCODING_AES_KEY一致）

## ✅ 验证清单

在配置回调URL前，请确认：

- [ ] 服务器已启动并运行在指定端口
- [ ] 服务器可以从公网访问（使用ngrok或部署在公网服务器）
- [ ] `.env` 文件中的 `WECHAT_TOKEN` 和 `WECHAT_ENCODING_AES_KEY` 已配置
- [ ] 企业微信后台填写的Token和EncodingAESKey与.env文件中的值完全一致
- [ ] URL格式正确：`http(s)://域名或IP:端口/ai-bot/callback/botid`
- [ ] 防火墙已开放相应端口
- [ ] 如果使用https，SSL证书有效

## 🚀 测试流程

1. **启动服务器**：
   ```bash
   python minimal_wechat_test.py
   ```

2. **配置ngrok**（如果本地测试）：
   ```bash
   ngrok http 8024
   ```

3. **在企业微信后台填写回调URL**：
   ```
   https://xxxx.ngrok.io/ai-bot/callback/test
   ```

4. **填写Token和EncodingAESKey**（与.env文件一致）

5. **点击保存**，观察服务器日志

6. **如果验证成功**，可以在企业微信中发送消息测试

## 📚 参考文档

- [企业微信回调配置文档](https://developer.work.weixin.qq.com/document/path/90930)
- [接收消息与事件](https://developer.work.weixin.qq.com/document/path/90968)


