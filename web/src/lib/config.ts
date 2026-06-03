export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const AUTH_TOKEN =
  process.env.NEXT_PUBLIC_AUTH_TOKEN ?? "token-brookfield-manager";

export const CURRENT_USER_BY_TOKEN: Record<
  string,
  { name: string; role: string; company: string }
> = {
  "token-brookfield-manager": {
    name: "Alice Chen",
    role: "Manager",
    company: "Brookfield Properties",
  },
  "token-brookfield-tech": {
    name: "Bob Smith",
    role: "Technician",
    company: "Brookfield Properties",
  },
  "token-brookfield-dispatcher": {
    name: "Priya Patel",
    role: "Dispatcher",
    company: "Brookfield Properties",
  },
  "token-hines-manager": {
    name: "Lisa Wang",
    role: "Manager",
    company: "Hines",
  },
  "token-hines-tech": {
    name: "Mark Lee",
    role: "Technician",
    company: "Hines",
  },
};

export const CURRENT_USER = CURRENT_USER_BY_TOKEN[AUTH_TOKEN] ?? {
  name: "Unknown User",
  role: "Unknown Role",
  company: "Unknown Company",
};

export const apiBaseUrl = API_BASE_URL;
export const authToken = AUTH_TOKEN;
