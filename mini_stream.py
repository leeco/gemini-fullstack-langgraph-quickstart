from langgraph_sdk import get_client
import asyncio
import sys

client = get_client(url="http://localhost:2024")

async def stream_chat(question: str, mode):
    """极简流式对话 - 支持单模式或多模式"""
    mode_display = mode if isinstance(mode, str) else " + ".join(mode)
    print(f"🚀 {mode_display.upper()} 模式")
    print(f"❓ {question}")
    print("-" * 50)
    
    last_content = ""
    
    async for chunk in client.runs.stream(
        None, "agent",
        input={"messages": [{"role": "human", "content": question}]},
        stream_mode=mode
    ):
        # 处理不同的事件类型 - 使用startswith匹配前缀
        if chunk.event and chunk.event.startswith("messages") and chunk.data:
            # Messages 模式 - 打字机效果
            # chunk.data 是列表，包含消息对象
            if isinstance(chunk.data, list) and chunk.data and chunk.data[0].get("type") == "ai":
                content = chunk.data[0].get("content", "")
                if content != last_content:
                    new_part = content[len(last_content):]
                    if new_part:
                        print(new_part, end="", flush=True)
                        last_content = content
                        
        elif chunk.event and chunk.event.startswith("updates") and chunk.data:
            # Updates 模式 - 节点更新
            for node_name, node_output in chunk.data.items():
                print(f"\n🔄 [{node_name}] ", end="")
                if isinstance(node_output, dict):
                    for key, value in node_output.items():
                        if isinstance(value, list) and value:
                            print(f"{key}: {len(value)} 项")
                        elif value:
                            value_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                            print(f"{key}: {value_str}")
                            
        elif chunk.event and chunk.event.startswith("custom") and chunk.data:
            # Custom 模式 - 自定义数据
            print(f"🔧 Custom: {chunk.data}")
            
        elif chunk.event and chunk.event.startswith("values") and chunk.data:
            # Values 模式 - 状态更新
            print(f"📊 状态更新: {list(chunk.data.keys())}")
        
        elif chunk.event and chunk.event == "metadata":
            # Metadata 事件
            print(f"📋 元数据: {chunk.data.get('run_id', 'N/A')[:8]}...")
        
        # 调试：显示未处理的事件类型
        elif chunk.event:
            print(f"\n⚡ [未知事件: {chunk.event}]")

    print(f"\n\n✅ 完成")

async def main():
    # 默认问题和模式
    question = "违规裁员的类型有哪些？"
    mode = ["updates", "messages"]
    await stream_chat(question, mode)

if __name__ == "__main__":
    asyncio.run(main()) 