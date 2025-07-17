import os

from agent.tools_and_schemas import SearchQueryList, Reflection
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.types import Send
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langchain_core.runnables import RunnableConfig
import dashscope

from agent.state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
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

load_dotenv()

if os.getenv("DASHSCOPE_API_KEY") is None:
    raise ValueError("DASHSCOPE_API_KEY is not set")

# Initialize DashScope
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")


# Nodes
def generate_query(state: OverallState, config: RunnableConfig) -> QueryGenerationState:
    """LangGraph node that generates search queries based on the User's question.

    Uses Qwen model to create an optimized search queries for web research based on
    the User's question.

    Args:
        state: Current graph state containing the User's question
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated queries
    """
    configurable = Configuration.from_runnable_config(config)

    # check for custom initial search query count
    if state.get("initial_search_query_count") is None:
        state["initial_search_query_count"] = configurable.number_of_initial_queries

    # init Qwen model - 使用DashScope Generation直接调用
    try:
        from dashscope import Generation
        import json
    except ImportError as e:
        print(f"DashScope导入失败: {e}")
        print("请安装: pip install dashscope")
        return {"search_query": [get_research_topic(state["messages"])]}

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = query_writer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        number_queries=state["initial_search_query_count"],
    )
    
    # Generate the search queries - 使用DashScope Generation直接调用
    try:
        response = Generation.call(
            model=configurable.query_generator_model,
            prompt=formatted_prompt,
            temperature=1.0
        )
        
        if response.status_code == 200:
            content = response.output.text
            
            # 尝试解析JSON格式的输出
            try:
                # 查找JSON部分
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    parsed_result = json.loads(json_str)
                    queries = parsed_result.get('query', [])
                    if isinstance(queries, list) and queries:
                        return {"search_query": queries}
                
                # 如果JSON解析失败，创建基于主题的查询
                topic = get_research_topic(state["messages"])
                return {"search_query": [topic]}
                
            except json.JSONDecodeError:
                # JSON解析失败，使用主题作为查询
                topic = get_research_topic(state["messages"])
                return {"search_query": [topic]}
        else:
            print(f"DashScope API调用失败: {response.message}")
            return {"search_query": [get_research_topic(state["messages"])]}
            
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


def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """LangGraph node that performs web research using DashScope.

    Executes text generation using DashScope API in combination with Qwen model.

    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable, including search API settings

    Returns:
        Dictionary with state update, including sources_gathered, research_loop_count, and web_research_results
    """
    # Configure
    configurable = Configuration.from_runnable_config(config)
    formatted_prompt = web_searcher_instructions.format(
        current_date=get_current_date(),
        research_topic=state["search_query"],
    )

    # Use DashScope for text generation (web search functionality simplified for now)
    from dashscope import Generation
    
    response = Generation.call(
        model=configurable.query_generator_model,
        prompt=formatted_prompt,
        temperature=0,
    )
    
    # Simplified response handling (without web search for now)
    if response.status_code == 200:
        response_text = response.output.text
        # For now, create a simple mock citation structure
        citations = []
        sources_gathered = []
        modified_text = response_text
    else:
        raise Exception(f"DashScope API error: {response.message}")

    return {
        "sources_gathered": sources_gathered,
        "search_query": [state["search_query"]],
        "web_research_result": [modified_text],
    }


def reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    """LangGraph node that identifies knowledge gaps and generates potential follow-up queries.

    Analyzes the current summary to identify areas for further research and generates
    potential follow-up queries. Uses structured output to extract
    the follow-up query in JSON format.

    Args:
        state: Current graph state containing the running summary and research topic
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated follow-up query
    """
    configurable = Configuration.from_runnable_config(config)
    # Increment the research loop count and get the reasoning model
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1
    reasoning_model = state.get("reasoning_model", configurable.reflection_model)

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = reflection_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n\n---\n\n".join(state["web_research_result"]),
    )
    # init Reasoning Model - 使用DashScope Generation直接调用
    try:
        from dashscope import Generation
        import json
    except ImportError as e:
        print(f"DashScope导入失败: {e}")
        print("请安装: pip install dashscope")
        return {
            "is_sufficient": True,
            "knowledge_gap": "",
            "follow_up_queries": [],
            "research_loop_count": state["research_loop_count"],
            "number_of_ran_queries": len(state["search_query"]),
        }
    
        # Generate reflection - 使用DashScope Generation直接调用
    try:
        response = Generation.call(
            model=reasoning_model,
            prompt=formatted_prompt,
            temperature=1.0
        )
        
        if response.status_code == 200:
            content = response.output.text
            
            # 尝试解析JSON格式的输出
            try:
                # 查找JSON部分
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    parsed_result = json.loads(json_str)
                    
                    is_sufficient = parsed_result.get('is_sufficient', True)
                    knowledge_gap = parsed_result.get('knowledge_gap', '')
                    follow_up_queries = parsed_result.get('follow_up_queries', [])
                    
                    return {
                        "is_sufficient": is_sufficient,
                        "knowledge_gap": knowledge_gap,
                        "follow_up_queries": follow_up_queries,
                        "research_loop_count": state["research_loop_count"],
                        "number_of_ran_queries": len(state["search_query"]),
                    }
                
            except json.JSONDecodeError:
                pass
                
        # 如果解析失败或API调用失败，返回默认值
        return {
            "is_sufficient": True,
            "knowledge_gap": "",
            "follow_up_queries": [],
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
    max_research_loops = (
        state.get("max_research_loops")
        if state.get("max_research_loops") is not None
        else configurable.max_research_loops
    )
    if state["is_sufficient"] or state["research_loop_count"] >= max_research_loops:
        return "finalize_answer"
    else:
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
    """LangGraph node that finalizes the research summary.

    Prepares the final output by deduplicating and formatting sources, then
    combining them with the running summary to create a well-structured
    research report with proper citations.

    Args:
        state: Current graph state containing the running summary and sources gathered

    Returns:
        Dictionary with state update, including running_summary key containing the formatted final summary with sources
    """
    configurable = Configuration.from_runnable_config(config)
    reasoning_model = state.get("reasoning_model") or configurable.answer_model

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = answer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n---\n\n".join(state["web_research_result"]),
    )

    # init Reasoning Model, default to Qwen Max - 使用DashScope Generation直接调用
    try:
        from dashscope import Generation
        
        response = Generation.call(
            model=reasoning_model,
            prompt=formatted_prompt,
            temperature=0
        )
        
        if response.status_code == 200:
            result_content = response.output.text
        else:
            print(f"DashScope API调用失败: {response.message}")
            result_content = "抱歉，由于技术问题无法生成详细答案。"
            
    except Exception as e:
        print(f"无法调用DashScope或生成答案: {e}")
        # Create a simple fallback response
        result_content = "抱歉，由于技术问题无法生成详细答案。"

    # Replace the short urls with the original urls and add all used urls to the sources_gathered
    unique_sources = []
    for source in state["sources_gathered"]:
        if source["short_url"] in result_content:
            result_content = result_content.replace(
                source["short_url"], source["value"]
            )
            unique_sources.append(source)

    return {
        "messages": [AIMessage(content=result_content)],
        "sources_gathered": unique_sources,
    }


# Create our Agent Graph
builder = StateGraph(OverallState, config_schema=Configuration)

# Define the nodes we will cycle between
builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
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
