"use client";

import {
  Strategy,
  type UserCreate,
} from "@/src/api/generated/nestorAssetManagerAPI.schemas";
import { useSetupProfileSetupPost, getGetProfileProfileGetQueryKey } from "@/src/api/generated/profile/profile";
import { STRATEGY_OPTIONS } from "@/src/lib/strategies";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import styles from "./OnboardingWizard.module.css";

const STEPS = ["Identité", "Stratégie", "Objectifs"] as const;

type FormState = {
  firstname: string;
  date_of_birth: string;
  strategy: Strategy | "";
  goals: string;
};

const initialForm: FormState = {
  firstname: "",
  date_of_birth: "",
  strategy: "",
  goals: "",
};

function validateStep(step: number, form: FormState): string | null {
  if (step === 0) {
    if (!form.firstname.trim()) return "Le prénom est requis.";
    if (!form.date_of_birth) return "La date de naissance est requise.";
    const dob = new Date(form.date_of_birth);
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const monthDiff = today.getMonth() - dob.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
      age -= 1;
    }
    if (age < 18) return "Vous devez avoir au moins 18 ans.";
    return null;
  }
  if (step === 1) {
    if (!form.strategy) return "Choisissez une stratégie.";
    return null;
  }
  if (step === 2) {
    if (!form.goals.trim()) return "Décrivez vos objectifs.";
    return null;
  }
  return null;
}

export function OnboardingWizard() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<FormState>(initialForm);
  const [error, setError] = useState<string | null>(null);

  const setup = useSetupProfileSetupPost({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getGetProfileProfileGetQueryKey(),
        });
        router.replace("/dashboard");
      },
      onError: (err) => setError(err.message),
    },
  });

  const update = (patch: Partial<FormState>) => {
    setForm((prev) => ({ ...prev, ...patch }));
    setError(null);
  };

  const goNext = () => {
    const validationError = validateStep(step, form);
    if (validationError) {
      setError(validationError);
      return;
    }
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };

  const goBack = () => {
    setError(null);
    setStep((s) => Math.max(s - 1, 0));
  };

  const submit = () => {
    const validationError = validateStep(2, form);
    if (validationError) {
      setError(validationError);
      return;
    }

    const payload: UserCreate = {
      firstname: form.firstname.trim(),
      date_of_birth: form.date_of_birth,
      strategy: form.strategy as Strategy,
      goals: form.goals.trim(),
    };

    setup.mutate({ data: payload });
  };

  const stepTitles = [
    "Créez votre profil",
    "Choisissez votre stratégie",
    "Définissez vos objectifs",
  ];

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.progress}>
          {STEPS.map((_, index) => (
            <div
              key={index}
              className={
                index <= step
                  ? `${styles.progressSegment} ${styles.progressSegmentActive}`
                  : styles.progressSegment
              }
            />
          ))}
        </div>

        <div className={styles.header}>
          <div className={styles.iconCircle}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z"
                stroke="currentColor"
                strokeWidth="1.5"
              />
              <path
                d="M4 20c0-3.314 3.582-6 8-6s8 2.686 8 6"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <p className={styles.eyebrow}>Bienvenue à bord</p>
          <h1 className={styles.title}>{stepTitles[step]}</h1>
          <p className={styles.subtitle}>
            Étape {step + 1} sur {STEPS.length} — {STEPS[step]}
          </p>
        </div>

        <div className={styles.form}>
          {step === 0 && (
            <>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>
                  <span className={styles.fieldNumber}>1</span>
                  Prénom
                </span>
                <input
                  className={styles.input}
                  type="text"
                  value={form.firstname}
                  onChange={(e) => update({ firstname: e.target.value })}
                  placeholder="Jean"
                  autoFocus
                />
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>
                  <span className={styles.fieldNumber}>2</span>
                  Date de naissance
                </span>
                <input
                  className={styles.input}
                  type="date"
                  value={form.date_of_birth}
                  onChange={(e) => update({ date_of_birth: e.target.value })}
                />
              </label>
            </>
          )}

          {step === 1 && (
            <div className={styles.strategyGrid}>
              {STRATEGY_OPTIONS.map((option, index) => (
                <button
                  key={option.value}
                  type="button"
                  className={
                    form.strategy === option.value
                      ? `${styles.strategyCard} ${styles.strategyCardSelected}`
                      : styles.strategyCard
                  }
                  onClick={() => update({ strategy: option.value })}
                >
                  <span className={styles.fieldNumber}>{index + 1}</span>
                  <span className={styles.strategyLabel}>{option.label}</span>
                  <span className={styles.strategyDescription}>
                    {option.description}
                  </span>
                </button>
              ))}
            </div>
          )}

          {step === 2 && (
            <>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>
                  <span className={styles.fieldNumber}>1</span>
                  Vos objectifs
                </span>
                <textarea
                  className={`${styles.input} ${styles.textarea}`}
                  rows={4}
                  value={form.goals}
                  onChange={(e) => update({ goals: e.target.value })}
                  placeholder="Ex. Constituer un capital retraite d'ici 2040…"
                  autoFocus
                />
              </label>

              <div className={styles.review}>
                <h2 className={styles.reviewTitle}>Récapitulatif</h2>
                <dl className={styles.reviewList}>
                  <div>
                    <dt>Prénom</dt>
                    <dd>{form.firstname}</dd>
                  </div>
                  <div>
                    <dt>Naissance</dt>
                    <dd>{form.date_of_birth}</dd>
                  </div>
                  <div>
                    <dt>Stratégie</dt>
                    <dd>
                      {
                        STRATEGY_OPTIONS.find((o) => o.value === form.strategy)
                          ?.label
                      }
                    </dd>
                  </div>
                </dl>
              </div>
            </>
          )}

          {error && <p className={styles.error}>{error}</p>}
        </div>

        <div className={styles.actions}>
          {step > 0 && (
            <button type="button" className={styles.btnSecondary} onClick={goBack}>
              ← Retour
            </button>
          )}
          {step < STEPS.length - 1 ? (
            <button type="button" className={styles.btnPrimary} onClick={goNext}>
              Étape suivante →
            </button>
          ) : (
            <button
              type="button"
              className={styles.btnPrimary}
              onClick={submit}
              disabled={setup.isPending}
            >
              {setup.isPending ? "Création…" : "Terminer →"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
