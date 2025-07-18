# 结构化输出改造说明

## 概述

本次改造将原有的基于DashScope直接调用的方式改为使用 `ChatTongyi + with_structured_output` 方法，实现了更可靠的结构化输出功能。

## 主要改造内容

### 1. 新增Pydantic模型

在 `tools_and_schemas.py` 中新增了以下结构化输出模型：

```python
class WebSearchResult(BaseModel):
    """网络搜索结果的结构化输出"""
    search_content: str = Field(description="搜索得到的内容摘要")
    sources: List[dict] = Field(description="信息来源列表，包含url和标题", default=[])
    key_findings: List[str] = Field(description="关键发现列表", default=[])

class FinalAnswer(BaseModel):
    """最终答案的结构化输出"""
    answer: str = Field(description="基于研究结果的完整答案")
    summary_points: List[str] = Field(description="关键要点列表", default=[])
    confidence_level: int = Field(description="答案可信度评分1-10", ge=1, le=10, default=8)
```

### 2. 更新提示词

在 `prompts.py` 中更新了以下提示词以支持结构化输出：

- `web_searcher_instructions`: 添加了JSON格式要求和关键发现提取
- `answer_instructions`: 添加了结构化输出格式要求，包括关键要点和可信度评分

### 3. 改造节点函数

在 `graph.py` 中改造了所有节点函数：

#### `generate_query` 函数
- 移除了DashScope直接调用
- 使用 `ChatTongyi` + `with_structured_output(SearchQueryList)`
- 简化了错误处理逻辑

#### `web_research` 函数
- 使用 `ChatTongyi` + `with_structured_output(WebSearchResult)`
- 改进了sources格式转换逻辑
- 添加了更好的错误处理

#### `reflection` 函数
- 使用 `ChatTongyi` + `with_structured_output(Reflection)`
- 移除了复杂的JSON解析逻辑
- 简化了函数结构

#### `finalize_answer` 函数
- 使用 `ChatTongyi` + `with_structured_output(FinalAnswer)`
- 添加了关键要点和可信度评分显示
- 改进了最终答案格式

### 4. 依赖项更新

在 `pyproject.toml` 中添加了：
```toml
"langchain-community"
```

## 优势和改进

### 1. 更可靠的结构化输出
- 使用Pydantic模型确保输出格式的一致性
- 自动验证输出数据类型和约束
- 减少了手动JSON解析的错误

### 2. 代码简化
- 移除了复杂的JSON解析逻辑
- 统一了错误处理方式
- 提高了代码可维护性

### 3. 更好的用户体验
- 最终答案包含关键要点总结
- 提供可信度评分
- 更规范的输出格式

### 4. 扩展性
- 易于添加新的结构化输出模型
- 支持复杂的数据验证规则
- 便于后续功能扩展

## 使用方法

### 运行测试
```bash
cd backend
python test_structured_output.py
```

### 环境变量
确保设置了以下环境变量：
```bash
export DASHSCOPE_API_KEY="your_api_key_here"
```

### 示例代码
```python
from langchain_community.chat_models import ChatTongyi
from src.agent.tools_and_schemas import SearchQueryList

# 初始化模型
llm = ChatTongyi(model="qwen-max")
structured_llm = llm.with_structured_output(SearchQueryList)

# 调用结构化输出
result = structured_llm.invoke("生成关于AI发展的搜索查询")
print(result.query)  # 直接访问结构化字段
```

## 注意事项

1. 确保安装了 `langchain-community` 包
2. 需要有效的 `DASHSCOPE_API_KEY`
3. 所有模型调用都已更改为使用通义千问模型
4. 保持了与原有状态管理系统的兼容性

## 向后兼容性

- 保持了原有的状态数据结构
- 节点函数的输入输出接口保持不变
- 现有的配置系统继续有效

这次改造大大提高了系统的稳定性和可维护性，同时为用户提供了更好的结构化输出体验。 