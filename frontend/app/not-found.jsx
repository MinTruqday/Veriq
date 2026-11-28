import SystemStatusPage from "@/shared/components/common/SystemStatusPage";

export default function NotFound() {
  return (
    <SystemStatusPage
      code="404"
      eyebrow="Không tìm thấy trang"
      title="Đường dẫn này không còn khả dụng"
      description="Kiểm tra lại địa chỉ hoặc quay về danh sách dự án để tiếp tục"
      primaryHref="/du-an"
      primaryLabel="Mở danh sách dự án"
    />
  );
}
