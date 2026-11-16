"use client";
import { Suspense } from "react";
import { usePathname } from "next/navigation";
import AppShell from "@/shared/components/layout/AppShell";
export default function MainLayout({ children }) {
  const pathname = usePathname();
  const isPublic = pathname.startsWith("/dieu-khoan") || pathname.startsWith("/tro-giup");
  if (isPublic) return children;
  return (
    <Suspense
      fallback={
        <div className="min-h-[100dvh] bg-canvas px-6 py-10">
          <div className="skeleton h-9 w-52" />
          <div className="skeleton mt-8 h-64 w-full" />
        </div>
      }
    >
      <AppShell requireAuth>{children}</AppShell>
    </Suspense>
  );
}
