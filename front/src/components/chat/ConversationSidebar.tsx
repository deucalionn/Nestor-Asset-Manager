"use client";

import { useChat } from "@/src/components/providers/ChatProvider";
import styles from "./ConversationSidebar.module.css";

function formatRelative(iso: string): string {
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "À l'instant";
  if (mins < 60) return `Il y a ${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `Il y a ${hours} h`;
  return date.toLocaleDateString("fr-FR");
}

export function ConversationSidebar() {
  const {
    conversations,
    activeThreadId,
    isLoadingThreads,
    selectConversation,
    createConversation,
    deleteConversation,
  } = useChat();

  return (
    <aside className={styles.sidebar}>
      <button type="button" className={styles.newButton} onClick={() => void createConversation()}>
        + Nouvelle conversation
      </button>
      <div className={styles.list}>
        {isLoadingThreads ? (
          <p className={styles.empty}>Chargement…</p>
        ) : conversations.length === 0 ? (
          <p className={styles.empty}>Aucune conversation</p>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.threadId}
              className={
                conv.threadId === activeThreadId
                  ? `${styles.item} ${styles.itemActive}`
                  : styles.item
              }
            >
              <button
                type="button"
                className={styles.itemButton}
                onClick={() => void selectConversation(conv.threadId)}
              >
                <span className={styles.itemTitle}>{conv.title}</span>
                {conv.isStreaming ? <span className={styles.streaming}>…</span> : null}
              </button>
              <button
                type="button"
                className={styles.deleteButton}
                aria-label="Supprimer"
                onClick={() => void deleteConversation(conv.threadId)}
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
