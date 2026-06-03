"use client";

import {
  Alert as MuiAlert,
  Avatar,
  Box,
  Button,
  Checkbox,
  Chip,
  Container,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Stack,
  TablePagination,
  TextField,
  Typography,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material/Select";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import Link from "next/link";
import { useMemo, useState } from "react";

import { CurrentUserBadge } from "@/components/CurrentUserBadge";
import {
  useAcknowledgeAlertMutation,
  useGetAlertsQuery,
} from "@/features/alerts/api";
import type {
  AlertSeverity,
  AlertSortBy,
  AlertStatus,
  SortOrder,
} from "@/features/alerts/types";

dayjs.extend(relativeTime);

const statusOptions: Array<AlertStatus | "all"> = [
  "all",
  "new",
  "acknowledged",
  "resolved",
  "dismissed",
];

const severityOptions: AlertSeverity[] = ["critical", "warning", "info"];

type SortValue = `${AlertSortBy}:${SortOrder}`;

const sortOptions: Array<{ value: SortValue; label: string }> = [
  { value: "triggered_at:desc", label: "Newest first" },
  { value: "triggered_at:asc", label: "Oldest first" },
  { value: "severity:desc", label: "Severity high first" },
  { value: "severity:asc", label: "Severity low first" },
  { value: "status:asc", label: "Status workflow" },
];

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

export default function AlertQueuePage() {
  const [statusFilter, setStatusFilter] = useState<AlertStatus | "all">("all");
  const [severityFilter, setSeverityFilter] = useState<AlertSeverity[]>([]);
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [sortValue, setSortValue] = useState<SortValue>("triggered_at:desc");
  const [sortBy, sortOrder] = sortValue.split(":") as [AlertSortBy, SortOrder];

  const queryParams = useMemo(
    () => ({
      ...(statusFilter !== "all" ? { status: [statusFilter] } : {}),
      ...(severityFilter.length > 0 ? { severity: severityFilter } : {}),
      ...(search.trim() ? { q: search.trim() } : {}),
      page: page + 1,
      page_size: pageSize,
      sort_by: sortBy,
      sort_order: sortOrder,
    }),
    [statusFilter, severityFilter, search, page, pageSize, sortBy, sortOrder],
  );

  const {
    data: summaryData,
    isLoading: isSummaryLoading,
    isError: isSummaryError,
    refetch: refetchSummary,
  } = useGetAlertsQuery();

  const { data, isLoading, isFetching, isError, refetch } =
    useGetAlertsQuery(queryParams);

  const [acknowledgeAlert, { isLoading: isAcknowledging }] =
    useAcknowledgeAlertMutation();

  const alerts = data?.items ?? [];
  const selectedNewAlerts = alerts.filter(
    (alertItem) =>
      selectedIds.includes(alertItem.id) && alertItem.status === "new",
  );
  const summary = summaryData?.summary ?? {
    new: 0,
    acknowledged: 0,
    resolved: 0,
    dismissed: 0,
  };
  const total = summaryData?.total ?? 0;

  const handleRefresh = () => {
    refetch();
    refetchSummary();
  };

  const resetPagination = () => {
    setPage(0);
    clearSelection();
  };

  const handleSeverityChange = (event: SelectChangeEvent<AlertSeverity[]>) => {
    const value = event.target.value;
    setSeverityFilter(
      typeof value === "string"
        ? (value.split(",").filter(Boolean) as AlertSeverity[])
        : value,
    );
    resetPagination();
  };

  const handleAcknowledge = async (alertId: number) => {
    try {
      await acknowledgeAlert(alertId).unwrap();
    } catch {
      window.alert(
        "Failed to acknowledge alert. The alert may have changed on the server.",
      );
    }
  };

  const toggleSelected = (id: number) => {
    setSelectedIds((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    );
  };

  const clearSelection = () => {
    setSelectedIds([]);
  };

  const handleBulkAcknowledge = async () => {
    try {
      await Promise.all(
        selectedNewAlerts.map((alertItem) =>
          acknowledgeAlert(alertItem.id).unwrap(),
        ),
      );
      clearSelection();
    } catch {
      window.alert(
        "Some alerts could not be acknowledged. Please refresh and try again.",
      );
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Stack spacing={3}>
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
            <Typography variant="h4" sx={{ fontWeight: 800 }}>
              Alert Queue
            </Typography>
            <Typography color="text.secondary">
              Triage active equipment alerts, assign owners, and track resolution.
            </Typography>
          </Box>

          <CurrentUserBadge />
        </Box>

        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            {statusOptions.map((status) => {
              const count = status === "all" ? total : summary[status];
              return (
                <Chip
                  key={status}
                  label={`${status === "all" ? "All" : status} (${count})`}
                  color={statusFilter === status ? "primary" : "default"}
                  variant={statusFilter === status ? "filled" : "outlined"}
                  onClick={() => {
                    setStatusFilter(status);
                    resetPagination();
                  }}
                  sx={{ textTransform: "capitalize" }}
                />
              );
            })}
          </Box>
        </Paper>

        <Paper sx={{ p: 2 }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={2}
            sx={{ alignItems: { xs: "stretch", md: "center" } }}
          >
            <TextField
              label="Search by alert, device, or type"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                resetPagination();
              }}
              fullWidth
            />

            <FormControl sx={{ minWidth: 220 }}>
              <InputLabel id="severity-filter-label">Severity</InputLabel>
              <Select
                labelId="severity-filter-label"
                multiple
                value={severityFilter}
                label="Severity"
                onChange={handleSeverityChange}
                renderValue={(selected) => selected.join(", ")}
              >
                {severityOptions.map((severity) => (
                  <MenuItem key={severity} value={severity}>
                    {severity}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl sx={{ minWidth: 220 }}>
              <InputLabel id="sort-alerts-label">Sort</InputLabel>
              <Select
                labelId="sort-alerts-label"
                value={sortValue}
                label="Sort"
                onChange={(event) => {
                  setSortValue(event.target.value as SortValue);
                  resetPagination();
                }}
              >
                {sortOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button variant="outlined" onClick={handleRefresh}>
              Refresh
            </Button>
          </Stack>
        </Paper>

        {(isSummaryLoading || isLoading || isFetching) && <LinearProgress />}

        {(isError || isSummaryError) && (
          <MuiAlert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={handleRefresh}>
                Retry
              </Button>
            }
          >
            Failed to load alerts. Make sure the backend API is running.
          </MuiAlert>
        )}

        {!isLoading && !isError && !isSummaryError && alerts.length === 0 && (
          <Paper sx={{ p: 5, textAlign: "center" }}>
            <Typography variant="h6">No alerts found</Typography>
            <Typography color="text.secondary">
              Try changing the filters or check back later.
            </Typography>
          </Paper>
        )}

        {!isLoading && !isError && !isSummaryError && alerts.length > 0 && (
          <Stack sx={{ gap: 2 }}>
            {selectedIds.length > 0 && (
              <Paper sx={{ p: 2 }}>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  sx={{
                    gap: 2,
                    alignItems: { xs: "stretch", sm: "center" },
                    justifyContent: "space-between",
                  }}
                >
                  <Typography>
                    {selectedIds.length} selected / {selectedNewAlerts.length} can
                    be acknowledged
                  </Typography>

                  <Stack direction="row" sx={{ gap: 1 }}>
                    <Button onClick={clearSelection}>Clear</Button>
                    <Button
                      variant="contained"
                      disabled={
                        selectedNewAlerts.length === 0 || isAcknowledging
                      }
                      onClick={handleBulkAcknowledge}
                    >
                      Bulk Acknowledge
                    </Button>
                  </Stack>
                </Stack>
              </Paper>
            )}

          <Paper sx={{ overflow: "hidden" }}>
            <Box component="table" sx={{ width: "100%", borderCollapse: "collapse" }}>
              <Box component="thead" sx={{ bgcolor: "action.hover" }}>
                <Box component="tr">
                  {[
                    "Select",
                    "Severity",
                    "Alert",
                    "Device",
                    "Triggered",
                    "Status",
                    "Assignee",
                    "Actions",
                  ].map((header) => (
                    <Box
                      key={header}
                      component="th"
                      sx={{
                        p: 2,
                        textAlign: "left",
                        fontSize: 14,
                        fontWeight: 700,
                        color: "text.secondary",
                      }}
                    >
                      {header}
                    </Box>
                  ))}
                </Box>
              </Box>

              <Box component="tbody">
                {alerts.map((alertItem) => (
                  <Box
                    key={alertItem.id}
                    component="tr"
                    sx={{
                      borderTop: "1px solid",
                      borderColor: "divider",
                      "&:hover": { bgcolor: "action.hover" },
                    }}
                  >
                    <Box component="td" sx={{ p: 2 }}>
                      <Checkbox
                        checked={selectedIds.includes(alertItem.id)}
                        onChange={() => toggleSelected(alertItem.id)}
                        slotProps={{
                          input: {
                            "aria-label": `Select alert ${alertItem.id}`,
                          },
                        }}
                      />
                    </Box>

                    <Box component="td" sx={{ p: 2 }}>
                      <Chip
                        size="small"
                        label={alertItem.severity}
                        color={getSeverityColor(alertItem.severity)}
                        sx={{ textTransform: "capitalize" }}
                      />
                    </Box>

                    <Box component="td" sx={{ p: 2, minWidth: 260 }}>
                      <Typography sx={{ fontWeight: 700 }}>{alertItem.title}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {alertItem.alert_type}
                      </Typography>
                      {alertItem.reading_name && (
                        <Typography variant="body2" color="text.secondary">
                          {alertItem.reading_name}: {alertItem.reading_value ?? "-"} /
                          threshold {alertItem.threshold_value ?? "-"}
                        </Typography>
                      )}
                    </Box>

                    <Box component="td" sx={{ p: 2 }}>
                      <Typography sx={{ fontWeight: 600 }}>{alertItem.device_name}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {alertItem.device_id} / {alertItem.device_location}
                      </Typography>
                    </Box>

                    <Box component="td" sx={{ p: 2 }}>
                      <Typography>{dayjs(alertItem.triggered_at).fromNow()}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {dayjs(alertItem.triggered_at).format("MMM D, HH:mm")}
                      </Typography>
                    </Box>

                    <Box component="td" sx={{ p: 2 }}>
                      <Chip
                        size="small"
                        label={alertItem.status}
                        variant="outlined"
                        sx={{ textTransform: "capitalize" }}
                      />
                    </Box>

                    <Box component="td" sx={{ p: 2 }}>
                      {alertItem.assigned_to ? (
                        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                          <Avatar sx={{ width: 28, height: 28, fontSize: 12 }}>
                            {getInitials(alertItem.assigned_to.name)}
                          </Avatar>
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {alertItem.assigned_to.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {alertItem.assigned_to.role}
                            </Typography>
                          </Box>
                        </Stack>
                      ) : (
                        <Typography color="text.secondary">Unassigned</Typography>
                      )}
                    </Box>

                    <Box component="td" sx={{ p: 2 }}>
                      <Stack direction="row" spacing={1}>
                        {alertItem.status === "new" && (
                          <Button
                            size="small"
                            variant="contained"
                            disabled={isAcknowledging}
                            onClick={() => handleAcknowledge(alertItem.id)}
                          >
                            Acknowledge
                          </Button>
                        )}

                        <Button
                          size="small"
                          variant="outlined"
                          component={Link}
                          href={`/alerts/${alertItem.id}`}
                        >
                          View Detail
                        </Button>
                      </Stack>
                    </Box>
                  </Box>
                ))}
              </Box>
            </Box>

            <TablePagination
              component="div"
              count={data?.total ?? 0}
              page={page}
              rowsPerPage={pageSize}
              rowsPerPageOptions={[5, 10, 20, 50]}
              onPageChange={(_event, nextPage) => {
                setPage(nextPage);
                clearSelection();
              }}
              onRowsPerPageChange={(event) => {
                setPageSize(Number(event.target.value));
                setPage(0);
                clearSelection();
              }}
            />
          </Paper>
          </Stack>
        )}
      </Stack>
    </Container>
  );
}
