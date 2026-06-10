import { customFetch } from "@/src/api/mutator";
import type { ChatThreadSummary } from "./types";

type ApiBody<T> = { data: T };

export async function listChatThreads(): Promise<ChatThreadSummary[]> {
  const res = await customFetch<ApiBody<ChatThreadSummary[]>>("/chat/threads");
  return res.data;
}

export async function createChatThread(title?: string): Promise<ChatThreadSummary> {
  const res = await customFetch<ApiBody<ChatThreadSummary>>("/chat/threads", {
    method: "POST",
    body: JSON.stringify(title ? { title } : {}),
  });
  return res.data;
}

export async function deleteChatThread(threadId: string): Promise<void> {
  await customFetch<void>("/chat/threads/" + threadId, { method: "DELETE" });
}

export async function fetchThreadMessages(
  threadId: string,
): Promise<{ role: string; content: string }[]> {
  const res = await customFetch<ApiBody<{ role: string; content: string }[]>>(
    `/chat/threads/${threadId}/messages`,
  );
  return res.data;
}
