"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useChat } from "@/src/components/providers/ChatProvider";
import styles from "./AppShell.module.css";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Portefeuille", enabled: true },
  { href: "/chat", label: "Chat", enabled: true },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isStreaming } = useChat();

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>N</span>
          <span className={styles.brandName}>Nestor</span>
        </div>
        <nav className={styles.nav}>
          {NAV_ITEMS.map((item) =>
            item.enabled ? (
              <Link
                key={item.href}
                href={item.href}
                className={
                  pathname.startsWith(item.href)
                    ? `${styles.navLink} ${styles.navLinkActive}`
                    : styles.navLink
                }
              >
                <span>{item.label}</span>
                {item.href === "/chat" && isStreaming ? (
                  <span className={styles.streamingBadge} title="Réponse en cours">
                    …
                  </span>
                ) : null}
              </Link>
            ) : (
              <span
                key={item.href}
                className={`${styles.navLink} ${styles.navLinkDisabled}`}
                title="Bientôt disponible"
              >
                {item.label}
                <span className={styles.badge}>Soon</span>
              </span>
            ),
          )}
        </nav>
      </aside>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
