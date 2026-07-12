import { useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardActionArea,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import UploadIcon from "@mui/icons-material/UploadFileRounded";
import { getNegotiation, listRounds, uploadRound } from "../api/client";
import type { NegotiationDetail as Detail, Round } from "../types";
import { ChangeFeed } from "../components/ChangeFeed";
import { ExportButton } from "../components/ExportButton";
import Eyebrow from "../components/common/Eyebrow";
import SerifHeading from "../components/common/SerifHeading";
import { C } from "../components/common/redline";

export function NegotiationDetail({ negotiationId }: { negotiationId: number }) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [party, setParty] = useState("");
  const [fileName, setFileName] = useState("");
  const [selectedRound, setSelectedRound] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = async () => {
    setDetail(await getNegotiation(negotiationId));
    setRounds(await listRounds(negotiationId));
  };
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [negotiationId]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file || !party) return;
    const round = await uploadRound(negotiationId, party, file);
    if (fileRef.current) fileRef.current.value = "";
    setParty("");
    setFileName("");
    await refresh();
    setSelectedRound(round.id);
  };

  if (!detail)
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );

  return (
    <Stack spacing={4}>
      <Box>
        <Eyebrow>Representing {detail.represented_party}</Eyebrow>
        <SerifHeading variant="h2" sx={{ mt: 1 }}>
          {detail.title}
        </SerifHeading>
      </Box>

      <Paper variant="outlined" sx={{ p: { xs: 2.5, md: 3 }, borderRadius: 5 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Upload a round
        </Typography>
        <Box component="form" onSubmit={submit} aria-label="upload-round">
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            sx={{ alignItems: { sm: "center" } }}
          >
            <TextField
              label="Submitted by party"
              placeholder="e.g. Seller"
              value={party}
              onChange={(e) => setParty(e.target.value)}
              inputProps={{ "aria-label": "submitted_by_party" }}
              fullWidth
            />
            <Button
              component="label"
              variant="outlined"
              startIcon={<UploadIcon />}
              sx={{ flexShrink: 0, height: 56, whiteSpace: "nowrap" }}
            >
              {fileName || "Choose .docx"}
              <input
                hidden
                aria-label="round-file"
                type="file"
                accept=".docx"
                ref={fileRef}
                onChange={(e) => setFileName(e.target.files?.[0]?.name ?? "")}
              />
            </Button>
            <Button
              type="submit"
              variant="contained"
              sx={{ flexShrink: 0, height: 56 }}
            >
              Upload round
            </Button>
          </Stack>
        </Box>
      </Paper>

      <ExportButton negotiationId={negotiationId} />

      <Box>
        <Eyebrow>Rounds</Eyebrow>
        {rounds.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            No rounds uploaded yet — upload a redlined .docx to begin.
          </Typography>
        ) : (
          <Stack spacing={1.5} sx={{ mt: 2 }}>
            {rounds.map((r) => {
              const active = selectedRound === r.id;
              return (
                <Card
                  key={r.id}
                  variant="outlined"
                  sx={{
                    borderColor: active ? C.cobalt : C.cloud,
                    bgcolor: active ? C.primaryWash : "background.paper",
                  }}
                >
                  <CardActionArea
                    onClick={() => setSelectedRound(r.id)}
                    sx={{
                      p: 2,
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 2,
                    }}
                  >
                    <Typography sx={{ fontWeight: 600 }}>
                      Round {r.round_no} — {r.submitted_by_party}
                    </Typography>
                    <Chip
                      size="small"
                      label={r.status}
                      sx={{
                        textTransform: "capitalize",
                        bgcolor: active ? "#fff" : C.snow,
                        color: C.slate,
                        border: `1px solid ${C.cloud}`,
                      }}
                    />
                  </CardActionArea>
                </Card>
              );
            })}
          </Stack>
        )}
      </Box>

      {selectedRound !== null && <ChangeFeed roundId={selectedRound} />}
    </Stack>
  );
}
