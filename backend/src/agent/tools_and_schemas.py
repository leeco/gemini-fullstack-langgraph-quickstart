from typing import List
from pydantic import BaseModel, Field


class SearchQueryList(BaseModel):
    query: List[str] = Field(
        description="A list of search queries to be used for web research."
    )
    rationale: str = Field(
        description="A brief explanation of why these queries are relevant to the research topic."
    )


class Reflection(BaseModel):
    is_sufficient: bool = Field(
        description="Whether the provided summaries are sufficient to answer the user's question."
    )
    knowledge_gap: str = Field(
        description="A description of what information is missing or needs clarification."
    )
    follow_up_queries: List[str] = Field(
        description="A list of follow-up queries to address the knowledge gap."
    )


class SearchResult(BaseModel):
    """网络搜索结果的结构化输出"""
    search_content: str = Field(description="搜索得到的内容摘要，不要遗漏任何和问题相关的信息")
    sources: List[dict] = Field(description="信息来源列表，包含url和标题", default=[])
    key_findings: List[str] = Field(description="关键发现列表", default=[])


class FinalAnswer(BaseModel):
    """最终答案的结构化输出"""
    answer: str = Field(description="基于研究结果的完整答案")
    summary_points: List[str] = Field(description="关键要点列表", default=[])
    confidence_level: int = Field(description="答案可信度评分1-10", ge=1, le=10, default=8)
