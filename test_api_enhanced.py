import requests
import json
import time
import asyncio
from typing import Generator, Dict, Any

# 配置 LangGraph Server (根据我们实际的设置)
BASE_URL = "http://localhost:2024"
HEADERS = {"Content-Type": "application/json", "Accept": "text/event-stream"}

class LangGraphAPIClient:
    """LangGraph API 客户端 - 专注于Messages模式"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            response = self.session.get(f"{self.base_url}/")
            return {"status": "success", "data": response.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def list_assistants(self) -> Dict[str, Any]:
        """列出可用的助手"""
        try:
            response = self.session.get(f"{self.base_url}/assistants")
            return {"status": "success", "data": response.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def create_thread(self) -> Dict[str, Any]:
        """创建新线程"""
        try:
            response = self.session.post(f"{self.base_url}/threads", json={})
            return {"status": "success", "data": response.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def run_stream(self, input_data: Dict[str, Any], assistant_id: str = "agent") -> Generator[str, None, None]:
        """流式运行助手 - 仅使用messages模式"""
        payload = {
            "assistant_id": assistant_id,
            "input": input_data,
            "stream_mode": "messages"  # 固定使用messages模式
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/runs/stream",
                json=payload,
                stream=True,
                headers=HEADERS
            )
            
            for line in response.iter_lines(decode_unicode=True):
                if line and line.strip():
                    if line.startswith('data: '):
                        data_content = line[6:]
                        if data_content and data_content not in ['[DONE]', '']:
                            yield data_content
        except Exception as e:
            yield f'{{"error": "{str(e)}"}}'
    
    def run_simple(self, input_data: Dict[str, Any], assistant_id: str = "agent") -> Dict[str, Any]:
        """简单非流式运行"""
        payload = {
            "assistant_id": assistant_id,
            "input": input_data
        }
        
        try:
            response = self.session.post(f"{self.base_url}/runs/wait", json=payload)
            return {"status": "success", "data": response.json()}
        except Exception as e:
            return {"status": "error", "message": str(e)}


def test_basic_functionality():
    """测试基本功能"""
    print("🔧 测试基本API功能")
    print("=" * 50)
    
    client = LangGraphAPIClient()
    
    # 1. 健康检查
    print("1. 🩺 健康检查...")
    health = client.health_check()
    print(f"   结果: {health['status']}")
    
    # 2. 列出助手
    print("\n2. 👥 列出助手...")
    assistants = client.list_assistants()
    if assistants['status'] == 'success':
        print(f"   助手列表: {list(assistants['data'].keys())}")
    else:
        print(f"   错误: {assistants['message']}")
    
    # 3. 创建线程
    print("\n3. 🧵 创建线程...")
    thread = client.create_thread()
    print(f"   结果: {thread['status']}")
    if thread['status'] == 'success':
        print(f"   线程ID: {thread['data'].get('thread_id', 'N/A')}")


def test_streaming_chat():
    """测试流式对话 - Messages模式"""
    print("\n🌊 测试Messages模式流式对话")
    print("=" * 50)
    print("专注于消息级流式输出，实现打字机效果\n")
    
    client = LangGraphAPIClient()
    
    # 测试用例
    test_cases = [
        {
            "name": "简单问题",
            "input": {
                "messages": [{
                    "role": "human",
                    "content": "你好，请介绍一下自己"
                }]
            }
        },
        {
            "name": "知识检索",
            "input": {
                "messages": [{
                    "role": "human", 
                    "content": "请简要介绍人工智能的发展历史"
                }]
            }
        },
        {
            "name": "复杂查询",
            "input": {
                "messages": [{
                    "role": "human",
                    "content": "分析深度学习在计算机视觉领域的应用和发展趋势"
                }]
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. 🧪 测试: {test_case['name']}")
        print("-" * 30)
        
        message_count = 0
        start_time = time.time()
        last_content = ""
        
        for chunk_data in client.run_stream(test_case['input']):
            try:
                chunk = json.loads(chunk_data)
                
                # 处理messages模式的数据
                if isinstance(chunk, dict):
                    if chunk.get("type") == "ai":
                        content = chunk.get("content", "")
                        if content and content != last_content:
                            new_part = content[len(last_content):]
                            if new_part:
                                message_count += 1
                                if message_count == 1:
                                    print(f"   🤖 AI开始回答...")
                                print(f"   📝 消息片段 #{message_count}: {new_part[:50]}...")
                                last_content = content
                
                elif isinstance(chunk, list):
                    for msg in chunk:
                        if isinstance(msg, dict) and msg.get("type") == "ai":
                            content = msg.get("content", "")
                            if content and content != last_content:
                                new_part = content[len(last_content):]
                                if new_part:
                                    message_count += 1
                                    if message_count == 1:
                                        print(f"   🤖 AI开始回答...")
                                    print(f"   📝 消息片段 #{message_count}: {new_part[:50]}...")
                                    last_content = content
                
            except json.JSONDecodeError:
                print(f"   ⚠️  无法解析的数据块: {chunk_data[:50]}...")
        
        elapsed = time.time() - start_time
        print(f"   📊 统计: {message_count} 个消息片段, 耗时 {elapsed:.2f}s")
        print(f"   📄 最终内容长度: {len(last_content)} 字符")
        
        # 暂停一下再进行下一个测试
        time.sleep(2)


def test_non_streaming():
    """测试非流式API"""
    print("\n🎯 测试非流式API")
    print("=" * 50)
    
    client = LangGraphAPIClient()
    
    input_data = {
        "messages": [{
            "role": "human",
            "content": "什么是机器学习？请简要回答。"
        }]
    }
    
    print("📤 发送请求...")
    start_time = time.time()
    
    result = client.run_simple(input_data)
    
    elapsed = time.time() - start_time
    
    if result['status'] == 'success':
        data = result['data']
        print(f"✅ 请求成功，耗时 {elapsed:.2f}s")
        
        # 显示结果摘要
        if 'messages' in data:
            for msg in data['messages']:
                if msg.get('type') == 'ai':
                    content = msg.get('content', '')[:200]
                    print(f"🤖 回答: {content}...")
    else:
        print(f"❌ 请求失败: {result['message']}")


def test_typewriter_demo():
    """打字机效果演示"""
    print("\n⌨️ 打字机效果演示")
    print("=" * 50)
    print("展示Messages模式的真实打字机效果\n")
    
    client = LangGraphAPIClient()
    
    test_input = {
        "messages": [{
            "role": "human",
            "content": "请简要介绍人工智能的发展历史"
        }]
    }
    
    print("🤖 AI助手正在回答...\n")
    
    last_content = ""
    message_count = 0
    start_time = time.time()
    
    for chunk_data in client.run_stream(test_input):
        try:
            chunk = json.loads(chunk_data)
            
            # 处理AI消息并实现打字机效果
            if isinstance(chunk, dict) and chunk.get("type") == "ai":
                content = chunk.get("content", "")
                if content and content != last_content:
                    new_part = content[len(last_content):]
                    if new_part:
                        message_count += 1
                        # 模拟打字机效果
                        for char in new_part:
                            print(char, end="", flush=True)
                            time.sleep(0.01)  # 打字间隔
                        last_content = content
            
            elif isinstance(chunk, list):
                for msg in chunk:
                    if isinstance(msg, dict) and msg.get("type") == "ai":
                        content = msg.get("content", "")
                        if content and content != last_content:
                            new_part = content[len(last_content):]
                            if new_part:
                                message_count += 1
                                for char in new_part:
                                    print(char, end="", flush=True)
                                    time.sleep(0.01)
                                last_content = content
                                
        except json.JSONDecodeError:
            continue
    
    elapsed = time.time() - start_time
    print(f"\n\n📊 统计: {message_count} 个消息更新, 耗时 {elapsed:.2f}s")
    print(f"📝 最终回答长度: {len(last_content)} 字符")


def interactive_mode():
    """交互模式 - Messages流式对话"""
    print("\n💬 进入Messages模式交互对话")
    print("=" * 50)
    print("专注于消息级流式输出，命令: 'quit' 退出, 'stream' 切换流式模式")
    
    client = LangGraphAPIClient()
    use_streaming = True
    
    while True:
        try:
            user_input = input("\n👤 用户: ").strip()
            
            if user_input.lower() == 'quit':
                print("👋 再见！")
                break
            elif user_input.lower() == 'stream':
                use_streaming = not use_streaming
                mode = "Messages流式" if use_streaming else "非流式"
                print(f"🔄 已切换到{mode}模式")
                continue
            elif not user_input:
                continue
            
            input_data = {
                "messages": [{
                    "role": "human",
                    "content": user_input
                }]
            }
            
            if use_streaming:
                print("🤖 助手 (Messages流式):")
                last_content = ""
                
                for chunk_data in client.run_stream(input_data):
                    try:
                        chunk = json.loads(chunk_data)
                        
                        # 处理AI消息
                        if isinstance(chunk, dict) and chunk.get("type") == "ai":
                            content = chunk.get("content", "")
                            if content and content != last_content:
                                new_part = content[len(last_content):]
                                if new_part:
                                    print(new_part, end="", flush=True)
                                    last_content = content
                                    
                        elif isinstance(chunk, list):
                            for msg in chunk:
                                if isinstance(msg, dict) and msg.get("type") == "ai":
                                    content = msg.get("content", "")
                                    if content and content != last_content:
                                        new_part = content[len(last_content):]
                                        if new_part:
                                            print(new_part, end="", flush=True)
                                            last_content = content
                    except:
                        continue
                        
                print()  # 换行
            else:
                result = client.run_simple(input_data)
                if result['status'] == 'success':
                    data = result['data']
                    for msg in data.get('messages', []):
                        if msg.get('type') == 'ai':
                            print(f"🤖 助手: {msg.get('content', '')}")
                            break
                else:
                    print(f"❌ 错误: {result['message']}")
                    
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")


def main():
    """主函数"""
    print("🚀 LangGraph Messages模式 API测试工具")
    print("=" * 60)
    print("专注于消息级流式输出，实现最佳打字机效果")
    
    while True:
        print("\n📋 选择测试项目:")
        print("1. 🔧 基本功能测试")
        print("2. 🌊 Messages流式对话测试") 
        print("3. 🎯 非流式API测试")
        print("4. ⌨️ 打字机效果演示")
        print("5. 💬 交互模式")
        print("6. 🔄 运行全部测试")
        print("0. 🚪 退出")
        
        choice = input("\n请选择 (0-6): ").strip()
        
        if choice == "0":
            print("👋 测试结束！")
            break
        elif choice == "1":
            test_basic_functionality()
        elif choice == "2":
            test_streaming_chat()
        elif choice == "3":
            test_non_streaming()
        elif choice == "4":
            test_typewriter_demo()
        elif choice == "5":
            interactive_mode()
        elif choice == "6":
            test_basic_functionality()
            test_streaming_chat()
            test_non_streaming()
            test_typewriter_demo()
        else:
            print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    main() 