"use client";

import { createTheme } from "@mui/material/styles";
import type { PaletteMode } from "@mui/material";

export function createAppTheme(mode: PaletteMode) {
  return createTheme({
    palette: {
      mode,
      primary: {
        main: "#EFC01A",
      },
      secondary: {
        main: "#4B8189",
      },
      error: {
        main: "#F44336",
      },
      warning: {
        main: "#FFA726",
      },
      info: {
        main: "#29B6F6",
      },
      success: {
        main: "#66BB6A",
      },
      background:
        mode === "dark"
          ? {
              default: "#111827",
              paper: "#18212F",
            }
          : {
              default: "#F8FAFC",
              paper: "#FFFFFF",
            },
    },
    shape: {
      borderRadius: 8,
    },
    components: {
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
          },
        },
      },
    },
  });
}
