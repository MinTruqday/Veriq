"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";

export function useProject(projectId) {
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);
  const lastAccessRefreshPath = useRef("");
  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    setForbidden(false);
    try {
      const value = await testingApi.getProject(projectId);
      setProject(value);
    } catch (reason) {
      setError(messageOf(reason));
      setForbidden(reason?.status === 403);
    } finally {
      setLoading(false);
    }
  }, [projectId]);
  useEffect(() => {
    void reload();
  }, [reload]);
  useEffect(() => {
    lastAccessRefreshPath.current = "";
    const refreshAccess = (event) => {
      const pagePath = event.detail?.pagePath || "";
      if (
        event.detail?.projectId !== projectId ||
        !pagePath ||
        lastAccessRefreshPath.current === pagePath
      )
        return;
      lastAccessRefreshPath.current = pagePath;
      const deniedPermission = event.detail?.permission;
      if (typeof deniedPermission === "string") {
        setProject((current) =>
          current
            ? {
                ...current,
                current_permissions: (current.current_permissions || []).filter(
                  (permission) => permission !== deniedPermission,
                ),
              }
            : current,
        );
      } else {
        setProject(null);
      }
      void reload();
    };
    window.addEventListener("veriq-project-access-denied", refreshAccess);
    return () => window.removeEventListener("veriq-project-access-denied", refreshAccess);
  }, [projectId, reload]);
  return { project, loading, error, forbidden, setError, reload };
}
