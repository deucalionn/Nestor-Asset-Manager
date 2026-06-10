"use client";

import {
  getListRecommendationsRecommendationsGetQueryKey,
  useListRecommendationsRecommendationsGet,
  useUpdateRecommendationRecommendationsRecommendationIdPatch,
} from "@/src/api/generated/recommendations/recommendations";
import type {
  RecommendationRead,
  RecommendationStatus,
  RecommendationType,
} from "@/src/api/generated/nestorAssetManagerAPI.schemas";
import { RecommendationStatus as StatusEnum } from "@/src/api/generated/nestorAssetManagerAPI.schemas";
import { ChatMarkdown } from "@/src/components/chat/ChatMarkdown";
import { ApiError } from "@/src/api/mutator";
import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import styles from "./RecommendationsSection.module.css";

type Filter = "pending" | "history";

const TYPE_LABELS: Record<RecommendationType, string> = {
  BUY: "Acheter",
  HOLD: "Conserver",
  SELL: "Vendre",
};

const STATUS_LABELS: Record<RecommendationStatus, string> = {
  PENDING: "En attente",
  APPLIED: "Acceptée",
  REJECTED: "Refusée",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function typeBadgeClass(type: RecommendationType): string {
  if (type === "BUY") return `${styles.badge} ${styles.badgeBuy}`;
  if (type === "SELL") return `${styles.badge} ${styles.badgeSell}`;
  return `${styles.badge} ${styles.badgeHold}`;
}

function statusClass(status: RecommendationStatus): string {
  if (status === "PENDING") return `${styles.status} ${styles.statusPending}`;
  if (status === "APPLIED") return `${styles.status} ${styles.statusApplied}`;
  return `${styles.status} ${styles.statusRejected}`;
}

type RecommendationCardProps = {
  recommendation: RecommendationRead;
};

function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const queryClient = useQueryClient();
  const update = useUpdateRecommendationRecommendationsRecommendationIdPatch();
  const [comment, setComment] = useState("");
  const [showAnalyses, setShowAnalyses] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isPending = recommendation.status === StatusEnum.PENDING;
  const analyses = recommendation.analyses ?? [];
  const isBusy = update.isPending;

  const handleResolve = async (status: typeof StatusEnum.APPLIED | typeof StatusEnum.REJECTED) => {
    setError(null);
    try {
      const response = await update.mutateAsync({
        recommendationId: recommendation.id,
        data: {
          status,
          user_comment: comment.trim() || null,
        },
      });
      if (response.status !== 200) {
        setError("Impossible de mettre à jour la recommandation.");
        return;
      }
      await queryClient.invalidateQueries({
        queryKey: getListRecommendationsRecommendationsGetQueryKey(),
      });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Impossible de mettre à jour la recommandation.";
      setError(message);
    }
  };

  return (
    <article className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={typeBadgeClass(recommendation.type)}>
          {TYPE_LABELS[recommendation.type]}
        </span>
        <span className={statusClass(recommendation.status)}>
          {STATUS_LABELS[recommendation.status]}
        </span>
        <time className={styles.date} dateTime={recommendation.created_at}>
          {formatDate(recommendation.created_at)}
        </time>
      </div>

      <div className={styles.content}>
        <ChatMarkdown content={recommendation.content} />
      </div>

      {analyses.length > 0 && (
        <div className={styles.analyses}>
          <button
            type="button"
            className={styles.analysesToggle}
            onClick={() => setShowAnalyses((open) => !open)}
            aria-expanded={showAnalyses}
          >
            {showAnalyses
              ? "Masquer les analyses liées"
              : `Voir les analyses liées (${analyses.length})`}
          </button>
          {showAnalyses && (
            <ul className={styles.analysesList}>
              {analyses.map((analysis) => (
                <li key={analysis.id} className={styles.analysisItem}>
                  {analysis.title}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {recommendation.user_comment && (
        <p className={styles.userComment}>
          Votre commentaire : {recommendation.user_comment}
        </p>
      )}

      {isPending && (
        <div className={styles.actions}>
          <div className={styles.commentField}>
            <label className={styles.commentLabel} htmlFor={`comment-${recommendation.id}`}>
              Commentaire (optionnel)
            </label>
            <textarea
              id={`comment-${recommendation.id}`}
              className={styles.commentInput}
              rows={2}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Ex. ordre passé chez mon courtier…"
              disabled={isBusy}
            />
          </div>
          <div className={styles.actionButtons}>
            <button
              type="button"
              className={styles.acceptBtn}
              disabled={isBusy}
              onClick={() => handleResolve(StatusEnum.APPLIED)}
            >
              Accepter
            </button>
            <button
              type="button"
              className={styles.rejectBtn}
              disabled={isBusy}
              onClick={() => handleResolve(StatusEnum.REJECTED)}
            >
              Refuser
            </button>
          </div>
        </div>
      )}

      {error && <p className={styles.cardError}>{error}</p>}
    </article>
  );
}

export function RecommendationsSection() {
  const [filter, setFilter] = useState<Filter>("pending");
  const query = useListRecommendationsRecommendationsGet(undefined, {
    query: {
      refetchInterval: filter === "pending" ? 60_000 : false,
    },
  });

  const recommendations = useMemo(() => {
    if (query.data?.status !== 200) return [];
    const items = [...query.data.data];
    items.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
    return items;
  }, [query.data]);

  const filtered = useMemo(() => {
    if (filter === "pending") {
      return recommendations.filter((item) => item.status === StatusEnum.PENDING);
    }
    return recommendations.filter((item) => item.status !== StatusEnum.PENDING);
  }, [filter, recommendations]);

  const pendingCount = recommendations.filter(
    (item) => item.status === StatusEnum.PENDING,
  ).length;

  return (
    <section className={styles.section} aria-labelledby="recommendations-heading">
      <div className={styles.header}>
        <h2 id="recommendations-heading" className={styles.title}>
          Recommandations
          {pendingCount > 0 && filter !== "history" ? ` (${pendingCount})` : ""}
        </h2>
        <div className={styles.tabs} role="tablist" aria-label="Filtrer les recommandations">
          <button
            type="button"
            role="tab"
            aria-selected={filter === "pending"}
            className={`${styles.tab} ${filter === "pending" ? styles.tabActive : ""}`}
            onClick={() => setFilter("pending")}
          >
            En attente
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={filter === "history"}
            className={`${styles.tab} ${filter === "history" ? styles.tabActive : ""}`}
            onClick={() => setFilter("history")}
          >
            Historique
          </button>
        </div>
      </div>

      {query.isLoading && (
        <p className={styles.loading}>Chargement des recommandations…</p>
      )}

      {query.isError && (
        <p className={styles.error}>Impossible de charger les recommandations.</p>
      )}

      {!query.isLoading && !query.isError && filtered.length === 0 && (
        <p className={styles.empty}>
          {filter === "pending"
            ? "Aucune recommandation en attente. Nestor vous proposera des actions après ses cycles d'analyse."
            : "Aucune recommandation dans l'historique."}
        </p>
      )}

      {!query.isLoading && !query.isError && filtered.length > 0 && (
        <div className={styles.list}>
          {filtered.map((recommendation) => (
            <RecommendationCard key={recommendation.id} recommendation={recommendation} />
          ))}
        </div>
      )}
    </section>
  );
}
