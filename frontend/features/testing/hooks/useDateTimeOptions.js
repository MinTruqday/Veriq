import { useMemo } from "react";
import { useAuth } from "@/features/authentication/contexts/AuthContext";

export function useDateTimeOptions(project = null) {
  const { user } = useAuth();
  return useMemo(
    () => ({
      locale: user?.locale || project?.locale || undefined,
      timeZone: user?.timezone || project?.timezone || undefined,
    }),
    [project?.locale, project?.timezone, user?.locale, user?.timezone],
  );
}
