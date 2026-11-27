# Bộ sơ đồ BPMN 2.0 cho Veriq

Bộ này mô hình hóa sáu quy trình nghiệp vụ liên quan đến yêu cầu và kiểm thử. Luồng được đối chiếu với mã nguồn hiện có, sau đó biểu diễn thành sơ đồ `.drawio` có thể mở và chỉnh sửa trong diagrams.net. Các sơ đồ là mô hình quy trình theo phạm vi được nêu dưới đây; chúng không khẳng định mọi biến thể vận hành hoặc chính sách cấu hình đều giống nhau ở mọi dự án.

## Tài liệu mô tả chi tiết

Bản thuyết minh theo từng bước, gồm điều kiện, nhánh ngoại lệ và trạng thái kết thúc: [Mo_ta_chi_tiet_6_quy_trinh.md](Mo_ta_chi_tiet_6_quy_trinh.md).

## Danh mục quy trình

| STT | Quy trình | Tệp sơ đồ |
|---|---|---|
| 01 | Trích xuất yêu cầu từ tài liệu | [BPMN_Requirements_01_Nhap_tai_lieu_va_trich_xuat_yeu_cau_v1.drawio](drawio/BPMN_Requirements_01_Nhap_tai_lieu_va_trich_xuat_yeu_cau_v1.drawio) |
| 02 | Soạn thảo và phê duyệt yêu cầu | [BPMN_Requirements_02_Soan_thao_va_phe_duyet_yeu_cau_v1.drawio](drawio/BPMN_Requirements_02_Soan_thao_va_phe_duyet_yeu_cau_v1.drawio) |
| 03 | Lập và phê duyệt kế hoạch kiểm thử | [BPMN_Testing_03_Lap_va_phe_duyet_ke_hoach_kiem_thu_v1.drawio](drawio/BPMN_Testing_03_Lap_va_phe_duyet_ke_hoach_kiem_thu_v1.drawio) |
| 04 | Thiết kế và phê duyệt ca kiểm thử | [BPMN_Testing_04_Thiet_ke_va_phe_duyet_ca_kiem_thu_v1.drawio](drawio/BPMN_Testing_04_Thiet_ke_va_phe_duyet_ca_kiem_thu_v1.drawio) |
| 05 | Phân công và thực thi kiểm thử | [BPMN_Testing_05_Phan_cong_va_thuc_thi_kiem_thu_v1.drawio](drawio/BPMN_Testing_05_Phan_cong_va_thuc_thi_kiem_thu_v1.drawio) |
| 06 | Xử lý lỗi và kiểm thử lại | [BPMN_Quality_06_Xu_ly_loi_va_kiem_thu_lai_v1.drawio](drawio/BPMN_Quality_06_Xu_ly_loi_va_kiem_thu_lai_v1.drawio) |

Sáu quy trình này bao quát chuỗi từ nhập và làm rõ yêu cầu đến lập kế hoạch, thiết kế ca, thực thi, rồi xử lý lỗi phát hiện được. “Rà soát yêu cầu”, “phê duyệt ca kiểm thử”, “thực thi kiểm thử” và “xử lý lỗi” là các hoạt động nằm trong quy trình rộng hơn, không bị bỏ khỏi phạm vi; chúng được thể hiện lần lượt trong quy trình 02, 04, 05 và 06.

## Mô tả quy trình và căn cứ từ mã nguồn

### 01. Trích xuất yêu cầu từ tài liệu

Luồng bắt đầu khi người dùng tải tệp hoặc nhập nội dung. Hệ thống kiểm tra định dạng, kích thước và nội dung; nếu hợp lệ, nội dung được đọc để trích xuất **yêu cầu đề xuất từ tài liệu**. Cách gọi này có chủ đích: nội dung trích xuất mới là đầu vào cần con người xác minh, chưa phải yêu cầu chính thức trong kho dữ liệu. Người rà soát có thể đối chiếu với tài liệu gốc và cảnh báo trùng, chỉnh sửa, gộp, tách hoặc loại nội dung không phù hợp. Chỉ các mục được chọn và xác nhận mới được ghi nhận thành yêu cầu; theo luồng tạo hiện có, chúng bắt đầu ở trạng thái `DRAFT`.

Mã nguồn không cho thấy một đường trích xuất AI duy nhất áp dụng cho mọi loại tài liệu. Nhánh AI phụ thuộc cấu hình và loại đầu vào; một số định dạng như OpenAPI hoặc Postman đi theo xử lý xác định thay vì nhánh AI. Phạm vi sơ đồ đặt tại thao tác nhập yêu cầu qua API, không gộp với worker phân tích tài liệu khác trong hệ thống.

