"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getAnnouncementsAPI,
  deleteAnnouncementAPI,
  markAllAnnouncementsReadAPI,
  markAnnouncementReadAPI,
} from "@/features/notification/services/announcement.service";
export function useAnnouncementsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const [loadFailed, setLoadFailed] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setLoadFailed(false);
    try {
      const response = await getAnnouncementsAPI();
      const data = response?.data || response || [];
      setItems(Array.isArray(data) ? data : []);
    } catch (reason) {
      setLoadFailed(true);
      setError(reason instanceof Error ? reason.message : "Không thể tải thông báo");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  const unread = useMemo(() => items.filter((item) => !item.is_read).length, [items]);
  const markRead = async (id) => {
    setError("");
    try {
      await markAnnouncementReadAPI(id);
      setItems((current) =>
        current.map((item) =>
          (item._id || item.id) === id
            ? {
                ...item,
                is_read: true,
              }
            : item,
        ),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể cập nhật thông báo");
    }
  };
  const markAllRead = async () => {
    if (!unread || processing) return;
    setProcessing(true);
    setError("");
    try {
      await markAllAnnouncementsReadAPI();
      setItems((current) =>
        current.map((item) => ({
          ...item,
          is_read: true,
        })),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể cập nhật thông báo");
    } finally {
      setProcessing(false);
    }
  };
  const remove = async (id) => {
    setProcessing(true);
    setError("");
    try {
      await deleteAnnouncementAPI(id);
      setItems((current) => current.filter((item) => (item._id || item.id) !== id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể xóa thông báo");
    } finally {
      setProcessing(false);
    }
  };
  return {
    items,
    unread,
    loading,
    processing,
    error,
    loadFailed,
    reload: load,
    markRead,
    markAllRead,
    remove,
  };
}
