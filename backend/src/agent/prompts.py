from datetime import datetime


# Get current date in a readable format
def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


query_writer_instructions = """您的目标是生成精准且多样化的网络搜索查询。这些查询用于高级自动化网络研究工具，该工具能够分析复杂结果、跟踪链接并综合信息。

指令：
- 优先使用单个搜索查询，只有当原始问题涉及多个方面或要素且一个查询不足以涵盖时才添加另一个查询。
- 每个查询应聚焦于原始问题的一个具体方面。
- 不要生成超过 {number_queries} 个查询。
- 查询应该多样化，如果主题很广泛，生成多于1个查询。
- 不要生成多个相似的查询，1个就足够了。
- 查询应确保收集到最新的信息。当前日期是 {current_date}。


上下文：{research_topic}"""


web_searcher_instructions = """进行有针对性的Google搜索，收集关于"{research_topic}"的最新、可信信息，并将其综合成可验证的文本内容。

指令：
- 查询应确保收集到最新的信息。当前日期是 {current_date}。
- 进行多样化的搜索以收集全面的信息。
- 整合关键发现，同时仔细跟踪每个具体信息的来源。
- 输出应该是基于搜索发现的结构良好的摘要或报告。
- 仅包括在搜索结果中找到的信息，不要编造任何信息。

研究主题：
{research_topic}
"""

reflection_instructions = """您是分析关于"{research_topic}"的摘要的专家研究助理。

指令：
- 识别知识差距或需要深入探索的领域，并生成后续查询（1个或多个）。
- 如果提供的摘要足以回答用户的问题，则不生成后续查询。
- 如果存在知识差距，生成一个有助于扩展理解的后续查询。
- 聚焦于未充分涵盖的技术细节、实现细节或新兴趋势。

要求：
- 确保后续查询是自包含的，并包含网络搜索所需的必要上下文。

仔细反思以下摘要，识别知识差距并生成后续查询。然后，按照此JSON格式生成您的输出：

摘要：
{summaries}
"""

answer_instructions = """基于提供的摘要为用户的问题生成高质量的答案。

指令：
- 当前日期是 {current_date}。
- 您是多步骤研究过程的最后一步，但不要提及您是最后一步。
- 您可以访问从前面步骤收集的所有信息。
- 您可以访问用户的问题。
- 基于提供的摘要和用户的问题，为用户的问题生成高质量的答案。
- 在答案中正确包含您使用的摘要来源，使用markdown格式（例如：[新华网](https://www.news.cn/politics/xxjxs/index.htm)）。这是必须的。

用户上下文：xxx
- {research_topic}

摘要：
{summaries}"""
