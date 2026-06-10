"use client";

import { AppShell } from "@/src/components/layout/AppShell";
import { ChatProvider } from "@/src/components/providers/ChatProvider";
import { useProfileGuard } from "@/src/lib/useProfileGuard";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isLoading } = useProfileGuard();

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--color-text-muted)",
        }}
      >
        Chargement…
      </div>
    );
  }

  return (
    <ChatProvider>
      <AppShell>{children}</AppShell>
    </ChatProvider>
  );
}
