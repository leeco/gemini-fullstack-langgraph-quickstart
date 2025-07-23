from langgraph_sdk import get_client
import asyncio
import json
import time

client = get_client(url="http://localhost:2024")

class StreamModeDemo:
    """Stream Mode 演示工具"""
    
    def __init__(self):
        self.test_input = {
            "messages": [{
                "role": "human",
                "content": "请简要介绍人工智能的发展历史"
            }]
        }
    
    async def demo_values_mode(self):
        """演示 values 模式 - 完整状态"""
        print("🔍 VALUES 模式演示 - 完整状态监控")
        print("=" * 50)
        print("特点: 返回每个节点执行后的完整图状态")
        print("用途: 状态管理、完整上下文监控\n")
        
        chunk_count = 0
        async for chunk in client.runs.stream(
            None,
            "agent",
            input=self.test_input,
            stream_mode="values"
        ):
            chunk_count += 1
            print(f"📦 状态更新 #{chunk_count}")
            if chunk.data:
                # 显示状态字段摘要
                for key, value in chunk.data.items():
                    if isinstance(value, list):
                        print(f"   {key}: {len(value)} 项")
                    else:
                        print(f"   {key}: {type(value).__name__}")
            print()
        
        print(f"✅ Values模式完成，共 {chunk_count} 次状态更新\n")
    
    async def demo_updates_mode(self):
        """演示 updates 模式 - 节点增量"""
        print("🔧 UPDATES 模式演示 - 节点增量输出")
        print("=" * 50)
        print("特点: 只返回每个节点的新输出")
        print("用途: 节点监控、工作流可视化\n")
        
        chunk_count = 0
        async for chunk in client.runs.stream(
            None,
            "agent", 
            input=self.test_input,
            stream_mode="updates"
        ):
            chunk_count += 1
            if chunk.data:
                print(f"🔄 节点更新 #{chunk_count}")
                for node_name, node_output in chunk.data.items():
                    print(f"   📍 节点: {node_name}")
                    if isinstance(node_output, dict):
                        for key, value in node_output.items():
                            if isinstance(value, list):
                                print(f"      └─ {key}: {len(value)} 项")
                            else:
                                value_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                                print(f"      └─ {key}: {value_str}")
                print()
        
        print(f"✅ Updates模式完成，共 {chunk_count} 次节点更新\n")
    
    async def demo_messages_mode(self):
        """演示 messages 模式 - 消息流"""
        print("💬 MESSAGES 模式演示 - 消息级流式输出")
        print("=" * 50)
        print("特点: 返回消息级别的流式更新，实现打字机效果")
        print("用途: 聊天界面、实时文本生成\n")
        
        chunk_count = 0
        content_buffer = ""
        
        async for chunk in client.runs.stream(
            None,
            "agent",
            input=self.test_input,
            stream_mode="messages"
        ):
            chunk_count += 1
            if chunk.data:
                # 处理AI消息 - chunk.data 是列表，包含消息对象
                if isinstance(chunk.data, list):
                    for msg in chunk.data:
                        if isinstance(msg, dict) and msg.get("type") == "ai":
                            content = msg.get("content", "")
                            if content != content_buffer:
                                new_part = content[len(content_buffer):]
                                if new_part:
                                    print(f"📝 消息增量 #{chunk_count}: {new_part[:50]}...")
                                    content_buffer = content
        
        print(f"\n✅ Messages模式完成，共 {chunk_count} 次消息更新")
        print(f"📄 最终内容长度: {len(content_buffer)} 字符\n")
    
    async def demo_combined_mode(self):
        """演示组合模式 - 多种模式同时使用"""
        print("🎛️ COMBINED 模式演示 - 多模式组合")
        print("=" * 50)
        print("特点: 同时使用多种模式，获得全面信息")
        print("用途: 调试、全面监控、复杂应用\n")
        
        stats = {
            "values": 0,
            "updates": 0, 
            "messages": 0,
            "other": 0
        }
        
        async for chunk in client.runs.stream(
            None,
            "agent",
            input=self.test_input,
            stream_mode=["values", "updates", "messages"]
        ):
            event_type = chunk.event
            
            if event_type == "values":
                stats["values"] += 1
                print(f"📊 [VALUES] 状态更新 #{stats['values']}")
                if chunk.data:
                    keys = list(chunk.data.keys())[:3]  # 只显示前3个字段
                    print(f"      包含字段: {keys}...")
                    
            elif event_type == "updates":
                stats["updates"] += 1
                print(f"🔄 [UPDATES] 节点更新 #{stats['updates']}")
                if chunk.data:
                    node_names = list(chunk.data.keys())
                    print(f"      活跃节点: {node_names}")
                    
            elif event_type == "messages":
                stats["messages"] += 1
                print(f"💬 [MESSAGES] 消息流 #{stats['messages']}")
                
            else:
                stats["other"] += 1
                print(f"⚡ [其他] {event_type} #{stats['other']}")
            
            print()
        
        print("📈 统计信息:")
        for mode, count in stats.items():
            print(f"   {mode}: {count} 次事件")
        print()
    
    async def compare_performance(self):
        """性能对比测试"""
        print("⚡ 性能对比测试")
        print("=" * 50)
        
        modes = [
            ("values", "values"),
            ("updates", "updates"), 
            ("messages", "messages"),
            ("combined", ["values", "updates"])
        ]
        
        for mode_name, mode_config in modes:
            print(f"🧪 测试 {mode_name.upper()} 模式...")
            
            start_time = time.time()
            chunk_count = 0
            data_size = 0
            
            async for chunk in client.runs.stream(
                None,
                "agent",
                input={
                    "messages": [{
                        "role": "human", 
                        "content": "简单测试问题"
                    }]
                },
                stream_mode=mode_config
            ):
                chunk_count += 1
                if chunk.data:
                    data_size += len(str(chunk.data))
            
            elapsed = time.time() - start_time
            
            print(f"   ⏱️  耗时: {elapsed:.2f}s")
            print(f"   📦 事件数: {chunk_count}")
            print(f"   📊 数据量: {data_size} 字符")
            print(f"   🚀 平均速度: {chunk_count/elapsed:.1f} 事件/秒")
            print()
        
        print("✅ 性能测试完成\n")


async def main():
    """主演示函数"""
    print("🎭 LangGraph Stream Mode 演示程序")
    print("=" * 60)
    
    demo = StreamModeDemo()
    
    while True:
        print("📋 选择演示项目:")
        print("1. 🔍 VALUES 模式 - 完整状态")
        print("2. 🔧 UPDATES 模式 - 节点增量")
        print("3. 💬 MESSAGES 模式 - 消息流")
        print("4. 🎛️ COMBINED 模式 - 组合模式")
        print("5. ⚡ 性能对比测试")
        print("6. 🔄 运行全部演示")
        print("0. 🚪 退出")
        
        choice = input("\n请选择 (0-6): ").strip()
        
        if choice == "0":
            print("👋 演示结束！")
            break
        elif choice == "1":
            await demo.demo_values_mode()
        elif choice == "2":
            await demo.demo_updates_mode()
        elif choice == "3":
            await demo.demo_messages_mode()
        elif choice == "4":
            await demo.demo_combined_mode()
        elif choice == "5":
            await demo.compare_performance()
        elif choice == "6":
            await demo.demo_values_mode()
            await demo.demo_updates_mode() 
            await demo.demo_messages_mode()
            await demo.demo_combined_mode()
        else:
            print("❌ 无效选择，请重新输入")
        
        input("\n按回车键继续...")


if __name__ == "__main__":
    asyncio.run(main()) 