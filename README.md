# Personal Agent Assistant

> "I am JARVIS. I run the house, I keep the schedule, and I execute the mission." - Tony Stark  
> "Amadeus, the AI assistant that understands your heart and memories." - Steins;Gate

一个**智能个人助手系统**，灵感来自钢铁侠的贾维斯（JARVIS）和命运石之门的 Amadeus。通过自然语言交互，帮助你管理生活、记录想法、分析数据，成为你的数字伙伴。


## 🚀 为什么选择这个项目？

| **特性**         | **描述**                                                   |
| ---------------- | ---------------------------------------------------------- |
| **自然语言驱动** | 告别复杂的命令或 UI，像聊天一样记账、管理工作。            |
| **多态部署**     | 同一套内核，同时驱动 CLI 测试环境和企业微信生产环境。      |
| **多机器人架构** | 支持在单一服务器上运行多个具有不同“性格”和“权限”的机器人。 |
| **隐私保障**     | 数据存储在本地 SQLite，支持用户隔离，你的记忆只属于你。    |
| **极简扩展**     | 采用插件式业务模块设计，新增功能只需在配置中“挂载”。       |

------
## 🛠️ 核心功能矩阵

### 💰 智能财务 (Accounting)

- **语义记账**：识别“中午喝咖啡花了35元”，自动归类并存入数据库。
- **财务洞察**：AI 定期分析消费趋势，发现你没察觉的开销黑洞。

### 📝 情感随笔 (Essay)

- **数字记忆**：记录瞬间灵感或情绪。
- **情感反馈**：AI 辅助分析情感倾向，并在特定时刻为你提供温暖的回应。

### 👥 团队/员工管理 (Employee)

- **执行追踪**：记录工作进度、状态及态度，形成自动化的效能报告。
- **智能洞察**：发现工作模式中的瓶颈与异常。

### 🔮 塔罗占卜 (Tarot)

- **沉浸式解读**：支持 1/3/5 张牌阵，由 LLM 提供充满启发性的解牌建议。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│              智能助手核心 (AI Core)                       │
│  - 自然语言理解 (LLM)                                    │
│  - 数据记忆管理 (Database)                               │
│  - 智能分析引擎 (Analysis)                               │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
┌───────▼────────┐                  ┌───────▼────────┐
│   业务模块层    │                  │   平台接入层    │
│  - 记账管理     │                  │  - 微信平台     │
│  - 随笔管理     │                  │    (多机器人)   │
│  - 员工管理     │                  │  - CLI平台     │
│  - 塔罗占卜     │                  │  - 独立测试     │
└────────────────┘                  └────────────────┘
```

### 分层设计

- **core/** - 基础能力层：数据库和LLM的统一接口
- **business/** - 业务逻辑层：各业务的核心逻辑（支持独立测试）
- **interfaces/** - 平台接入层：微信和CLI适配
- **shared/** - 共享工具：配置、模型、工具函数
- **config/** - 配置文件：系统配置（system.yaml）和机器人配置（bots.yaml）

### 多机器人支持

系统支持在同一服务器上部署多个机器人，每个机器人可以：
- 配置不同的微信应用参数
- 开放不同的功能集（通过 `features` 配置）
- 独立管理用户会话和数据
- 共享相同的业务逻辑和AI能力

## 🎯 设计原则

1. **智能优先**：自然语言交互，无需学习复杂命令
2. **记忆管理**：自动保存所有交互，形成个人知识库
3. **情感理解**：理解用户意图和情感，提供个性化服务
4. **无缝切换**：本地测试和线上部署使用完全相同的代码
5. **易于扩展**：添加新业务只需配置和实现，无需修改其他代码
6. **多机器人支持**：同一服务器支持部署多个机器人，每个机器人可配置不同功能集

## 📦 快速开始

### 安装

```bash
# 创建环境
conda create -n personal-assistant python=3.11 -y
conda activate personal-assistant

