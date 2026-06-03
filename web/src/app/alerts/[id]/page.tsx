"use client";

import {
  Alert as MuiAlert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Divider,
  LinearProgress,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import NotesIcon from "@mui/icons-material/Notes";
import PersonIcon from "@mui/icons-material/Person";
import TimelineIcon from "@mui/icons-material/Timeline";
import dayjs from "dayjs";
import { useFormik } from "formik";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as Yup from "yup";

import { CurrentUserBadge } from "@/components/CurrentUserBadge";
import {
  useAcknowledgeAlertMutation,
  useAddNoteMutation,
  useGetAlertQuery,
} from "@/features/alerts/api";
import type { AlertSeverity } from "@/features/alerts/types";

function getSeverityColor(severity: AlertSeverity) {
  if (severity === "critical") return "error";
  if (severity === "warning") return "warning";
  return "info";
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function formatAction(action: string): string {
  return action.replaceAll("_", " ");
}

export default function AlertDetailPage() {
  const params = useParams<{ id: string }>();
  const alertId = Number(params.id);

  const {
    data: alertDetail,
    isLoading,
    isFetching,
    isError,
    refetch,
  } = useGetAlertQuery(alertId, {
    skip: Number.isNaN(alertId),
  });

  const [acknowledgeAlert, { isLoading: isAcknowledging }] =
    useAcknowledgeAlertMutation();
  const [addNote, { isLoading: isAddingNote }] = useAddNoteMutation();

  const noteForm = useFormik({
    initialValues: {
      note: "",
    },
    validationSchema: Yup.object({
      note: Yup.string().trim().required("Note is required"),
    }),
    onSubmit: async (values, helpers) => {
      if (!alertDetail) return;

      try {
        await addNote({
          id: alertDetail.id,
          body: {
            note: values.note.trim(),
          },
        }).unwrap();

        helpers.resetForm();
        helpers.setStatus(undefined);
      } catch {
        helpers.setStatus("Failed to add note. Please try again.");
      }
    },
  });

  async function handleAcknowledge() {
    if (!alertDetail) return;

    try {
      await acknowledgeAlert(alertDetail.id).unwrap();
    } catch {
      window.alert(
        "Failed to acknowledge alert. It may have already changed on the server.",
      );
    }
  }

  if (Number.isNaN(alertId)) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <MuiAlert severity="error">Invalid alert id.</MuiAlert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Stack sx={{ gap: 3 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: 2,
            flexDirection: { xs: "column", md: "row" },
          }}
        >
          <Box>
            <Button
              component={Link}
              href="/alerts"
              startIcon={<ArrowBackIcon />}
              sx={{ mb: 2 }}
            >
              Back to queue
            </Button>

            <Typography variant="h4" sx={{ fontWeight: 800 }}>
              Alert Detail
            </Typography>
            <Typography color="text.secondary">
              Review alert context, ownership, timeline, and resolution workflow.
            </Typography>
          </Box>

          <CurrentUserBadge />
        </Box>

        {(isLoading || isFetching) && <LinearProgress />}

        {isError && (
          <MuiAlert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={() => refetch()}>
                Retry
              </Button>
            }
          >
            Failed to load alert detail.
          </MuiAlert>
        )}

        {!isLoading && !isError && alertDetail && (
          <>
            <Paper sx={{ p: 3 }}>
              <Stack
                direction={{ xs: "column", md: "row" }}
                sx={{
                  justifyContent: "space-between",
                  gap: 2,
                }}
              >
                <Box>
                  <Stack
                    direction="row"
                    sx={{
                      gap: 1,
                      alignItems: "center",
                      mb: 1,
                      flexWrap: "wrap",
                    }}
                  >
                    <Chip
                      label={alertDetail.severity}
                      color={getSeverityColor(alertDetail.severity)}
                      sx={{ textTransform: "capitalize" }}
                    />
                    <Chip
                      label={alertDetail.status}
                      variant="outlined"
                      sx={{ textTransform: "capitalize" }}
                    />
                    {alertDetail.recovered_at && (
                      <Chip label="Device recovered" color="success" />
                    )}
                  </Stack>

                  <Typography variant="h5" sx={{ fontWeight: 800 }}>
                    {alertDetail.title}
                  </Typography>

                  <Typography color="text.secondary">
                    {alertDetail.device.name} / {alertDetail.device.location}
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 1 }}
                  >
                    Triggered{" "}
                    {dayjs(alertDetail.triggered_at).format("MMM D, YYYY HH:mm")}
                  </Typography>
                </Box>

                <Stack
                  direction="row"
                  sx={{
                    gap: 1,
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                  }}
                >
                  {alertDetail.status === "new" && (
                    <>
                      <Button
                        variant="contained"
                        disabled={isAcknowledging}
                        onClick={handleAcknowledge}
                      >
                        Acknowledge
                      </Button>
                      <Button variant="outlined" disabled>
                        Assign
                      </Button>
                    </>
                  )}

                  {alertDetail.status === "acknowledged" && (
                    <>
                      <Button variant="contained" disabled>
                        Resolve
                      </Button>
                      <Button variant="outlined" disabled>
                        Assign
                      </Button>
                    </>
                  )}

                  {(alertDetail.status === "resolved" ||
                    alertDetail.status === "dismissed") && (
                    <Chip label="Read-only" variant="outlined" />
                  )}
                </Stack>
              </Stack>
            </Paper>

            <Stack direction={{ xs: "column", md: "row" }} sx={{ gap: 3 }}>
              <Card sx={{ flex: 1 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                    Metric
                  </Typography>

                  <Typography variant="body2" color="text.secondary">
                    Reading
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 800 }}>
                    {alertDetail.reading_name ?? "N/A"}
                  </Typography>

                  <Divider sx={{ my: 2 }} />

                  <Stack direction="row" sx={{ gap: 4 }}>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Value
                      </Typography>
                      <Typography sx={{ fontWeight: 700 }}>
                        {alertDetail.reading_value ?? "-"}
                      </Typography>
                    </Box>

                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Threshold
                      </Typography>
                      <Typography sx={{ fontWeight: 700 }}>
                        {alertDetail.threshold_value ?? "-"}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>

              <Card sx={{ flex: 1 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                    Assignment
                  </Typography>

                  {alertDetail.assigned_to ? (
                    <Stack direction="row" sx={{ gap: 2, alignItems: "center" }}>
                      <Avatar>{getInitials(alertDetail.assigned_to.name)}</Avatar>
                      <Box>
                        <Typography sx={{ fontWeight: 700 }}>
                          {alertDetail.assigned_to.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {alertDetail.assigned_to.role}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {alertDetail.assigned_to.email}
                        </Typography>
                      </Box>
                    </Stack>
                  ) : (
                    <Stack direction="row" sx={{ gap: 1, alignItems: "center" }}>
                      <PersonIcon color="disabled" />
                      <Typography color="text.secondary">Unassigned</Typography>
                    </Stack>
                  )}

                  <Button sx={{ mt: 2 }} variant="outlined" disabled>
                    Change assignment
                  </Button>
                </CardContent>
              </Card>
            </Stack>

            {alertDetail.resolution && (
              <Card>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                    Resolution
                  </Typography>

                  <Stack sx={{ gap: 1 }}>
                    <Typography>
                      <strong>Type:</strong> {alertDetail.resolution.type}
                    </Typography>
                    <Typography>
                      <strong>Root cause:</strong>{" "}
                      {alertDetail.resolution.root_cause}
                    </Typography>
                    <Typography>
                      <strong>Action taken:</strong>{" "}
                      {alertDetail.resolution.action_taken}
                    </Typography>
                    {alertDetail.resolution.preventive_measures && (
                      <Typography>
                        <strong>Preventive measures:</strong>{" "}
                        {alertDetail.resolution.preventive_measures}
                      </Typography>
                    )}
                    {alertDetail.resolution.time_spent_minutes != null && (
                      <Typography>
                        <strong>Time spent:</strong>{" "}
                        {alertDetail.resolution.time_spent_minutes} minutes
                      </Typography>
                    )}
                  </Stack>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardContent>
                <Stack
                  direction="row"
                  sx={{ gap: 1, alignItems: "center", mb: 2 }}
                >
                  <NotesIcon />
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    Add Note
                  </Typography>
                </Stack>

                <Box component="form" onSubmit={noteForm.handleSubmit}>
                  <Stack sx={{ gap: 2 }}>
                    <TextField
                      name="note"
                      label="Note"
                      multiline
                      minRows={3}
                      value={noteForm.values.note}
                      onChange={noteForm.handleChange}
                      onBlur={noteForm.handleBlur}
                      error={
                        noteForm.touched.note && Boolean(noteForm.errors.note)
                      }
                      helperText={noteForm.touched.note ? noteForm.errors.note : ""}
                      fullWidth
                    />

                    {noteForm.status && (
                      <MuiAlert severity="error">{noteForm.status}</MuiAlert>
                    )}

                    <Box>
                      <Button
                        type="submit"
                        variant="contained"
                        disabled={isAddingNote || !noteForm.isValid}
                      >
                        Add Note
                      </Button>
                    </Box>
                  </Stack>
                </Box>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Stack
                  direction="row"
                  sx={{ gap: 1, alignItems: "center", mb: 2 }}
                >
                  <TimelineIcon />
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    Timeline
                  </Typography>
                </Stack>

                <Stack sx={{ gap: 2 }}>
                  {alertDetail.timeline.map((item, index) => (
                    <Box key={item.id}>
                      <Stack direction="row" sx={{ gap: 2 }}>
                        <Avatar sx={{ width: 32, height: 32 }}>
                          {item.action === "resolved" ? (
                            <CheckCircleIcon fontSize="small" />
                          ) : (
                            index + 1
                          )}
                        </Avatar>

                        <Box sx={{ flex: 1 }}>
                          <Typography
                            sx={{
                              fontWeight: 700,
                              textTransform: "capitalize",
                            }}
                          >
                            {formatAction(item.action)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {item.user_name} /{" "}
                            {dayjs(item.timestamp).format("MMM D, YYYY HH:mm")}
                          </Typography>

                          {item.note && (
                            <Typography sx={{ mt: 1 }}>{item.note}</Typography>
                          )}

                          {item.details && (
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{ display: "block", mt: 1 }}
                            >
                              {JSON.stringify(item.details)}
                            </Typography>
                          )}
                        </Box>
                      </Stack>

                      {index < alertDetail.timeline.length - 1 && (
                        <Divider sx={{ my: 2, ml: 2 }} />
                      )}
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </>
        )}
      </Stack>
    </Container>
  );
}
