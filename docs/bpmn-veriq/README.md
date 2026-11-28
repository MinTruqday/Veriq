# Sáu sơ đồ BPMN và mô tả quy trình

Bộ tài liệu gồm sáu sơ đồ có thể mở và chỉnh sửa bằng Draw.io, kèm phần mô tả theo từng bước. Nội dung được đối chiếu với mã nguồn của dự án. Các sơ đồ sử dụng các vai trò BA, Tester, Admin và Hệ thống; quy trình xử lý lỗi chỉ có các làn Tester, Admin và Hệ thống. Thông tin phân công thuộc hồ sơ lỗi, không tạo thêm tác nhân.

## Danh mục sơ đồ

| STT | Quy trình | Sơ đồ |
|---|---|---|
| 01 | Nhập tài liệu và trích xuất yêu cầu | [Mở sơ đồ](drawio/BPMN_Requirements_01_Nhap_tai_lieu_va_trich_xuat_yeu_cau_v1.drawio) |
| 02 | Soạn thảo và phê duyệt yêu cầu | [Mở sơ đồ](drawio/BPMN_Requirements_02_Soan_thao_va_phe_duyet_yeu_cau_v1.drawio) |
| 03 | Lập và phê duyệt kế hoạch kiểm thử | [Mở sơ đồ](drawio/BPMN_Testing_03_Lap_va_phe_duyet_ke_hoach_kiem_thu_v1.drawio) |
| 04 | Thiết kế và phê duyệt ca kiểm thử | [Mở sơ đồ](drawio/BPMN_Testing_04_Thiet_ke_va_phe_duyet_ca_kiem_thu_v1.drawio) |
| 05 | Phân công và thực thi kiểm thử | [Mở sơ đồ](drawio/BPMN_Testing_05_Phan_cong_va_thuc_thi_kiem_thu_v1.drawio) |
| 06 | Xử lý lỗi và kiểm thử lại | [Mở sơ đồ](drawio/BPMN_Quality_06_Xu_ly_loi_va_kiem_thu_lai_v1.drawio) |

## Mô tả đầy đủ

[Mở phần mô tả sáu quy trình](Mo_ta_chi_tiet_6_quy_trinh.md). Mỗi quy trình có phần diễn giải luồng chính, các bước chi tiết và quy tắc nghiệp vụ. Tại mỗi bước, các mục về tác nhân, đầu vào, xử lý, đầu ra và nhánh lỗi được nêu khi phù hợp với quy trình.

Sơ đồ ca kiểm thử thể hiện Admin là người phê duyệt. Tester gửi ca để xét duyệt nhưng không tự phê duyệt.
