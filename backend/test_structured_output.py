#!/usr/bin/env python3
"""
测试结构化输出功能的示例脚本
演示如何使用新的Pydantic模型和ChatTongyi进行结构化输出
"""

import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from src.agent.tools_and_schemas import SearchQueryList, Reflection, WebSearchResult, FinalAnswer

# 加载环境变量
load_dotenv()


def test_search_query_generation():
    """测试搜索查询生成的结构化输出"""
    print("=== 测试搜索查询生成 ===")
    
    try:
        llm = ChatTongyi(model="qwen-max")
        structured_llm = llm.with_structured_output(SearchQueryList)
        
        prompt = """您的目标是生成精准且多样化的网络搜索查询。

指令：
- 优先使用单个搜索查询，只有当原始问题涉及多个方面或要素且一个查询不足以涵盖时才添加另一个查询。
- 每个查询应聚焦于原始问题的一个具体方面。
- 不要生成超过 3 个查询。

格式：
- 将您的回复格式化为包含以下两个确切键的JSON对象：
   - "rationale": 简要解释为什么这些查询相关
   - "query": 搜索查询列表

上下文：2024年人工智能发展趋势"""

        result: SearchQueryList = structured_llm.invoke(prompt)
        print(f"查询理由: {result.rationale}")
        print(f"生成的查询: {result.query}")
        print("✓ 搜索查询生成测试成功")
        
    except Exception as e:
        print(f"✗ 搜索查询生成测试失败: {e}")


def test_web_search_result():
    """测试网络搜索结果的结构化输出"""
    print("\n=== 测试网络搜索结果 ===")
    
    try:
        llm = ChatTongyi(model="qwen-max")
        structured_llm = llm.with_structured_output(WebSearchResult)
        
        prompt = """进行有针对性的网络搜索，收集关于"人工智能在医疗领域的应用"的最新、可信信息。

指令：
- 整合关键发现，同时仔细跟踪每个具体信息的来源。
- 输出应该是基于搜索发现的结构良好的摘要或报告。
- 提取3-5个关键发现点

格式：
- 将您的回复格式化为包含以下键的JSON对象：
   - "search_content": 基于搜索发现的结构良好的摘要或报告
   - "sources": 信息来源列表，每个源包含url和title字段（如果无法获取真实源，可以为空列表）
   - "key_findings": 从搜索内容中提取的3-5个关键发现点列表"""

        result: WebSearchResult = structured_llm.invoke(prompt)
        print(f"搜索内容: {result.search_content[:200]}...")
        print(f"信息源数量: {len(result.sources)}")
        print(f"关键发现: {result.key_findings}")
        print("✓ 网络搜索结果测试成功")
        
    except Exception as e:
        print(f"✗ 网络搜索结果测试失败: {e}")


def test_reflection():
    """测试反思功能的结构化输出"""
    print("\n=== 测试反思功能 ===")
    
    try:
        llm = ChatTongyi(model="qwen-max")
        structured_llm = llm.with_structured_output(Reflection)
        
        prompt = """您是分析关于"人工智能发展趋势"的摘要的专家研究助理。

指令：
- 识别知识差距或需要深入探索的领域，并生成后续查询（1个或多个）。
- 如果提供的摘要足以回答用户的问题，则不生成后续查询。

输出格式：
- 将响应格式化为包含以下确切键的JSON对象：
   - "is_sufficient": true 或 false
   - "knowledge_gap": 描述缺少的信息或需要澄清的内容
   - "follow_up_queries": 编写一个特定问题以解决此差距

摘要：
人工智能在2024年取得了显著进展，特别是在大语言模型领域。GPT-4和Claude等模型展现了强大的能力。"""

        result: Reflection = structured_llm.invoke(prompt)
        print(f"信息是否充足: {result.is_sufficient}")
        print(f"知识差距: {result.knowledge_gap}")
        print(f"后续查询: {result.follow_up_queries}")
        print("✓ 反思功能测试成功")
        
    except Exception as e:
        print(f"✗ 反思功能测试失败: {e}")


def test_final_answer():
    """测试最终答案的结构化输出"""
    print("\n=== 测试最终答案 ===")
    
    try:
        llm = ChatTongyi(model="qwen-max")
        structured_llm = llm.with_structured_output(FinalAnswer)
        
        prompt = """基于提供的摘要为用户的问题生成高质量的答案。

指令：
- 基于提供的摘要和用户的问题，生成高质量的答案。
- 提供3-5个关键要点总结
- 对答案的可信度进行1-10评分

格式：
- 将您的回复格式化为包含以下键的JSON对象：
   - "answer": 基于研究结果的完整答案，包含适当的引用
   - "summary_points": 3-5个关键要点的列表
   - "confidence_level": 基于可用信息质量的可信度评分(1-10)

用户问题：人工智能的发展趋势如何？

摘要：
人工智能在2024年展现了前所未有的发展速度，大语言模型技术日趋成熟，多模态AI成为新的研究热点。"""

        result: FinalAnswer = structured_llm.invoke(prompt)
        print(f"答案: {result.answer[:200]}...")
        print(f"关键要点: {result.summary_points}")
        print(f"可信度评分: {result.confidence_level}/10")
        print("✓ 最终答案测试成功")
        
    except Exception as e:
        print(f"✗ 最终答案测试失败: {e}")


if __name__ == "__main__":
    print("开始测试结构化输出功能...\n")
    
    # 检查环境变量
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("错误: 请设置 DASHSCOPE_API_KEY 环境变量")
        exit(1)
    
    # 运行所有测试
    test_search_query_generation()
    test_web_search_result() 
    test_reflection()
    test_final_answer()
    
    print("\n测试完成！") 