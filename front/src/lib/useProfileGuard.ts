"use client";

import { ApiError } from "@/src/api/mutator";
import { useGetProfileProfileGet } from "@/src/api/generated/profile/profile";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

export function useProfileGuard() {
  const router = useRouter();
  const pathname = usePathname();
  const query = useGetProfileProfileGet({
    query: { retry: false },
  });

  const hasProfile =
    query.isSuccess && query.data.status === 200 && Boolean(query.data.data);
  const isNotFound =
    query.isError &&
    query.error instanceof ApiError &&
    query.error.status === 404;

  useEffect(() => {
    if (query.isLoading) return;

    if (pathname.startsWith("/onboarding")) {
      if (hasProfile) router.replace("/dashboard");
      return;
    }

    if (pathname.startsWith("/dashboard") && (isNotFound || !hasProfile)) {
      router.replace("/onboarding");
    }
  }, [
    hasProfile,
    isNotFound,
    pathname,
    query.isLoading,
    router,
  ]);

  return {
    isLoading: query.isLoading,
    hasProfile,
    profile: hasProfile ? query.data.data : undefined,
  };
}
