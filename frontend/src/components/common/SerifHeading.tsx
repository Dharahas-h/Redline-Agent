import { Typography } from "@mui/material";
import type { TypographyProps } from "@mui/material";
import type { ReactNode } from "react";

const SERIF = '"Kalice", "Cormorant Garamond", "Times New Roman", serif';

/**
 * Kalice serif heading that carries an italic-cobalt fragment via `<em>`:
 *   <SerifHeading>Start a new <em>screening workflow.</em></SerifHeading>
 * On the dark card, pass tone="mint" to flip the italic fragment to mint.
 * Styling-only — no state, no Redux.
 */
export default function SerifHeading({
  children,
  variant = "h3",
  tone = "cobalt",
  sx,
  ...rest
}: {
  children: ReactNode;
  tone?: "cobalt" | "mint";
} & TypographyProps) {
  const emColor = tone === "mint" ? "#8DD3D2" : "#3A63E0";
  return (
    <Typography
      variant={variant}
      sx={{
        fontFamily: SERIF,
        fontWeight: 400,
        "& em": {
          fontStyle: "italic",
          fontFamily: SERIF,
          color: emColor,
        },
        ...sx,
      }}
      {...rest}
    >
      {children}
    </Typography>
  );
}
