# 系统架构文档

## 设计目标

实现**本地测试和线上部署使用完全相同的业务逻辑**，无需修改任何代码即可切换。

> 本文档详细说明系统的技术架构和设计理念。

## 架构设计

### 核心原则

1. **分层架构**：
   - `core` 层：基础能力（database, llm）
   - `business.*.manager` 层：业务逻辑层，使用 core 的基础能力，支持独立测试
   - `business.*.service` 层：适配层，调用 Manager 的业务逻辑，适配微信消息驱动模式
2. **统一配置**：菜单和业务配置在 `shared/menu_config.py` 中统一管理
3. **适配器模式**：CLI 通过 `ServiceAdapter` 使用 Service 层，提供交互式界面

### 架构层次

```
┌─────────────────────────────────────────────────────────┐
│                   统一菜单配置                            │
│              shared/menu_config.py                       │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
┌───────▼────────┐                  ┌───────▼────────┐
│   CLI 模式     │                  │   微信服务器    │
│                │                  │                │
│ ServiceAdapter │                  │  message_router│
│  (交互式适配)   │                  │  (消息驱动)     │
└───────┬────────┘                  └───────┬────────┘
        │                                   │
        └─────────────────┬─────────────────┘
                          │
              ┌───────────▼───────────┐
              │   适配层 (Service)     │
              │  business.*.service  │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │  业务逻辑层 (Manager)   │
              │  business.*.manager  │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   基础能力层 (Core)    │
              │  core.database       │
              │  core.llm            │
              └───────────────────────┘
```

## 工作流程

### 独立测试（Manager层）

1. 运行 `python -m business.accounting.manager --debug`
2. 直接测试 Manager 层的业务逻辑
3. 使用交互式界面，适合开发阶段快速测试

### 本地测试（CLI）

1. 运行 `python -m interfaces.cli.main`
2. CLI 通过 `ServiceAdapter` 调用 `business.*.service`
3. Service 调用 Manager 的业务逻辑
4. `ServiceAdapter` 将 Service 的消息驱动接口转换为交互式界面
5. **使用与线上完全相同的业务逻辑**

### 线上部署（微信服务器）

1. 运行 `python -m interfaces.wechat.server`
2. 微信消息通过 `message_router` 路由到 `business.*.service`
3. Service 调用 Manager 的业务逻辑
4. **使用与本地测试完全相同的业务逻辑**

## 关键文件

### 1. `shared/menu_config.py`
- 统一管理所有业务配置
- 定义业务类型、Manager/Service 类路径
- 提供菜单生成函数

### 2. `interfaces/cli/service_adapter.py`
- CLI 适配器，将 Service 的消息驱动接口转换为交互式接口
- 确保 CLI 使用与微信服务器完全相同的业务逻辑

### 3. `interfaces/cli/main.py`
- CLI 主入口
- 使用 `ServiceAdapter` 调用业务逻辑

### 4. `interfaces/wechat/message_router.py`
- 微信消息路由器
- 动态加载 Service 并处理消息

### 5. `business.*.manager`
- **业务逻辑层**，使用 core 的基础能力
- 支持独立测试（`python -m business.*.manager --debug`）
- 包含完整的业务逻辑实现

### 6. `business.*.service`
- **适配层**，调用 Manager 的业务逻辑
- 适配微信消息驱动模式
- 同时被 CLI 和微信服务器使用

## 添加新业务

只需在 `shared/menu_config.py` 中添加配置：

```python
BUSINESS_CONFIG = {
    # ... 现有业务 ...
    "new_business": {
        "id": "5",
        "name": "新业务",
        "manager_class": "business.new_business.manager.NewBusinessManager",
        "service_class": "business.new_business.service.NewBusinessService",
        "display_name": "新业务管理"
    }
}

MENU_ORDER = [..., "new_business"]
```

然后：
1. 创建 `business/new_business/manager.py`，实现业务逻辑（使用 core 的基础能力）
2. 创建 `business/new_business/service.py`，调用 Manager 的业务逻辑，实现 `process_message()` 方法
3. CLI 和微信服务器会自动识别并使用新业务
4. **支持独立测试**：`python -m business.new_business.manager --debug`

## 优势

✅ **完全统一**：CLI 和微信服务器使用完全相同的业务逻辑  
✅ **零代码修改**：添加新业务只需配置 + 实现 Service  
✅ **本地测试即线上代码**：本地测试的就是线上运行的代码  
✅ **易于维护**：业务逻辑集中在一个地方  

## 使用示例

### 独立测试（开发阶段）
```bash
# 测试记账业务
python -m business.accounting.manager --debug

# 测试塔罗牌业务
python -m business.tarot.manager --debug

# 支持多用户模式
python -m business.accounting.manager --debug --user-id test_user
```

### 本地测试（集成测试）
```bash
python -m interfaces.cli.main
# 选择业务，所有逻辑都在本地执行
```

### 线上部署
```bash
python -m interfaces.wechat.server
# 微信消息自动路由到相同的业务逻辑
```

## 注意事项

1. **业务逻辑在 Manager 层实现**，使用 `core.database` 和 `core.llm` 的基础能力
2. **Service 层调用 Manager 的业务逻辑**，适配微信消息驱动模式
3. **使用统一的菜单配置**，不要硬编码菜单
4. **Service 的 `process_message()` 方法**是核心接口，必须正确实现
5. **支持独立测试**：每个 Manager 都有 `main()` 函数，支持 `--debug` 参数
6. **基础能力从 core 获取**：不要使用 `agent_*` 或 `business_services` 中的组件

