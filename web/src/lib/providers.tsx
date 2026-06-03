"use client";

import { CssBaseline, ThemeProvider } from "@mui/material";
import type { PaletteMode } from "@mui/material";
import { Provider } from "react-redux";
import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { store } from "./store";
import { createAppTheme } from "./theme";

type ProvidersProps = {
  children: ReactNode;
};

type ThemeModeContextValue = {
  mode: PaletteMode;
  toggleMode: () => void;
};

const ThemeModeContext = createContext<ThemeModeContextValue | null>(null);

export function useThemeMode() {
  const value = useContext(ThemeModeContext);

  if (!value) {
    throw new Error("useThemeMode must be used within Providers");
  }

  return value;
}

export function Providers({ children }: ProvidersProps) {
  const [mode, setMode] = useState<PaletteMode>(() => {
    if (typeof window === "undefined") return "light";

    const savedMode = window.localStorage.getItem("knaq-theme-mode");
    return savedMode === "light" || savedMode === "dark" ? savedMode : "light";
  });

  const theme = useMemo(() => createAppTheme(mode), [mode]);

  const contextValue = useMemo<ThemeModeContextValue>(
    () => ({
      mode,
      toggleMode: () => {
        setMode((currentMode) => {
          const nextMode = currentMode === "light" ? "dark" : "light";
          window.localStorage.setItem("knaq-theme-mode", nextMode);
          return nextMode;
        });
      },
    }),
    [mode],
  );

  return (
    <Provider store={store}>
      <ThemeModeContext.Provider value={contextValue}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </ThemeModeContext.Provider>
    </Provider>
  );
}
