import logging
import asyncio
from typing import List, Dict, Any
from langchain_core.runnables import RunnableConfig
from langchain_community.chat_models import ChatTongyi

from agent.tools_and_schemas import WebSearchResult
from agent.state import WebSearchState, OverallState
from agent.doc_search import query_async
from agent.configuration import Configuration
from agent.prompts import get_current_date

# 配置日志
logger = logging.getLogger(__name__)

# 知识库内容适配的提示词
KNOWLEDGE_BASE_ADAPTER_PROMPT = """基于知识库检索结果，为用户查询"{research_topic}"生成结构化的研究报告。

## 检索到的知识库内容：
{retrieved_content}

## 你的任务：
1. 仔细分析上述知识库内容
2. 针对用户查询"{research_topic}"进行智能整合和总结
3. 生成结构化的研究报告，包含：
   - search_content: 基于检索内容的综合分析和回答
   - key_findings: 从内容中提取所有的关键信息，不要遗漏任何和问题相关的信息
   - sources: 内容来源信息

## 要求：
- 内容要有针对性，直接回答用户的查询
- 整合多个文档片段的信息，避免简单拼接
- 关键发现要有洞察性，不只是统计信息
- 保持客观性，基于检索内容进行分析
- 如果内容不足以完全回答查询，明确指出限制

当前日期: {current_date}
"""


class MilvusAdapter:
    """Milvus查询结果智能适配器 - 使用大模型进行内容整合"""
    
    @staticmethod
    async def search(query_text: str, top_k: int = 5, collection: str = "demo") -> WebSearchResult:
        """执行Milvus查询并使用大模型进行智能适配"""
        try:
            # 1. 执行Milvus查询
            results = await query_async(query_text, top_k, collection)
            
            if not results:
                return WebSearchResult(
                    search_content=f"未在知识库中找到关于'{query_text}'的相关信息。",
                    sources=[],
                    key_findings=["知识库中暂无相关内容"]
                )
            
            # 2. 使用大模型进行智能适配
            return await MilvusAdapter._ai_adapt_results(results, query_text)
            
        except Exception as e:
            logger.error(f"Milvus查询失败: {e}")
            return WebSearchResult(
                search_content=f"知识库查询'{query_text}'失败: {str(e)}",
                sources=[],
                key_findings=["查询过程出现技术问题"]
            )
    
    @staticmethod
    async def _ai_adapt_results(results: List[Dict], query_text: str) -> WebSearchResult:
        """使用AI模型对检索结果进行智能适配"""
        try:
            # 准备检索内容
            retrieved_content = MilvusAdapter._format_retrieved_content(results)
            
            # 初始化大模型
            llm = ChatTongyi(model="qwen-max")  # 使用最强模型进行内容理解
            structured_llm = llm.with_structured_output(WebSearchResult)
            
            # 构建提示词
            prompt = KNOWLEDGE_BASE_ADAPTER_PROMPT.format(
                research_topic=query_text,
                retrieved_content=retrieved_content,
                current_date=get_current_date()
            )
            
            # AI生成结构化结果
            ai_result: WebSearchResult = structured_llm.invoke(prompt)
            
            # 补充sources信息（AI可能无法完整生成）
            enhanced_sources = MilvusAdapter._enhance_sources(ai_result.sources, results)
            
            return WebSearchResult(
                search_content=ai_result.search_content,
                sources=enhanced_sources,
                key_findings=ai_result.key_findings
            )
            
        except Exception as e:
            logger.error(f"AI适配失败，回退到简单适配: {e}")
            # 回退到简单适配
            return MilvusAdapter._simple_adapt_results(results, query_text)
    
    @staticmethod
    def _format_retrieved_content(results: List[Dict]) -> str:
        """格式化检索内容供AI处理"""
        content_sections = []
        
        for i, result in enumerate(results, 1):
            title = result.get("title", f"文档{i}")
            summary = result.get("summary", "")
            score = result.get("score", 0.0)
            url = result.get("url", "")
            
            section = f"""
=== 文档{i}: {title} ===
相似度: {score:.3f}
内容: {summary}
来源: {url}
"""
            content_sections.append(section)
        
        return "\n".join(content_sections)
    
    @staticmethod
    def _enhance_sources(ai_sources: List[dict], original_results: List[Dict]) -> List[dict]:
        """增强AI生成的sources信息"""
        enhanced_sources = []
        
        # 如果AI生成了sources，使用AI的；否则使用原始结果
        if ai_sources:
            # 合并AI生成的sources和原始的详细信息
            for ai_source in ai_sources:
                # 尝试匹配原始结果
                matched_result = None
                for result in original_results:
                    if (ai_source.get("title", "").lower() in result.get("title", "").lower() or
                        result.get("title", "").lower() in ai_source.get("title", "").lower()):
                        matched_result = result
                        break
                
                enhanced_source = {
                    "url": ai_source.get("url") or (matched_result.get("url") if matched_result else ""),
                    "title": ai_source.get("title") or (matched_result.get("title") if matched_result else ""),
                    "score": matched_result.get("score", 0.0) if matched_result else 0.0
                }
                enhanced_sources.append(enhanced_source)
        else:
            # AI没有生成sources，使用原始结果
            enhanced_sources = [
                {
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "score": r.get("score", 0.0)
                }
                for r in original_results
            ]
        
        return enhanced_sources
    
    @staticmethod
    def _simple_adapt_results(results: List[Dict], query_text: str) -> WebSearchResult:
        """简单适配作为AI适配失败时的回退方案"""
        # 生成基础内容摘要
        content_parts = []
        for result in results:
            title = result.get("title", "未知文档")
            summary = result.get("summary", "")[:300]
            score = result.get("score", 0.0)
            if summary:
                content_parts.append(f"**{title}** (相似度: {score:.2f})\n{summary}")
        
        search_content = f"""基于知识库检索关于"{query_text}"的信息：

{chr(10).join(content_parts)}

共检索到{len(results)}个相关文档片段。"""
        
        # 转换sources
        sources = [
            {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "score": r.get("score", 0.0)
            }
            for r in results
        ]
        
        # 生成基础关键发现
        avg_score = sum(r.get("score", 0) for r in results) / len(results)
        high_relevance = sum(1 for r in results if r.get("score", 0) > 0.8)
        
        key_findings = [
            f"检索到{len(results)}个相关文档",
            f"平均相似度: {avg_score:.2f}"
        ]
        if high_relevance > 0:
            key_findings.append(f"高相关度文档: {high_relevance}个")
        
        return WebSearchResult(
            search_content=search_content,
            sources=sources,
            key_findings=key_findings
        )


