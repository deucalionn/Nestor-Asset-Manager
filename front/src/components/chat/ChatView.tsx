"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ChatMarkdown } from "./ChatMarkdown";
import styles from "./ChatView.module.css";

const THREAD_STORAGE_KEY = "nam_chat_thread_id";

function loadThreadId(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(THREAD_STORAGE_KEY);
}

function saveThreadId(threadId: string) {
  sessionStorage.setItem(THREAD_STORAGE_KEY, threadId);
}

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type ActivityStatus = "thinking" | "tool" | "writing" | null;

type StreamEvent = {
  type: "token" | "status" | "done" | "error";
  content?: string;
  status?: "thinking" | "tool" | "writing";
  tool?: string;
  thread_id?: string;
  message?: string;
};

function wsUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const url = new URL(base);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/chat";
  return url.toString();
}

function activityLabel(status: ActivityStatus, tool: string | null): string {
  if (status === "tool" && tool) return tool;
  if (status === "writing") return "Rédaction de la réponse…";
  return "Nestor réfléchit…";
}

export function ChatView() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState<string | null>(loadThreadId);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activityStatus, setActivityStatus] = useState<ActivityStatus>(null);
  const [activityTool, setActivityTool] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const intentionalCloseRef = useRef(false);
  const listRef = useRef<HTMLDivElement>(null);
  const assistantBufferRef = useRef("");
  const assistantIdRef = useRef<string | null>(null);
  const isStreamingRef = useRef(false);
  const [activeAssistantId, setActiveAssistantId] = useState<string | null>(null);
  const [wsReady, setWsReady] = useState(false);

  useEffect(() => {
    isStreamingRef.current = isStreaming;
  }, [isStreaming]);

  useEffect(() => {
    let unmounted = false;
    intentionalCloseRef.current = false;
    const socket = new WebSocket(wsUrl());
    wsRef.current = socket;

    socket.onopen = () => {
      if (unmounted) return;
      setWsReady(true);
      setError(null);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data) as StreamEvent;
      if (data.type === "status") {
        setActivityStatus(data.status ?? "thinking");
        setActivityTool(data.tool ?? null);
      } else if (data.type === "token" && data.content) {
        setActivityStatus("writing");
        assistantBufferRef.current += data.content;
        const assistantId = assistantIdRef.current;
        if (!assistantId) return;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: assistantBufferRef.current }
              : msg,
          ),
        );
      } else if (data.type === "done") {
        if (data.thread_id) {
          setThreadId(data.thread_id);
          saveThreadId(data.thread_id);
        }
        const assistantId = assistantIdRef.current;
        const buffered = assistantBufferRef.current;
        if (assistantId && buffered.trim()) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId ? { ...msg, content: buffered } : msg,
            ),
          );
        } else if (assistantId) {
          setMessages((prev) => prev.filter((msg) => msg.id !== assistantId));
          setError("Nestor n'a pas renvoyé de réponse. Réessayez dans un instant.");
        }
        setIsStreaming(false);
        setActivityStatus(null);
        setActivityTool(null);
        assistantIdRef.current = null;
        setActiveAssistantId(null);
        assistantBufferRef.current = "";
      } else if (data.type === "error") {
        const assistantId = assistantIdRef.current;
        if (assistantId && !assistantBufferRef.current.trim()) {
          setMessages((prev) => prev.filter((msg) => msg.id !== assistantId));
        }
        setError(data.message ?? "Erreur de chat");
        setIsStreaming(false);
        setActivityStatus(null);
        setActivityTool(null);
        assistantIdRef.current = null;
        setActiveAssistantId(null);
        assistantBufferRef.current = "";
      }
    };

    socket.onerror = () => {
      if (unmounted || intentionalCloseRef.current) return;
      setWsReady(false);
      setError("Connexion WebSocket impossible");
      setIsStreaming(false);
      setActivityStatus(null);
    };

    socket.onclose = () => {
      setWsReady(false);
      if (unmounted) return;
      if (
        isStreamingRef.current &&
        !assistantBufferRef.current.trim() &&
        assistantIdRef.current
      ) {
        const assistantId = assistantIdRef.current;
        setMessages((prev) => prev.filter((msg) => msg.id !== assistantId));
        setError(
          "La connexion a été interrompue pendant l'analyse. Réessayez (nouvelle conversation conseillée).",
        );
      }
      setIsStreaming(false);
      setActivityStatus(null);
      setActivityTool(null);
      assistantIdRef.current = null;
      setActiveAssistantId(null);
    };

    return () => {
      unmounted = true;
      intentionalCloseRef.current = true;
      socket.close();
      wsRef.current = null;
    };
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, activityStatus, activityTool]);

  const sendMessage = useCallback(
    (event: FormEvent) => {
      event.preventDefault();
      const content = input.trim();
      const socket = wsRef.current;
      if (!content || isStreaming) {
        return;
      }
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        setError("Connexion au chat indisponible. Rechargez la page.");
        return;
      }

      setError(null);
      setInput("");
      setIsStreaming(true);
      setActivityStatus("thinking");
      setActivityTool(null);

      const userId = crypto.randomUUID();
      const assistantId = crypto.randomUUID();
      assistantIdRef.current = assistantId;
      setActiveAssistantId(assistantId);
      assistantBufferRef.current = "";

      setMessages((prev) => [
        ...prev,
        { id: userId, role: "user", content },
        { id: assistantId, role: "assistant", content: "" },
      ]);

      socket.send(
        JSON.stringify({
          content,
          ...(threadId ? { thread_id: threadId } : {}),
        }),
      );
    },
    [input, isStreaming, threadId],
  );

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Chat</h1>
        <p className={styles.subtitle}>
          Posez vos questions à Nestor — analyses, portefeuille, marchés.
        </p>
      </header>

      <div className={styles.panel}>
        <div ref={listRef} className={styles.messages}>
          {messages.length === 0 ? (
            <p className={styles.empty}>Démarrez une conversation avec Nestor.</p>
          ) : (
            messages.map((msg, index) => {
              const isLastAssistant =
                msg.role === "assistant" &&
                !messages.slice(index + 1).some((m) => m.role === "assistant");
              const isActiveAssistant =
                msg.role === "assistant" &&
                isStreaming &&
                !msg.content &&
                (msg.id === activeAssistantId || isLastAssistant);

              return (
                <div
                  key={msg.id}
                  className={
                    msg.role === "user" ? styles.messageUser : styles.messageAssistant
                  }
                >
                  <span className={styles.messageRole}>
                    {msg.role === "user" ? "Vous" : "Nestor"}
                  </span>
                  <div
                    className={
                      msg.role === "user"
                        ? `${styles.messageBody} ${styles.messageBodyUser}`
                        : `${styles.messageBody} ${styles.messageBodyAssistant}`
                    }
                  >
                    {msg.role === "user" ? (
                      msg.content
                    ) : msg.content ? (
                      <ChatMarkdown content={msg.content} />
                    ) : isActiveAssistant ? (
                      <div className={styles.activity} aria-live="polite">
                        <span className={styles.activityDots} aria-hidden="true">
                          <span />
                          <span />
                          <span />
                        </span>
                        <span className={styles.activityText}>
                          {activityLabel(activityStatus, activityTool)}
                        </span>
                      </div>
                    ) : (
                      <span className={styles.activityText}>
                        Réponse indisponible — réessayez.
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {error ? <p className={styles.error}>{error}</p> : null}

        <form className={styles.form} onSubmit={sendMessage}>
          <input
            className={styles.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Votre message…"
            disabled={isStreaming}
            maxLength={16000}
          />
          <button
            className={styles.sendButton}
            type="submit"
            disabled={isStreaming || !input.trim() || !wsReady}
          >
            {isStreaming ? "En cours…" : !wsReady ? "Connexion…" : "Envoyer"}
          </button>
        </form>
      </div>
    </div>
  );
}
