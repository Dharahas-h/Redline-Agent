import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Link,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/DownloadRounded";
import DescriptionIcon from "@mui/icons-material/DescriptionRounded";
import { createExport, exportDownloadUrl } from "../api/client";
import type { Export } from "../types";

// Generates a latest-vs-prior tracked-changes .docx for the negotiation, then
// surfaces a download link for the produced redline. Disabled while a redline
// is being generated; a negotiation needs two rounds before one can be made.
export function ExportButton({ negotiationId }: { negotiationId: number }) {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState<Export | null>(null);

  const generate = async () => {
    setGenerating(true);
    setError(null);
    setReady(null);
    try {
      setReady(await createExport(negotiationId));
    } catch {
      setError("Could not generate a redline (two rounds are required).");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <Paper
      component="section"
      aria-label="export-redline"
      variant="outlined"
      sx={{
        p: { xs: 2, md: 2.5 },
        borderRadius: 4,
        display: "flex",
        flexDirection: { xs: "column", sm: "row" },
        alignItems: { sm: "center" },
        justifyContent: "space-between",
        gap: 2,
      }}
    >
      <Box>
        <Typography sx={{ fontWeight: 600 }}>Tracked-changes redline</Typography>
        <Typography variant="body2" color="text.secondary">
          Generate a latest-vs-prior .docx for the negotiation.
        </Typography>
      </Box>

      <Stack spacing={1.5} sx={{ alignItems: { xs: "flex-start", sm: "flex-end" } }}>
        <Button
          type="button"
          variant="contained"
          onClick={generate}
          disabled={generating}
          startIcon={
            generating ? (
              <CircularProgress size={16} color="inherit" />
            ) : (
              <DescriptionIcon />
            )
          }
        >
          {generating ? "Generating redline…" : "Export redline"}
        </Button>

        {error && (
          <Alert severity="error" variant="outlined" data-testid="export-error" sx={{ borderRadius: 2 }}>
            {error}
          </Alert>
        )}

        {ready && (
          <Link
            data-testid="download-redline"
            href={exportDownloadUrl(ready.id)}
            download={ready.filename}
            underline="none"
            sx={{
              display: "inline-flex",
              alignItems: "center",
              gap: 0.75,
              fontWeight: 600,
            }}
          >
            <DownloadIcon fontSize="small" />
            Download {ready.filename}
          </Link>
        )}
      </Stack>
    </Paper>
  );
}
