import { Box, Chip } from "@mui/material";
import type { ReactNode } from "react";

// Viljetech token subset the redline domain leans on. The verdict pair
// (forest / terracotta) is reserved for favored-party — the one signal an
// attorney reads first — and never reused for the diff text or change type.
export const C = {
  slate: "#7C8E9D",
  cloud: "#DDE3E8",
  snow: "#F6F9FC",
  navy: "#1B2D45",
  cobalt: "#3A63E0",
  primaryInk: "#2849B8",
  primaryWash: "#E1E7FB",
  forest: "#2E7D66",
  forestInk: "#1E5346",
  forestWash: "#CCDED7",
  terracotta: "#C16236",
  terracottaInk: "#8C4221",
  terracottaWash: "#F1D9CB",
  saffron: "#A6841B",
  saffronWash: "#F3ECD2",
} as const;

const MONO = '"JetBrains Mono", ui-monospace, monospace';

const CHANGE_TYPE_LABELS: Record<string, string> = {
  added: "Added",
  removed: "Removed",
  modified: "Modified",
};

// change_type stays deliberately colorless — a mono eyebrow label — so the
// verdict palette is never diluted. testid/class preserved for the suite.
export function ChangeTypeLabel({ type }: { type: string }) {
  return (
    <Box
      component="span"
      className={`change-type ${type}`}
      data-testid="change-type"
      sx={{
        fontFamily: MONO,
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color: C.slate,
      }}
    >
      {CHANGE_TYPE_LABELS[type] ?? type}
    </Box>
  );
}

function Pill({
  children,
  className,
  testId,
  role,
  bg,
  fg,
  border,
}: {
  children: ReactNode;
  className: string;
  testId: string;
  role?: string;
  bg: string;
  fg: string;
  border?: string;
}) {
  return (
    <Chip
      size="small"
      label={children}
      className={className}
      data-testid={testId}
      role={role}
      sx={{
        bgcolor: bg,
        color: fg,
        border: border ? `1px solid ${border}` : "none",
        fontWeight: 600,
        fontSize: 12,
      }}
    />
  );
}

const MATERIALITY_LABELS: Record<string, string> = {
  substantive: "Substantive",
  cosmetic: "Cosmetic",
};

// Substantive earns the cobalt wash; cosmetic is a quiet slate outline.
export function MaterialityBadge({ materiality }: { materiality: string }) {
  const substantive = materiality === "substantive";
  return (
    <Pill
      className={`materiality-badge ${materiality}`}
      testId="materiality-badge"
      bg={substantive ? C.primaryWash : "transparent"}
      fg={substantive ? C.primaryInk : C.slate}
      border={substantive ? undefined : C.cloud}
    >
      {MATERIALITY_LABELS[materiality] ?? materiality}
    </Pill>
  );
}

// Favored-party is stored relative to the represented party, so it maps
// straight to the attorney's point of view — and carries the verdict color.
const FAVORED_PARTY_LABELS: Record<string, string> = {
  represented: "Favors me",
  counterparty: "Favors them",
  neutral: "Neutral",
};

export function FavoredPartyBadge({ favored }: { favored: string }) {
  const style =
    favored === "represented"
      ? { bg: C.forestWash, fg: C.forestInk, border: undefined }
      : favored === "counterparty"
        ? { bg: C.terracottaWash, fg: C.terracottaInk, border: undefined }
        : { bg: "transparent", fg: C.slate, border: C.cloud };
  return (
    <Pill
      className={`favored-party-badge ${favored}`}
      testId="favored-party-badge"
      bg={style.bg}
      fg={style.fg}
      border={style.border}
    >
      {FAVORED_PARTY_LABELS[favored] ?? favored}
    </Pill>
  );
}

const CATEGORY_LABELS: Record<string, string> = {
  payment: "Payment",
  liability: "Liability",
  ip: "IP",
  termination: "Termination",
  confidentiality: "Confidentiality",
  other: "Other",
};

export function CategoryTag({ category }: { category: string }) {
  return (
    <Pill
      className={`category-tag ${category}`}
      testId="category-tag"
      bg="transparent"
      fg={C.slate}
      border={C.cloud}
    >
      {CATEGORY_LABELS[category] ?? category}
    </Pill>
  );
}
