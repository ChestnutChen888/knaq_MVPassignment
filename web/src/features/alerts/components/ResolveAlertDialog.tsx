"use client";

import {
  Alert as MuiAlert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import { useFormik } from "formik";
import * as Yup from "yup";

import { useResolveAlertMutation } from "@/features/alerts/api";
import type { ResolutionType } from "@/features/alerts/types";

type ResolveAlertDialogProps = {
  open: boolean;
  alertId: number;
  onClose: () => void;
};

type ResolveFormValues = {
  resolution_type: ResolutionType | "";
  root_cause: string;
  action_taken: string;
  preventive_measures: string;
  time_spent_minutes: string;
};

const resolutionTypes: Array<{ value: ResolutionType; label: string }> = [
  { value: "fixed", label: "Fixed" },
  { value: "false_alarm", label: "False alarm" },
  { value: "known_issue", label: "Known issue" },
  { value: "deferred", label: "Deferred" },
  { value: "cannot_reproduce", label: "Cannot reproduce" },
];

export function ResolveAlertDialog({
  open,
  alertId,
  onClose,
}: ResolveAlertDialogProps) {
  const [resolveAlert, { isLoading }] = useResolveAlertMutation();

  const formik = useFormik<ResolveFormValues>({
    initialValues: {
      resolution_type: "",
      root_cause: "",
      action_taken: "",
      preventive_measures: "",
      time_spent_minutes: "",
    },
    validationSchema: Yup.object({
      resolution_type: Yup.string().required("Resolution type is required"),
      root_cause: Yup.string().trim().required("Root cause is required"),
      action_taken: Yup.string().trim().required("Action taken is required"),
      preventive_measures: Yup.string().trim(),
      time_spent_minutes: Yup.number()
        .typeError("Time spent must be a number")
        .integer("Time spent must be a whole number")
        .min(0, "Time spent cannot be negative")
        .nullable()
        .transform((value, originalValue) =>
          originalValue === "" ? null : value,
        ),
    }),
    onSubmit: async (values, helpers) => {
      if (!values.resolution_type) return;

      try {
        await resolveAlert({
          id: alertId,
          body: {
            resolution_type: values.resolution_type,
            root_cause: values.root_cause.trim(),
            action_taken: values.action_taken.trim(),
            preventive_measures:
              values.preventive_measures.trim() || undefined,
            time_spent_minutes:
              values.time_spent_minutes.trim() === ""
                ? undefined
                : Number(values.time_spent_minutes),
          },
        }).unwrap();

        helpers.resetForm();
        helpers.setStatus(undefined);
        onClose();
      } catch {
        helpers.setStatus(
          "Failed to resolve alert. It may have changed on the server.",
        );
      }
    },
    validateOnMount: true,
  });

  function handleClose() {
    formik.resetForm();
    formik.setStatus(undefined);
    onClose();
  }

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>Resolve Alert</DialogTitle>

      <DialogContent>
        <Stack
          component="form"
          id="resolve-alert-form"
          onSubmit={formik.handleSubmit}
          sx={{ gap: 2, pt: 1 }}
        >
          <TextField
            select
            name="resolution_type"
            label="Resolution Type"
            value={formik.values.resolution_type}
            onChange={formik.handleChange}
            onBlur={formik.handleBlur}
            error={
              formik.touched.resolution_type &&
              Boolean(formik.errors.resolution_type)
            }
            helperText={
              formik.touched.resolution_type
                ? formik.errors.resolution_type
                : ""
            }
            fullWidth
            required
          >
            {resolutionTypes.map((item) => (
              <MenuItem key={item.value} value={item.value}>
                {item.label}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            name="root_cause"
            label="Root Cause"
            value={formik.values.root_cause}
            onChange={formik.handleChange}
            onBlur={formik.handleBlur}
            error={formik.touched.root_cause && Boolean(formik.errors.root_cause)}
            helperText={
              formik.touched.root_cause ? formik.errors.root_cause : ""
            }
            fullWidth
            required
          />

          <TextField
            name="action_taken"
            label="Action Taken"
            value={formik.values.action_taken}
            onChange={formik.handleChange}
            onBlur={formik.handleBlur}
            error={
              formik.touched.action_taken && Boolean(formik.errors.action_taken)
            }
            helperText={
              formik.touched.action_taken ? formik.errors.action_taken : ""
            }
            multiline
            minRows={3}
            fullWidth
            required
          />

          <TextField
            name="preventive_measures"
            label="Preventive Measures"
            value={formik.values.preventive_measures}
            onChange={formik.handleChange}
            onBlur={formik.handleBlur}
            multiline
            minRows={2}
            fullWidth
          />

          <TextField
            name="time_spent_minutes"
            label="Time Spent"
            type="number"
            value={formik.values.time_spent_minutes}
            onChange={formik.handleChange}
            onBlur={formik.handleBlur}
            error={
              formik.touched.time_spent_minutes &&
              Boolean(formik.errors.time_spent_minutes)
            }
            helperText={
              formik.touched.time_spent_minutes
                ? formik.errors.time_spent_minutes
                : "Minutes"
            }
            fullWidth
          />

          {formik.status && <MuiAlert severity="error">{formik.status}</MuiAlert>}
        </Stack>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          type="submit"
          form="resolve-alert-form"
          variant="contained"
          disabled={isLoading || !formik.isValid}
        >
          Resolve
        </Button>
      </DialogActions>
    </Dialog>
  );
}
