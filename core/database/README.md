# 数据库基础功能模块

## 概述

`core/database` 模块提供统一的数据库操作接口，支持两种模式：
- **单数据库模式**：所有数据存储在同一个数据库中
- **多用户数据库模式**：每个用户拥有独立的数据库文件

## 核心接口

### DatabaseManager

数据库管理器基类，提供统一的CRUD操作接口。

#### 主要方法

##### `get_session() -> Session`
获取数据库会话对象。

##### `create_record(original_text, structured_data, record_type, table_name=None, metadata=None) -> StructuredRecord`
创建新记录。

**参数**：
- `original_text` (str): 原始文本
- `structured_data` (dict): 结构化数据字典
- `record_type` (str): 记录类型（如"记账"、"随笔"等）
- `table_name` (str, optional): 表名/目录名
- `metadata` (dict, optional): 额外元数据

**返回**：创建的 `StructuredRecord` 对象

##### `query_records(filters=None, limit=None, offset=None, order_by=None) -> List[StructuredRecord]`
查询记录。

**参数**：
- `filters` (dict, optional): 过滤条件，支持：
  - `record_type`: 记录类型
  - `table_name`: 表名
  - `date_from`: 开始日期 (YYYY-MM-DD)
  - `date_to`: 结束日期 (YYYY-MM-DD)
  - `keyword`: 关键词搜索（在original_text中搜索）
- `limit` (int, optional): 限制返回数量
- `offset` (int, optional): 偏移量
- `order_by` (str, optional): 排序字段，如 `'created_at'` 或 `'-created_at'`（降序）

**返回**：记录列表

##### `get_record(record_id) -> Optional[StructuredRecord]`
根据ID获取单条记录。

##### `update_record(record_id, **kwargs) -> bool`
更新记录。支持更新所有字段。

##### `delete_record(record_id) -> bool`
删除记录。

##### `get_statistics(filters=None) -> dict`
获取统计信息。

**返回**：
```python
{
    'total_count': int,           # 总记录数
    'by_type': {str: int},        # 按类型统计
    'by_table': {str: int},       # 按表统计
    'date_range': {               # 日期范围
        'min': str,               # ISO格式日期
        'max': str
    }
}
```

### UserDatabaseManager

用户数据库管理器（单例），为每个用户创建独立的数据库文件。

#### 主要方法

##### `get_user_db(user_id) -> UserDatabase`
获取用户的数据库实例。

##### `get_user_session(user_id) -> Session`
获取用户的数据库会话。

##### `initialize_user_db(user_id) -> bool`
初始化用户数据库。

##### `close_user_db(user_id)`
关闭指定用户的数据库连接。

##### `close_all()`
关闭所有用户数据库连接。

## 使用示例

### 单数据库模式

```python
from core.database import get_database_manager

# 获取数据库管理器（不使用用户ID）
db = get_database_manager()

# 创建记录
record = db.create_record(
    original_text="今天花了50元买咖啡",
    structured_data={
        "type": "记账",
        "fields": {"amount": 50, "category": "餐饮"},
        "summary": "买咖啡"
    },
    record_type="记账",
    table_name="记账"
)

# 查询记录
records = db.query_records(
    filters={
        "record_type": "记账",
        "date_from": "2024-01-01",
        "date_to": "2024-01-31"
    },
    limit=10
)

# 获取统计信息
stats = db.get_statistics(filters={"record_type": "记账"})
print(f"总记录数: {stats['total_count']}")
```

### 多用户数据库模式

```python
from core.database import get_database_manager

# 获取用户数据库管理器
db = get_database_manager(user_id="user123")

# 创建记录（自动使用用户数据库）
record = db.create_record(
    original_text="今天心情很好",
    structured_data={
        "type": "随笔",
        "fields": {"mood": "开心"},
        "summary": "心情很好"
    },
    record_type="随笔",
    table_name="随笔",
    user_id="user123"  # 必须提供user_id
)

# 查询记录
records = db.query_records(
    filters={"record_type": "随笔"},
    user_id="user123"
)
```

## 注意事项

1. **线程安全**：`UserDatabaseManager` 是线程安全的单例
2. **资源管理**：使用完会话后会自动关闭，但建议使用 `with` 语句或 `try-finally`
3. **用户ID安全**：用户ID会自动清理不安全字符，确保可以作为文件名
4. **数据库路径**：单数据库模式使用 `settings.database_path`，多用户模式使用 `settings.user_database_dir`

