import logging
import asyncio
from typing import List, Dict, Any
from langchain_core.runnables import RunnableConfig
from langchain_community.chat_models import ChatTongyi

from agent.tools_and_schemas import SearchResult
from agent.state import SearchState, OverallState
from agent.doc_search import query_sync  # 使用新的同步接口
from agent.configuration import Configuration
from agent.prompts import get_current_date

# 配置日志
logger = logging.getLogger(__name__)

MIN_SCORE = 0.5

# 知识库内容适配的提示词
KNOWLEDGE_BASE_ADAPTER_PROMPT = """你将获得与用户查询“{research_topic}”相关的知识库检索内容。

## 检索到的知识库内容：
{retrieved_content}

## 你的任务：
- 仔细阅读所有检索内容，筛选、保留与用户问题高度相关的所有信息，不能遗漏任何与问题相关的要点或细节。
- 对相关内容进行归纳、整合和完善，形成结构化、条理清晰的研究报告。
- 不要遗漏任何与问题相关的信息，确保所有有用内容都被覆盖。
- 不相关的信息无需包含在报告中。

## 输出要求：
- 保持客观、中立，仅基于检索内容进行分析，不要引入外部知识。
- 如果检索内容不足以完全回答问题，请明确指出哪些方面信息不足。

当前日期: {current_date}
"""


