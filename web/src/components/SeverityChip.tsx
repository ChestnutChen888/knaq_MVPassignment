"use client";

import { Chip } from "@mui/material";

type SeverityChipProps = {
  severity: string;
};

export function SeverityChip({ severity }: SeverityChipProps) {
  return <Chip label={severity} size="small" />;
}
