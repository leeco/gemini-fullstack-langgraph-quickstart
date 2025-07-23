#!/usr/bin/env python3
"""
LangGraph 可视化调试工具
"""

import sys
from pathlib import Path

# 添加backend/src到Python路径
backend_src = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

def visualize_graph():
    """可视化图结构"""
    try:
        from agent.graph import graph
        
        print("🎨 生成图可视化...")
        
        # 尝试生成图的可视化
        try:
            # 如果安装了graphviz，可以生成图形
            image_data = graph.get_graph().draw_mermaid()
            
            # 保存为文件
            with open("graph_structure.mmd", "w", encoding="utf-8") as f:
                f.write(image_data)
            
            print("✅ 图结构已保存为 'graph_structure.mmd'")
            print("   可以在 https://mermaid.live/ 中查看可视化")
            
        except Exception as e:
            print(f"⚠️  无法生成图形可视化: {e}")
            
            # 回退到文本描述
            print("\n📋 图结构 (文本描述):")
            print("=" * 50)
            
            # 获取图信息
            nodes = list(graph.get_graph().nodes.keys())
            edges = graph.get_graph().edges
            
            print(f"节点数量: {len(nodes)}")
            print(f"边数量: {len(edges)}")
            
            print("\n🔗 节点列表:")
            for i, node in enumerate(nodes, 1):
                print(f"  {i}. {node}")
            
            print("\n🔗 边连接:")
            for edge in edges:
                print(f"  {edge}")
                
    except Exception as e:
        print(f"❌ 无法加载图: {e}")

def create_execution_flow_diagram():
    """创建执行流程图"""
    flow_diagram = """
    # LangGraph 执行流程

    ```mermaid
    graph TD
        START([开始]) --> generate_query[生成查询]
        generate_query --> web_research[网络研究]
        web_research --> reflection{反思评估}
        reflection -->|需要更多信息| web_research
        reflection -->|信息充足| finalize_answer[生成最终答案]
        finalize_answer --> END([结束])
        
        style START fill:#e1f5fe
        style END fill:#e8f5e8
        style generate_query fill:#fff3e0
        style web_research fill:#f3e5f5
        style reflection fill:#fff8e1
        style finalize_answer fill:#e0f2f1
    ```

    ## 节点说明

    ### 1. generate_query
    - **功能**: 根据用户问题生成搜索查询
    - **输入**: 用户消息
    - **输出**: 搜索查询列表
    - **调试要点**: 查看生成的查询是否合适

    ### 2. web_research
    - **功能**: 执行网络搜索并收集结果
    - **输入**: 搜索查询
    - **输出**: 搜索结果和资源
    - **调试要点**: 检查搜索结果质量和数量

    ### 3. reflection
    - **功能**: 评估当前研究进度
    - **输入**: 当前状态
    - **输出**: 下一步决策 (继续研究/生成答案)
    - **调试要点**: 确认决策逻辑是否正确

    ### 4. finalize_answer
    - **功能**: 基于收集的信息生成最终答案
    - **输入**: 所有研究结果
    - **输出**: 格式化的最终答案
    - **调试要点**: 检查答案质量和引用

    ## 状态变量

    - `messages`: 对话消息历史
    - `search_query`: 当前搜索查询
    - `web_research_result`: 搜索结果
    - `sources_gathered`: 收集的资源
    - `research_loop_count`: 研究轮次计数
    """
    
    with open("execution_flow.md", "w", encoding="utf-8") as f:
        f.write(flow_diagram)
    
    print("📊 执行流程图已保存为 'execution_flow.md'")

if __name__ == "__main__":
    print("🎨 LangGraph 可视化工具")
    print("=" * 50)
    
    # 可视化图结构
    visualize_graph()
    
    # 创建流程图
    create_execution_flow_diagram()
    
    print("\n📝 生成的文件:")
    print("- graph_structure.mmd (图结构)")
    print("- execution_flow.md (执行流程)")
    print("\n💡 提示: 可以在 mermaid.live 查看图形化效果") 