"use client";

import { Box, Typography } from "@mui/material";

type EmptyStateProps = {
  title?: string;
};

export function EmptyState({ title = "No records found" }: EmptyStateProps) {
  return (
    <Box sx={{ py: 4 }}>
      <Typography color="text.secondary">{title}</Typography>
    </Box>
  );
}
