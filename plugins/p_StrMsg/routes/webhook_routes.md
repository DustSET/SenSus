
### 1. **必填字段**
- **title**：消息标题，不能为空。
- **source**：消息来源，不能为空。
- **content**：消息内容，不能为空。

### 2. **可选字段**
这些字段在请求中不是必须的，如果没有提供，系统会使用默认值。
- **fixed**：一个标识符，通常用于固定消息的状态。默认值是 `0`。
- **status**：消息的状态，默认值是 `'pending'`，可选的状态例如 `'active'`, `'inactive'`, `'completed'` 等。
- **message_type**：消息类型，默认值是 `'message'`。可以是 `'message'`, `'alert'` 等。
- **priority**：消息的优先级，默认值是 `1`，通常用较小的数字表示较高的优先级。
- **tags**：标签，可以包含与消息相关的多个标签（列表形式），默认值是一个空数组 `[]`。
- **user_id**：与该消息相关的用户ID，默认为 `null`，表示没有指定用户。
- **is_active**：消息是否处于活跃状态，默认值是 `0`（不活跃）。
- **expires_at**：消息的过期时间，系统自动计算并返回，表示该消息的有效期。过期时间默认为三天后。

### 3. **返回数据字段**
- **receiving_time**：消息接收的时间，格式为 `YYYY-MM-DD HH:MM:SS`。
- **current_time**：当前时间，与 `receiving_time` 一致，标记消息处理时的时间。
- **expires_time**：消息的过期时间，格式为 `YYYY-MM-DD HH:MM:SS`，计算为接收消息后三天。
  
### 4. **响应结构**
响应返回的数据结构通常包含以下内容：
- **message**：表示请求成功或失败的提示信息，返回字符串类型。
- **response**：
  - **data**：消息的主要数据，包括 `title`、`source`、`content` 和 `receiving_time`。
  - **optional_fields**：所有可选字段（包括 `fixed`, `status`, `message_type`, `priority`, `tags`, `user_id`, `is_active`, `expires_at`）。
  - **current_time**：消息处理的时间。
  - **expires_time**：计算的过期时间。

### 示例：

假设发起了如下 GET 请求：

```
GET http://host:port/ENT?title=Test%20Message&source=System&content=This%20is%20a%20test&status=active&priority=2
```

服务器返回的响应数据将会包括：

```json
{
  "message": "Webhook received successfully",
  "response": {
    "data": {
      "title": "Test Message",
      "source": "System",
      "content": "This is a test",
      "receiving_time": "2024-12-09 09:00:00"
    },
    "optional_fields": {
      "fixed": 0,
      "status": "active",
      "message_type": "message",
      "priority": 2,
      "tags": [],
      "user_id": null,
      "is_active": 0,
      "expires_at": "2024-12-12 09:00:00"
    },
    "current_time": "2024-12-09 09:00:00",
    "expires_time": "2024-12-12 09:00:00"
  }
}
```

### 说明：
1. **data**：包含消息的标题、来源、内容和接收时间。
2. **optional_fields**：包含所有可选的字段和他们的值（比如状态、优先级、过期时间等）。
3. **current_time**：记录处理请求时的时间。
4. **expires_time**：记录三天后的过期时间。
