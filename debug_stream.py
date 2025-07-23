import requests
import json

BASE_URL = "http://localhost:8123"

def debug_stream_structure():
    """调试流式API的实际返回结构"""
    data = {
        "assistant_id": "agent",
        "input": {
            "messages": [
                {"role": "user", "content": "请简单介绍一下人工智能"}
            ]
        },
        "stream_mode": ["updates", "messages", "custom"]
    }

    print("🔍 调试流式API数据结构")
    print("=" * 50)
    
    response = requests.post(
        f"{BASE_URL}/runs/stream",
        json=data,
        stream=True,
        headers={'Accept': 'text/event-stream'}
    )

    event_count = 0
    for line in response.iter_lines(decode_unicode=True):
        if line and line.startswith('data: '):
            try:
                payload = line[6:]
                if payload and payload not in ['[DONE]', '']:
                    event_count += 1
                    event = json.loads(payload)
                    print(f"\n📦 事件 #{event_count}:")
                    print(f"   类型: {type(event)}")
                    print(f"   键: {list(event.keys()) if isinstance(event, dict) else 'N/A'}")
                    print(f"   内容: {str(event)[:200]}...")
                    
                    # 如果是字典，详细分析每个键
                    if isinstance(event, dict):
                        for key, value in event.items():
                            print(f"   └─ {key}: {type(value)} = {str(value)[:100]}...")
                    
            except Exception as e:
                print(f"\n⚠️ 解析异常: {e}")
                print(f"   原始数据: {line}")

    print(f"\n" + "=" * 50)
    print(f"✅ 总共收到 {event_count} 个事件")

if __name__ == "__main__":
    debug_stream_structure() 