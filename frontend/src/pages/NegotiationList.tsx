import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardActionArea,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/AddRounded";
import { createNegotiation, listNegotiations } from "../api/client";
import type { Negotiation } from "../types";
import Eyebrow from "../components/common/Eyebrow";
import SerifHeading from "../components/common/SerifHeading";
import { C } from "../components/common/redline";

export function NegotiationList({
  onSelect,
}: {
  onSelect: (id: number) => void;
}) {
  const [items, setItems] = useState<Negotiation[]>([]);
  const [title, setTitle] = useState("");
  const [party, setParty] = useState("");

  const refresh = () => listNegotiations().then(setItems);
  useEffect(() => {
    refresh();
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !party) return;
    await createNegotiation(title, party);
    setTitle("");
    setParty("");
    await refresh();
  };

  return (
    <Stack spacing={4}>
      <Box>
        <Eyebrow>Negotiations</Eyebrow>
        <SerifHeading variant="h2" sx={{ mt: 1 }}>
          Track every <em>redline</em> across rounds.
        </SerifHeading>
      </Box>

      <Paper variant="outlined" sx={{ p: { xs: 2.5, md: 3 }, borderRadius: 5 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          New negotiation
        </Typography>
        <Box component="form" onSubmit={submit} aria-label="create-negotiation">
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            sx={{ alignItems: { sm: "flex-start" } }}
          >
            <TextField
              label="Contract title"
              placeholder="e.g. Acme MSA"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              inputProps={{ "aria-label": "title" }}
              fullWidth
            />
            <TextField
              label="Party you represent"
              placeholder="e.g. Buyer"
              value={party}
              onChange={(e) => setParty(e.target.value)}
              inputProps={{ "aria-label": "represented_party" }}
              fullWidth
            />
            <Button
              type="submit"
              variant="contained"
              startIcon={<AddIcon />}
              sx={{ flexShrink: 0, height: 56 }}
            >
              Create negotiation
            </Button>
          </Stack>
        </Box>
      </Paper>

      {items.length === 0 ? (
        <Paper
          variant="outlined"
          sx={{
            p: 6,
            borderRadius: 5,
            textAlign: "center",
            borderStyle: "dashed",
          }}
        >
          <SerifHeading variant="h5" sx={{ color: "text.secondary" }}>
            No negotiations yet.
          </SerifHeading>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Create your first negotiation above to start tracking redlines.
          </Typography>
        </Paper>
      ) : (
        <Stack spacing={1.5}>
          {items.map((n) => (
            <Card key={n.id} variant="outlined">
              <CardActionArea
                onClick={() => onSelect(n.id)}
                sx={{ p: 2.5, display: "block" }}
              >
                <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
                  {n.title} — representing {n.represented_party}
                </Typography>
                <Typography
                  variant="body2"
                  sx={{ mt: 0.5, color: C.cobalt, fontWeight: 600 }}
                >
                  Open negotiation →
                </Typography>
              </CardActionArea>
            </Card>
          ))}
        </Stack>
      )}
    </Stack>
  );
}