**Căn cứ:** `backend/testing/src/modules/requirements/services/requirement_import_workflow.py`, `backend/testing/src/modules/requirements/services/requirement_lifecycle.py` và các tuyến/API nhập yêu cầu tương ứng.

### 02. Soạn thảo và phê duyệt yêu cầu

Người dùng tạo hoặc cập nhật nội dung cùng tiêu chí chấp nhận. Hệ thống kiểm tra dữ liệu và phiên bản trước khi yêu cầu được gửi rà soát. Nếu chưa đạt, người soạn bổ sung; nếu đạt, người rà soát có thể phê duyệt hoặc trả lại kèm nhận xét. Một yêu cầu được phê duyệt còn phải qua bước ghi nhận baseline và cập nhật chỉ mục. Vì thế, “đã được người rà soát chấp thuận” và “đã hoàn tất ghi nhận phiên bản nền” là hai mốc liên quan nhưng không nên nhập làm một.

Mã nguồn có ngoại lệ tự phê duyệt cho một số quyền như trưởng dự án hoặc quản trị viên hệ thống. Quy trình cũng có rà soát kỹ thuật, nhưng không thể kết luận đó là bước bắt buộc trong mọi đường đi; sơ đồ không biến nó thành điều kiện cứng. Các lỗi kiểm định hoặc xung đột phiên bản được thể hiện như đường không hoàn tất phê duyệt.

**Căn cứ:** `backend/testing/src/modules/requirements/services/requirement_lifecycle.py` và các dịch vụ kiểm định/baseline mà luồng này gọi.

### 03. Lập và phê duyệt kế hoạch kiểm thử

Kế hoạch có thể được khởi tạo thủ công hoặc nhận gợi ý sinh tự động. Người lập hoàn thiện phạm vi, môi trường và bộ kiểm thử; tiếp theo hệ thống kiểm tra tính đầy đủ trước khi gửi rà soát. Kế hoạch bị trả lại sẽ quay về bước chỉnh sửa. Khi được chấp thuận, hệ thống kiểm tra lại phạm vi và phiên bản để tạo snapshot đã duyệt. Snapshot này tạo mốc ổn định cho lượt chạy sau, thay vì để kế hoạch đang thay đổi âm thầm làm thay đổi nội dung đã được duyệt.

Khả năng tự phê duyệt phụ thuộc vai trò và trạng thái lưu nháp. Sơ đồ vì vậy biểu diễn đây là nhánh có điều kiện, không phải mặc định áp dụng cho mọi người lập kế hoạch.

**Căn cứ:** `backend/testing/src/modules/execution/services/test_plan.py`, `backend/testing/src/modules/execution/services/test_plan_generation.py`.

### 04. Thiết kế và phê duyệt ca kiểm thử

Ca kiểm thử có thể được soạn thủ công hoặc khởi tạo bằng gợi ý AI từ phiên bản yêu cầu. Người thiết kế hoàn thiện các bước và kết quả mong đợi. Trước khi gửi rà soát, hệ thống kiểm tra cấu trúc, mức đầy đủ và bằng chứng nguồn; nội dung chưa đạt quay lại chỉnh sửa. Người rà soát đánh giá ca và đối chiếu nguồn. Khi chấp thuận, hệ thống kiểm tra tính hiện hành của nguồn và tính duy nhất, rồi mới tạo phiên bản đã duyệt, đóng băng bản nháp.

Các bước lint, đối chiếu nguồn và đóng băng phiên bản được giữ riêng trên sơ đồ vì chúng bảo vệ những thuộc tính khác nhau: chất lượng cấu trúc, khả năng truy nguyên, và tính ổn định của bản đã phát hành. Quyền tự phê duyệt hiện có được thể hiện dưới dạng ngoại lệ theo quyền, không phải quy tắc chung.

**Căn cứ:** `backend/testing/src/modules/design/services/test_case_lifecycle.py`, `backend/testing/src/modules/design/services/test_case_generation.py`, `backend/testing/src/modules/design/api/test_design.py`.

### 05. Phân công và thực thi kiểm thử

Người điều phối chọn kế hoạch, bộ ca và môi trường. Nếu gắn kế hoạch, phạm vi phải tham chiếu kế hoạch đã duyệt/snapshot phù hợp; hệ thống tạo lượt chạy cùng các kết quả ban đầu rồi cho phép phân công ở cấp lượt chạy hoặc từng ca. Tester thực thi từng ca và ghi nhận kết quả. Gateway lặp thể hiện còn ca nào cần thực thi hay không; nó không hàm ý thứ tự cố định hoặc chạy song song. Khi hết ca, chính sách dự án quyết định lượt chạy có thể hoàn tất với kết quả một phần hay phải tiếp tục/hủy với lý do.

