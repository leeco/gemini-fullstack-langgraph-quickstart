# LangGraph Stream Mode 控制指南

## 🎛️ Stream Mode 概述

LangGraph 提供了多种 `stream_mode` 选项来控制流式输出的内容和粒度。不同的模式适用于不同的应用场景。

## 📋 Stream Mode 选项详解

### 1. **values** 模式
- **用途**: 返回每个节点执行后的完整状态
- **数据结构**: 完整的图状态对象
- **适用场景**: 需要监控整个图的状态变化

```python
# 返回示例
{
    "messages": [...],
    "search_query": [...],
    "web_research_result": [...],
    "sources_gathered": [...],
    "research_loop_count": 1
}
```

### 2. **updates** 模式
- **用途**: 返回每个节点的输出增量
- **数据结构**: `{节点名: 节点输出}`
- **适用场景**: 需要知道哪个节点产生了什么输出

```python
# 返回示例
{
    "generate_query": {
        "search_query": ["人工智能发展历史", "AI里程碑事件"]
    }
}
```

### 3. **messages** 模式
- **用途**: 返回消息级别的流式更新
- **数据结构**: 消息对象和元数据
- **适用场景**: 实现真正的打字机效果

```python
# 返回示例
("messages", (AIMessageChunk(content="人工智能"), {"langgraph_node": "finalize_answer"}))
```

### 4. **custom** 模式
- **用途**: 返回用户自定义的流式数据
- **数据结构**: 用户定义的任意数据
- **适用场景**: 特殊的流式输出需求

### 5. **debug** 模式
- **用途**: 返回详细的调试信息
- **数据结构**: 包含节点执行状态、时间戳等
- **适用场景**: 开发和调试阶段

## 🔧 在不同客户端中配置 Stream Mode

### 1. **Python LangGraph SDK**

```python
from langgraph_sdk import get_client

client = get_client(url="http://localhost:2024")

# 单一模式
async for chunk in client.runs.stream(
    None,
    "agent", 
    input={"messages": [{"role": "human", "content": "问题"}]},
    stream_mode="values"  # 单一模式
):
    print(chunk.data)

# 多模式组合
async for chunk in client.runs.stream(
    None,
    "agent",
    input={"messages": [{"role": "human", "content": "问题"}]},
    stream_mode=["values", "updates", "messages"]  # 多模式
):
    print(f"Event: {chunk.event}, Data: {chunk.data}")
```

### 2. **直接图调用**

```python
from agent.graph import graph

# 本地图流式调用
for chunk in graph.stream(
    state, 
    stream_mode=["updates", "messages", "custom"]
):
    chunk_type, chunk_data = chunk
    if chunk_type == "updates":
        for node_name, output in chunk_data.items():
            print(f"节点 {node_name}: {output}")
    elif chunk_type == "messages":
        message, metadata = chunk_data
        print(f"消息: {message.content}")
```

### 3. **HTTP API 调用**

```python
import requests

payload = {
    "assistant_id": "agent",
    "input": {"messages": [{"role": "human", "content": "问题"}]},
    "stream_mode": ["values", "updates"]  # 可以组合多种模式
}

response = requests.post(
    "http://localhost:2024/runs/stream",
    json=payload,
    stream=True,
    headers={"Accept": "text/event-stream"}
)
```

## 🎯 不同场景的推荐配置

### **场景1: 打字机效果**
```python
stream_mode = ["messages"]
# 适用于: 聊天界面、实时文本生成
```

### **场景2: 节点执行监控**
```python
stream_mode = ["updates"]
# 适用于: 工作流可视化、进度追踪
```

### **场景3: 完整状态监控**
```python
stream_mode = ["values"]
# 适用于: 状态管理、完整上下文需求
```

### **场景4: 全面监控**
```python
stream_mode = ["values", "updates", "messages"]
# 适用于: 调试、全面监控、复杂UI
```

### **场景5: 开发调试**
```python
stream_mode = ["debug", "updates", "messages"]
# 适用于: 开发阶段、性能分析
```

## 📊 Stream Mode 对比表

| Mode | 粒度 | 实时性 | 数据量 | 适用场景 |
|------|------|--------|--------|----------|
| values | 粗粒度 | 中等 | 大 | 状态监控 |
| updates | 中粒度 | 高 | 中等 | 节点追踪 |
| messages | 细粒度 | 极高 | 小 | 打字机效果 |
| custom | 可变 | 可变 | 可变 | 自定义需求 |
| debug | 详细 | 中等 | 很大 | 开发调试 |

## 🛠️ 实际控制示例

### 控制输出详细程度

```python
# 最少输出 - 只要最终结果
stream_mode = ["values"]

# 中等输出 - 节点级别的变化
stream_mode = ["updates"]

# 详细输出 - 包含消息流
stream_mode = ["values", "messages"]

# 调试输出 - 包含所有信息
stream_mode = ["values", "updates", "messages", "debug"]
```

### 动态控制

```python
# 根据用户设置动态选择
user_preference = "detailed"  # "simple", "normal", "detailed"

mode_map = {
    "simple": ["values"],
    "normal": ["updates"],
    "detailed": ["values", "updates", "messages"]
}

stream_mode = mode_map[user_preference]
```

## 🚀 最佳实践

1. **生产环境**: 使用 `["values", "updates"]` 平衡性能和信息量
2. **开发环境**: 使用 `["values", "updates", "messages", "debug"]` 获取完整信息
3. **用户界面**: 使用 `["messages"]` 实现流畅的打字机效果
4. **监控系统**: 使用 `["updates"]` 追踪节点执行状态
5. **性能考虑**: 避免在高频场景下使用所有模式，会增加网络传输量

## ⚡ 性能影响

- **values**: 中等性能影响，返回完整状态
- **updates**: 较小性能影响，只返回增量
- **messages**: 最小性能影响，但频率最高
- **debug**: 最大性能影响，包含详细调试信息

选择合适的 stream_mode 可以在功能需求和性能之间找到最佳平衡点。 