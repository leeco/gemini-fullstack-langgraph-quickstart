#!/usr/bin/env python3
"""
LangGraph API 测试脚本
使用Python requests库测试各个API接口
"""

import requests
import json
import time
from typing import Dict, Any

# API基础URL
BASE_URL = "http://localhost:8123"

def test_api_health():
    """测试API服务健康状态"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"✅ API服务运行正常 - 状态码: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务，请确保服务正在运行")
        return False

def test_create_assistant():
    """测试创建助手"""
    data = {
        "graph_id": "agent",
        "config": {},
        "name": "Python Test Agent"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/assistants", json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 助手创建成功 - ID: {result.get('assistant_id')}")
            return result.get('assistant_id')
        else:
            print(f"❌ 助手创建失败 - 状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 助手创建异常: {e}")
        return None

def test_search_assistants():
    """测试搜索助手"""
    data = {
        "limit": 10,
        "offset": 0
    }
    
    try:
        response = requests.post(f"{BASE_URL}/assistants/search", json=data)
        if response.status_code == 200:
            results = response.json()
            print(f"✅ 找到 {len(results)} 个助手")
            for assistant in results:
                print(f"  - {assistant.get('name', 'Unnamed')} (ID: {assistant.get('assistant_id')})")
            return results
        else:
            print(f"❌ 搜索助手失败 - 状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 搜索助手异常: {e}")
    return []

def test_create_thread():
    """测试创建线程"""
    data = {
        "metadata": {
            "session_id": "python_test_session",
            "user_id": "test_user"
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/threads", json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 线程创建成功 - ID: {result.get('thread_id')}")
            return result.get('thread_id')
        else:
            print(f"❌ 线程创建失败 - 状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"❌ 线程创建异常: {e}")
    return None

def test_simple_run():
    """测试简单的运行（无状态）"""
    data = {
        "assistant_id": "agent",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "你好，请简单介绍一下自己"
                }
            ]
        }
    }
    
    try:
        print("🔄 发送测试查询...")
        response = requests.post(f"{BASE_URL}/runs/wait", json=data)
        if response.status_code == 200:
            result = response.json()
            print("✅ 查询成功！")
            
            # 提取响应消息
            if "messages" in result:
                for msg in result["messages"]:
                    if msg.get("role") == "assistant":
                        print(f"🤖 助手回复: {msg.get('content', 'No content')[:200]}...")
                        break
            return result
        else:
            print(f"❌ 查询失败 - 状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"❌ 查询异常: {e}")
    return None

def test_knowledge_search():
    """测试知识库搜索（非流式）"""
    data = {
        "assistant_id": "agent",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "违规裁员的类型"
                }
            ]
        }
    }
    
    try:
        print("🔍 测试知识库搜索...")
        response = requests.post(f"{BASE_URL}/runs/wait", json=data)
        if response.status_code == 200:
            result = response.json()
            print("✅ 知识库搜索成功！")
            
            # 检查是否有源信息
            if "sources_gathered" in result:
                sources = result["sources_gathered"]
                print(f"📚 找到 {len(sources)} 个相关源")
                
            return result
        else:
            print(f"❌ 知识库搜索失败 - 状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 知识库搜索异常: {e}")
    return None

def test_knowledge_search_stream():
    """测试知识库搜索（流式输出）"""
    data = {
        "assistant_id": "agent",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "违规裁员的类型有哪些"
                }
            ]
        },
        "stream_mode": ["values"]
    }
    
    try:
        print("🌊 测试知识库搜索（流式输出）...")
        print("📡 开始流式接收数据...")
        
        # 使用流式请求
        response = requests.post(
            f"{BASE_URL}/runs/stream", 
            json=data,
            stream=True,
            headers={'Accept': 'text/event-stream'}
        )
        
        if response.status_code == 200:
            print("✅ 流式连接建立成功！")
            print("-" * 60)
            
            # 解析SSE流
            sources_count = 0
            message_parts = []
            
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    line = line.strip()
                    
                    # 跳过注释行和空行
                    if line.startswith(':') or not line:
                        continue
                    
                    # 解析SSE数据
                    if line.startswith('data: '):
                        try:
                            data_content = line[6:]  # 移除 'data: ' 前缀
                            
                            # 跳过特殊控制消息
                            if data_content in ['[DONE]', '']:
                                continue
                                
                            # 解析JSON数据
                            event_data = json.loads(data_content)
                            
                            # 处理不同类型的事件
                            if isinstance(event_data, list) and len(event_data) > 0:
                                event_data = event_data[0]  # 取第一个元素
                            
                            if isinstance(event_data, dict):
                                # 检查是否包含消息
                                if "messages" in event_data:
                                    messages = event_data["messages"]
                                    for msg in messages:
                                        if msg.get("role") == "assistant":
                                            content = msg.get("content", "")
                                            if content:
                                                print(f"🤖 [流式] {content[:100]}...")
                                                message_parts.append(content)
                                
                                # 检查是否包含源信息
                                if "sources_gathered" in event_data:
                                    sources = event_data["sources_gathered"]
                                    new_sources = len(sources) - sources_count
                                    if new_sources > 0:
                                        print(f"📚 [流式] 新增 {new_sources} 个信息源")
                                        sources_count = len(sources)
                                        for source in sources[-new_sources:]:
                                            if isinstance(source, dict):
                                                title = source.get("title", "未知标题")
                                                url = source.get("url", "无URL")
                                                print(f"   └─ {title} ({url[:50]}...)")
                                
                                # 显示其他有用信息
                                for key in ["search_query", "web_research_result"]:
                                    if key in event_data and event_data[key]:
                                        value = event_data[key]
                                        if isinstance(value, list) and value:
                                            print(f"🔎 [流式] {key}: {str(value[0])[:80]}...")
                                        elif isinstance(value, str):
                                            print(f"🔎 [流式] {key}: {value[:80]}...")
                        
                        except json.JSONDecodeError as e:
                            print(f"⚠️  JSON解析错误: {e}")
                            print(f"   原始数据: {data_content[:100]}...")
                        except Exception as e:
                            print(f"⚠️  数据处理错误: {e}")
            
            print("-" * 60)
            print(f"✅ 流式输出完成！")
            print(f"📊 总计收到 {len(message_parts)} 个消息片段")
            print(f"📚 总计找到 {sources_count} 个信息源")
            return True
            
        else:
            print(f"❌ 流式搜索失败 - 状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 流式搜索异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_stream():
    """简单的流式输出测试 - 模拟实时逐字输出"""
    data = {
        "assistant_id": "agent",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "请简单解释什么是LangGraph"
                }
            ]
        },
        "stream_mode": ["values"]
    }
    
    try:
        print("💫 简单流式输出测试...")
        response = requests.post(
            f"{BASE_URL}/runs/stream", 
            json=data,
            stream=True,
            headers={'Accept': 'text/event-stream'}
        )
        
        if response.status_code == 200:
            print("✅ 连接成功，开始接收流式数据...")
            print("=" * 50)
            
            full_content = ""
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith('data: '):
                    try:
                        data_content = line[6:]
                        if data_content and data_content not in ['[DONE]', '']:
                            event_data = json.loads(data_content)
                            
                            # 处理流式内容
                            if isinstance(event_data, dict):
                                if "messages" in event_data:
                                    messages = event_data["messages"]
                                    for msg in messages:
                                        if msg.get("role") == "assistant" and msg.get("content"):
                                            content = msg.get("content", "")
                                            # 模拟逐字输出效果
                                            if content != full_content:
                                                # 只输出新增的部分
                                                new_content = content[len(full_content):]
                                                if new_content:
                                                    print(new_content, end="", flush=True)
                                                    full_content = content
                            
                    except (json.JSONDecodeError, Exception):
                        continue
            
            print("\n" + "=" * 50)
            print("✅ 流式输出完成！")
            return True
        else:
            print(f"❌ 连接失败 - 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def test_real_stream_output():
    """真正的流式输出测试 - 参考cli_research.py的实现"""
    data = {
        "assistant_id": "agent",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "请详细解释什么是人工智能"
                }
            ]
        },
        "stream_mode": ["updates", "messages", "values"]
    }
    
    try:
        print("🌊 真正的流式输出测试...")
        response = requests.post(
            f"{BASE_URL}/runs/stream", 
            json=data,
            stream=True,
            headers={'Accept': 'text/event-stream'}
        )
        
        if response.status_code == 200:
            print("✅ 流式连接建立成功！")
            print("=" * 60)
            
            current_message = ""
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith('data: '):
                    try:
                        data_content = line[6:]
                        if data_content and data_content not in ['[DONE]', '']:
                            event_data = json.loads(data_content)
                            
                            # 处理不同类型的流式数据
                            if isinstance(event_data, dict):
                                # 处理消息流
                                if "messages" in event_data:
                                    messages = event_data["messages"]
                                    for msg in messages:
                                        if msg.get("role") == "assistant" and msg.get("content"):
                                            content = msg.get("content", "")
                                            # 实现真正的流式输出
                                            if content != current_message:
                                                # 只输出新增内容
                                                new_part = content[len(current_message):]
                                                if new_part:
                                                    print(new_part, end="", flush=True)
                                                    current_message = content
                                
                                # 处理节点更新信息
                                for key in ["search_query", "web_research_result", "sources_gathered"]:
                                    if key in event_data and event_data[key]:
                                        value = event_data[key]
                                        if isinstance(value, list) and value:
                                            print(f"\n🔍 [{key}] {str(value[0])[:100]}...")
                                        elif isinstance(value, str):
                                            print(f"\n🔍 [{key}] {value[:100]}...")
                            
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"\n⚠️ 数据处理错误: {e}")
            
            print("\n" + "=" * 60)
            print("✅ 流式输出完成！")
            return True
            
        else:
            print(f"❌ 流式连接失败 - 状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 流式输出异常: {e}")
        return False

def test_store_operations():
    """测试存储操作"""
    # 存储数据
    store_data = {
        "namespace": ["test", "python"],
        "key": "sample_item",
        "value": {
            "title": "Python API测试",
            "content": "这是通过Python API创建的测试数据",
            "timestamp": time.time()
        }
    }
    
    try:
        # 存储项目
        response = requests.put(f"{BASE_URL}/store/items", json=store_data)
        if response.status_code == 204:
            print("✅ 数据存储成功")
            
            # 搜索项目
            search_data = {
                "namespace_prefix": ["test"],
                "limit": 10
            }
            
            response = requests.post(f"{BASE_URL}/store/items/search", json=search_data)
            if response.status_code == 200:
                results = response.json()
                items = results.get("items", [])
                print(f"✅ 找到 {len(items)} 个存储项目")
                for item in items:
                    print(f"  - {item.get('key')}: {item.get('value', {}).get('title', 'No title')}")
                return True
        else:
            print(f"❌ 存储操作失败 - 状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 存储操作异常: {e}")
    return False

def interactive_menu():
    """交互式测试菜单"""
    while True:
        print("\n🎯 LangGraph API 测试菜单")
        print("=" * 40)
        print("1. 🩺 服务健康检查")
        print("2. 👥 助手管理测试")
        print("3. 🧵 线程管理测试")
        print("4. 💫 简单流式输出演示")
        print("5. 🌊 真正流式输出测试")
        print("6. 📋 非流式知识检索测试")
        print("7. 🌊 详细流式知识检索测试")
        print("8. 💾 存储操作测试")
        print("9. 🚀 运行全部测试")
        print("0. 🚪 退出")
        print("=" * 40)
        
        try:
            choice = input("请选择测试项目 (0-9): ").strip()
            
            if choice == "0":
                print("👋 测试结束！")
                break
            elif choice == "1":
                test_api_health()
            elif choice == "2":
                test_search_assistants()
            elif choice == "3":
                test_create_thread()
            elif choice == "4":
                test_simple_stream()
            elif choice == "5":
                test_real_stream_output()
            elif choice == "6":
                test_knowledge_search()
            elif choice == "7":
                test_knowledge_search_stream()
            elif choice == "8":
                test_store_operations()
            elif choice == "9":
                run_all_tests()
            else:
                print("❌ 无效选择，请输入 0-9 之间的数字")
                
        except KeyboardInterrupt:
            print("\n👋 测试中断！")
            break
        except Exception as e:
            print(f"❌ 输入错误: {e}")

def run_all_tests():
    """运行所有测试"""
    print("🚀 开始完整API测试")
    print("=" * 50)
    
    # 1. 检查服务健康状态
    if not test_api_health():
        return
    
    print("\n1️⃣ 测试助手管理...")
    test_search_assistants()
    
    print("\n2️⃣ 测试线程创建...")
    test_create_thread()
    
    print("\n3️⃣ 测试简单流式输出...")
    test_simple_stream()
    
    print("\n4️⃣ 测试非流式知识检索...")
    test_knowledge_search()
    
    print("\n5️⃣ 测试详细流式知识检索...")
    test_knowledge_search_stream()
    
    print("\n6️⃣ 测试存储操作...")
    test_store_operations()
    
    print("\n" + "=" * 50)
    print("✅ 所有测试完成！")

def main():
    """主函数 - 支持命令行参数"""
    import sys
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        print(f"🚀 运行指定测试: {test_type}")
        
        if test_type in ["stream", "流式"]:
            print("🌊 运行流式测试...")
            if test_api_health():
                test_simple_stream()
                test_knowledge_search_stream()
        elif test_type in ["knowledge", "知识库"]:
            print("🔍 运行知识库测试...")
            if test_api_health():
                test_knowledge_search()
                test_knowledge_search_stream()
        elif test_type in ["all", "全部"]:
            run_all_tests()
        else:
            print(f"❌ 未知测试类型: {test_type}")
            print("支持的类型: stream, knowledge, all")
    else:
        # 交互式菜单
        interactive_menu()

if __name__ == "__main__":
    main() 