Mã nguồn cũng hỗ trợ chạy lại trong một số trạng thái kết thúc. Tuy nhiên, chạy lại là một thao tác vòng đời riêng và không được mở rộng thành nhánh trong sơ đồ này, vốn tập trung vào một lượt phân công và thực thi.

**Căn cứ:** `backend/testing/src/modules/execution/services/test_run.py`, `test_run_execution.py`, `execution_state.py` và API thực thi.

### 06. Xử lý lỗi và kiểm thử lại

Lỗi được ghi nhận, có thể liên kết với kết quả kiểm thử, rồi phân loại. Tùy kết quả, hệ thống có thể xác nhận lỗi, đánh dấu trùng hoặc từ chối với lý do. Lỗi đã xác nhận được giao xử lý và cập nhật trạng thái. Sau khi xử lý, đường đi có thể đưa lỗi sang sẵn sàng kiểm thử lại hoặc mở lại để tiếp tục xử lý, phù hợp với các trạng thái chuyển tiếp được mã hóa. Khi kiểm thử lại, kết quả mới được ghi nhận gắn với ca tương ứng. Kết quả đạt dẫn đến đóng lỗi; không đạt thì mở lại lỗi.

Sơ đồ không giả định rằng mọi lỗi đều qua cùng một chuỗi trạng thái tuyến tính. Nhánh trùng/từ chối kết thúc riêng; các chuyển trạng thái của lỗi đã xác nhận phụ thuộc ma trận trạng thái hiện hành. Những bước điều tra nguyên nhân sâu hoặc phân tích xu hướng không được thêm nếu không phải là điều kiện bắt buộc trong luồng được triển khai.

**Căn cứ:** `backend/testing/src/modules/quality/services/defect_lifecycle.py`, `defect_records.py`, `backend/testing/src/modules/execution/services/execution_state.py`, cùng logic giao diện kiểm thử lại trong `frontend/features/testing/pages/workspace/defectRetest.logic.mjs`.

## Phân loại và truy vết quy trình

| STT | Trigger và vai trò chính | Phân loại | Căn cứ mã nguồn chính |
|---|---|---|---|
| 01 | Người dùng nhập tài liệu; Veriq trích xuất, người dùng rà soát và xác nhận | BPMN Process nội bộ | `requirement_import_workflow.py`: `create_requirement_import_job`, `extract_requirement_candidates`, `compare_requirement_import_job`, `resolve_requirement_import_candidate`, `merge_requirement_import_candidates`, `split_requirement_import_candidate`, `reject_requirement_import_candidate`, `apply_requirement_import_job` |
| 02 | Người soạn gửi yêu cầu; người rà soát quyết định; Veriq baseline | BPMN Process nội bộ | `requirement_lifecycle.py`: `submit_requirement_for_review`, `return_requirement_for_changes`, `technical_review_requirement`, `baseline_requirement` |
| 03 | Người lập tạo kế hoạch; người rà soát duyệt; Veriq tạo snapshot | BPMN Process nội bộ | `test_plan.py`: `create_test_plan_record`, `validate_test_plan_record`, `submit_test_plan_record`, `approve_test_plan_record`, `request_test_plan_revision`, `plan_snapshot`; `test_plan_generation.py::generate_test_plan_suggestion` |
| 04 | Người thiết kế tạo ca; người rà soát phê duyệt; Veriq lint và đóng băng phiên bản | BPMN Process nội bộ | `test_design.py`: `create_test_case_draft`, `generate_test_cases`, `submit_test_case_review`, `request_test_case_changes`, `approve_test_case`; `test_case_generation.py::generate_test_case_draft_records`; `test_case_lifecycle.py`: `lint_test_case_draft_record`, `submit_test_case_review_record`, `approve_test_case_draft_record` |
| 05 | Điều phối viên tạo/phân công lượt chạy; tester ghi kết quả; Veriq kiểm tra phạm vi | BPMN Process nội bộ | `test_run.py`: `create_test_run_record`, `assign_test_run_record`; `test_run_execution.py`: `start_test_run_record`, `record_test_result_entry`, `complete_test_run_record`, `abort_test_run_record`; `execution_state.py` |
| 06 | Người dùng ghi nhận lỗi; người xử lý chuyển trạng thái; tester kiểm thử lại | BPMN Process nội bộ | `defect_records.py::create_defect_record`; `defect_lifecycle.py`: `update_defect_record`, `transition_defect_record`, `retest_defect_record`; `execution_state.py::defect_transitions` |

