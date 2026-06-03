"use client";

import { Alert } from "@mui/material";

type ErrorStateProps = {
  message?: string;
};

export function ErrorState({ message = "Something went wrong" }: ErrorStateProps) {
  return <Alert severity="error">{message}</Alert>;
}
