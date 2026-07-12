import { createTheme } from "@mui/material/styles";

const SERIF = '"Kalice", "Cormorant Garamond", "Times New Roman", serif';
const MONO = '"JetBrains Mono", ui-monospace, monospace';

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#3A63E0", // cobalt — the one accent
      dark: "#2849B8", // primary-ink (pressed / hover-dark)
      light: "#E1E7FB", // primary-wash (tinted active backgrounds)
      contrastText: "#F6F9FC",
    },
    secondary: {
      main: "#1B2D45", // navy / ink
      light: "#2A3F5A",
      dark: "#0E1B2C",
      contrastText: "#F6F9FC",
    },
    background: {
      default: "#F6F9FC", // snow
      paper: "#FFFFFF",
    },
    text: {
      primary: "#1B2D45", // navy ink
      secondary: "#7C8E9D", // slate
    },
    divider: "#DDE3E8", // cloud / hairline
    // Status palette remapped to the brand (ResumeUpload chips, generic Alerts).
    // ScreeningResults verdicts do NOT use these — they hardcode forest/terra.
    success: { main: "#2E7D66", contrastText: "#F6F9FC" }, // forest
    error: { main: "#C16236", contrastText: "#F6F9FC" }, // terracotta
    warning: { main: "#A6841B", contrastText: "#F6F9FC" }, // saffron-ink
    info: { main: "#3A63E0", contrastText: "#F6F9FC" }, // cobalt
  },
  shape: {
    borderRadius: 12,
  },
  typography: {
    fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
    // Big titles → Kalice serif (decision #6). Everything else stays Inter.
    h1: {
      fontFamily: SERIF,
      fontWeight: 400,
      letterSpacing: "-0.02em",
      lineHeight: 1.1,
    },
    h2: {
      fontFamily: SERIF,
      fontWeight: 400,
      letterSpacing: "-0.02em",
      lineHeight: 1.12,
    },
    h3: {
      fontFamily: SERIF,
      fontWeight: 400,
      letterSpacing: "-0.01em",
      lineHeight: 1.18,
    },
    h4: { fontWeight: 600, letterSpacing: "-0.01em" },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    button: { fontWeight: 600 },
    overline: {
      fontFamily: MONO,
      fontWeight: 500,
      letterSpacing: "0.14em",
      textTransform: "uppercase",
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: "#F6F9FC",
          backgroundImage: "none",
          minHeight: "100vh",
        },
      },
    },
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
      styleOverrides: {
        root: {
          textTransform: "none",
          borderRadius: 999,
          paddingInline: 20,
          boxShadow: "none",
          "&:active": {
            transform: "translateY(0.5px)",
          },
          "&.Mui-focusVisible": {
            boxShadow: "0 0 0 3px rgba(58, 99, 224, 0.28)",
          },
          "&.MuiButton-containedPrimary:hover": {
            backgroundColor: "#0E1B2C", // navy CTA hover, no shadow/scale
            boxShadow: "none",
          },
        },
        outlined: {
          borderColor: "#DDE3E8",
          "&:hover": {
            borderColor: "#DDE3E8",
            backgroundColor: "#DDE3E8",
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
        outlined: {
          borderColor: "#DDE3E8",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          borderColor: "#DDE3E8",
          boxShadow: "none",
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          "&.MuiChip-outlined": {
            borderColor: "#DDE3E8",
          },
          "&.MuiChip-filledPrimary": {
            backgroundColor: "#E1E7FB", // cobalt wash
            color: "#2849B8",
          },
          "&.MuiChip-filledPrimary:hover": {
            backgroundColor: "#D2DBFA",
          },
          "&.MuiChip-filledPrimary .MuiChip-deleteIcon": {
            color: "#2849B8",
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "rgba(246, 249, 252, 0.86)",
          backdropFilter: "blur(8px)",
          color: "#1B2D45",
          borderBottom: "1px solid #DDE3E8",
          boxShadow: "none",
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: "outlined",
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          backgroundColor: "#FFFFFF",
          "&:hover .MuiOutlinedInput-notchedOutline": {
            borderColor: "#C3CBD3", // fog
          },
          "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
            borderColor: "#3A63E0",
          },
          "&.Mui-focused": {
            boxShadow: "0 0 0 3px rgba(58, 99, 224, 0.28)",
          },
        },
        notchedOutline: {
          borderColor: "#DDE3E8",
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: {
          backgroundColor: "#3A63E0",
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 600,
          "&.Mui-selected": {
            color: "#1B2D45",
          },
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: "#1B2D45",
          color: "#F6F9FC",
          borderRadius: 12,
          boxShadow: "0 24px 48px -28px rgba(27, 45, 69, 0.22)",
          fontSize: 12,
        },
        arrow: {
          color: "#1B2D45",
        },
      },
    },
    MuiCircularProgress: {
      styleOverrides: {
        root: {
          color: "#3A63E0",
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        bar: {
          backgroundColor: "#3A63E0",
        },
      },
    },
    MuiPaginationItem: {
      styleOverrides: {
        root: {
          "&.Mui-selected": {
            backgroundColor: "#E1E7FB",
            color: "#2849B8",
          },
        },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: {
          borderRadius: 12,
          boxShadow: "0 24px 48px -28px rgba(27, 45, 69, 0.22)",
        },
      },
    },
    MuiPopover: {
      styleOverrides: {
        paper: {
          borderRadius: 12,
          boxShadow: "0 24px 48px -28px rgba(27, 45, 69, 0.22)",
        },
      },
    },
  },
});

export default theme;
