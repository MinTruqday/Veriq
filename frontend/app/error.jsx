"use client";
import { useEffect } from "react";
import SystemStatusPage from "@/shared/components/common/SystemStatusPage";
export default function AppError({ error, reset }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <SystemStatusPage
      code="!"
      eyebrow="Có lỗi xảy ra"
      title="Không thể hiển thị trang này"
      description="Thử tải lại trang hoặc quay về trang chủ để tiếp tục."
      onRetry={reset}
      primaryLabel="Thử lại"
      secondaryHref="/"
      secondaryLabel="Về trang chủ"
    />
  );
}
