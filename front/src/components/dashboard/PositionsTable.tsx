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

function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString("fr-FR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} %`;
}

function formatSignedEuro(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  const sign = num > 0 ? "+" : "";
  return `${sign}${formatDecimal(String(num))} €`;
}

function pnlClass(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return styles.pnlFlat;
  }
  if (value > 0) return styles.pnlUp;
  if (value < 0) return styles.pnlDown;
  return styles.pnlFlat;
}

function PnlCell({
  pct,
  amount,
}: {
  pct: number | null | undefined;
  amount?: string | null;
}) {
  const label = formatPct(pct);
  const tone = pnlClass(pct);

  return (
    <td className={styles.pnlCell}>
      <span className={`${styles.pnlBadge} ${tone}`} title={amount ? formatSignedEuro(amount) : undefined}>
        {label}
      </span>
    </td>
  );
}

type Props = {
  holdings: HoldingRow[];
};

export function PositionsTable({ holdings }: Props) {
  const totals = holdings.reduce(
    (acc, row) => {
      const rowCost = costBasis(row.quantity, row.average_cost);
      acc.cost += rowCost;
      if (row.market_value != null) {
        acc.market += Number(row.market_value);
        acc.pricedCost += rowCost;
      }
      return acc;
    },
    { cost: 0, market: 0, pricedCost: 0 },
  );
  const totalPnlPct =
    totals.pricedCost > 0
      ? ((totals.market - totals.pricedCost) / totals.pricedCost) * 100
      : null;

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
              <PnlCell pct={row.gain_loss_pct} amount={row.unrealized_pnl} />
            </tr>
          ))}
        </tbody>
        {holdings.length > 0 && (
          <tfoot>
            <tr className={styles.totalRow}>
              <td colSpan={4} className={styles.totalLabel}>
                Total coût d&apos;acquisition
              </td>
              <td className={styles.num}>{formatDecimal(String(totals.cost))} €</td>
              <PnlCell pct={totalPnlPct} />
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
