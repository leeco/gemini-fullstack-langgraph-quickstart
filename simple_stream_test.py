#!/usr/bin/env python3
"""
简化的流式输出测试 - 专注于逐字输出效果
"""

from langgraph_sdk import get_client
import asyncio

client = get_client(url="http://localhost:2024")

async def test_stream(question: str, mode: str = "messages"):
    """极简流式测试"""
    print(f"🚀 {mode.upper()} 模式流式检索")
    print(f"❓ 问题: {question}")
    print("-" * 50)
    
    last_content = ""
    
    async for chunk in client.runs.stream(
        None,
        "agent",
        input={"messages": [{"role": "human", "content": question}]},
        stream_mode=mode
    ):
        if chunk.event and chunk.event.startswith("messages") and chunk.data:
            # 处理 messages 模式 - 打字机效果
            # chunk.data 是列表，包含消息对象
            if isinstance(chunk.data, list) and chunk.data and chunk.data[0].get("type") == "ai":
                content = chunk.data[0].get("content", "")
                if content != last_content:
                    new_part = content[len(last_content):]
                    if new_part:
                        print(new_part, end="", flush=True)
                        last_content = content
                        
        elif chunk.event and chunk.event.startswith("custom") and chunk.data:
            # 处理 custom 模式 - 显示自定义数据
            print(f"🔧 Custom: {chunk.data}")

    print(f"\n\n✅ {mode.upper()} 模式完成")

async def main():
    """主函数"""
    print("🎯 极简流式检索测试")
    print("=" * 40)
    
    # 测试问题
    question = "请简要介绍人工智能的发展历史"
    
    print("1️⃣ Messages 模式测试")
    await test_stream(question, "messages")
    
    print("\n" + "=" * 40)
    print("2️⃣ Custom 模式测试")  
    await test_stream(question, "custom")

if __name__ == "__main__":
    asyncio.run(main()) 