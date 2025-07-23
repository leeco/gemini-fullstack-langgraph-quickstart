import sys
import os
from pathlib import Path

# 确保使用本地代码而不是已安装的包
current_dir = Path(__file__).parent
src_dir = current_dir.parent / "src"
sys.path.insert(0, str(src_dir))

import argparse
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
from agent.graph import graph


def main() -> None:
    """Run the research agent from the command line."""
    parser = argparse.ArgumentParser(description="Run the LangGraph research agent")
    parser.add_argument(
        "question", 
        nargs='?',  # 使question参数可选，支持调试模式
        default="2024年3月份发行人有息债务总额?",  # 默认问题，便于调试
        help="Research question (default: 什么是人工智能？)"
    )
    parser.add_argument(
        "--initial-queries",
        type=int,
        default=3,
        help="Number of initial search queries",
    )
    parser.add_argument(
        "--max-loops",
        type=int,
        default=2,
        help="Maximum number of research loops",
    )
    parser.add_argument(
        "--reasoning-model",
        default="qwen-max",
        help="Model for the final answer",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose output",
    )
    args = parser.parse_args()
    
    # 检查并设置API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("⚠️  警告: 未设置 DASHSCOPE_API_KEY 环境变量")
        print("请设置API Key: set DASHSCOPE_API_KEY=your-api-key")
        print("或者创建 .env 文件设置环境变量")
        print("继续使用测试模式...")
        os.environ["DASHSCOPE_API_KEY"] = "test-key-for-debugging"
    
    # Debug模式信息输出
    if args.debug:
        print("🐛 Debug模式已启用")
        print(f"📝 研究问题: {args.question}")
        print(f"🔍 初始查询数: {args.initial_queries}")
        print(f"🔄 最大循环数: {args.max_loops}")
        print(f"🤖 推理模型: {args.reasoning_model}")
        print(f"🔑 API Key: {'已设置' if api_key else '未设置（使用测试模式）'}")
        print("-" * 50)

    state = {
        "messages": [HumanMessage(content=args.question)],
        "initial_search_query_count": args.initial_queries,
        "max_research_loops": args.max_loops,
        "reasoning_model": args.reasoning_model,
    }

    try:
        print(f"🚀 开始研究问题: {args.question}")
        print("-" * 50)
        
        # 使用 stream 方法和 stream_mode="updates" 流式获取每一步的增量更新
        for chunk in graph.stream(state, stream_mode=["updates", "messages", "custom"]):
            # print(chunk)
            chunk_type, chunk_data = chunk
            if chunk_type == "messages":
                node_data, node_meta = chunk_data
                print(node_meta.get("langgraph_node","unknown_node"))
                aimessage:AIMessageChunk  =  node_data
                print(aimessage.content)
            elif chunk_type == "custom":
                print(chunk_data)
            elif chunk_type == "updates":
                # 解析 chunk_data，提取 node_name 和 node_message
                for node_name, node_message in chunk_data.items():
                    print(f"节点名称: {node_name}")
                    print(f"节点消息: {node_message}")
               
                
            # for node_name, node_output in chunk.items():
            #     if node_name == "__start__":
            #         continue
                
            #     # 打印节点名称，表示进入该节点
            #     print(f"\n--- [节点: {node_name}] ---")
                
            #     # 检查是否为 finalize_answer 节点的流式输出
            #     if node_name == 'finalize_answer' and isinstance(node_output, dict) and 'messages' in node_output:
            #         # 实时打印流式答案
            #         message = node_output['messages'][-1]
            #         if isinstance(message, AIMessage):
            #             # 打印 AIMessage 的内容
            #             print(f"{message.content}", end="", flush=True)

        print("\n" + "="*50)
        print("\n📖 研究完成")

    except Exception as e:
        print(f"❌ 发生错误: {e}")
        if args.debug:
            import traceback
            print(f"详细错误信息:\n{traceback.format_exc()}")


if __name__ == "__main__":
    main()
