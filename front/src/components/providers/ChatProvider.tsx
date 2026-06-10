"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  createChatThread,
  deleteChatThread,
  fetchThreadMessages,
  listChatThreads,
} from "@/src/lib/chat/threadsApi";
import {
  emptyConversation,
  historyToMessages,
  type ActivityStatus,
  type ChatMessage,
  type ConversationState,
  type StreamEvent,
} from "@/src/lib/chat/types";

function wsUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const url = new URL(base);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/chat";
  return url.toString();
}

type ChatContextValue = {
  conversations: ConversationState[];
  activeThreadId: string | null;
  activeConversation: ConversationState | null;
  isLoadingThreads: boolean;
  isStreaming: boolean;
  wsReady: boolean;
  selectConversation: (threadId: string) => Promise<void>;
  createConversation: () => Promise<void>;
  deleteConversation: (threadId: string) => Promise<void>;
  sendMessage: (content: string) => void;
};

const ChatContext = createContext<ChatContextValue | null>(null);

export function useChat(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error("useChat must be used within ChatProvider");
  }
  return ctx;
}

type AssistantDraft = {
  assistantId: string;
  buffer: string;
};

export function ChatProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<Record<string, ConversationState>>({});
  const [threadOrder, setThreadOrder] = useState<string[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [isLoadingThreads, setIsLoadingThreads] = useState(true);
  const [wsReady, setWsReady] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const intentionalCloseRef = useRef(false);
  const draftsRef = useRef<Map<string, AssistantDraft>>(new Map());

  const upsertConversation = useCallback(
    (threadId: string, patch: Partial<ConversationState>) => {
      setConversations((prev) => {
        const current = prev[threadId] ?? emptyConversation(threadId);
        const next: ConversationState = { ...current, ...patch };
        if (patch.messages === undefined) {
          next.messages = current.messages;
        }
        return { ...prev, [threadId]: next };
      });
    },
    [],
  );

  const applyStreamEvent = useCallback((data: StreamEvent) => {
    const threadId = data.thread_id;
    if (!threadId) return;

    if (data.type === "status") {
      upsertConversation(threadId, {
        activityStatus: data.status ?? "thinking",
        activityTool: data.tool ?? null,
      });
      return;
    }

    if (data.type === "token" && data.content) {
      const draft = draftsRef.current.get(threadId);
      if (!draft) return;
      draft.buffer += data.content;
      setConversations((prev) => {
        const conv = prev[threadId] ?? emptyConversation(threadId);
        const messages = conv.messages ?? [];
        return {
          ...prev,
          [threadId]: {
            ...conv,
            activityStatus: "writing",
            messages: messages.map((msg) =>
              msg.id === draft.assistantId ? { ...msg, content: draft.buffer } : msg,
            ),
          },
        };
      });
      return;
    }

    if (data.type === "done") {
      const draft = draftsRef.current.get(threadId);
      if (draft) {
        const buffered = draft.buffer.trim();
        setConversations((prev) => {
          const conv = prev[threadId] ?? emptyConversation(threadId);
          let messages = conv.messages ?? [];
          if (draft.assistantId && buffered) {
            messages = messages.map((msg) =>
              msg.id === draft.assistantId ? { ...msg, content: buffered } : msg,
            );
          } else if (draft.assistantId) {
            messages = messages.filter((msg) => msg.id !== draft.assistantId);
          }
          return {
            ...prev,
            [threadId]: {
              ...conv,
              messages,
              isStreaming: false,
              activityStatus: null,
              activityTool: null,
              activeAssistantId: null,
              error: buffered ? null : "Nestor n'a pas renvoyé de réponse.",
            },
          };
        });
        draftsRef.current.delete(threadId);
      } else {
        upsertConversation(threadId, {
          isStreaming: false,
          activityStatus: null,
          activityTool: null,
          activeAssistantId: null,
        });
      }
      return;
    }

    if (data.type === "error") {
      const draft = draftsRef.current.get(threadId);
      setConversations((prev) => {
        const conv = prev[threadId] ?? emptyConversation(threadId);
        let messages = conv.messages ?? [];
        if (draft?.assistantId && !draft.buffer.trim()) {
          messages = messages.filter((msg) => msg.id !== draft.assistantId);
        }
        return {
          ...prev,
          [threadId]: {
            ...conv,
            messages,
            isStreaming: false,
            activityStatus: null,
            activityTool: null,
            activeAssistantId: null,
            error: data.message ?? "Erreur de chat",
          },
        };
      });
      if (draft) draftsRef.current.delete(threadId);
    }
  }, [upsertConversation]);

  useEffect(() => {
    let unmounted = false;
    intentionalCloseRef.current = false;
    const socket = new WebSocket(wsUrl());
    wsRef.current = socket;

    socket.onopen = () => {
      if (unmounted) return;
      setWsReady(true);
    };

    socket.onmessage = (event) => {
      applyStreamEvent(JSON.parse(event.data) as StreamEvent);
    };

    socket.onerror = () => {
      if (unmounted || intentionalCloseRef.current) return;
      setWsReady(false);
    };

    socket.onclose = () => setWsReady(false);

    return () => {
      unmounted = true;
      intentionalCloseRef.current = true;
      socket.close();
      wsRef.current = null;
    };
  }, [applyStreamEvent]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const threads = await listChatThreads();
        if (cancelled) return;
        const map: Record<string, ConversationState> = {};
        for (const t of threads) {
          map[t.id] = emptyConversation(t.id, t.title);
        }
        setConversations(map);
        setThreadOrder(threads.map((t) => t.id));
        if (threads.length > 0) {
          const first = threads[0].id;
          setActiveThreadId(first);
          const history = await fetchThreadMessages(first);
          if (!cancelled) {
            setConversations((prev) => ({
              ...prev,
              [first]: {
                ...(prev[first] ?? emptyConversation(first)),
                messages: historyToMessages(history),
              },
            }));
          }
        }
      } catch {
        if (!cancelled) setConversations({});
      } finally {
        if (!cancelled) setIsLoadingThreads(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectConversation = useCallback(async (threadId: string) => {
    setActiveThreadId(threadId);
    try {
      const history = await fetchThreadMessages(threadId);
      setConversations((prev) => ({
        ...prev,
        [threadId]: {
          ...(prev[threadId] ?? emptyConversation(threadId)),
          messages: historyToMessages(history),
          error: null,
        },
      }));
    } catch {
      upsertConversation(threadId, { error: "Impossible de charger l'historique." });
    }
  }, [upsertConversation]);

  const createConversation = useCallback(async () => {
    const thread = await createChatThread();
    setConversations((prev) => ({
      ...prev,
      [thread.id]: emptyConversation(thread.id, thread.title),
    }));
    setThreadOrder((prev) => [thread.id, ...prev]);
    setActiveThreadId(thread.id);
  }, []);

  const deleteConversation = useCallback(async (threadId: string) => {
    await deleteChatThread(threadId);
    draftsRef.current.delete(threadId);
    setConversations((prev) => {
      const next = { ...prev };
      delete next[threadId];
      return next;
    });
    setThreadOrder((prev) => {
      const remaining = prev.filter((id) => id !== threadId);
      setActiveThreadId((current) => (current === threadId ? remaining[0] ?? null : current));
      return remaining;
    });
  }, []);

  const sendMessage = useCallback(
    (content: string) => {
      const trimmed = content.trim();
      const threadId = activeThreadId;
      const socket = wsRef.current;
      if (!trimmed || !threadId) return;
      const conv = conversations[threadId];
      if (conv?.isStreaming) return;
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        upsertConversation(threadId, {
          error: "Connexion au chat indisponible. Rechargez la page.",
        });
        return;
      }

      const userId = crypto.randomUUID();
      const assistantId = crypto.randomUUID();
      draftsRef.current.set(threadId, { assistantId, buffer: "" });

      setConversations((prev) => {
        const current = prev[threadId] ?? emptyConversation(threadId);
        return {
          ...prev,
          [threadId]: {
            ...current,
            error: null,
            isStreaming: true,
            activityStatus: "thinking",
            activityTool: null,
            activeAssistantId: assistantId,
            messages: [
              ...(current.messages ?? []),
              { id: userId, role: "user", content: trimmed },
              { id: assistantId, role: "assistant", content: "" },
            ],
          },
        };
      });

      socket.send(JSON.stringify({ content: trimmed, thread_id: threadId }));
    },
    [activeThreadId, conversations, upsertConversation],
  );

  const list = threadOrder
    .map((id) => conversations[id])
    .filter((conv): conv is ConversationState => Boolean(conv));
  const activeConversation = activeThreadId ? conversations[activeThreadId] ?? null : null;
  const isStreaming = list.some((conv) => conv.isStreaming);

  return (
    <ChatContext.Provider
      value={{
        conversations: list,
        activeThreadId,
        activeConversation,
        isLoadingThreads,
        isStreaming,
        wsReady,
        selectConversation,
        createConversation,
        deleteConversation,
        sendMessage,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export type { ChatMessage, ActivityStatus, ConversationState };
