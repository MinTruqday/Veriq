"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  getAnnouncementsAPI,
  deleteAnnouncementAPI,
  markAllAnnouncementsReadAPI,
  markAnnouncementReadAPI,
} from "@/features/notification/services/announcement.service";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
export function useAnnouncementsPage() {
  const { user } = useAuth();
  const userId = user?._id || null;
  const requestId = useRef(0);
  const [items, setItems] = useState([]);
  const [itemsOwnerId, setItemsOwnerId] = useState(null);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const [loadFailed, setLoadFailed] = useState(false);
  const load = useCallback(async () => {
    if (!userId) return;
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError("");
    setLoadFailed(false);
    try {
      const response = await getAnnouncementsAPI();
      if (currentRequest !== requestId.current) return;
      const data = response?.data || response || [];
      const nextItems = Array.isArray(data) ? data : data?.items;
      setItems(Array.isArray(nextItems) ? nextItems : []);
      setItemsOwnerId(userId);
      setUnread(
        Number.isFinite(data?.unread)
          ? data.unread
          : Array.isArray(nextItems)
            ? nextItems.filter((item) => !item.is_read).length
            : 0,
      );
    } catch (reason) {
      if (currentRequest !== requestId.current) return;
      setLoadFailed(true);
      setError(reason instanceof Error ? reason.message : "Không thể tải thông báo");
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }, [userId]);
  useEffect(() => {
    requestId.current += 1;
    setItems([]);
    setItemsOwnerId(null);
    setUnread(0);
    setLoading(Boolean(userId));
    setProcessing(false);
    setError("");
    setLoadFailed(false);
    if (!userId) return undefined;
    load();
    return () => {
      requestId.current += 1;
    };
  }, [load, userId]);
  const markRead = async (id) => {
    const currentRequest = requestId.current;
    setError("");
    try {
      await markAnnouncementReadAPI(id);
      if (currentRequest !== requestId.current) return;
      const notification = items.find((item) => (item._id || item.id) === id);
      if (notification && !notification.is_read) {
        setUnread((count) => Math.max(0, count - 1));
      }
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
      if (currentRequest !== requestId.current) return;
      setError(reason instanceof Error ? reason.message : "Không thể cập nhật thông báo");
    }
  };
  const markAllRead = async () => {
    if (!unread || processing) return;
    const currentRequest = requestId.current;
    setProcessing(true);
    setError("");
    try {
      await markAllAnnouncementsReadAPI();
      if (currentRequest !== requestId.current) return;
      setItems((current) =>
        current.map((item) => ({
          ...item,
          is_read: true,
        })),
      );
      setUnread(0);
    } catch (reason) {
      if (currentRequest !== requestId.current) return;
      setError(reason instanceof Error ? reason.message : "Không thể cập nhật thông báo");
    } finally {
      if (currentRequest === requestId.current) setProcessing(false);
    }
  };
  const remove = async (id) => {
    const currentRequest = requestId.current;
    setProcessing(true);
    setError("");
    try {
      await deleteAnnouncementAPI(id);
      if (currentRequest !== requestId.current) return;
      const notification = items.find((item) => (item._id || item.id) === id);
      if (notification && !notification.is_read) {
        setUnread((count) => Math.max(0, count - 1));
      }
      setItems((current) => current.filter((item) => (item._id || item.id) !== id));
    } catch (reason) {
      if (currentRequest !== requestId.current) return;
      setError(reason instanceof Error ? reason.message : "Không thể xóa thông báo");
    } finally {
      if (currentRequest === requestId.current) setProcessing(false);
    }
  };
  const visibleItems = itemsOwnerId === userId ? items : [];
  return {
    items: visibleItems,
    unread: itemsOwnerId === userId ? unread : 0,
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
