import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Loader2,
  Activity,
  Info,
  Search,
  TextSearch,
  Brain,
  Pen,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useEffect, useState } from "react";

export interface ProcessedEvent {
  title: string;
  data: string | number | boolean | string[] | Record<string, unknown>;
  timestamp?: Date;
}

interface ActivityTimelineProps {
  processedEvents: ProcessedEvent[];
  isLoading: boolean;
}

export function ActivityTimeline({
  processedEvents,
  isLoading,
}: ActivityTimelineProps) {
  const [isTimelineCollapsed, setIsTimelineCollapsed] =
    useState<boolean>(false);
  const getEventIcon = (title: string, index: number) => {
    if (index === 0 && isLoading && processedEvents.length === 0) {
      return <Loader2 className="h-4 w-4 text-neutral-400 animate-spin" />;
    }
    
    const lowerTitle = title.toLowerCase();
    
    // 使用emoji图标来匹配不同的节点类型
    if (lowerTitle.includes("🔍") || lowerTitle.includes("生成搜索查询") || lowerTitle.includes("查询")) {
      return <TextSearch className="h-4 w-4 text-yellow-400" />;
    } else if (lowerTitle.includes("📚") || lowerTitle.includes("网络研究") || lowerTitle.includes("research") || lowerTitle.includes("研究") || lowerTitle.includes("搜索") || lowerTitle.includes("文档")) {
      return <Search className="h-4 w-4 text-blue-400" />;
    } else if (lowerTitle.includes("🤔") || lowerTitle.includes("研究反思") || lowerTitle.includes("reflection") || lowerTitle.includes("反思")) {
      return <Brain className="h-4 w-4 text-purple-400" />;
    } else if (lowerTitle.includes("⚖️") || lowerTitle.includes("评估") || lowerTitle.includes("evaluate")) {
      return <Activity className="h-4 w-4 text-orange-400" />;
    } else if (lowerTitle.includes("✨") || lowerTitle.includes("生成最终答案") || lowerTitle.includes("finalizing") || lowerTitle.includes("答案")) {
      return <Pen className="h-4 w-4 text-green-400" />;
    } else if (lowerTitle.includes("❌") || lowerTitle.includes("错误") || lowerTitle.includes("error")) {
      return <Activity className="h-4 w-4 text-red-400" />;
    } else if (lowerTitle.includes("🔧")) {
      return <Activity className="h-4 w-4 text-gray-400" />;
    }
    
    return <Activity className="h-4 w-4 text-neutral-400" />;
  };

  useEffect(() => {
    if (!isLoading && processedEvents.length !== 0) {
      setIsTimelineCollapsed(true);
    }
  }, [isLoading, processedEvents]);

  return (
    <Card className="border-none rounded-lg bg-neutral-700 max-h-96">
      <CardHeader>
        <CardDescription className="flex items-center justify-between">
          <div
            className="flex items-center justify-start text-sm w-full cursor-pointer gap-2 text-neutral-100"
            onClick={() => setIsTimelineCollapsed(!isTimelineCollapsed)}
          >
            Research
            {isTimelineCollapsed ? (
              <ChevronDown className="h-4 w-4 mr-2" />
            ) : (
              <ChevronUp className="h-4 w-4 mr-2" />
            )}
          </div>
        </CardDescription>
      </CardHeader>
      {!isTimelineCollapsed && (
        <ScrollArea className="max-h-96 overflow-y-auto">
          <CardContent>
            {isLoading && processedEvents.length === 0 && (
              <div className="relative pl-8 pb-4">
                <div className="absolute left-3 top-3.5 h-full w-0.5 bg-neutral-800" />
                <div className="absolute left-0.5 top-2 h-5 w-5 rounded-full bg-neutral-800 flex items-center justify-center ring-4 ring-neutral-900">
                  <Loader2 className="h-3 w-3 text-neutral-400 animate-spin" />
                </div>
                <div>
                  <p className="text-sm text-neutral-300 font-medium">
                    Searching...
                  </p>
                </div>
              </div>
            )}
            {processedEvents.length > 0 ? (
              <div className="space-y-0">
                {processedEvents.map((eventItem, index) => (
                  <div key={index} className="relative pl-8 pb-4">
                    {index < processedEvents.length - 1 ||
                    (isLoading && index === processedEvents.length - 1) ? (
                      <div className="absolute left-3 top-3.5 h-full w-0.5 bg-neutral-600" />
                    ) : null}
                    <div className="absolute left-0.5 top-2 h-6 w-6 rounded-full bg-neutral-600 flex items-center justify-center ring-4 ring-neutral-700">
                      {getEventIcon(eventItem.title, index)}
                    </div>
                    <div>
                      <p className="text-sm text-neutral-300 font-medium">
                        {eventItem.title}
                      </p>
                      <p className="text-xs text-neutral-400 mt-1 leading-relaxed">
                        {typeof eventItem.data === "string"
                          ? eventItem.data
                          : Array.isArray(eventItem.data)
                          ? (eventItem.data as string[]).join(", ")
                          : JSON.stringify(eventItem.data, null, 2)}
                      </p>
                      <p className="text-xs text-neutral-500 mt-1">
                        {eventItem.timestamp?.toLocaleTimeString() || new Date().toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
                {isLoading && processedEvents.length > 0 && (
                  <div className="relative pl-8 pb-4">
                    <div className="absolute left-0.5 top-2 h-5 w-5 rounded-full bg-neutral-600 flex items-center justify-center ring-4 ring-neutral-700">
                      <Loader2 className="h-3 w-3 text-neutral-400 animate-spin" />
                    </div>
                    <div>
                      <p className="text-sm text-neutral-300 font-medium">
                        Searching...
                      </p>
                    </div>
                  </div>
                )}
              </div>
            ) : !isLoading ? ( // Only show "No activity" if not loading and no events
              <div className="flex flex-col items-center justify-center h-full text-neutral-500 pt-10">
                <Info className="h-6 w-6 mb-3" />
                <p className="text-sm">No activity to display.</p>
                <p className="text-xs text-neutral-600 mt-1">
                  Timeline will update during processing.
                </p>
              </div>
            ) : null}
          </CardContent>
        </ScrollArea>
      )}
    </Card>
  );
}