def milvus_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """Milvus知识库研究节点 - 使用AI智能适配"""
    search_query = state["search_query"]
    logger.info(f"Milvus AI研究: {search_query}")
    
    try:
        # 执行AI增强的查询
        import nest_asyncio
        nest_asyncio.apply()
        result = asyncio.run(MilvusAdapter.search(search_query, top_k=5))
        
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
        
        logger.info(f"AI适配完成，生成{len(sources_gathered)}个源，内容长度: {len(result.search_content)}")
        
        return {
            "sources_gathered": sources_gathered,
            "search_query": [search_query],
            "web_research_result": [result.search_content],
        }
        
    except Exception as e:
        logger.error(f"Milvus AI研究失败: {e}")
        return {
            "sources_gathered": [],
            "search_query": [search_query],
            "web_research_result": [f"知识库AI分析失败: {str(e)}"],
        }


def hybrid_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """混合研究节点 - 智能选择知识库AI分析或web研究"""
    # 先尝试知识库AI分析
    milvus_result = milvus_research(state, config)
    
    # 检查结果质量
    if (milvus_result["sources_gathered"] and 
        "失败" not in milvus_result["web_research_result"][0] and
        len(milvus_result["web_research_result"][0]) > 100):  # 内容要有一定长度
        logger.info("使用知识库AI分析结果")
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
async def search_kb(query: str, top_k: int = 5, collection: str = "demo") -> WebSearchResult:
    """便捷的AI增强知识库搜索接口"""
    return await MilvusAdapter.search(query, top_k, collection)


def search_kb_sync(query: str, top_k: int = 5, collection: str = "demo") -> WebSearchResult:
    """同步版本的AI增强知识库搜索"""
    import nest_asyncio
    nest_asyncio.apply()
    return asyncio.run(search_kb(query, top_k, collection))


if __name__ == "__main__":
    async def test():
        result = await search_kb("违法裁员的类型有哪些？", 10)
        print("=== AI适配结果 ===")
        print(f"内容: {(result.search_content)}")
        print(f"关键: {result.key_findings}")
        print(f"信息源: {len(result.sources)}")
        print("\n--- 内容摘要 ---")
        print(result.search_content[:500] + "...")
    
    asyncio.run(test())

