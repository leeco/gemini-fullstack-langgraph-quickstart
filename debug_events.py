from langgraph_sdk import get_client
import asyncio
import json

client = get_client(url="http://localhost:2024")

async def debug_all_events():
    """调试所有事件类型"""
    print("🔍 LangGraph 事件类型调试工具")
    print("=" * 60)
    
    events_seen = set()
    event_count = 0
    
    async for chunk in client.runs.stream(
        None,
        "agent",
        input={"messages": [{"role": "human", "content": "请简要介绍人工智能"}]},
        stream_mode=["values", "updates", "messages", "custom"]
    ):
        event_count += 1
        event_type = chunk.event if chunk.event else "None"
        
        # 记录看到的事件类型
        if event_type not in events_seen:
            events_seen.add(event_type)
            print(f"\n📋 新事件类型发现: '{event_type}'")
            print(f"   数据类型: {type(chunk.data)}")
            if chunk.data:
                data_preview = str(chunk.data)[:150] + "..." if len(str(chunk.data)) > 150 else str(chunk.data)
                print(f"   数据预览: {data_preview}")
        
        # 只显示前10个事件的详细信息
        if event_count <= 10:
            print(f"\n🔄 事件 #{event_count}")
            print(f"   事件类型: '{event_type}'")
            print(f"   有数据: {chunk.data is not None}")
            
            if chunk.data:
                if isinstance(chunk.data, dict):
                    print(f"   字典键: {list(chunk.data.keys())}")
                elif isinstance(chunk.data, list):
                    print(f"   列表长度: {len(chunk.data)}")
                else:
                    print(f"   数据: {str(chunk.data)[:100]}...")
    
    print(f"\n" + "=" * 60)
    print(f"📊 调试总结:")
    print(f"   总事件数: {event_count}")
    print(f"   事件类型数: {len(events_seen)}")
    print(f"   发现的事件类型:")
    for event in sorted(events_seen):
        print(f"      - '{event}'")

if __name__ == "__main__":
    asyncio.run(debug_all_events()) 