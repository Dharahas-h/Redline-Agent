import { useState } from "react";
import {
  AppBar,
  Box,
  Button,
  Container,
  Divider,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBackRounded";
import { NegotiationList } from "./pages/NegotiationList";
import { NegotiationDetail } from "./pages/NegotiationDetail";
import Eyebrow from "./components/common/Eyebrow";

export default function App() {
  const [selected, setSelected] = useState<number | null>(null);

  return (
    <Box sx={{ minHeight: "100vh" }}>
      <AppBar position="sticky">
        <Toolbar sx={{ gap: 2 }}>
          <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
            <Box>
              <Typography
                variant="subtitle1"
                sx={{ fontWeight: 700, lineHeight: 1.1, letterSpacing: "-0.01em" }}
              >
                Redline&nbsp;Agent
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Contract negotiation intelligence
              </Typography>
            </Box>
            <Divider
              orientation="vertical"
              flexItem
              sx={{ mx: 0.5, my: 1, borderColor: "divider" }}
            />
            <Box sx={{ display: { xs: "none", sm: "block" } }}>
              <Eyebrow>Attorney work-product — for review</Eyebrow>
            </Box>
          </Stack>
        </Toolbar>
      </AppBar>

      <Container
        maxWidth={selected === null ? "md" : "lg"}
        sx={{ py: { xs: 3, md: 5 } }}
      >
        {selected === null ? (
          <NegotiationList onSelect={setSelected} />
        ) : (
          <Stack spacing={3}>
            <Button
              onClick={() => setSelected(null)}
              startIcon={<ArrowBackIcon />}
              color="inherit"
              sx={{ alignSelf: "flex-start", color: "text.secondary", px: 1 }}
            >
              All negotiations
            </Button>
            <NegotiationDetail negotiationId={selected} />
          </Stack>
        )}
      </Container>
    </Box>
  );
}
