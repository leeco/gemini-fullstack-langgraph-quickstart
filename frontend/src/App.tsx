import { useStream } from "@langchain/langgraph-sdk/react";
import type { Message } from "@langchain/langgraph-sdk";
import { useState, useEffect, useRef, useCallback } from "react";
import { ProcessedEvent } from "@/components/ActivityTimeline";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { ChatMessagesView } from "@/components/ChatMessagesView";
import { Button } from "@/components/ui/button";

/**
 * The main application component that orchestrates the chat interface,
 * handles streaming data from the backend, and manages application state.
 */
export default function App() {
  /**
   * State for storing the timeline of processed events from the backend graph.
   * These are displayed in the activity timeline.
   */
  const [processedEventsTimeline, setProcessedEventsTimeline] = useState<
    ProcessedEvent[]
  >([]);
  /**
   * State for storing historical activities for each AI message.
   * The key is the AI message ID, and the value is the list of events for that message.
   */
  const [historicalActivities, setHistoricalActivities] = useState<
    Record<string, ProcessedEvent[]>
  >({});
  /**
   * State for storing the chat messages displayed in the UI.
   */
  const [chatMessages, setChatMessages] = useState<Message[]>([]);
  /**
   * Ref for the scroll area component to programmatically scroll to the bottom.
   */
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  /**
   * Ref to track if the 'finalize_answer' event has occurred.
   * This helps in associating the activity timeline with the correct AI message.
   */
  const hasFinalizeEventOccurredRef = useRef(false);
  /**
   * State for storing any errors that occur during the stream.
   */
  const [error, setError] = useState<string | null>(null);

  /**
   * `useStream` hook from LangGraph SDK to manage the connection to the backend.
   * It handles streaming events and provides methods to interact with the stream.
   */
  const thread = useStream<{
    messages: Message[];
    initial_search_query_count: number;
    max_research_loops: number;
    reasoning_model: string;
  }>({
    apiUrl: import.meta.env.DEV
      ? "http://localhost:2024" // Development API URL
      : "http://localhost:8123", // Production API URL
    assistantId: "agent",
    // We manually handle messages, so messagesKey is not used.
    /**
     * Callback for handling update events from the LangGraph stream.
     * This function processes events from different nodes in the graph
     * and updates the activity timeline.
     * @param {Record<string, any>} event - The event object from the stream.
     */
                // Disabled onUpdateEvent - now using onCustomEvent instead
      // onUpdateEvent: (data: unknown) => { ... },
      
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      onCustomEvent: (data: unknown, options?: any) => {
        let processedEvent: ProcessedEvent | null = null;
        
        try {
          // Detailed debug log for incoming custom events.
          console.log("Received custom event:", JSON.stringify(data, null, 2));
          
          // Process custom event data
          if (data && typeof data === 'object') {
            const eventData = data as Record<string, any>;
            
            // Handle LangGraph node events with langgraph_node field
            if (eventData.langgraph_node && eventData.message) {
              const nodeName = eventData.langgraph_node;
              const message = eventData.message;
              
              console.log(`Custom event - Node ${nodeName}:`, message);
              
              // Only messages from the 'finalize_answer' node are added to the chat.
              if (nodeName === "finalize_answer") {
                // Add the final answer message to the chat messages.
                const aiMessage = {
                  type: "ai" as const,
                  content: message,
                  id: `finalize-${Date.now()}`,
                };
                setChatMessages(prev => [...prev, aiMessage]);
                hasFinalizeEventOccurredRef.current = true;
              }
              
              // Create different timeline events based on the node name.
              switch (nodeName) {
                case "generate_query": {
                  // Extract query information from message
                  processedEvent = {
                    title: "🔍 Generating Search Queries",
                    data: message.length > 150 ? message.substring(0, 150) + '...' : message,
                  };
                  break;
                }
                case "web_research": {
                  processedEvent = {
                    title: "🌐 Web Research",
                    data: message.length > 150 ? message.substring(0, 150) + '...' : message,
                  };
                  break;
                }
                case "doc_research": {
                  // Extract document count and relevance info
                  const docCount = (message.match(/共返回(\d+)个/)?.[1]) || "unknown";
                  const relevanceInfo = message.includes("相关度") ? `Found ${docCount} relevant documents` : "Searching knowledge base";
                  
                  processedEvent = {
                    title: "📚 Knowledge Base Research",
                    data: relevanceInfo + (message.length > 100 ? ` - ${message.substring(0, 100)}...` : ` - ${message}`),
                  };
                  break;
                }
                case "reflection": {
                  try {
                    // Try to parse JSON reflection data
                    const reflectionData = JSON.parse(message);
                    const isSufficient = reflectionData.is_sufficient;
                    const knowledgeGap = reflectionData.knowledge_gap;
                    const followUpQueries = reflectionData.follow_up_queries || [];
                    
                    let details = [];
                    if (isSufficient !== undefined) {
                      details.push(isSufficient ? "✅ Research results are sufficient" : "⚠️ Further research needed");
                    }
                    if (knowledgeGap) {
                      details.push(`Knowledge Gap: ${knowledgeGap.length > 80 ? knowledgeGap.substring(0, 80) + '...' : knowledgeGap}`);
                    }
                    if (followUpQueries.length > 0) {
                      details.push(`Follow-up queries: ${followUpQueries.length} planned`);
                    }
                    
                    processedEvent = {
                      title: "🤔 Research Reflection",
                      data: details.length > 0 ? details.join(" | ") : "Analyzing research results...",
                    };
                  } catch {
                    // Fallback if message is not JSON
                    processedEvent = {
                      title: "🤔 Research Reflection",
                      data: message.length > 150 ? message.substring(0, 150) + '...' : message,
                    };
                  }
                  break;
                }
                case "evaluate_research": {
                  processedEvent = {
                    title: "⚖️ Evaluating Research Progress",
                    data: message,
                  };
                  break;
                }
                case "finalize_answer": {
                  processedEvent = {
                    title: "✨ Generating Final Answer",
                    data: "Consolidating all research findings to generate a comprehensive answer...",
                  };
                  break;
                }
                default: {
                  // For unknown nodes, display the message
                  processedEvent = {
                    title: `🔧 ${nodeName}`,
                    data: message.length > 150 ? message.substring(0, 150) + '...' : message,
                  };
                  break;
                }
              }
            } else {
              // Handle other types of custom events (fallback)
              switch (eventData.type) {
                case 'progress_update':
                  processedEvent = {
                    title: "📊 Progress Update",
                    data: eventData.message || "Progress update received",
                  };
                  break;
                case 'error_occurred':
                  setError(eventData.message || 'An unknown error occurred');
                  processedEvent = {
                    title: "❌ Error",
                    data: eventData.message || "An error occurred",
                  };
                  break;
                case 'status_change':
                  processedEvent = {
                    title: "🔄 Status Change",
                    data: eventData.message || "Status changed",
                  };
                  break;
                default:
                  // Handle unknown event format
                  processedEvent = {
                    title: "📢 Custom Event",
                    data: `Received: ${JSON.stringify(eventData).substring(0, 100)}...`,
                  };
                  break;
              }
            }
          }
        } catch (error) {
          console.error("Error processing custom event:", error);
          processedEvent = {
            title: "❌ Custom Event Processing Error",
            data: `An error occurred during custom event processing: ${error instanceof Error ? error.message : String(error)}`,
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

  /**
   * Effect to scroll the chat view to the bottom whenever new messages are added.
   */
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

  /**
   * Effect to associate the completed activity timeline with the last AI message.
   * This runs when the stream is no longer loading and a final answer has been generated.
   */
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

  /**
   * Callback to handle form submission.
   * It sends the user's message and configuration to the backend.
   * @param {string} submittedInputValue - The user's input message.
   * @param {string} effort - The selected effort level ('low', 'medium', 'high').
   * @param {string} model - The selected reasoning model.
   */
  const handleSubmit = useCallback(
    (submittedInputValue: string, effort: string, model: string) => {
      if (!submittedInputValue.trim()) return;
      setProcessedEventsTimeline([]);
      hasFinalizeEventOccurredRef.current = false;

      // Convert effort to initial_search_query_count and max_research_loops.
      // low: max 1 loop and 1 query
      // medium: max 3 loops and 3 queries
      // high: max 10 loops and 5 queries
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

      // Add user message to the chat.
      const userMessage: Message = {
        type: "human",
        content: submittedInputValue,
        id: `user-${Date.now()}`,
      };
      setChatMessages(prev => [...prev, userMessage]);

      // Prepare the messages to be sent to the backend.
      const newMessages: Message[] = [
        ...(chatMessages || []),
        userMessage,
      ];
      // Submit the message and configuration to the stream.
      thread.submit({
        messages: newMessages,
        initial_search_query_count: initial_search_query_count,
        max_research_loops: max_research_loops,
        reasoning_model: model,
      });
    },
    [thread, chatMessages]
  );

  /**
   * Callback to handle stream cancellation.
   * Stops the stream and reloads the page.
   */
  const handleCancel = useCallback(() => {
    thread.stop();
    window.location.reload();
  }, [thread]);

  return (
    <div className="flex h-screen bg-neutral-800 text-neutral-100 font-sans antialiased">
      <main className="h-full w-full max-w-4xl mx-auto">
          {chatMessages.length === 0 ? (
            // Display the welcome screen if there are no messages.
            <WelcomeScreen
              handleSubmit={handleSubmit}
              isLoading={thread.isLoading}
              onCancel={handleCancel}
            />
          ) : error ? (
            // Display an error message if an error occurs.
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
            // Display the chat messages view.
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
