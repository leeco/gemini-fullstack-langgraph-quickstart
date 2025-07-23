#!/usr/bin/env python3
"""
专门的流式输出测试脚本
参考 cli_research.py 的实现方式
"""

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:8123"

def test_real_time_stream():
    """真正的实时流式输出测试"""
    data = {
        "assistant_id": "agent",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "请详细解释什么是人工智能，包括其定义、发展历史和主要应用领域"
                }
            ]
        },
        "stream_mode": ["updates", "messages", "values"]
    }
    
    try:
        print("🌊 开始真正的流式输出测试...")
        print("📡 建立流式连接...")
        
        response = requests.post(
            f"{BASE_URL}/runs/stream", 
            json=data,
            stream=True,
            headers={'Accept': 'text/event-stream'}
        )
        
        if response.status_code == 200:
            print("✅ 流式连接建立成功！")
            print("=" * 80)
            print("🤖 开始实时输出：")
            print("-" * 80)
            
            current_content = ""
            node_info = {}
            
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith('data: '):
                    try:
                        data_content = line[6:]
                        if data_content and data_content not in ['[DONE]', '']:
                            event_data = json.loads(data_content)
                            
                            # 处理消息流 - 实现真正的逐字输出
                            if isinstance(event_data, dict):
                                if "messages" in event_data:
                                    messages = event_data["messages"]
                                    for msg in messages:
                                        if msg.get("role") == "assistant" and msg.get("content"):
                                            content = msg.get("content", "")
                                            # 只输出新增的内容
                                            if content != current_content:
                                                new_part = content[len(current_content):]
                                                if new_part:
                                                    print(new_part, end="", flush=True)
                                                    current_content = content
                                
                                # 处理节点信息
                                for key in ["search_query", "web_research_result", "sources_gathered"]:
                                    if key in event_data and event_data[key]:
                                        value = event_data[key]
                                        if key not in node_info or str(value) != str(node_info.get(key)):
                                            node_info[key] = value
                                            if isinstance(value, list) and value:
                                                print(f"\n\n🔍 [{key.upper()}] {str(value[0])[:150]}...")
                                            elif isinstance(value, str):
                                                print(f"\n\n🔍 [{key.upper()}] {value[:150]}...")
                            
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"\n⚠️ 数据处理错误: {e}")
            
            print("\n" + "=" * 80)
            print("✅ 流式输出完成！")
            return True
            
        else:
            print(f"❌ 流式连接失败 - 状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 流式输出异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_knowledge_stream():
    """知识库流式搜索测试"""
    data = {
        "assistant_id": "agent",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "违规裁员的类型有哪些？请详细说明"
                }
            ]
        },
        "stream_mode": ["updates", "messages", "values"]
    }
    
    try:
        print("🔍 开始知识库流式搜索测试...")
        print("📡 建立流式连接...")
        
        response = requests.post(
            f"{BASE_URL}/runs/stream", 
            json=data,
            stream=True,
            headers={'Accept': 'text/event-stream'}
        )
        
        if response.status_code == 200:
            print("✅ 流式连接建立成功！")
            print("=" * 80)
            print("🤖 开始实时输出：")
            print("-" * 80)
            
            current_content = ""
            sources_count = 0
            
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith('data: '):
                    try:
                        data_content = line[6:]
                        if data_content and data_content not in ['[DONE]', '']:
                            event_data = json.loads(data_content)
                            
                            if isinstance(event_data, dict):
                                # 处理消息流
                                if "messages" in event_data:
                                    messages = event_data["messages"]
                                    for msg in messages:
                                        if msg.get("role") == "assistant" and msg.get("content"):
                                            content = msg.get("content", "")
                                            if content != current_content:
                                                new_part = content[len(current_content):]
                                                if new_part:
                                                    print(new_part, end="", flush=True)
                                                    current_content = content
                                
                                # 处理源信息
                                if "sources_gathered" in event_data:
                                    sources = event_data["sources_gathered"]
                                    if len(sources) > sources_count:
                                        new_sources = sources[sources_count:]
                                        for source in new_sources:
                                            if isinstance(source, dict):
                                                title = source.get("title", "未知标题")
                                                url = source.get("url", "无URL")
                                                print(f"\n\n📚 发现新信息源: {title}")
                                                print(f"   └─ {url[:100]}...")
                                        sources_count = len(sources)
                            
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"\n⚠️ 数据处理错误: {e}")
            
            print("\n" + "=" * 80)
            print("✅ 知识库流式搜索完成！")
            print(f"📊 总计找到 {sources_count} 个信息源")
            return True
            
        else:
            print(f"❌ 流式连接失败 - 状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 知识库流式搜索异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 LangGraph 流式输出测试")
    print("=" * 50)
    
    # 测试1: 一般流式输出
    print("\n1️⃣ 测试一般流式输出...")
    test_real_time_stream()
    
    print("\n" + "=" * 50)
    
    # 测试2: 知识库流式搜索
    print("\n2️⃣ 测试知识库流式搜索...")
    test_knowledge_stream()
    
    print("\n" + "=" * 50)
    print("✅ 所有流式测试完成！")

if __name__ == "__main__":
    main() 