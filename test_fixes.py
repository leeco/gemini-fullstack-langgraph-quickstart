#!/usr/bin/env python3
"""
测试修复效果的脚本
"""

from langgraph_sdk import get_client
import asyncio

client = get_client(url="http://localhost:2024")

async def test_message_processing():
    """测试消息处理修复是否正常工作"""
    print("🧪 测试修复效果")
    print("=" * 50)
    print("测试问题: 请简要介绍人工智能")
    print("-" * 50)
    
    chunk_count = 0
    last_content = ""
    
    async for chunk in client.runs.stream(
        None, "agent",
        input={"messages": [{"role": "human", "content": "请简要介绍人工智能"}]},
        stream_mode="messages"
    ):
        chunk_count += 1
        
        # 验证修复：chunk.data应该是列表
        if chunk.event and chunk.event.startswith("messages") and chunk.data:
            
            # 打印调试信息（前5个chunk）
            if chunk_count <= 5:
                print(f"[调试 #{chunk_count}] event: {chunk.event}, data类型: {type(chunk.data)}")
                
            # 验证修复后的处理逻辑
            if isinstance(chunk.data, list) and chunk.data and chunk.data[0].get("type") == "ai":
                content = chunk.data[0].get("content", "")
                if content != last_content:
                    new_part = content[len(last_content):]
                    if new_part:
                        print(new_part, end="", flush=True)
                        last_content = content
            elif isinstance(chunk.data, dict):
                # 如果仍然检测到dict，说明修复不完整
                print(f"\n⚠️  检测到dict格式数据: {chunk.data}")
    
    print(f"\n\n✅ 测试完成")
    print(f"📊 处理了 {chunk_count} 个chunk")
    print(f"📄 最终内容长度: {len(last_content)} 字符")

if __name__ == "__main__":
    asyncio.run(test_message_processing()) 