# 安装依赖
pip install -r requirements.txt
```

### 配置

项目使用 **YAML 配置文件**进行配置管理，支持多机器人部署。

**首次克隆后**（这些文件不会出现在仓库里，请勿把真实密钥提交到 Git）：

```bash
cp config/system_example.yaml config/system.yaml
cp config/bots_example.yaml config/bots.yaml
# 按需创建 .env（若你的部署方式仍读取环境变量）
# cp .env.test.example .env.test
```

然后编辑上述本地文件，填入你的 API Key、企业微信 Token/Secret 等。

#### 1. 系统配置（`config/system.yaml`）

编辑 `config/system.yaml` 配置系统级参数（由 `system_example.yaml` 复制而来）。

#### 2. 机器人配置（`config/bots.yaml`）

编辑 `config/bots.yaml` 配置一个或多个机器人（由 `bots_example.yaml` 复制而来）。

**功能说明**：
- 每个机器人可以配置不同的功能集（`features`）
- 支持的功能：`accounting`（记账）、`essay`（随笔）、`employee`（员工管理）、`tarot`（塔罗占卜）
- 未在 `features` 中列出的功能将不会在该机器人的菜单中显示

**详细配置指南**：请参考 [WECHAT_API_SETUP_GUIDE.md](./WECHAT_API_SETUP_GUIDE.md)

#### 3. 测试工具配置（可选）

项目提供了两个测试工具，用于验证企业微信配置：

- **minimal_callback_verify.py** - 仅用于回调URL验证（最简单）
  - 使用 `.env.test` 配置文件
  - 详细用法：参考 [WECHAT_TEST_GUIDE.md](./docs/WECHAT_TEST_GUIDE.md)

- **minimal_test_server.py** - 完整的消息收发测试（推荐）
  - 使用 `config/bots.yaml` 配置文件
  - 支持多机器人测试
  - 详细用法：参考 [MINIMAL_TEST_GUIDE.md](./docs/MINIMAL_TEST_GUIDE.md)

### 运行

#### 方式一：微信模式（推荐）
```bash
# 使用启动脚本（自动清理端口）
./scripts/start_wechat_server.sh
# 或使用 Python 版本
python scripts/start_wechat_server.py

# 或直接启动（需要手动清理端口）
python -m interfaces.wechat.server
```
启动后，在微信中与助手对话，体验智能交互。

**启动脚本功能**：
- 自动检测并清理占用端口的进程
- 支持多种端口检测工具（lsof/netstat/ss）
- 优雅终止进程，必要时强制终止

#### 方式二：CLI模式（本地测试）
```bash
# 默认模式（全功能）
python -m interfaces.cli.main

# 指定机器人ID（只显示该机器人的功能）
python -m interfaces.cli.main --bot test

# 服务端模式（从Redis队列消费消息）
python -m interfaces.cli.main --server
```
通过命令行界面测试所有功能，与微信模式使用完全相同的业务逻辑。支持指定机器人ID来模拟特定机器人的功能集。

#### 方式三：独立测试（开发调试）
```bash
# 测试记账功能
python -m business.accounting.manager --debug

# 测试塔罗牌功能
python -m business.tarot.manager --debug
```

#### 方式四：微信配置测试（首次配置推荐）
```bash
# 1. 仅验证回调URL（最简单）
python minimal_callback_verify.py

# 2. 完整消息收发测试（推荐）
python minimal_test_server.py
```

**测试工具说明**：
- `minimal_callback_verify.py` - 仅用于验证企业微信回调URL是否正确配置
- `minimal_test_server.py` - 完整的消息收发测试，支持多机器人

详细用法请参考：
- [回调验证工具指南](./docs/WECHAT_TEST_GUIDE.md)
- [消息收发测试指南](./docs/MINIMAL_TEST_GUIDE.md)

## 💡 使用示例

### 记账管理
```
你：今天花了50元买了一杯咖啡
助手：✓ 记账保存成功！
      💰 金额: ¥50
      📂 类别: 餐饮
      📅 日期: 2024-01-16
      💳 支付方式: 微信支付

你：查询这个月的支出
助手：找到 15 条记录
      【总结分析结果】
      本月总支出：¥2,350
      主要支出类别：餐饮(40%)、交通(30%)、购物(20%)...
