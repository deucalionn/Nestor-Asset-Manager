"use client";

import { ApiError } from "@/src/api/mutator";
import { useGetProfileProfileGet } from "@/src/api/generated/profile/profile";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function HomePage() {
  const router = useRouter();
  const query = useGetProfileProfileGet({ query: { retry: false } });

  useEffect(() => {
    if (query.isLoading) return;

    const hasProfile =
      query.isSuccess && query.data.status === 200 && Boolean(query.data.data);
    const isNotFound =
      query.isError &&
      query.error instanceof ApiError &&
      query.error.status === 404;

    if (hasProfile) {
      router.replace("/dashboard");
    } else if (isNotFound || query.isError) {
      router.replace("/onboarding");
    }
  }, [query.isLoading, query.isSuccess, query.isError, query.data, query.error, router]);

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
