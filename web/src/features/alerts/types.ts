export type AlertStatus = "new" | "acknowledged" | "resolved" | "dismissed";

export type AlertSeverity = "info" | "warning" | "critical";

export type ResolutionType =
  | "fixed"
  | "false_alarm"
  | "known_issue"
  | "deferred"
  | "cannot_reproduce";

export type User = {
  id: string;
  name: string;
  email?: string | null;
  role: string;
  company?: string | null;
};

export type AlertListItem = {
  id: number;
  title: string;
  device_id: string;
  device_name: string;
  device_location: string;
  alert_type: string;
  severity: AlertSeverity;
  status: AlertStatus;
  assigned_to: User | null;
  triggered_at: string;
  recovered_at?: string | null;
  reading_name?: string | null;
  reading_value?: number | null;
  threshold_value?: number | null;
};

export type AlertSummary = Record<AlertStatus, number>;

export type AlertListResponse = {
  items: AlertListItem[];
  total: number;
  summary: AlertSummary;
};

export type GetAlertsParams = {
  severity?: AlertSeverity[];
  status?: AlertStatus[];
  device_id?: string;
  assigned_to?: string;
  q?: string;
  from?: string;
  to?: string;
};

export type TimelineEntry = {
  id: number;
  timestamp: string;
  action: string;
  user_name: string;
  source_raw_message_id?: number | null;
  details?: Record<string, unknown> | null;
  note?: string | null;
  created_at: string;
};

export type AlertDetail = AlertListItem & {
  device: {
    device_id: string;
    name: string;
    type: string;
    company: string;
    location: string;
    timezone: string;
    installed_date?: string | null;
    floor_count?: number | null;
  };
  acknowledged_at?: string | null;
  resolved_at?: string | null;
  resolution?: {
    type?: string | null;
    root_cause?: string | null;
    action_taken?: string | null;
    preventive_measures?: string | null;
    time_spent_minutes?: number | null;
  } | null;
  timeline: TimelineEntry[];
};

export type Device = {
  device_id: string;
  name: string;
  type: string;
  company: string;
  location: string;
  timezone: string;
  installed_date?: string | null;
  floor_count?: number | null;
  reading_types?: string[] | null;
  alert_thresholds?: Record<string, unknown> | null;
};

export type AddNoteRequest = {
  note: string;
};

export type AssignAlertRequest = {
  assignee_id: string;
  note?: string;
};

export type ResolveAlertRequest = {
  resolution_type: ResolutionType;
  root_cause: string;
  action_taken: string;
  preventive_measures?: string;
  time_spent_minutes?: number;
};
