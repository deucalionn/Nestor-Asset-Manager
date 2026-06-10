"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useChat, type ActivityStatus } from "@/src/components/providers/ChatProvider";
import { ChatMarkdown } from "./ChatMarkdown";
import styles from "./ChatView.module.css";

function activityLabel(status: ActivityStatus, tool: string | null): string {
  if (status === "tool" && tool) return tool;
  if (status === "writing") return "Rédaction de la réponse…";
  return "Nestor réfléchit…";
}

export function ChatView() {
  const { activeConversation, wsReady, sendMessage } = useChat();
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  const messages = activeConversation?.messages ?? [];
  const isStreaming = activeConversation?.isStreaming ?? false;
  const activityStatus = activeConversation?.activityStatus ?? null;
  const activityTool = activeConversation?.activityTool ?? null;
  const activeAssistantId = activeConversation?.activeAssistantId ?? null;
  const error = activeConversation?.error ?? null;

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, activityStatus, activityTool]);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const content = input.trim();
    if (!content || isStreaming || !activeConversation) return;
    sendMessage(content);
    setInput("");
  };

  if (!activeConversation) {
    return (
      <div className={styles.container}>
        <p className={styles.empty}>Créez une conversation pour commencer.</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>{activeConversation.title}</h1>
        <p className={styles.subtitle}>Posez vos questions à Nestor — analyses, portefeuille, marchés.</p>
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
                      <span className={styles.activityText}>Réponse indisponible — réessayez.</span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {error ? <p className={styles.error}>{error}</p> : null}

        <form className={styles.form} onSubmit={handleSubmit}>
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
