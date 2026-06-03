"use client";

import { Box, CircularProgress } from "@mui/material";

export function LoadingState() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
      <CircularProgress size={24} />
    </Box>
  );
}
