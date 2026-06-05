import { Strategy } from "@/src/api/generated/nestorAssetManagerAPI.schemas";

export const STRATEGY_OPTIONS: {
  value: Strategy;
  label: string;
  description: string;
}[] = [
  {
    value: Strategy.CONSERVATIVE,
    label: "Prudent",
    description: "Priorité à la préservation du capital et aux revenus stables.",
  },
  {
    value: Strategy.BALANCED,
    label: "Équilibré",
    description: "Mix croissance / sécurité pour un profil intermédiaire.",
  },
  {
    value: Strategy.GROWTH,
    label: "Croissance",
    description: "Orientation long terme avec volatilité modérée acceptée.",
  },
  {
    value: Strategy.AGGRESSIVE,
    label: "Dynamique",
    description: "Maximiser la performance avec une tolérance au risque élevée.",
  },
];

export function strategyLabel(value: Strategy): string {
  return STRATEGY_OPTIONS.find((o) => o.value === value)?.label ?? value;
}