class MilvusAdapter:
    """Milvus查询结果智能适配器 - 完全同步版本"""
    
    @staticmethod
    def search(query_text: str, top_k: int = 5, collection: str = "demo", use_ai: bool = True) -> SearchResult:
        """执行Milvus查询并适配结果 - 完全同步版本"""
        try:
            # 使用原生同步查询
            results = query_sync(query_text, top_k, collection)
            
            if not results:
                return SearchResult(
                    search_content=f"未在知识库中找到关于'{query_text}'的相关信息。",
                    sources=[],
                    key_findings=["知识库中暂无相关内容"]
                )
            
            # 2. 根据开关选择适配方式
            if use_ai:
                logger.info(f"使用AI适配模式处理{len(results)}个结果")
                return MilvusAdapter._ai_adapt_results(results, query_text)
            else:
                logger.info(f"使用非AI适配模式处理{len(results)}个结果")
                return MilvusAdapter._simple_adapt_results(results, query_text)
                
        except Exception as e:
            logger.error(f"Milvus查询失败: {e}")
            return SearchResult(
                search_content=f"知识库查询'{query_text}'失败: {str(e)}",
                sources=[],
                key_findings=["查询过程出现技术问题"]
            )
    
    @staticmethod
    def _ai_adapt_results(results: List[Dict], query_text: str) -> SearchResult:
        """AI智能适配 - 同步版本"""
        try:
            # 先清理结果，只保留指定字段
            cleaned_results = []
            for r in results:
                clean_result = {
                    "source": r.get("source", ""),
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "summary": r.get("summary", ""),
                    "score": r.get("score", 0.0)
                }
                cleaned_results.append(clean_result)
            
            # 准备检索内容
            retrieved_content = MilvusAdapter._format_retrieved_content(cleaned_results)
            
            # 初始化大模型
            llm = ChatTongyi(model="qwen-max")
            structured_llm = llm.with_structured_output(SearchResult)
            
            # 构建提示词
            prompt = f"""基于知识库检索结果，为用户查询"{query_text}"生成结构化的研究报告。

                ## 检索到的知识库内容：
                {retrieved_content}

                ## 你的任务：
                1. 仔细分析上述知识库内容
                2. 针对用户查询"{query_text}"进行智能整合和总结
                3. 生成结构化的研究报告

                当前日期: {get_current_date()}
                """
            
            # AI生成结构化结果
            ai_result: SearchResult = structured_llm.invoke(prompt)
            
            # 补充sources信息
            enhanced_sources = MilvusAdapter._enhance_sources(ai_result.sources, cleaned_results)
            
            return SearchResult(
                search_content=ai_result.search_content,
                sources=enhanced_sources,
                key_findings=ai_result.key_findings
            )
            
        except Exception as e:
            logger.error(f"AI适配失败，回退到简单适配: {e}")
            return MilvusAdapter._simple_adapt_results(results, query_text)
    

    @staticmethod
    def _filter_summary(summary: str, query_text: str) -> str:
        """使用LLM对summary进行二次提炼，仅保留与query_text高度相关的内容"""
        llm = ChatTongyi(model="qwen-max")
        prompt = f"""你将获得与用户查询“{query_text}”相关的知识库检索内容摘要。请你仔细阅读内容，仅保留与该查询高度相关、最有价值的信息，去除无关或冗余部分，并用简洁、专业的语言进行二次提炼和总结，输出精炼后的内容。
                请直接输出优化后的摘要，不要添加额外说明。  

                ## 检索到的知识库内容：
                {summary}

                """
        if not summary or not summary.strip():
            return ""
        result = llm.invoke(prompt)
        return result.content if hasattr(result, "content") and result.content else ""

    @staticmethod
    def _simple_adapt_results(results: List[Dict], query_text: str) -> SearchResult:
        """非AI适配 - 基于阈值的简单整合"""
        # 筛选高相关文档，并只保留指定字段
        filtered_results = []
        for r in results:
            if r.get("score", 0) >= MIN_SCORE:
                # 只保留指定的字段
                clean_result = {
                    "source": r.get("source", ""),
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "summary": r.get("summary", ""),
                    "score": r.get("score", 0.0)
                }
                filtered_results.append(clean_result)
        
        if not filtered_results:
            return SearchResult(
                search_content=f"未找到与'{query_text}'高度相关的信息（阈值>{MIN_SCORE}）。",
                sources=[],
                key_findings=["无高相关内容"]
            )
        
        # 生成内容摘要
        content_parts = [f"针对查询'{query_text}'，以下为相关性高于{MIN_SCORE}的知识库内容：\n"]
        
        for i, result in enumerate(filtered_results, 1):
            title = result.get("title", f"文档{i}")
            summary = result.get("summary", "")
            score = result.get("score", 0.0)
            summary = MilvusAdapter._filter_summary(summary, query_text)
            content_parts.append(f"**{i}. {title}** (相关度: {score:.2f})")
            content_parts.append(f"{summary}\n")
        
        content_parts.append(f"共返回{len(filtered_results)}个高相关文档片段。")
        
        search_content = "\n\n".join(content_parts)
        
        sources = [
            {
                "source": r.get("source", ""),
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "summary": r.get("summary", ""),
                "score": r.get("score", 0.0)
            }
            for r in filtered_results
        ]
        
        key_findings = [
            f"共返回{len(filtered_results)}个高相关文档片段",
            f"相关性阈值: {MIN_SCORE}",
            f"平均相关度: {sum(r.get('score', 0) for r in filtered_results) / len(filtered_results):.2f}"
        ]
        
        return SearchResult(
            search_content=search_content,
            sources=sources,
            key_findings=key_findings
        )
    
    @staticmethod
    def _build_structured_content(results: List[Dict], query_text: str) -> str:
        """构建结构化内容摘要"""
        if not results:
            return f"未找到关于'{query_text}'的相关信息。"
        
        # 分析最高分结果
        top_result = results[0]
        top_score = top_result.get("score", 0)
        
        # 构建回答
        content_parts = [f"针对查询'{query_text}'，基于知识库分析如下：\n"]
        
        # 主要内容
        for i, result in enumerate(results):
            title = result.get("title", f"文档{i}")
            summary = result.get("summary", "")
            score = result.get("score", 0.0)
            if score < MIN_SCORE:
                continue
            
            if summary:
                # 智能截取关键部分
                key_content = summary
                content_parts.append(f"**{i}. {title}** (相关度: {score:.2f})")
                content_parts.append(f"{key_content}\n")
        
        # 添加总结
        if top_score > 0.8:
            content_parts.append("**总结**: 知识库中包含高度相关的信息，能够较好地回答您的问题。")
        elif top_score > 0.6:
            content_parts.append("**总结**: 知识库中包含相关信息，但可能不够全面。")
        else:
            content_parts.append("**总结**: 知识库中信息与查询的相关性较低，建议调整查询词。")
        
        return "\n\n".join(content_parts)
    

    
    @staticmethod
    def _extract_sources(results: List[Dict]) -> List[dict]:
        """提取源信息，只保留指定字段"""
        return [
            {
                "source": r.get("source", ""),
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "summary": r.get("summary", ""),
                "score": r.get("score", 0.0)
            }
            for r in results
        ]
    
    @staticmethod
    def _extract_smart_findings(results: List[Dict], query_text: str) -> List[str]:
        """提取智能关键发现"""
        findings = []
        
        if not results:
            return ["未找到相关信息"]
        
        # 基础统计
        total_docs = len(results)
        avg_score = sum(r.get("score", 0) for r in results) / total_docs
        
        return findings

    @staticmethod
    def _format_retrieved_content(results: List[Dict]) -> str:
        """格式化检索内容"""
        content_sections = []
        for i, result in enumerate(results, 1):
            title = result.get("title", f"文档{i}")
            summary = result.get("summary", "")
            score = result.get("score", 0.0)
            
            section = f"### 文档{i}: {title} (相关度: {score:.2f})\n{summary}"
            content_sections.append(section)
        return "\n".join(content_sections)
    
    @staticmethod
    def _enhance_sources(ai_sources: List[dict], original_results: List[Dict]) -> List[dict]:
        """增强AI生成的sources信息，只保留指定字段"""
        if ai_sources:
            enhanced_sources = []
            for ai_source in ai_sources:
                # 尝试匹配原始结果
                matched_result = None
                for result in original_results:
                    if (ai_source.get("title", "").lower() in result.get("title", "").lower() or
                        result.get("title", "").lower() in ai_source.get("title", "").lower()):
                        matched_result = result
                        break
                
                enhanced_source = {
                    "source": ai_source.get("source") or (matched_result.get("source") if matched_result else ""),
                    "title": ai_source.get("title") or (matched_result.get("title") if matched_result else ""),
                    "url": ai_source.get("url") or (matched_result.get("url") if matched_result else ""),
                    "summary": ai_source.get("summary") or (matched_result.get("summary") if matched_result else ""),
                    "score": matched_result.get("score", 0.0) if matched_result else 0.0
                }
                enhanced_sources.append(enhanced_source)
            return enhanced_sources
        else:
            return MilvusAdapter._extract_sources(original_results)


