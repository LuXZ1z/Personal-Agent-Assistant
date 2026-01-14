# 个人助手系统

基于微信API的多Agent个人助手系统，实现自然语言文本的结构化存储和查询总结功能。

## 系统架构

系统采用多Agent架构，通过Redis消息队列实现Agent间通信：

- **Agent 1: 微信接口Agent** - 处理微信HTTP接口和消息加解密
- **Agent 0: 消息路由Agent** - 消息路由和命令解析（规则引擎）
- **Agent 2: 文本结构化Agent** - 调用LLM API将自然语言转换为结构化JSON
- **Agent 3: 数据存储Agent** - 数据库存储操作（纯规则实现）
- **Agent 4: 数据服务Agent** - 数据查询和总结服务（查询用规则，总结用LLM API）

## 设计原则

1. **代码可维护性优先** - 清晰的模块化设计，完善的注释和文档
2. **规则优先，API最小化** - 命令解析、数据库操作用规则实现，只有文本结构化和总结调用LLM API
3. **数据库组织方式** - 支持表/目录概念，用户可以通过命令选择表或目录

## 功能特性

- ✅ 微信消息接收和发送
- ✅ 自然语言文本结构化（LLM API）
- ✅ 结构化数据存储（SQLite）
- ✅ 数据查询（规则引擎）
- ✅ 数据总结（LLM API）
- ✅ 表/目录管理（虚拟目录）
- ✅ 记账业务管理（完整CRUD、时间段查询、统计分析、AI总结）
- ✅ 随笔业务管理（完整CRUD、AI情感分析和内容总结）
- ✅ 员工工作情况管理（完整CRUD、多维度统计分析）

## 技术栈

- **Web框架**: FastAPI
- **数据库**: SQLite (SQLAlchemy ORM)
- **消息队列**: Redis
- **LLM API**: OpenAI GPT-4
- **加密库**: pycryptodome

## 安装和配置

### 1. 创建Conda环境

```bash
conda create -n personal-assistant python=3.11 -y
conda activate personal-assistant
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `env.example` 为 `.env` 并填写配置：

```bash
cp env.example .env
```

编辑 `.env` 文件：

```env
# 微信配置
WECHAT_TOKEN=your_wechat_token_here
WECHAT_ENCODING_AES_KEY=your_encoding_aes_key_here

# OpenAI配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 数据库配置
DATABASE_PATH=./data/assistant.db

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/assistant.log
```

### 4. 启动Redis

确保Redis服务正在运行：

```bash
redis-server
```

## 运行

### 启动所有Agent

```bash
python main.py
```

系统将启动：
- 微信服务器（端口80）
- Agent 0: 消息路由
- Agent 2: 文本结构化
- Agent 3: 数据存储
- Agent 4: 数据服务

### 单独运行Agent（用于调试）

```bash
# Agent 0: 消息路由
python -m agent_router.queue_consumer

# Agent 2: 文本结构化
python -m agent_structurizer.queue_consumer

# Agent 3: 数据存储
python -m agent_storage.queue_consumer

# Agent 4: 数据服务
python -m agent_service.queue_consumer

