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
        // 处理节点更新事件 - LangGraph SDK的onUpdateEvent接收的是节点更新
        if (event && typeof event === 'object') {
          // 处理节点更新事件
          for (const nodeName of Object.keys(event)) {
            if (event[nodeName] && typeof event[nodeName] === 'object') {
              // 只有 finalize_answer 节点的消息才添加到对话中
              if (nodeName === "finalize_answer" && event[nodeName].messages) {
                // 添加最终答案消息到聊天消息中
                const newMessages = event[nodeName].messages.map((msg: any, index: number) => ({
                  ...msg,
                  id: `finalize-${Date.now()}-${index}`,
                }));
                setChatMessages(prev => [...prev, ...newMessages]);
              }
              
              // 根据节点名称创建不同的时间线事件
              switch (nodeName) {
                case "generate_query": {
                  processedEvent = {
                    title: "生成搜索查询",
                    data: `生成了 ${event[nodeName].search_query?.length || 0} 个查询`,
                  };
                  break;
                }
                case "web_research":
                case "doc_research": {
                  const sources = event[nodeName].sources_gathered || [];
                  processedEvent = {
                    title: "文档研究",
                    data: `收集了 ${sources.length} 个资源`,
                  };
                  break;
                }
                case "reflection": {
                  processedEvent = {
                    title: "研究反思",
                    data: event[nodeName].is_sufficient 
                      ? "研究结果充足，准备生成答案"
                      : "需要进一步研究",
                  };
                  break;
                }
                case "finalize_answer": {
                  processedEvent = {
                    title: "生成最终答案",
                    data: "正在整合研究结果生成最终答案...",
                  };
                  hasFinalizeEventOccurredRef.current = true;
                  break;
                }
                default: {
                  // 对于未知节点，显示基本信息
                  processedEvent = {
                    title: `节点: ${nodeName}`,
                    data: "节点执行完成",
                  };
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
          title: "处理错误",
          data: "事件处理过程中发生错误",
        };
      }
      
      if (processedEvent) {
        setProcessedEventsTimeline((prevEvents) => [
          ...prevEvents,
          processedEvent!,
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
