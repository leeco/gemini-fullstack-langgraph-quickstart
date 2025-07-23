import { useStream } from "@langchain/langgraph-sdk/react";
import type { Message } from "@langchain/langgraph-sdk";
import { useState, useEffect, useRef, useCallback } from "react";
import { ProcessedEvent } from "@/components/ActivityTimeline";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { ChatMessagesView } from "@/components/ChatMessagesView";
import { Button } from "@/components/ui/button";

export default function App() {
  const [processedEventsTimeline, setProcessedEventsTimeline] = useState<
    ProcessedEvent[]
  >([]);
  const [historicalActivities, setHistoricalActivities] = useState<
    Record<string, ProcessedEvent[]>
  >({});
  const [chatMessages, setChatMessages] = useState<Message[]>([]);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const hasFinalizeEventOccurredRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const thread = useStream<{
    messages: Message[];
    initial_search_query_count: number;
    max_research_loops: number;
    reasoning_model: string;
  }>({
    apiUrl: import.meta.env.DEV
      ? "http://localhost:2024"
      : "http://localhost:8123",
    assistantId: "agent",
    // 移除 messagesKey，手动处理消息
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onUpdateEvent: (event: Record<string, any>) => {
      let processedEvent: ProcessedEvent | null = null;
      
      try {
        // 添加详细的调试日志
        console.log("收到事件:", JSON.stringify(event, null, 2));
        
        // 处理节点更新事件 - LangGraph SDK的onUpdateEvent接收的是节点更新
        if (event && typeof event === 'object') {
          // 处理节点更新事件
          for (const nodeName of Object.keys(event)) {
            if (event[nodeName] && typeof event[nodeName] === 'object') {
              const nodeData = event[nodeName];
              console.log(`节点 ${nodeName} 数据:`, nodeData);
              
              // 只有 finalize_answer 节点的消息才添加到对话中
              if (nodeName === "finalize_answer" && nodeData.messages) {
                // 添加最终答案消息到聊天消息中
                const newMessages = nodeData.messages.map((msg: any, index: number) => ({
                  ...msg,
                  id: `finalize-${Date.now()}-${index}`,
                }));
                setChatMessages(prev => [...prev, ...newMessages]);
              }
              
              // 根据节点名称创建不同的时间线事件
              switch (nodeName) {
                case "generate_query": {
                  const queries = nodeData.search_query || [];
                  const queryList = Array.isArray(queries) ? queries.join(", ") : queries;
                  processedEvent = {
                    title: "🔍 生成搜索查询",
                    data: queries.length > 0 
                      ? `生成了 ${queries.length} 个查询: ${queryList.length > 100 ? queryList.substring(0, 100) + '...' : queryList}`
                      : "正在生成搜索查询...",
                  };
                  break;
                }
                case "web_research":
                case "doc_research": {
                  const sources = nodeData.sources_gathered || [];
                  const searchQuery = nodeData.search_query;
                  const researchResult = nodeData.research_result;
                  
                  let details = [];
                  if (searchQuery) {
                    details.push(`查询: "${Array.isArray(searchQuery) ? searchQuery[0] : searchQuery}"`);
                  }
                  if (sources.length > 0) {
                    details.push(`收集了 ${sources.length} 个资源`);
                    const titles = sources.map((s: any) => s.title).filter(Boolean).slice(0, 2);
                    if (titles.length > 0) {
                      details.push(`包括: ${titles.join(", ")}${sources.length > 2 ? " 等" : ""}`);
                    }
                  }
                  if (researchResult && researchResult.length > 0) {
                    const result = Array.isArray(researchResult) ? researchResult[0] : researchResult;
                    if (result && result.length > 50) {
                      details.push(`研究摘要: ${result.substring(0, 80)}...`);
                    }
                  }
                  
                  processedEvent = {
                    title: "📚 网络研究",
                    data: details.length > 0 ? details.join(" | ") : "正在进行网络研究...",
                  };
                  break;
                }
                case "reflection": {
                  const isSufficient = nodeData.is_sufficient;
                  const knowledgeGap = nodeData.knowledge_gap;
                  const followUpQueries = nodeData.follow_up_queries || [];
                  
                  let details = [];
                  if (isSufficient !== undefined) {
                    details.push(isSufficient ? "✅ 研究结果充足" : "⚠️ 需要进一步研究");
                  }
                  if (knowledgeGap) {
                    details.push(`知识缺口: ${knowledgeGap.length > 60 ? knowledgeGap.substring(0, 60) + '...' : knowledgeGap}`);
                  }
                  if (followUpQueries.length > 0) {
                    details.push(`后续查询: ${followUpQueries.slice(0, 2).join(", ")}${followUpQueries.length > 2 ? " 等" : ""}`);
                  }
                  
                  processedEvent = {
                    title: "🤔 研究反思",
                    data: details.length > 0 ? details.join(" | ") : "正在分析研究结果...",
                  };
                  break;
                }
                case "evaluate_research": {
                  processedEvent = {
                    title: "⚖️ 评估研究进度",
                    data: "评估当前研究是否充分，决定下一步行动",
                  };
                  break;
                }
                case "finalize_answer": {
                  processedEvent = {
                    title: "✨ 生成最终答案",
                    data: "正在整合所有研究结果，生成综合性答案...",
                  };
                  hasFinalizeEventOccurredRef.current = true;
                  break;
                }
                default: {
                  // 对于未知节点，显示更详细信息
                  const dataKeys = Object.keys(nodeData);
                  const summary = dataKeys.length > 0 
                    ? `包含字段: ${dataKeys.slice(0, 3).join(", ")}${dataKeys.length > 3 ? " 等" : ""}`
                    : "节点执行完成";
                  
                  processedEvent = {
                    title: `🔧 ${nodeName}`,
                    data: summary,
                  };
                  break;
                }
              }
              
              // 找到第一个匹配的节点后停止
              break;
            }
          }
        }
      } catch (error) {
        console.error("处理事件时出错:", error);
        processedEvent = {
          title: "❌ 处理错误",
          data: `事件处理过程中发生错误: ${error instanceof Error ? error.message : String(error)}`,
        };
      }
      
      if (processedEvent) {
        setProcessedEventsTimeline((prevEvents) => [
          ...prevEvents,
          {
            ...processedEvent!,
            timestamp: new Date(),
          },
        ]);
      }
    },
    onError: (error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : String(error);
      setError(errorMessage);
    },
  });

  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollViewport = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollViewport) {
        scrollViewport.scrollTop = scrollViewport.scrollHeight;
      }
    }
  }, [chatMessages]);

  useEffect(() => {
    if (
      hasFinalizeEventOccurredRef.current &&
      !thread.isLoading &&
      chatMessages.length > 0
    ) {
      const lastMessage = chatMessages[chatMessages.length - 1];
      if (lastMessage && lastMessage.type === "ai" && lastMessage.id) {
        setHistoricalActivities((prev) => ({
          ...prev,
          [lastMessage.id!]: [...processedEventsTimeline],
        }));
      }
      hasFinalizeEventOccurredRef.current = false;
    }
  }, [chatMessages, thread.isLoading, processedEventsTimeline]);

  const handleSubmit = useCallback(
    (submittedInputValue: string, effort: string, model: string) => {
      if (!submittedInputValue.trim()) return;
      setProcessedEventsTimeline([]);
      hasFinalizeEventOccurredRef.current = false;

      // convert effort to, initial_search_query_count and max_research_loops
      // low means max 1 loop and 1 query
      // medium means max 3 loops and 3 queries
      // high means max 10 loops and 5 queries
      let initial_search_query_count = 0;
      let max_research_loops = 0;
      switch (effort) {
        case "low":
          initial_search_query_count = 1;
          max_research_loops = 1;
          break;
        case "medium":
          initial_search_query_count = 3;
          max_research_loops = 3;
          break;
        case "high":
          initial_search_query_count = 5;
          max_research_loops = 10;
          break;
      }

      // 添加用户消息到聊天消息中
      const userMessage: Message = {
        type: "human",
        content: submittedInputValue,
        id: `user-${Date.now()}`,
      };
      setChatMessages(prev => [...prev, userMessage]);

      const newMessages: Message[] = [
        ...(chatMessages || []),
        userMessage,
      ];
      thread.submit({
        messages: newMessages,
        initial_search_query_count: initial_search_query_count,
        max_research_loops: max_research_loops,
        reasoning_model: model,
      });
    },
    [thread, chatMessages]
  );

  const handleCancel = useCallback(() => {
    thread.stop();
    window.location.reload();
  }, [thread]);

  return (
    <div className="flex h-screen bg-neutral-800 text-neutral-100 font-sans antialiased">
      <main className="h-full w-full max-w-4xl mx-auto">
          {chatMessages.length === 0 ? (
            <WelcomeScreen
              handleSubmit={handleSubmit}
              isLoading={thread.isLoading}
              onCancel={handleCancel}
            />
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="flex flex-col items-center justify-center gap-4">
                <h1 className="text-2xl text-red-400 font-bold">Error</h1>
                <p className="text-red-400">{JSON.stringify(error)}</p>

                <Button
                  variant="destructive"
                  onClick={() => window.location.reload()}
                >
                  Retry
                </Button>
              </div>
            </div>
          ) : (
            <ChatMessagesView
              messages={chatMessages}
              isLoading={thread.isLoading}
              scrollAreaRef={scrollAreaRef}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              liveActivityEvents={processedEventsTimeline}
              historicalActivities={historicalActivities}
            />
          )}
      </main>
    </div>
  );
}
