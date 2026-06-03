"use client";

import { Chip } from "@mui/material";

type StatusChipProps = {
  status: string;
};

export function StatusChip({ status }: StatusChipProps) {
  return <Chip label={status} size="small" variant="outlined" />;
}
