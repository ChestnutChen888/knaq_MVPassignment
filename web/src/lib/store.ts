import { configureStore } from "@reduxjs/toolkit";

import { alertsApi } from "@/features/alerts/api";

export const store = configureStore({
  reducer: {
    [alertsApi.reducerPath]: alertsApi.reducer,
  },
  middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(alertsApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