# 微信服务器
python -m agent_wechat.server
```

## 使用说明

### 1. 发送普通文本

直接发送文本消息，系统会自动：
- 识别文本类型
- 转换为结构化数据
- 存储到数据库

示例：
```
今天花了50元买了一杯咖啡
```

### 2. 查询数据

使用查询命令：

- `查询` - 查询所有记录
- `查询类型：随笔` - 按类型查询
- `查询日期：2024-01-01` - 按日期查询
- `查询关键词：咖啡` - 按关键词查询
- `查询表：随笔目录` - 查询指定表/目录

### 3. 总结数据

使用总结命令：

- `总结` - 总结所有记录
- `总结类型：记账` - 总结指定类型的记录
- `总结日期：2024-01-01 到 2024-01-31` - 总结日期范围内的记录

### 4. 选择表/目录

使用导航命令：

- `进入随笔` - 切换到随笔目录
- `切换到记账` - 切换到记账目录
- `选择员工管理` - 选择员工管理表

## 项目结构

```
Personal-Agent-Assistant/
├── agent_wechat/          # Agent 1: 微信接口Agent
├── agent_router/          # Agent 0: 消息路由Agent
├── agent_structurizer/    # Agent 2: 文本结构化Agent
├── agent_storage/         # Agent 3: 数据存储Agent
├── agent_service/         # Agent 4: 数据服务Agent
├── shared/                # 共享模块
├── data/                  # 数据库文件目录
├── logs/                  # 日志文件目录
├── main.py               # 主程序
├── accounting_manager.py  # 记账业务管理器
├── essay_manager.py      # 随笔业务管理器
├── employee_manager.py   # 员工业务管理器
├── requirements.txt      # Python依赖
└── README.md            # 项目文档
```

## 开发说明

### 代码规范

- 使用 `snake_case` 命名
- 完善的 docstring（Google风格）
- 类型提示（Type Hints）
- 统一的错误处理

### 日志

系统使用 `colorlog` 进行日志记录，支持：
- 控制台输出（带颜色）
- 文件输出（可选）

日志级别：DEBUG, INFO, WARNING, ERROR

### 测试

（待实现）

## 注意事项

1. **微信消息加解密**：完全重新实现，参考示例代码但不直接调用
2. **规则优先原则**：命令解析、数据库操作都用规则实现，只有文本结构化和总结调用LLM API
3. **表/目录概念**：通过`table_name`字段实现虚拟目录
4. **错误处理**：所有Agent都有完善的错误处理和日志记录

## 业务模块

系统现已实现三个独立的业务模块，每个模块都有完整的管理功能：

### 1. 记账业务管理系统

**启动方式：**
```bash
python accounting_manager.py
```

**主要功能：**
- 自然语言记账记录（自动结构化）
- 多种查询方式（日期、时间段、类别、金额范围、关键词）
- 查询结果AI总结
- 统计分析（总支出、分类统计、支付方式统计、支出趋势）
- 表/目录管理

**使用示例：**
- 输入："今天花了50元买了一杯咖啡"
- 系统自动提取：金额、类别、日期、支付方式等信息

### 2. 随笔业务管理系统

**启动方式：**
```bash
python essay_manager.py
```

**主要功能：**
- 自然语言随笔记录（自动结构化）
- 多种查询方式（日期、时间段、标签、关键词、心情）
- **AI分析功能**：记录后自动进行情感分析和内容总结，提供有温度的回应
- 表/目录管理

**使用示例：**
- 输入："今天心情很好，在咖啡厅写下了这些想法..."
- 系统自动提取：内容、日期、标签、心情等信息
- 可选择进行AI分析，获得情感分析和内容总结的综合回应

### 3. 员工工作情况管理系统

**启动方式：**
```bash
python employee_manager.py
```

**主要功能：**
- 自然语言员工工作记录（自动结构化）
- 多种查询方式（员工姓名、日期、时间段、状态、工作态度、工作状态）
- **统计分析功能**：
  - 按员工统计（记录数、任务数、状态分布、工作态度、工作状态、平均完成度）
  - 按时间段统计
  - 按状态、工作态度、工作状态统计
  - 工作记录趋势分析
- 表/目录管理

**使用示例：**
- 输入："今天张三完成了项目文档编写，工作态度积极，完成度90%"
- 系统自动提取：员工姓名、任务、状态、工作态度、完成度等信息

## 业务隔离

每个业务模块都有独立的数据隔离：
- 每个管理器只能访问自己业务类型的表（通过 `record_type` 字段隔离）
- 切换表/目录时只能选择当前业务类型的表
- 确保不同业务之间的数据完全隔离

## 技术实现

各业务模块通过定义不同的`record_type`和扩展`structured_data`的schema来区分：
- 记账：`record_type = "记账"`，字段包括 amount、category、date 等
- 随笔：`record_type = "随笔"`，字段包括 content、title、tags、mood 等
- 员工：`record_type = "员工"`，字段包括 name、task、status、work_attitude 等

## 许可证

（待定）

