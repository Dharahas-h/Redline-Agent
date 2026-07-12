import { Box } from "@mui/material";
import type { ReactNode } from "react";

/**
 * Mono uppercase eyebrow with a 6px cobalt dot. One per screen, above the title.
 * The dark card (Complete) flips the dot to mint via `tone="mint"`.
 */
export default function Eyebrow({
  children,
  tone = "cobalt",
}: {
  children: ReactNode;
  tone?: "cobalt" | "mint";
}) {
  return (
    <Box
      component="span"
      className={tone === "mint" ? "vt-eyebrow vt-eyebrow--mint" : "vt-eyebrow"}
    >
      {children}
    </Box>
  );
}
