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
    """Milvus查询结果智能适配器 - 支持AI/非AI两种模式"""
    
    @staticmethod
    async def search(query_text: str, top_k: int = 5, collection: str = "demo", use_ai: bool = True) -> WebSearchResult:
        """执行Milvus查询并适配结果
        
        Args:
            query_text: 查询文本
            top_k: 返回结果数量
            collection: 集合名称
            use_ai: 是否使用AI智能适配
        """
        try:
            # 1. 执行Milvus查询
            results = await query_async(query_text, top_k, collection)
            
            if not results:
                return WebSearchResult(
                    search_content=f"未在知识库中找到关于'{query_text}'的相关信息。",
                    sources=[],
                    key_findings=["知识库中暂无相关内容"]
                )
            
            # 2. 根据开关选择适配方式
            if use_ai:
                logger.info(f"使用AI适配模式处理{len(results)}个结果")
                return await MilvusAdapter._ai_adapt_results(results, query_text)
            else:
                logger.info(f"使用非AI适配模式处理{len(results)}个结果")
                return MilvusAdapter._simple_adapt_results(results, query_text)
                
        except Exception as e:
            logger.error(f"Milvus查询失败: {e}")
            return WebSearchResult(
                search_content=f"知识库查询'{query_text}'失败: {str(e)}",
                sources=[],
                key_findings=["查询过程出现技术问题"]
            )
    
    @staticmethod
    async def _ai_adapt_results(results: List[Dict], query_text: str) -> WebSearchResult:
        """AI智能适配"""
        try:
            # 准备检索内容
            retrieved_content = MilvusAdapter._format_retrieved_content(results)
            
            # 初始化大模型
            llm = ChatTongyi(model="qwen-max")
            structured_llm = llm.with_structured_output(WebSearchResult)
            
            # 构建提示词
            prompt = KNOWLEDGE_BASE_ADAPTER_PROMPT.format(
                research_topic=query_text,
                retrieved_content=retrieved_content,
                current_date=get_current_date()
            )
            
            # AI生成结构化结果
            ai_result: WebSearchResult = structured_llm.invoke(prompt)
            
            # 补充sources信息
            enhanced_sources = MilvusAdapter._enhance_sources(ai_result.sources, results)
            
            return WebSearchResult(
                search_content=ai_result.search_content,
                sources=enhanced_sources,
                key_findings=ai_result.key_findings
            )
            
        except Exception as e:
            logger.error(f"AI适配失败，回退到简单适配: {e}")
            return MilvusAdapter._simple_adapt_results(results, query_text)
    
    @staticmethod
    def _simple_adapt_results(results: List[Dict], query_text: str) -> WebSearchResult:
        """非AI适配 - 基于规则的智能整合"""
        # 按相似度排序
        sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
        
        # 生成结构化内容
        search_content = MilvusAdapter._build_structured_content(sorted_results, query_text)
        sources = MilvusAdapter._extract_sources(sorted_results)
        key_findings = MilvusAdapter._extract_smart_findings(sorted_results, query_text)
        
        return WebSearchResult(
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
        for i, result in enumerate(results[:3], 1):  # 取前3个最相关的
            title = result.get("title", f"文档{i}")
            summary = result.get("summary", "")
            score = result.get("score", 0.0)
            
            if summary:
                # 智能截取关键部分
                key_content = MilvusAdapter._extract_key_content(summary, query_text)
                content_parts.append(f"**{i}. {title}** (相关度: {score:.2f})")
                content_parts.append(f"{key_content}\n")
        
        # 添加总结
        if top_score > 0.8:
            content_parts.append("**总结**: 知识库中包含高度相关的信息，能够较好地回答您的问题。")
        elif top_score > 0.6:
            content_parts.append("**总结**: 知识库中包含相关信息，但可能不够全面。")
        else:
            content_parts.append("**总结**: 知识库中信息与查询的相关性较低，建议调整查询词。")
        
        return "\n".join(content_parts)
    
    @staticmethod
    def _extract_key_content(text: str, query: str) -> str:
        """从文本中提取与查询相关的关键内容"""
        # 简单的关键词匹配逻辑
        query_words = query.lower().split()
        sentences = text.split('。')
        
        relevant_sentences = []
        for sentence in sentences:
            if any(word in sentence.lower() for word in query_words):
                relevant_sentences.append(sentence.strip())
        
        if relevant_sentences:
            # 返回最相关的句子，限制长度
            key_content = '。'.join(relevant_sentences[:3])
            return key_content[:300] + "..." if len(key_content) > 300 else key_content
        else:
            # 如果没有匹配的句子，返回前300字符
            return text[:300] + "..." if len(text) > 300 else text
    
    @staticmethod
    def _extract_sources(results: List[Dict]) -> List[dict]:
        """提取源信息"""
        return [
            {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
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
        high_score_docs = [r for r in results if r.get("score", 0) > 0.8]
        medium_score_docs = [r for r in results if 0.6 <= r.get("score", 0) <= 0.8]
        
        # 生成发现
        findings.append(f"检索到{total_docs}个相关文档，平均相关度{avg_score:.2f}")
        
        if high_score_docs:
            findings.append(f"发现{len(high_score_docs)}个高度相关文档")
            # 添加最相关文档的具体信息
            top_doc = max(results, key=lambda x: x.get("score", 0))
            findings.append(f"最相关文档: {top_doc.get('title', '未知')} (相关度: {top_doc.get('score', 0):.2f})")
        
        if medium_score_docs:
            findings.append(f"发现{len(medium_score_docs)}个中等相关文档")
        
        # 内容覆盖分析
        all_content = " ".join([r.get("summary", "") for r in results])
        query_words = query_text.lower().split()
        covered_words = [word for word in query_words if word in all_content.lower()]
        
        if covered_words:
            findings.append(f"知识库覆盖了查询中的关键词: {', '.join(covered_words[:5])}")
        
        # 质量评估
        if avg_score > 0.8:
            findings.append("内容质量评估: 高度匹配，能够充分回答问题")
        elif avg_score > 0.6:
            findings.append("内容质量评估: 部分匹配，提供了相关信息")
        else:
            findings.append("内容质量评估: 匹配度较低，建议重新构造查询")
        
        return findings
    
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
                    "url": ai_source.get("url") or (matched_result.get("url") if matched_result else ""),
                    "title": ai_source.get("title") or (matched_result.get("title") if matched_result else ""),
                    "score": matched_result.get("score", 0.0) if matched_result else 0.0
                }
                enhanced_sources.append(enhanced_source)
            return enhanced_sources
        else:
            return MilvusAdapter._extract_sources(original_results)


def milvus_research(state: WebSearchState, config: RunnableConfig, use_ai: bool = True) -> OverallState:
    """Milvus知识库研究节点"""
    search_query = state["search_query"]
    mode = "AI智能" if use_ai else "规则化"
    logger.info(f"Milvus {mode}研究: {search_query}")
    
    try:
        import nest_asyncio
        nest_asyncio.apply()
        result = asyncio.run(MilvusAdapter.search(search_query, top_k=10, use_ai=use_ai))
        
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


def hybrid_research(state: WebSearchState, config: RunnableConfig, use_ai: bool = True) -> OverallState:
    """混合研究节点"""
    milvus_result = milvus_research(state, config, use_ai)
    
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
async def search_kb(query: str, top_k: int = 5, collection: str = "demo", use_ai: bool = True) -> WebSearchResult:
    """便捷的知识库搜索接口"""
    return await MilvusAdapter.search(query, top_k, collection, use_ai)


def search_kb_sync(query: str, top_k: int = 5, collection: str = "demo", use_ai: bool = True) -> WebSearchResult:
    """同步版本的知识库搜索"""
    import nest_asyncio
    nest_asyncio.apply()
    return asyncio.run(search_kb(query, top_k, collection, use_ai))


if __name__ == "__main__":
    async def test():
        print("=== AI适配模式 ===")
        result_ai = await search_kb("违法裁员的类型有哪些？", 10, use_ai=True)
        print(f"AI内容: {(result_ai.search_content)}")
        print(f"AI关键发现数: {len(result_ai.key_findings)}")
        
        print("\n=== 非AI适配模式 ===")
        result_simple = await search_kb("违法裁员的类型有哪些？", 10, use_ai=False)
        print(f"非AI内容: {(result_simple.search_content)}")
        print(f"非AI关键发现数: {len(result_simple.key_findings)}")
        
        print("\n=== 非AI适配详细结果 ===")
        print("内容:", result_simple.search_content[:300], "...")
        print("关键发现:", result_simple.key_findings[:3])
    
    asyncio.run(test())

