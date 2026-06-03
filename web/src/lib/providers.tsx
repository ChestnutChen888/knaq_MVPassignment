"use client";

import { CssBaseline, ThemeProvider } from "@mui/material";
import { Provider } from "react-redux";
import type { ReactNode } from "react";

import { store } from "./store";
import { theme } from "./theme";

type ProvidersProps = {
  children: ReactNode;
};

export function Providers({ children }: ProvidersProps) {
  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </Provider>
  );
}
