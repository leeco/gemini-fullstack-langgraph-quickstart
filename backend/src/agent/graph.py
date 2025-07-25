import os

from agent.tools_and_schemas import SearchQueryList, Reflection, SearchResult, FinalAnswer
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.types import Send
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langchain_core.runnables import RunnableConfig
from langchain_community.chat_models import ChatTongyi
from agent.search_adapter import search_kb_sync
from langgraph.config import get_stream_writer
import json

from agent.state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    SearchState,
)
from agent.configuration import Configuration
from agent.prompts import (
    get_current_date,
    query_writer_instructions,
    web_searcher_instructions,
    reflection_instructions,
    answer_instructions,
)

from agent.utils import (
    get_citations,
    get_research_topic,
    insert_citation_markers,
    resolve_urls,
)


# Nodes
def generate_query(state: OverallState, config: RunnableConfig) -> QueryGenerationState:
    """LangGraph node that generates search queries based on the User's question.

    Uses ChatTongyi with structured output to create optimized search queries for web research.

    Args:
        state: Current graph state containing the User's question
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated queries
    """
    configurable = Configuration.from_runnable_config(config)
    writer = get_stream_writer()
    # check for custom initial search query count
    if state.get("initial_search_query_count") is None:
        state["initial_search_query_count"] = configurable.number_of_initial_queries

    try:
        # 初始化ChatTongyi模型
        llm = ChatTongyi(model=configurable.query_generator_model)
        
        # 创建结构化LLM
        structured_llm = llm.with_structured_output(SearchQueryList)
        
        research_topic =get_research_topic(state["messages"])
        # Format the prompt
        current_date = get_current_date()
        formatted_prompt = query_writer_instructions.format(
            current_date=current_date,
            research_topic = research_topic,
            number_queries=state["initial_search_query_count"],
        )
        
        # 调用结构化输出
        result: SearchQueryList = structured_llm.invoke(formatted_prompt)
        writer({"langgraph_node": "generate_query", "message": f"{research_topic}生成查询：{result.query}"})
        return {"search_query": result.query}
        
    except Exception as e:
        print(f"在生成查询过程中发生错误: {e}")
        # Fallback: create a simple query from the topic
        return {"search_query": [get_research_topic(state["messages"])]}


def continue_to_web_research(state: QueryGenerationState):
    """LangGraph node that sends the search queries to the web research node.

    This is used to spawn n number of web research nodes, one for each search query.
    """
    return [
        Send("web_research", {"search_query": search_query, "id": int(idx)})
        for idx, search_query in enumerate(state["search_query"])
    ]



def doc_research(state: SearchState, config: RunnableConfig) -> OverallState:
    """LangGraph节点：知识库文档检索（同步版本）"""
    try:
        writer = get_stream_writer()
        # 使用完全同步的接口
        from agent.search_adapter import search_kb_sync
        result: SearchResult = search_kb_sync(state["search_query"], 10, use_ai=False)
        writer({"langgraph_node": "doc_research", "message": f"知识库检索结果：{result.search_content}"})
        # 转换sources格式
        sources_gathered = []
        for source in result.sources:
            sources_gathered.append({
                "url": source.get("url", ""),
                "title": source.get("title", ""),
                "short_url": source.get("url", ""),
                "value": source.get("url", "")
            })

        return {
            "sources_gathered": sources_gathered,
            "search_query": [state["search_query"]],
            "research_result": [result.search_content],
        }
    except Exception as e:
        print(f"知识库检索失败: {e}")
        return {
            "sources_gathered": [],
            "search_query": [state["search_query"]],
            "research_result": [f"知识库检索失败: {str(e)}"],
        }


def web_research(state: SearchState, config: RunnableConfig) -> OverallState:
    """LangGraph node that performs web research using ChatTongyi with structured output.

    Executes web research using ChatTongyi model with structured output format.

    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable, including search API settings

    Returns:
        Dictionary with state update, including sources_gathered, research_loop_count, and research_results
    """
    configurable = Configuration.from_runnable_config(config)
    writer = get_stream_writer()
    try:
        # 初始化ChatTongyi模型
        llm = ChatTongyi(model=configurable.query_generator_model)
        
        # 创建结构化LLM
        structured_llm = llm.with_structured_output(SearchResult)
        
        formatted_prompt = web_searcher_instructions.format(
            current_date=get_current_date(),
            research_topic=state["search_query"],
        )

        # 调用结构化输出
        result: SearchResult = structured_llm.invoke(formatted_prompt)
        writer({"langgraph_node": "web_research", "message": f"网络检索结果：{result.search_content}"})
        # 转换sources格式以匹配现有的数据结构
        sources_gathered = []
        for source in result.sources:
            sources_gathered.append({
                "url": source.get("url", ""),
                "title": source.get("title", ""),
                "short_url": source.get("url", ""),
                "value": source.get("url", "")
            })

        return {
            "sources_gathered": sources_gathered,
            "search_query": [state["search_query"]],
            "research_result": [result.search_content],
        }
        
    except Exception as e:
        print(f"在网络研究过程中发生错误: {e}")
        # Fallback response
        return {
            "sources_gathered": [],
            "search_query": [state["search_query"]],
            "research_result": [f"搜索查询: {state['search_query']} 的结果暂时无法获取。"],
        }


def reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    """LangGraph node that identifies knowledge gaps and generates potential follow-up queries.

    Analyzes the current summary to identify areas for further research and generates
    potential follow-up queries using ChatTongyi with structured output.

    Args:
        state: Current graph state containing the running summary and research topic
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated follow-up query
    """
    configurable = Configuration.from_runnable_config(config)   
    writer = get_stream_writer()
    # Increment the research loop count and get the reasoning model
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1
    reasoning_model = state.get("reasoning_model", configurable.reflection_model)

    try:
        # 初始化ChatTongyi模型
        llm = ChatTongyi(model=reasoning_model)
        
        # 创建结构化LLM
        structured_llm = llm.with_structured_output(Reflection)
        
        # Format the prompt
        current_date = get_current_date()
        formatted_prompt = reflection_instructions.format(
            current_date=current_date,
            research_topic=get_research_topic(state["messages"]),
            summaries="\n\n---\n\n".join(state["research_result"]),
        )
        
        # 调用结构化输出
        result: Reflection = structured_llm.invoke(formatted_prompt)
      
        reflection_output = {
            "is_sufficient": result.is_sufficient,
            "knowledge_gap": result.knowledge_gap,
            "follow_up_queries": result.follow_up_queries,
        }
        writer({
            "langgraph_node": "reflection",
            "message": json.dumps(reflection_output, ensure_ascii=False)
        })

        return {
            "is_sufficient": result.is_sufficient,
            "knowledge_gap": result.knowledge_gap,
            "follow_up_queries": result.follow_up_queries,
            "research_loop_count": state["research_loop_count"],
            "number_of_ran_queries": len(state["search_query"]),
        }
        
    except Exception as e:
        print(f"在反思过程中发生错误: {e}")
        # Fallback values
        return {
            "is_sufficient": True,
            "knowledge_gap": "",
            "follow_up_queries": [],
            "research_loop_count": state["research_loop_count"],
            "number_of_ran_queries": len(state["search_query"]),
        }


def evaluate_research(
    state: ReflectionState,
    config: RunnableConfig,
) -> OverallState:
    """LangGraph routing function that determines the next step in the research flow.

    Controls the research loop by deciding whether to continue gathering information
    or to finalize the summary based on the configured maximum number of research loops.

    Args:
        state: Current graph state containing the research loop count
        config: Configuration for the runnable, including max_research_loops setting

    Returns:
        String literal indicating the next node to visit ("web_research" or "finalize_summary")
    """
    configurable = Configuration.from_runnable_config(config)
    writer = get_stream_writer()
    max_research_loops = (
        state.get("max_research_loops")
        if state.get("max_research_loops") is not None
        else configurable.max_research_loops
    )
    if state["is_sufficient"]:
        writer({"langgraph_node": "evaluate_research", "message": f"研究结果充足，进入最终答案节点"})
        return "finalize_answer"
    elif state["research_loop_count"] >= max_research_loops:
        writer({"langgraph_node": "evaluate_research", "message": f"已经达到最大研究次数，进入最终答案节点"})
        return "finalize_answer"
    else:
        writer({"langgraph_node": "evaluate_research", "message": f"研究结果不足，进入补充检索节点"})
        return [
            Send(
                "web_research",
                {
                    "search_query": follow_up_query,
                    "id": state["number_of_ran_queries"] + int(idx),
                },
            )
            for idx, follow_up_query in enumerate(state["follow_up_queries"])
        ]


def finalize_answer(state: OverallState, config: RunnableConfig):
    """LangGraph node that finalizes the research summary."""
    configurable = Configuration.from_runnable_config(config)
    writer = get_stream_writer()
    reasoning_model = state.get("reasoning_model") or configurable.answer_model

    # 初始化模型
    llm = ChatTongyi(model=reasoning_model)
    
    # 限制摘要长度到25k字符
    summaries = "\n---\n\n".join(state.get("research_result", []))
    if len(summaries) > 25000:
        summaries = summaries[:25000] + "...(内容已截断)"
    
    # 生成答案 - 保持原有的 formatted_prompt
    formatted_prompt = answer_instructions.format(
        current_date=get_current_date(),
        research_topic=get_research_topic(state["messages"]),
        summaries=summaries,
    )
    
    # 直接调用LLM，不使用结构化输出
    result = llm.invoke(formatted_prompt)
    result_content = result.content if hasattr(result, "content") else str(result)
    writer({"langgraph_node": "finalize_answer", "message": f"最终答案：{result_content}"})
    return {
        "messages": [AIMessage(content=result_content)],
        "sources_gathered": state.get("sources_gathered", []),
    }


# Create our Agent Graph
builder = StateGraph(OverallState, config_schema=Configuration)

# Define the nodes we will cycle between
builder.add_node("generate_query", generate_query)
# builder.add_node("web_research", web_research)
builder.add_node("web_research", doc_research)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

# Set the entrypoint as `generate_query`
# This means that this node is the first one called
builder.add_edge(START, "generate_query")
# Add conditional edge to continue with search queries in a parallel branch
builder.add_conditional_edges(
    "generate_query", continue_to_web_research, ["web_research"]
)
# Reflect on the web research
builder.add_edge("web_research", "reflection")
# Evaluate the research
builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
# Finalize the answer
builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent")
