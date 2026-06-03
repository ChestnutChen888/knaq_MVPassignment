"use client";

import { Box } from "@mui/material";
import type { ReactNode } from "react";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return <Box component="main">{children}</Box>;
}
