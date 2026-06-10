export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export type ChatThreadSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ActivityStatus = "thinking" | "tool" | "writing" | null;

export type StreamEvent = {
  type: "token" | "status" | "done" | "error";
  content?: string;
  status?: "thinking" | "tool" | "writing";
  tool?: string;
  thread_id?: string;
  message?: string;
};

export type ConversationState = {
  threadId: string;
  title: string;
  messages: ChatMessage[];
  isStreaming: boolean;
  activityStatus: ActivityStatus;
  activityTool: string | null;
  activeAssistantId: string | null;
  error: string | null;
};

export function emptyConversation(threadId: string, title = "New conversation"): ConversationState {
  return {
    threadId,
    title,
    messages: [],
    isStreaming: false,
    activityStatus: null,
    activityTool: null,
    activeAssistantId: null,
    error: null,
  };
}

export function historyToMessages(rows: { role: string; content: string }[]): ChatMessage[] {
  return rows.map((row) => ({
    id: crypto.randomUUID(),
    role: row.role === "user" ? "user" : "assistant",
    content: row.content,
  }));
}