Sáu luồng được xếp là Process vì mô tả phối hợp nội bộ giữa người dùng và dịch vụ Veriq. Không thấy participant bên thứ ba độc lập trao đổi thông điệp trong phạm vi này, nên không chọn Collaboration. Hoạt động AI là dịch vụ nội bộ, không phải một tổ chức tham gia riêng.

### Ánh xạ node theo nhóm chức năng

- **01:** Nhập và tạo job thuộc `create_requirement_import_job`; đọc/trích xuất thuộc `extract_requirement_candidates`; so sánh và giải quyết trùng thuộc `compare_requirement_import_job` và `resolve_requirement_import_candidate`; gộp/tách/từ chối thuộc hàm tương ứng; xác nhận và ghi dữ liệu thuộc `apply_requirement_import_job`/`confirm_requirement_import_job`.
- **02:** Soạn, kiểm tra, gửi, trả sửa, rà soát kỹ thuật và baseline ánh xạ lần lượt tới các hàm cùng tên trong `requirement_lifecycle.py` nêu trên.
- **03:** Tạo, kiểm định, gửi, duyệt và trả sửa ánh xạ tới hàm tương ứng trong `test_plan.py`; gợi ý thuộc `generate_test_plan_suggestion`; snapshot thuộc `plan_snapshot` và `plan_snapshot_hash`.
- **04:** Tạo/sinh bản nháp thuộc các API trong `test_design.py` và `generate_test_case_draft_records`; lint, rà soát, trả sửa và phê duyệt/đóng băng thuộc `test_case_lifecycle.py`.
- **05:** Tạo lượt chạy và phân công thuộc `test_run.py`; bắt đầu, ghi kết quả, hoàn tất và hủy thuộc các hàm cùng tên trong `test_run_execution.py`.
- **06:** Tạo lỗi thuộc `create_defect_record`; cập nhật/chuyển trạng thái/kiểm thử lại thuộc các hàm trong `defect_lifecycle.py`; ma trận trạng thái ở `defect_transitions`.

Trong từng spec JSON, `id` của node nối trực tiếp với các bước trong sơ đồ. Các node `process_data` là kho dữ liệu nghiệp vụ khái quát, không đại diện riêng cho một bảng vật lý.

## Checklist bàn giao

| Kiểm tra | Kết quả | Ghi chú |
|---|---|---|
| Start Event và đường đi tới End Event | Đạt theo verifier | Kiểm tra khả năng đi tới End. |
| Nhánh Gateway có nhãn; Parallel Gateway có cặp tách/nối | Đạt | Mọi nhánh gateway có nhãn; không dùng Parallel Gateway. |
| Node mồ côi, endpoint edge, ID trùng | Đạt, 0 lỗi | Đã kiểm tra cả sáu tệp. |
| Message Flow giữa các pool khác nhau | Không áp dụng | Không có Message Flow hoặc pool ngoài. |
| Task/Event/Gateway dùng shape BPMN | Đạt theo style XML | Đã đối chiếu tên shape; chưa render trực quan. |
| Đã xét Message, Timer, Error/Escalation, Compensation, Signal, Event Gateway, Multi-instance/Loop, Call Activity, Data Store, Black-box Pool | Đạt, có loại trừ | Lý do trong phần quy ước; Data Store được dùng. |
| Nhánh lỗi/ngoại lệ có căn cứ | Đạt trong phạm vi mô hình | Có lỗi nhập, trả sửa, xung đột nguồn/phiên bản, hoàn tất một phần, hủy, từ chối và kiểm thử lại không đạt. |
| `verify_drawio.py` | Đạt, 0 lỗi | 6 file, 109 node, 117 cạnh; 53 cạnh thẳng được kiểm tra; 64 cạnh waypoint được kiểm tra vuông góc/giao cắt. |
| Render PNG | Chưa thực hiện | Môi trường không có CLI diagrams.net. |
| XML parse và cấu trúc `.drawio` | Đạt | XML đọc được; cần mở trong diagrams.net để xác nhận hiển thị. |

## Quy ước và phạm vi mô hình hóa