def milvus_research_sync(state: SearchState, config: RunnableConfig, use_ai: bool = True) -> OverallState:
    """Milvus知识库研究节点 - 完全同步版本"""
    search_query = state["search_query"]
    mode = "AI智能" if use_ai else "规则化"
    logger.info(f"Milvus {mode}研究: {search_query}")
    
    try:
        # 使用完全同步的接口
        result = MilvusAdapter.search(search_query, top_k=10, use_ai=use_ai)
        
        # 转换为graph期望格式
        sources_gathered = [
            {
                "url": source["url"],
                "title": source["title"],
                "short_url": source["url"],
                "value": source["url"],
                "source_type": "knowledge_base",
                "score": source.get("score", 0.0)
            }
            for source in result.sources
        ]
        
        logger.info(f"{mode}适配完成，生成{len(sources_gathered)}个源")
        
        return {
            "sources_gathered": sources_gathered,
            "search_query": [search_query],
            "web_research_result": [result.search_content],
        }
        
    except Exception as e:
        logger.error(f"Milvus {mode}研究失败: {e}")
        return {
            "sources_gathered": [],
            "search_query": [search_query],
            "web_research_result": [f"知识库{mode}分析失败: {str(e)}"],
        }


def hybrid_research(state: SearchState, config: RunnableConfig, use_ai: bool = True) -> OverallState:
    """混合研究节点"""
    milvus_result = milvus_research_sync(state, config, use_ai)
    
    # 检查结果质量
    if (milvus_result["sources_gathered"] and 
        "失败" not in milvus_result["web_research_result"][0] and
        len(milvus_result["web_research_result"][0]) > 100):
        mode = "AI智能" if use_ai else "规则化"
        logger.info(f"使用知识库{mode}分析结果")
        return milvus_result
    
    # 回退到web research
    logger.info("回退到web research")
    try:
        from agent.graph import web_research
        return web_research(state, config)
    except Exception as e:
        logger.error(f"Web research也失败: {e}")
        return milvus_result


# 便捷接口
def search_kb_sync(query: str, top_k: int = 5, collection: str = "demo", use_ai: bool = True) -> SearchResult:
    """同步版本的知识库搜索"""
    return MilvusAdapter.search(query, top_k, collection, use_ai)


if __name__ == "__main__":
    async def test():
        # print("=== AI适配模式 ===")
        # result_ai = await search_kb("违法裁员的类型有哪些？", 10, use_ai=True)
        # print(f"AI内容: {(result_ai.search_content)}")
        # print(f"AI关键发现数: {len(result_ai.key_findings)}")
        
        print("\n=== 非AI适配模式 ===")
        result_simple = await search_kb_sync("违法裁员的类型有哪些？", 10, use_ai=False)
        print(f"非AI内容: {(result_simple.search_content)}")
        print(f"非AI关键发现数: {len(result_simple.key_findings)}")
        
        # print("\n=== 非AI适配详细结果 ===")
        # print("内容:", result_simple.search_content[:300], "...")
        # print("关键发现:", result_simple.key_findings[:3])
    
    asyncio.run(test())

