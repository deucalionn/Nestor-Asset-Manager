"use client";

import type { IndexRead, PositionRead } from "@/src/api/generated/nestorAssetManagerAPI.schemas";
import styles from "./PositionsTable.module.css";

export type HoldingRow = PositionRead & {
  indexName: string;
  indexIsin: string;
};

function formatDecimal(value: string, digits = 2): string {
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  return num.toLocaleString("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function costBasis(quantity: string, averageCost: string): number {
  return Number(quantity) * Number(averageCost);
}

type Props = {
  holdings: HoldingRow[];
};

export function PositionsTable({ holdings }: Props) {
  const totalCost = holdings.reduce(
    (sum, row) => sum + costBasis(row.quantity, row.average_cost),
    0,
  );

  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Indice</th>
            <th>ISIN</th>
            <th className={styles.num}>Quantité</th>
            <th className={styles.num}>PRU</th>
            <th className={styles.num}>Coût</th>
            <th className={styles.num}>P/L</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((row) => (
            <tr key={row.id}>
              <td className={styles.name}>{row.indexName}</td>
              <td className={styles.isin}>{row.indexIsin}</td>
              <td className={styles.num}>{formatDecimal(row.quantity, 4)}</td>
              <td className={styles.num}>{formatDecimal(row.average_cost)} €</td>
              <td className={styles.num}>
                {formatDecimal(String(costBasis(row.quantity, row.average_cost)))} €
              </td>
              <td className={`${styles.num} ${styles.placeholder}`}>—</td>
            </tr>
          ))}
        </tbody>
        {holdings.length > 0 && (
          <tfoot>
            <tr className={styles.totalRow}>
              <td colSpan={4} className={styles.totalLabel}>
                Total coût d&apos;acquisition
              </td>
              <td className={styles.num}>{formatDecimal(String(totalCost))} €</td>
              <td className={`${styles.num} ${styles.placeholder}`}>—</td>
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );
}

export function joinHoldings(
  positions: PositionRead[],
  indices: IndexRead[],
): HoldingRow[] {
  const indexMap = new Map(indices.map((i) => [i.id, i]));
  return positions.map((position) => {
    const index = indexMap.get(position.index_id);
    return {
      ...position,
      indexName: index?.name ?? "Indice inconnu",
      indexIsin: index?.isin ?? "—",
    };
  });
}
