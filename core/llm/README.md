# LLM基础功能模块

## 概述

`core/llm` 模块提供统一的大语言模型（LLM）调用接口，封装了与OpenAI兼容API的交互逻辑，包括重试机制、错误处理等功能。

## 核心接口

### LLMClient

LLM客户端类，提供统一的LLM调用接口。

#### 初始化

```python
from core.llm import LLMClient

# 使用默认配置
client = LLMClient()

# 使用自定义配置
client = LLMClient(api_key="your-key", base_url="https://api.example.com")
```

#### 主要方法

##### `structure_text(text: str, prompt_template: str) -> dict`
将文本转换为结构化数据。

**参数**：
- `text` (str): 原始文本
- `prompt_template` (str): 提示词模板，支持format格式（如 `"{text}"`）

**返回**：
```python
{
    "type": "记录类型",
    "fields": {
        # 结构化字段
    },
    "summary": "简要摘要"
}
```

**示例**：
```python
template = "请将以下文本转换为JSON：{text}"
result = client.structure_text("今天花了50元", template)
```

##### `summarize(records: List[dict], summary_type: str = "general", custom_prompt: Optional[str] = None) -> str`
对多条记录进行总结。

**参数**：
- `records` (List[dict]): 记录列表，每个记录应包含 `structured_data` 或 `summary` 字段
- `summary_type` (str): 总结类型
  - `"general"`: 简要总结
  - `"detailed"`: 详细总结
  - `"analysis"`: 分析总结
- `custom_prompt` (str, optional): 自定义提示词模板，支持 `{records_data}` 占位符

**返回**：总结文本

**示例**：
```python
records = [
    {"structured_data": {"summary": "买咖啡"}},
    {"structured_data": {"summary": "买午餐"}}
]
summary = client.summarize(records, summary_type="detailed")
```

##### `analyze(content: str, analysis_type: str = "general", custom_prompt: Optional[str] = None) -> str`
分析内容。

**参数**：
- `content` (str): 要分析的内容
- `analysis_type` (str): 分析类型
  - `"general"`: 一般性分析
  - `"detailed"`: 详细分析
  - `"sentiment"`: 情感分析
  - `"theme"`: 主题分析
- `custom_prompt` (str, optional): 自定义提示词模板，支持 `{content}` 占位符

**返回**：分析结果文本

**示例**：
```python
analysis = client.analyze("今天心情很好", analysis_type="sentiment")
```

##### `chat(messages: List[dict], temperature: float = 0.7, max_tokens: int = 1000) -> str`
通用对话接口。

**参数**：
- `messages` (List[dict]): 消息列表，格式为：
  ```python
  [
      {"role": "system", "content": "你是一个助手"},
      {"role": "user", "content": "你好"}
  ]
  ```
- `temperature` (float): 温度参数（0-2），控制随机性，默认0.7
- `max_tokens` (int): 最大token数，默认1000

**返回**：回复文本

**示例**：
```python
messages = [
    {"role": "system", "content": "你是一个专业的助手"},
    {"role": "user", "content": "请介绍一下Python"}
]
reply = client.chat(messages, temperature=0.5)
```

## 特性

### 自动重试
所有方法都支持自动重试机制（默认3次），在API调用失败时会自动重试。

### 错误处理
- JSON解析失败时返回默认结构
- API错误会记录日志并重试
- 达到最大重试次数后抛出异常或返回默认值

### 日志记录
所有操作都会记录日志，便于调试和监控。

## 使用示例

### 基本使用

```python
from core.llm import LLMClient

client = LLMClient()

# 结构化文本
template = "请将以下记账信息转换为JSON：{text}"
result = client.structure_text("今天花了50元买咖啡", template)
print(result)
# {
#     "type": "记账",
#     "fields": {"amount": 50, "category": "餐饮"},
#     "summary": "买咖啡"
# }

# 总结记录
records = [{"structured_data": {"summary": "买咖啡"}}]
summary = client.summarize(records)
print(summary)

# 分析内容
analysis = client.analyze("今天心情很好", analysis_type="sentiment")
print(analysis)
```

### 自定义提示词

```python
# 使用自定义总结提示词
custom_prompt = """请对以下记账记录进行详细分析：

{records_data}

请重点关注：
1. 支出趋势
2. 消费习惯
3. 优化建议
"""
summary = client.summarize(records, custom_prompt=custom_prompt)
```

## 配置

LLM客户端使用 `shared.config.settings` 中的配置：
- `openai_api_key`: API密钥
- `openai_base_url`: API基础URL

## 注意事项

1. **API限制**：注意API的调用频率限制和token限制
2. **重试机制**：默认重试3次，每次重试间隔递增
3. **JSON解析**：如果LLM返回的JSON包含代码块标记（```json），会自动提取
4. **默认值**：某些方法在失败时会返回默认值，而不是抛出异常

