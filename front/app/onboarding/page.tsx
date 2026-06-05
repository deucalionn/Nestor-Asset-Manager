"use client";

import { OnboardingWizard } from "@/src/components/onboarding/OnboardingWizard";
import { useProfileGuard } from "@/src/lib/useProfileGuard";

export default function OnboardingPage() {
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

  return <OnboardingWizard />;
}
