"use client";
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import {
  getAnnouncementsAPI,
  markAnnouncementReadAPI,
} from "@/features/notification/services/announcement.service";
import { useAuth } from "@/features/authentication/contexts/AuthContext";
const AnnouncementContext = createContext(undefined);
export function AnnouncementProvider({ children }) {
  const { user } = useAuth();
  const userId = user?._id || null;
  const [announcements, setAnnouncements] = useState([]);
  const [announcementsOwnerId, setAnnouncementsOwnerId] = useState(null);
  const requestId = useRef(0);
  const fetchAnnouncements = useCallback(async () => {
    if (!userId) return;
    const currentRequest = ++requestId.current;
    try {
      const data = await getAnnouncementsAPI();
      if (currentRequest !== requestId.current) return;
      let arr = data.data || data || [];
      if (!Array.isArray(arr)) arr = [];
      setAnnouncements(arr);
      setAnnouncementsOwnerId(userId);
    } catch (e) {
      if (currentRequest === requestId.current) {
        console.error("Error fetching global announcements:", e);
      }
    }
  }, [userId]);
  const markAsRead = useCallback(async (id) => {
    const currentRequest = requestId.current;
    try {
      await markAnnouncementReadAPI(id);
      if (currentRequest !== requestId.current) return;
      setAnnouncements((prev) =>
        prev.map((n) =>
          n._id === id
            ? {
                ...n,
                is_read: true,
              }
            : n,
        ),
      );
    } catch (e) {
      if (currentRequest === requestId.current) {
        console.error("Error marking announcement as read:", e);
      }
    }
  }, []);
  useEffect(() => {
    requestId.current += 1;
    setAnnouncements([]);
    setAnnouncementsOwnerId(null);
    if (!userId) {
      setAnnouncements([]);
      return;
    }
    fetchAnnouncements();
    const interval = setInterval(() => {
      fetchAnnouncements();
    }, 30000);
    return () => {
      clearInterval(interval);
      requestId.current += 1;
    };
  }, [userId, fetchAnnouncements]);
  const visibleAnnouncements = announcementsOwnerId === userId ? announcements : [];
  const unreadCount = Array.isArray(visibleAnnouncements)
    ? visibleAnnouncements.filter((n) => !n.is_read).length
    : 0;
  return (
    <AnnouncementContext.Provider
      value={{
        announcements: visibleAnnouncements,
        unreadCount,
        fetchAnnouncements,
        markAsRead,
      }}
    >
      {children}
    </AnnouncementContext.Provider>
  );
}
export function useAnnouncements() {
  const context = useContext(AnnouncementContext);
  if (!context) {
    throw new Error("useAnnouncements must be used within a AnnouncementProvider");
  }
  return context;
}
