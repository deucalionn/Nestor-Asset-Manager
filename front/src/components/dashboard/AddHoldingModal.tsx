"use client";

import { TransactionType } from "@/src/api/generated/nestorAssetManagerAPI.schemas";
import { useCreateIndexIndicesPost } from "@/src/api/generated/indices/indices";
import {
  getListIndicesIndicesGetQueryKey,
  useListIndicesIndicesGet,
} from "@/src/api/generated/indices/indices";
import {
  getListPositionsPositionsGetQueryKey,
} from "@/src/api/generated/positions/positions";
import { useCreateTransactionTransactionsPost } from "@/src/api/generated/transactions/transactions";
import { ApiError } from "@/src/api/mutator";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import styles from "./AddHoldingModal.module.css";

type Props = {
  open: boolean;
  onClose: () => void;
};

type Mode = "existing" | "new";

export function AddHoldingModal({ open, onClose }: Props) {
  const queryClient = useQueryClient();
  const indicesQuery = useListIndicesIndicesGet();
  const indices =
    indicesQuery.data?.status === 200 ? indicesQuery.data.data : [];

  const [mode, setMode] = useState<Mode>("existing");
  const [indexId, setIndexId] = useState("");
  const [newName, setNewName] = useState("");
  const [newIsin, setNewIsin] = useState("");
  const [price, setPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [fees, setFees] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const createIndex = useCreateIndexIndicesPost();
  const createTransaction = useCreateTransactionTransactionsPost();

  const reset = () => {
    setMode(indices.length > 0 ? "existing" : "new");
    setIndexId("");
    setNewName("");
    setNewIsin("");
    setPrice("");
    setQuantity("");
    setDate(new Date().toISOString().slice(0, 10));
    setFees("");
    setError(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      let targetIndexId = indexId;

      if (mode === "new") {
        if (!newName.trim() || !newIsin.trim()) {
          setError("Nom et ISIN sont requis.");
          setIsSubmitting(false);
          return;
        }
        const created = await createIndex.mutateAsync({
          data: { name: newName.trim(), isin: newIsin.trim().toUpperCase() },
        });
        if (created.status !== 201) {
          throw new Error("Impossible de créer l'indice.");
        }
        targetIndexId = created.data.id;
        await queryClient.invalidateQueries({
          queryKey: getListIndicesIndicesGetQueryKey(),
        });
      } else if (!targetIndexId) {
        setError("Sélectionnez un indice.");
        setIsSubmitting(false);
        return;
      }

      if (!price || !quantity || !date) {
        setError("Prix, quantité et date sont requis.");
        setIsSubmitting(false);
        return;
      }

      await createTransaction.mutateAsync({
        data: {
          index_id: targetIndexId,
          type: TransactionType.BUY,
          price,
          quantity,
          date,
          fees: fees || null,
        },
      });

      await queryClient.invalidateQueries({
        queryKey: getListPositionsPositionsGetQueryKey(),
      });

      handleClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Une erreur est survenue.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.overlay} onClick={handleClose} role="presentation">
      <div
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-holding-title"
      >
        <header className={styles.header}>
          <h2 id="add-holding-title">Ajouter une position</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose}>
            ×
          </button>
        </header>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.modeToggle}>
            <button
              type="button"
              className={mode === "existing" ? styles.modeActive : styles.modeBtn}
              onClick={() => setMode("existing")}
              disabled={indices.length === 0}
            >
              Indice existant
            </button>
            <button
              type="button"
              className={mode === "new" ? styles.modeActive : styles.modeBtn}
              onClick={() => setMode("new")}
            >
              Nouvel indice
            </button>
          </div>

          {mode === "existing" ? (
            <label className={styles.field}>
              <span>Indice</span>
              <select
                className={styles.input}
                value={indexId}
                onChange={(e) => setIndexId(e.target.value)}
              >
                <option value="">Sélectionner…</option>
                {indices.map((index) => (
                  <option key={index.id} value={index.id}>
                    {index.name} ({index.isin})
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <>
              <label className={styles.field}>
                <span>Nom</span>
                <input
                  className={styles.input}
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="CAC 40"
                />
              </label>
              <label className={styles.field}>
                <span>ISIN</span>
                <input
                  className={styles.input}
                  value={newIsin}
                  onChange={(e) => setNewIsin(e.target.value)}
                  placeholder="FR0003500008"
                  maxLength={12}
                />
              </label>
            </>
          )}

          <div className={styles.row}>
            <label className={styles.field}>
              <span>Prix unitaire (€)</span>
              <input
                className={styles.input}
                type="number"
                step="any"
                min="0"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </label>
            <label className={styles.field}>
              <span>Quantité</span>
              <input
                className={styles.input}
                type="number"
                step="any"
                min="0"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </label>
          </div>

          <div className={styles.row}>
            <label className={styles.field}>
              <span>Date</span>
              <input
                className={styles.input}
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </label>
            <label className={styles.field}>
              <span>Frais (€)</span>
              <input
                className={styles.input}
                type="number"
                step="any"
                min="0"
                value={fees}
                onChange={(e) => setFees(e.target.value)}
                placeholder="Optionnel"
              />
            </label>
          </div>

          {error && <p className={styles.error}>{error}</p>}

          <div className={styles.actions}>
            <button type="button" className={styles.btnSecondary} onClick={handleClose}>
              Annuler
            </button>
            <button type="submit" className={styles.btnPrimary} disabled={isSubmitting}>
              {isSubmitting ? "Enregistrement…" : "Enregistrer l'achat"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
