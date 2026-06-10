"use client";

import { useListIndicesIndicesGet } from "@/src/api/generated/indices/indices";
import { useListPositionsPositionsGet } from "@/src/api/generated/positions/positions";
import { useProfileGuard } from "@/src/lib/useProfileGuard";
import { useState } from "react";
import { AddHoldingModal } from "./AddHoldingModal";
import { joinHoldings, PositionsTable } from "./PositionsTable";
import { RecommendationsSection } from "./RecommendationsSection";
import styles from "./DashboardView.module.css";

export function DashboardView() {
  const { profile, isLoading: profileLoading } = useProfileGuard();
  const positionsQuery = useListPositionsPositionsGet();
  const indicesQuery = useListIndicesIndicesGet();
  const [modalOpen, setModalOpen] = useState(false);

  const isLoading =
    profileLoading || positionsQuery.isLoading || indicesQuery.isLoading;

  const positions =
    positionsQuery.data?.status === 200 ? positionsQuery.data.data : [];
  const indices =
    indicesQuery.data?.status === 200 ? indicesQuery.data.data : [];
  const holdings = joinHoldings(positions, indices);

  if (isLoading) {
    return <div className={styles.loading}>Chargement du portefeuille…</div>;
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>
            Bonjour{profile?.firstname ? `, ${profile.firstname}` : ""}
          </h1>
          <p className={styles.subtitle}>Vue d&apos;ensemble de votre portefeuille</p>
        </div>
        <button
          type="button"
          className={styles.addBtn}
          onClick={() => setModalOpen(true)}
        >
          + Ajouter une position
        </button>
      </header>

      {holdings.length === 0 ? (
        <div className={styles.empty}>
          <p className={styles.emptyTitle}>Aucune position pour le moment</p>
          <p className={styles.emptyText}>
            Commencez par enregistrer un achat sur un indice ou ETF.
          </p>
          <button
            type="button"
            className={styles.addBtn}
            onClick={() => setModalOpen(true)}
          >
            Ajouter ma première position
          </button>
        </div>
      ) : (
        <PositionsTable holdings={holdings} />
      )}

      <RecommendationsSection />

      <AddHoldingModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
}
