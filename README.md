# Personal Agent Assistant

> "I am JARVIS. I run the house, I keep the schedule, and I execute the mission." - Tony Stark  
> "Amadeus, the AI assistant that understands your heart and memories." - Steins;Gate

一个**智能个人助手系统**，灵感来自钢铁侠的贾维斯（JARVIS）和命运石之门的 Amadeus。通过自然语言交互，帮助你管理生活、记录想法、分析数据，成为你的数字伙伴。

## 🌟 核心理念

### 像贾维斯一样智能
- **自然语言交互**：用日常语言与系统对话，无需记忆复杂命令
- **多任务管理**：同时处理记账、随笔、员工管理、占卜等多种业务
- **智能分析**：自动结构化数据，提供深度分析和洞察
- **无缝集成**：支持微信、CLI等多种接入方式

### 像 Amadeus 一样理解
- **记忆管理**：自动保存和管理你的所有记录，形成个人知识库
- **情感理解**：理解你的随笔情感，提供有温度的回应
- **个性化交互**：根据你的使用习惯，提供个性化的服务体验
- **时间线管理**：记录和分析时间线上的变化和发展

## 🚀 核心功能

### 💰 智能记账管理
- **自然语言记账**：说"今天花了50元买咖啡"，系统自动识别金额、类别、支付方式
- **智能查询**：按日期、类别、金额范围、关键词等多种方式查询
- **AI总结分析**：自动分析你的消费习惯，提供财务洞察
- **统计分析**：支出趋势、分类统计、支付方式分析

### 📝 随笔情感管理
- **自然语言记录**：记录你的想法、感受、日常
- **AI情感分析**：自动分析情感倾向，提供有温度的回应
- **智能查询**：按日期、标签、关键词、心情查询
- **内容总结**：AI帮你总结和回顾重要内容

### 👥 员工工作管理
- **工作记录**：自然语言记录员工工作情况
- **多维度统计**：按员工、时间段、状态、工作态度等维度分析
- **趋势分析**：工作记录趋势，完成度分析
- **智能洞察**：发现工作模式和问题

### 🔮 塔罗牌占卜
- **单张牌占卜**：快速了解当前状况
- **三张牌占卜**：过去-现在-未来的时间线分析
- **五张牌占卜**：全面的洞察和建议
- **AI解读**：温暖、有启发性且带emoji的解读

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
│  - 随笔管理     │                  │  - CLI平台     │
│  - 员工管理     │                  │  - 独立测试     │
│  - 塔罗占卜     │                  │                │
└────────────────┘                  └────────────────┘
```

### 分层设计

- **core/** - 基础能力层：数据库和LLM的统一接口
- **business/** - 业务逻辑层：各业务的核心逻辑（支持独立测试）
- **interfaces/** - 平台接入层：微信和CLI适配
- **shared/** - 共享工具：配置、模型、工具函数

## 🎯 设计原则

1. **智能优先**：自然语言交互，无需学习复杂命令
2. **记忆管理**：自动保存所有交互，形成个人知识库
3. **情感理解**：理解用户意图和情感，提供个性化服务
4. **无缝切换**：本地测试和线上部署使用完全相同的代码
5. **易于扩展**：添加新业务只需配置和实现，无需修改其他代码

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

复制 `env.example` 为 `.env` 并填写配置：

```env
# 微信配置（如使用微信模式）
WECHAT_TOKEN=your_token
WECHAT_ENCODING_AES_KEY=your_key
WECHAT_CORP_ID=your_corp_id
WECHAT_CORP_SECRET=your_secret
WECHAT_AGENT_ID=your_agent_id

# LLM配置（支持OpenAI兼容API）
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# 数据库配置
DATABASE_PATH=./data/assistant.db
USER_DATABASE_DIR=./data/users
```

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
python -m interfaces.cli.main
```
通过命令行界面测试所有功能，与微信模式使用完全相同的业务逻辑。

#### 方式三：独立测试（开发调试）
```bash
# 测试记账功能
python -m business.accounting.manager --debug

# 测试塔罗牌功能
python -m business.tarot.manager --debug
```

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
- **LLM**: OpenAI兼容API（DeepSeek、GPT等）
- **加密**: pycryptodome（微信消息加解密）

## 📚 项目结构

```
Personal-Agent-Assistant/
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
│   ├── wechat/              # 微信平台
│   └── cli/                 # 命令行界面
│
└── shared/                  # 共享工具
    ├── menu_config.py       # 统一菜单配置
    └── ...
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

- [统一架构说明](docs/UNIFIED_ARCHITECTURE.md) - 了解系统架构和设计理念
- [数据库接口](core/database/README.md) - 数据库操作接口文档
- [LLM接口](core/llm/README.md) - LLM调用接口文档
- [部署指南](DEPLOYMENT.md) - 生产环境部署说明
- [回调URL配置](CALLBACK_URL_GUIDE.md) - 微信回调URL配置指南

## 🌈 愿景

打造一个**真正理解你**的智能助手：
- 记住你的每一个重要时刻
- 理解你的情感和需求
- 提供个性化的建议和洞察
- 成为你生活中不可或缺的数字伙伴

就像贾维斯管理托尼的生活，Amadeus理解冈部的情感，这个系统将成为你的智能伙伴。

---

**开始你的智能助手之旅吧！** 🚀
