"use client";

import { Avatar, Box, Chip, Stack, Typography } from "@mui/material";

import { CURRENT_USER } from "@/lib/config";
import { ThemeModeToggle } from "./ThemeModeToggle";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function CurrentUserBadge() {
  return (
    <Stack
      direction="row"
      sx={{
        alignItems: "center",
        gap: 1.5,
        flexWrap: "wrap",
        justifyContent: { xs: "flex-start", sm: "flex-end" },
      }}
    >
      <ThemeModeToggle />

      <Avatar sx={{ width: 36, height: 36, fontSize: 14 }}>
        {getInitials(CURRENT_USER.name)}
      </Avatar>

      <Box>
        <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
          {CURRENT_USER.name}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {CURRENT_USER.role} / {CURRENT_USER.company}
        </Typography>
      </Box>

      <Chip size="small" label="Simulated user" variant="outlined" />
    </Stack>
  );
}
