# LangGraph API 测试指南

## 基础测试命令

### 1. 检查服务状态
```bash
curl http://localhost:8123/docs
```

### 2. 创建助手
```bash
curl -X POST "http://localhost:8123/assistants" \
  -H "Content-Type: application/json" \
  -d '{
    "graph_id": "agent",
    "config": {},
    "name": "Test Agent"
  }'
```

### 3. 搜索助手
```bash
curl -X POST "http://localhost:8123/assistants/search" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 10,
    "offset": 0
  }'
```

### 4. 创建线程
```bash
curl -X POST "http://localhost:8123/threads" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "session_id": "test_session"
    }
  }'
```

### 5. 运行查询（流式）
```bash
curl -X POST "http://localhost:8123/runs/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [
        {
          "role": "user", 
          "content": "你好，请介绍一下自己"
        }
      ]
    }
  }'
```

### 6. 运行查询（等待结果）
```bash
curl -X POST "http://localhost:8123/runs/wait" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "什么是LangGraph？"
        }
      ]
    }
  }'
```

## 高级测试示例

### 知识库搜索测试
```bash
curl -X POST "http://localhost:8123/runs/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "请搜索关于人工智能的相关信息"
        }
      ]
    },
    "stream_mode": ["values"]
  }'
```

### 获取图结构
```bash
curl "http://localhost:8123/assistants/agent/graph"
```

### 存储数据测试
```bash
curl -X PUT "http://localhost:8123/store/items" \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": ["test"],
    "key": "sample_data",
    "value": {
      "title": "测试数据",
      "content": "这是一个测试数据项"
    }
  }'
```

### 搜索存储数据
```bash
curl -X POST "http://localhost:8123/store/items/search" \
  -H "Content-Type: application/json" \
  -d '{
    "namespace_prefix": ["test"],
    "limit": 10
  }'
```

## 环境变量要求

确保设置了必要的环境变量：
```bash
# 通义千问API密钥
export DASHSCOPE_API_KEY="your_api_key_here"

# Milvus配置（可选）
export MILVUS_URI="your_milvus_uri"
export MILVUS_TOKEN="your_milvus_token"
```

## 常见响应格式

### 成功响应
```json
{
  "messages": [
    {
      "role": "assistant",
      "content": "响应内容"
    }
  ],
  "sources_gathered": []
}
```

### 错误响应
```json
{
  "detail": "错误描述信息"
}
``` 