- Mỗi sơ đồ có một pool Veriq và các lane theo nhóm trách nhiệm đã suy ra từ điểm tương tác người dùng/hệ thống. Tên vai trò nghiệp vụ cụ thể chưa được xác minh đầy đủ trong mã nguồn; cần chủ quy trình xác nhận trước khi dùng làm tài liệu vận hành chính thức.
- Data Store được nối với hoạt động liên quan bằng Data Association. Sequence Flow mô tả thứ tự điều khiển trong cùng pool. Không có Message Flow vì phạm vi hiện tại không mô tả tương tác với participant bên ngoài.
- Không đưa Timer Event, Error Boundary Event, Compensation, Signal, Event-based Gateway, Parallel Gateway, Multi-instance hay Call Activity vào các sơ đồ. Chúng không cần thiết để biểu diễn các nhánh được xác nhận trong phạm vi hiện tại; không nên suy diễn đồng thời hoặc xử lý bù nếu mã nguồn chưa chứng minh điều đó.
- Nhánh tự phê duyệt chỉ được dùng nơi có căn cứ vai trò/trạng thái. Nhánh AI được coi là xử lý nội bộ của Veriq, không tách thành pool ngoài.
- Tệp JSON trong `specs/` lưu ý định quy trình và vị trí dạng lưới; `gen_drawio.py` dùng chung để tạo sáu sơ đồ. Người chỉnh sửa có thể cập nhật spec rồi sinh lại sơ đồ thay vì sửa tay sáu bản riêng lẻ.

## Kiểm tra tệp

Chạy từ thư mục gốc repository:

```bash
python3 docs/bpmn-veriq/gen_drawio.py
python3 docs/bpmn-veriq/verify_drawio.py
```

Trình kiểm tra xác nhận XML đọc được, ID duy nhất, parent và geometry hợp lệ, tọa độ theo lưới 10 px, node nằm trong lane và không chồng lấn, endpoint hợp lệ, phạm vi pool của các loại flow, điểm neo, đường nối vuông góc và không xuyên node, nhánh gateway có nhãn, Start/End cùng khả năng đi tới End, và Data Store có Data Association.

Lần chạy bàn giao: **6 sơ đồ, 109 node, 117 cạnh; 53 cạnh không waypoint được kiểm tra thẳng hàng, 64 cạnh waypoint; 0 lỗi theo bộ kiểm tra hình học và cấu trúc trên.** Đây không phải chứng nhận đầy đủ ngữ nghĩa BPMN 2.0 hoặc kiểm thử hiển thị bằng ứng dụng diagrams.net. Trong môi trường hiện tại không có CLI diagrams.net để render từng sơ đồ; do đó người dùng nên mở các tệp trong diagrams.net để rà soát lần cuối về bố cục và khả năng đọc.

## CHƯA RÕ và xác nhận trước khi phát hành

Các điểm sau đây không được mã nguồn xác định đầy đủ, nên không nên xem sơ đồ là quy định tổ chức đã được phê chuẩn:

1. **Tên vai trò nghiệp vụ:** lane hiện dùng nhãn chức năng tổng quát như “Người nhập và rà soát”, “Người lập kế hoạch”, “Người rà soát” và “Tester”. Cần chủ quy trình ánh xạ các lane này sang chức danh hoặc nhóm thực tế nếu dùng sơ đồ trong SOP.
2. **Chính sách theo dự án:** tự phê duyệt, quyền hoàn tất lượt chạy một phần và điều kiện xử lý phiên bản có thể chịu ảnh hưởng của quyền hoặc cấu hình triển khai. Mã có nhánh điều kiện, nhưng giá trị cấu hình cụ thể cần được đối chiếu ở môi trường sử dụng.
3. **Thuật ngữ giao diện:** “Yêu cầu đề xuất từ tài liệu” chỉ nội dung trích xuất chờ xác minh. Nếu giao diện đang dùng tên khác, nên thống nhất nhãn mà vẫn phân biệt rõ nội dung đề xuất với yêu cầu đã được nhập/chấp thuận.
4. **Xác nhận trực quan:** style BPMN được đối chiếu với mã nguồn diagrams.net, nhưng chưa render bằng phiên bản ứng dụng đích trong môi trường này. Cần mở sáu tệp và xác nhận bố cục trước khi phát hành chính thức.

## CHƯA CHẮC STYLE

Không có tên shape hoặc thuộc tính nào được cố ý để ở trạng thái chưa xác minh: các style đang dùng được đối chiếu với `Sidebar-BPMN.js` và `mxBpmnShape2.js` của dự án diagrams.net. Tuy vậy, việc xác nhận mã nguồn style không thay thế kiểm tra hiển thị thực tế; mục xác nhận trực quan ở trên vẫn còn hiệu lực.

Nguồn đối chiếu style: [Sidebar-BPMN.js](https://github.com/jgraph/drawio/blob/dev/src/main/webapp/js/diagramly/sidebar/Sidebar-BPMN.js) và [mxBpmnShape2.js](https://github.com/jgraph/drawio/blob/dev/src/main/webapp/shapes/bpmn/mxBpmnShape2.js).
