import { ChatView } from "@/src/components/chat/ChatView";
import { ConversationSidebar } from "@/src/components/chat/ConversationSidebar";
import styles from "./chat-layout.module.css";

export default function ChatPage() {
  return (
    <div className={styles.layout}>
      <ConversationSidebar />
      <ChatView />
    </div>
  );
}
