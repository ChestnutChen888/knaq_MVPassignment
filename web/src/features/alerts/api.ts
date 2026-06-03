import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

import { apiBaseUrl, authToken } from "@/lib/config";
import type {
  AddNoteRequest,
  AlertDetail,
  AlertListResponse,
  AssignAlertRequest,
  Device,
  GetAlertsParams,
  ResolveAlertRequest,
  User,
} from "./types";

function buildAlertQuery(params?: GetAlertsParams): string {
  if (!params) return "";

  const search = new URLSearchParams();

  params.severity?.forEach((value) => search.append("severity", value));
  params.status?.forEach((value) => search.append("status", value));

  if (params.device_id) search.set("device_id", params.device_id);
  if (params.assigned_to) search.set("assigned_to", params.assigned_to);
  if (params.q) search.set("q", params.q);
  if (params.from) search.set("from", params.from);
  if (params.to) search.set("to", params.to);
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));

  const query = search.toString();
  return query ? `?${query}` : "";
}

export const alertsApi = createApi({
  reducerPath: "alertsApi",
  baseQuery: fetchBaseQuery({
    baseUrl: apiBaseUrl,
    prepareHeaders: (headers) => {
      if (authToken) {
        headers.set("Authorization", `Bearer ${authToken}`);
      }
      return headers;
    },
  }),
  tagTypes: ["Alert", "Alerts", "Devices", "Users"],
  endpoints: (builder) => ({
    getAlerts: builder.query<AlertListResponse, GetAlertsParams | void>({
      query: (params) => `/alerts${buildAlertQuery(params ?? undefined)}`,
      providesTags: ["Alerts"],
    }),
    getAlert: builder.query<AlertDetail, number>({
      query: (id) => `/alerts/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Alert", id }],
    }),
    getDevices: builder.query<Device[], void>({
      query: () => "/devices",
      providesTags: ["Devices"],
    }),
    getUsers: builder.query<User[], void>({
      query: () => "/users",
      providesTags: ["Users"],
    }),
    acknowledgeAlert: builder.mutation<AlertDetail, number>({
      query: (id) => ({
        url: `/alerts/${id}/acknowledge`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, id) => [
        "Alerts",
        { type: "Alert", id },
      ],
    }),
    assignAlert: builder.mutation<
      AlertDetail,
      { id: number; body: AssignAlertRequest }
    >({
      query: ({ id, body }) => ({
        url: `/alerts/${id}/assign`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        "Alerts",
        { type: "Alert", id },
      ],
    }),
    resolveAlert: builder.mutation<
      AlertDetail,
      { id: number; body: ResolveAlertRequest }
    >({
      query: ({ id, body }) => ({
        url: `/alerts/${id}/resolve`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        "Alerts",
        { type: "Alert", id },
      ],
    }),
    dismissAlert: builder.mutation<AlertDetail, number>({
      query: (id) => ({
        url: `/alerts/${id}/dismiss`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, id) => [
        "Alerts",
        { type: "Alert", id },
      ],
    }),
    reopenAlert: builder.mutation<AlertDetail, number>({
      query: (id) => ({
        url: `/alerts/${id}/reopen`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, id) => [
        "Alerts",
        { type: "Alert", id },
      ],
    }),
    addNote: builder.mutation<AlertDetail, { id: number; body: AddNoteRequest }>({
      query: ({ id, body }) => ({
        url: `/alerts/${id}/notes`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        "Alerts",
        { type: "Alert", id },
      ],
    }),
  }),
});

export const {
  useGetAlertQuery,
  useGetAlertsQuery,
  useGetDevicesQuery,
  useGetUsersQuery,
  useAcknowledgeAlertMutation,
  useAssignAlertMutation,
  useResolveAlertMutation,
  useDismissAlertMutation,
  useReopenAlertMutation,
  useAddNoteMutation,
} = alertsApi;
