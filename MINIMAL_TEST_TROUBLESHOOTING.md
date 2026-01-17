# 最小化测试服务器故障排查

## 签名验证失败问题

如果看到错误：
```
签名验证失败: 期望xxx, 实际yyy
解密消息失败: 签名验证失败
```

### 原因

`receive_id` 配置不正确。企业微信智能机器人的 `receive_id` 可能是：
1. **空字符串** `""`（大多数情况）
2. **企业微信 CorpID**（某些配置）

### 解决方法

编辑 `minimal_test_server.py`，修改第 35 行：

```python
# 方法1：使用空字符串（默认，先试这个）
USE_CORP_ID_AS_RECEIVE_ID = False

# 方法2：如果方法1不行，改为使用 corp_id
USE_CORP_ID_AS_RECEIVE_ID = True
```

### 测试步骤

1. **先测试空字符串**（默认配置）
   ```bash
   # 确保 USE_CORP_ID_AS_RECEIVE_ID = False
   ./start_minimal_test.sh
   ```
   
   在微信中发送消息，查看日志：
   - ✅ 如果看到 `✓ 解密成功`，说明配置正确
   - ❌ 如果看到 `签名验证失败`，继续下一步

2. **如果空字符串不行，测试 corp_id**
   ```python
   # 修改 minimal_test_server.py 第 35 行
   USE_CORP_ID_AS_RECEIVE_ID = True
   ```
   
   重启服务器，再次测试。

## 环境问题

### 确保使用正确的虚拟环境

```bash
# 方法1：使用启动脚本（推荐）
./start_minimal_test.sh

# 方法2：手动激活
conda activate personal-assistant
cd /home/Personal-Agent-Assistant
python minimal_test_server.py
```

### 检查依赖

```bash
conda activate personal-assistant
pip list | grep -E "yaml|fastapi|uvicorn"
```

如果缺少，安装：
```bash
pip install pyyaml fastapi uvicorn
```

## 常见错误

### 1. ModuleNotFoundError: No module named 'yaml'

**解决**：
```bash
conda activate personal-assistant
pip install pyyaml
```

### 2. ModuleNotFoundError: No module named 'fastapi'

**解决**：
```bash
conda activate personal-assistant
pip install fastapi uvicorn
```

### 3. 端口被占用

**解决**：
```bash
lsof -t -i:8024 | xargs kill -9
```

### 4. 收不到消息

**检查项**：
1. 企业微信后台的回调URL是否正确
   - test: `http://你的IP:8024/ai-bot/callback/test`
   - family: `http://你的IP:8024/ai-bot/callback/family`
2. 服务器防火墙是否开放 8024 端口
3. 企业微信后台是否显示"接收消息服务器配置"验证成功

### 5. 收到消息但不回复

**检查项**：
1. 查看日志中的 `✗ 获取 access_token 失败`
2. 检查 yaml 配置中的 `wechat_corp_secret` 是否正确
3. 检查 yaml 配置中的 `wechat_agent_id` 是否正确

## 调试技巧

### 查看详细日志

服务器启动后会显示：
```
✓ 加载机器人: test - 测试机器人 (receive_id='')
✓ 加载机器人: family - 家庭机器人 (receive_id='')
```

### 测试消息流程

1. **发送消息后，应该看到**：
   ```
   ======== 收到消息: test ========
   ✓ 解密成功
   用户: xxx
   内容: 测试
   ✓ 已创建后台任务，立即返回响应
   [后台] 开始处理: test, xxx, 测试
   ✓ 获取 test access_token 成功
   ✓ 发送成功: test -> xxx
   [后台] ✓ 回复成功: test
   ```

2. **如果签名验证失败**：
   ```
   ======== 收到消息: test ========
   ✗ 签名验证失败: 期望xxx, 实际yyy
   ```
   
   这时需要切换 `USE_CORP_ID_AS_RECEIVE_ID` 的值。

## 成功标志

如果一切正常，你应该看到：

1. ✅ 服务器启动成功，显示加载的机器人
2. ✅ 发送消息后，日志显示 `收到消息` 和 `解密成功`
3. ✅ 微信收到回复消息
4. ✅ 连续发送多条消息，都能正常接收和回复

## 下一步

如果最小化测试成功，说明：
- ✅ yaml 配置正确
- ✅ 网络通信正常
- ✅ 企业微信配置正确
- ✅ 基础代码逻辑正常

那么可以回到完整程序，检查业务逻辑是否有问题。

