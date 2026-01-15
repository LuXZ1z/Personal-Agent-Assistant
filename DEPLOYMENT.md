# 部署指南

本文档说明如何将个人助手系统部署到生产环境（微信企业号）。

## 前置要求

### 1. 服务器要求

- **公网可访问的服务器**（微信需要回调你的服务器）
- **域名**（建议使用HTTPS，需要SSL证书）
- **Python 3.11+**
- **Redis服务**
- **系统要求**：Linux/Unix系统（推荐Ubuntu 20.04+）

### 2. 微信配置

在微信企业号管理后台获取以下信息：
- **WECHAT_TOKEN**：应用Token
- **WECHAT_ENCODING_AES_KEY**：Base64编码的AES密钥
- **机器人ID (botid)**：在回调URL中使用

## 部署步骤

### 1. 服务器环境准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python 3.11和pip
sudo apt install python3.11 python3.11-venv python3-pip -y

# 安装Redis
sudo apt install redis-server -y
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 安装Nginx（用于反向代理和HTTPS）
sudo apt install nginx -y
```

### 2. 部署代码

```bash
# 创建应用目录
sudo mkdir -p /opt/personal-assistant
sudo chown $USER:$USER /opt/personal-assistant
cd /opt/personal-assistant

# 克隆或上传代码
# git clone <your-repo> .  # 或使用scp上传

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制配置模板
cp env.example .env

# 编辑配置文件
nano .env
```

填写以下配置：

```env
# 微信配置（必须从微信平台获取）
WECHAT_TOKEN=your_actual_token_here
WECHAT_ENCODING_AES_KEY=your_actual_aes_key_here

# OpenAI配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com/v1

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 数据库配置
DATABASE_PATH=/opt/personal-assistant/data/assistant.db

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/opt/personal-assistant/logs/assistant.log

# 服务器配置
SERVER_HOST=127.0.0.1  # 只监听本地，通过Nginx反向代理
SERVER_PORT=8000       # 内部端口
SERVER_WORKERS=4      # 根据CPU核心数调整
```

### 4. 配置Nginx反向代理

创建Nginx配置文件：

```bash
sudo nano /etc/nginx/sites-available/personal-assistant
```

配置内容：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名

    # 重定向到HTTPS（可选，如果已配置SSL）
    # return 301 https://$server_name$request_uri;

    # 如果暂时不使用HTTPS，直接代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 微信回调需要较长的超时时间
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}

# 如果使用HTTPS（推荐）
# server {
#     listen 443 ssl http2;
#     server_name your-domain.com;
# 
#     ssl_certificate /path/to/ssl/cert.pem;
#     ssl_certificate_key /path/to/ssl/key.pem;
# 
#     location / {
#         proxy_pass http://127.0.0.1:8000;
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto $scheme;
#         proxy_read_timeout 300s;
#         proxy_connect_timeout 75s;
#     }
# }
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/personal-assistant /etc/nginx/sites-enabled/
sudo nginx -t  # 测试配置
sudo systemctl reload nginx
```

### 5. 配置SSL证书（推荐）

使用Let's Encrypt免费SSL证书：

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

### 6. 配置Systemd服务

创建systemd服务文件：

```bash
sudo nano /etc/systemd/system/personal-assistant.service
```

内容：

```ini
[Unit]
Description=Personal Assistant WeChat Service
After=network.target redis.service

[Service]
Type=simple
User=your-username  # 替换为你的用户名
WorkingDirectory=/opt/personal-assistant
Environment="PATH=/opt/personal-assistant/venv/bin"
ExecStart=/opt/personal-assistant/venv/bin/python main.py
Restart=always
RestartSec=10

# 日志配置
StandardOutput=journal
StandardError=journal
SyslogIdentifier=personal-assistant

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable personal-assistant
sudo systemctl start personal-assistant
sudo systemctl status personal-assistant
```

### 7. 配置微信回调URL

在微信企业号管理后台：

1. 进入应用管理 -> 你的应用
2. 配置回调URL：
   - **URL**: `https://your-domain.com/ai-bot/callback/{botid}`
   - **Token**: 填写你的 `WECHAT_TOKEN`
   - **EncodingAESKey**: 填写你的 `WECHAT_ENCODING_AES_KEY`
3. 保存并验证URL

### 8. 验证部署

```bash
# 检查服务状态
sudo systemctl status personal-assistant

# 查看日志
sudo journalctl -u personal-assistant -f

# 或查看应用日志
tail -f /opt/personal-assistant/logs/assistant.log

# 测试健康检查接口
curl http://localhost:8000/health
```

## 监控和维护

### 查看日志

```bash
# Systemd日志
sudo journalctl -u personal-assistant -n 100 -f

# 应用日志
tail -f /opt/personal-assistant/logs/assistant.log

# Nginx日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 重启服务

```bash
sudo systemctl restart personal-assistant
```

### 更新代码

```bash
cd /opt/personal-assistant
source venv/bin/activate
git pull  # 或上传新代码
pip install -r requirements.txt  # 如果有新依赖
sudo systemctl restart personal-assistant
```

## 故障排查

### 1. 服务无法启动

```bash
# 检查日志
sudo journalctl -u personal-assistant -n 50

# 检查配置
python -c "from shared.config import settings; settings.validate()"

# 检查Redis连接
redis-cli ping
```

### 2. 微信回调失败

- 检查Nginx配置和日志
- 检查防火墙是否开放80/443端口
- 检查域名DNS解析
- 验证微信配置的Token和AESKey是否正确

### 3. 消息处理异常

- 查看应用日志：`tail -f logs/assistant.log`
- 检查Redis队列：`redis-cli LLEN wechat_messages`
- 检查数据库连接

## 安全建议

1. **使用HTTPS**：生产环境必须使用HTTPS
2. **防火墙配置**：只开放必要的端口（80, 443）
3. **定期更新**：保持系统和依赖包更新
4. **备份数据**：定期备份数据库文件
5. **监控告警**：配置日志监控和异常告警

## 性能优化

1. **调整Worker数量**：根据CPU核心数设置 `SERVER_WORKERS`
2. **Redis优化**：配置Redis持久化和内存限制
3. **数据库优化**：定期清理旧数据，优化查询
4. **日志轮转**：配置logrotate避免日志文件过大

## 注意事项

1. **端口配置**：生产环境建议使用Nginx反向代理，应用监听127.0.0.1:8000
2. **资源限制**：根据服务器配置调整worker数量和Redis连接数
3. **超时设置**：微信回调可能需要较长时间，确保Nginx超时设置足够
4. **错误处理**：所有异常都应返回"success"给微信，避免重试

