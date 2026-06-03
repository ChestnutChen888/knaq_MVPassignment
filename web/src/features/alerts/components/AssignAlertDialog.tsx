"use client";

import {
  Alert as MuiAlert,
  Avatar,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItemAvatar,
  ListItemButton,
  ListItemText,
  TextField,
  Typography,
} from "@mui/material";
import { useMemo, useState } from "react";

import {
  useAssignAlertMutation,
  useGetUsersQuery,
} from "@/features/alerts/api";

type AssignAlertDialogProps = {
  open: boolean;
  alertId: number;
  currentAssigneeId?: string | null;
  onClose: () => void;
};

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function AssignAlertDialog({
  open,
  alertId,
  currentAssigneeId,
  onClose,
}: AssignAlertDialogProps) {
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [note, setNote] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: users = [], isLoading, isError } = useGetUsersQuery();
  const [assignAlert, { isLoading: isAssigning }] = useAssignAlertMutation();
  const effectiveSelectedUserId = selectedUserId ?? currentAssigneeId ?? null;

  const filteredUsers = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    if (!keyword) return users;

    return users.filter((user) => {
      return (
        user.name.toLowerCase().includes(keyword) ||
        (user.email?.toLowerCase().includes(keyword) ?? false) ||
        user.role.toLowerCase().includes(keyword)
      );
    });
  }, [users, search]);

  async function handleAssign() {
    if (!effectiveSelectedUserId) {
      setErrorMessage("Please select a team member.");
      return;
    }

    try {
      setErrorMessage(null);

      await assignAlert({
        id: alertId,
        body: {
          assignee_id: effectiveSelectedUserId,
          note: note.trim() || undefined,
        },
      }).unwrap();

      handleClose();
    } catch {
      setErrorMessage(
        "Failed to assign alert. The alert may have changed on the server.",
      );
    }
  }

  function handleClose() {
    setSelectedUserId(null);
    setSearch("");
    setNote("");
    setErrorMessage(null);
    onClose();
  }

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>Assign Alert</DialogTitle>

      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <TextField
            label="Search team members"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            fullWidth
            sx={{ mb: 2 }}
          />

          {isLoading && (
            <Typography color="text.secondary">Loading team members...</Typography>
          )}

          {isError && (
            <MuiAlert severity="error" sx={{ mb: 2 }}>
              Failed to load team members.
            </MuiAlert>
          )}

          {!isLoading && !isError && filteredUsers.length === 0 && (
            <Typography color="text.secondary">No team members found.</Typography>
          )}

          <List sx={{ maxHeight: 320, overflow: "auto" }}>
            {filteredUsers.map((user) => {
              const selected = effectiveSelectedUserId === user.id;
              const isCurrent = currentAssigneeId === user.id;

              return (
                <ListItemButton
                  key={user.id}
                  selected={selected}
                  onClick={() => setSelectedUserId(user.id)}
                  sx={{
                    borderRadius: 1,
                    mb: 0.5,
                  }}
                >
                  <ListItemAvatar>
                    <Avatar>{getInitials(user.name)}</Avatar>
                  </ListItemAvatar>

                  <ListItemText
                    primary={
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 1,
                        }}
                      >
                        <Typography sx={{ fontWeight: 700 }}>
                          {user.name}
                        </Typography>
                        {isCurrent && (
                          <Typography
                            variant="caption"
                            color="primary"
                            sx={{ fontWeight: 700 }}
                          >
                            Current
                          </Typography>
                        )}
                      </Box>
                    }
                    secondary={`${user.role}${user.email ? ` / ${user.email}` : ""}`}
                  />
                </ListItemButton>
              );
            })}
          </List>

          <TextField
            label="Reason for assignment"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            multiline
            minRows={2}
            fullWidth
            sx={{ mt: 2 }}
          />

          {errorMessage && (
            <MuiAlert severity="error" sx={{ mt: 2 }}>
              {errorMessage}
            </MuiAlert>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          disabled={isAssigning || !effectiveSelectedUserId}
          onClick={handleAssign}
        >
          Assign
        </Button>
      </DialogActions>
    </Dialog>
  );
}