```

### 随笔管理
```
你：今天心情很好，完成了重要项目
助手：✓ 随笔保存成功！
      【AI情感分析】
      😊 检测到积极情绪
      💡 建议：继续保持这种状态，可以记录一下成功的经验...
```

### 塔罗牌占卜
```
你：我想知道最近的工作运势
助手：🔮 抽取的牌：太阳 (The Sun) ⬆️
      【AI解读】
      ☀️ 这张牌预示着光明和成功...
      你最近的工作运势非常积极...
```

## 🔧 技术栈

- **Web框架**: FastAPI（高性能异步框架）
- **数据库**: SQLite（轻量级，支持多用户）
- **消息队列**: Redis（异步消息处理）
- **LLM**: OpenAI兼容API（DeepSeek、GPT等）
- **加密**: pycryptodome（微信消息加解密）
- **配置管理**: YAML（支持多机器人配置）

## 📚 项目结构

```
Personal-Agent-Assistant/
├── config/                  # 配置文件目录
│   ├── system.yaml          # 系统配置（LLM、数据库、Redis等）
│   └── bots.yaml            # 机器人配置（多机器人支持）
│
├── core/                    # 基础能力层（AI核心）
│   ├── database/           # 记忆管理（数据库）
│   └── llm/                 # 自然语言理解（LLM）
│
├── business/                # 业务模块层
│   ├── accounting/          # 记账管理
│   ├── essay/               # 随笔管理
│   ├── employee/            # 员工管理
│   └── tarot/               # 塔罗占卜
│
├── interfaces/              # 平台接入层
│   ├── wechat/              # 微信平台（支持多机器人）
│   │   ├── bot_manager.py   # 机器人管理器
│   │   └── server.py        # FastAPI服务器
│   └── cli/                 # 命令行界面
│
├── shared/                  # 共享工具
│   ├── config.py            # 配置管理（读取YAML）
│   ├── menu_config.py       # 统一菜单配置
│   └── ...
│
└── scripts/                 # 启动脚本
    ├── start_wechat_server.py
    └── start_wechat_server.sh
```

## 🎨 添加新功能

只需在 `shared/menu_config.py` 中添加配置：

```python
BUSINESS_CONFIG = {
    "new_feature": {
        "id": "5",
        "name": "新功能",
        "manager_class": "business.new_feature.manager.NewFeatureManager",
        "service_class": "business.new_feature.service.NewFeatureService",
        "display_name": "新功能管理"
    }
}
```

然后创建对应的 Manager 和 Service，系统会自动识别并使用！

## 📖 详细文档

### 配置与测试
- [企业微信API配置指南](./WECHAT_API_SETUP_GUIDE.md) - 完整的微信配置和测试指南
- [回调验证工具指南](./docs/WECHAT_TEST_GUIDE.md) - minimal_callback_verify.py 使用说明
- [消息收发测试指南](./docs/MINIMAL_TEST_GUIDE.md) - minimal_test_server.py 使用说明

### 架构与开发
- [统一架构说明](./docs/UNIFIED_ARCHITECTURE.md) - 了解系统架构和设计理念
- [数据库接口](./core/database/README.md) - 数据库操作接口文档
- [LLM接口](./core/llm/README.md) - LLM调用接口文档

## 🌈 愿景

打造一个**真正理解你**的智能助手：
- 记住你的每一个重要时刻
- 理解你的情感和需求
- 提供个性化的建议和洞察
- 成为你生活中不可或缺的数字伙伴

---

**开始你的智能助手之旅吧！** 🚀

## 📅 TODO

- [ ] **添加新功能教程**：提供以“健康管理”为示例的二次开发指南（涵盖减肥记录、饮食记录、运动打卡等数据库交互业务）。
- [ ] **在线对话能力**：在 `core` 核心层新增实时对话功能，支持基于上下文的连续交互。
- [ ]  **定时推送业务**：构建定时任务系统，实现如股票走势、天气预报等信息的自动化主动推送。
- [ ] **安全与权限控制**：引入更严格的通信加密机制以及基于角色的访问权限控制（RBAC）。
