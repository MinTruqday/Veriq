# Kiểm tra nghiệp vụ và phân quyền Veriq

Ngày lập: 05/11/2026. Tài liệu theo dõi triển khai kế hoạch đã chốt với người dùng. Đây là hồ sơ kiểm tra mã và nghiệm thu; việc có route, service hoặc màn hình không có nghĩa luồng đã đạt trên Docker.

## 1. Quyết định nghiệp vụ đã chốt

- Không khóa danh mục role nghiệp vụ trong sản phẩm. Mỗi dự án cấu hình role ID, capability và phạm vi trách nhiệm theo chính sách của dự án; một người có thể được gán các trách nhiệm khác nhau theo từng phạm vi nếu policy cho phép.
- Quyền soạn, sửa, rà soát, duyệt, thực thi, ghi kết quả, xử lý lỗi và phát hành được cấu hình thành capability riêng; người dùng chỉ thao tác trong scope được giao.
- Tác giả và người tham gia sửa nội dung của revision gửi duyệt không được duyệt revision đó. Việc gửi hộ, nếu không sửa nội dung, không biến người gửi thành tác giả.
- Thiếu người duyệt đủ capability thì chờ phân công; người tạo/sửa revision không được tự duyệt revision đó. Quyền quản trị nền tảng không tự cấp quyền nghiệp vụ dự án.
- Chủ nghiệp vụ và người quyết định phát hành là trách nhiệm được chỉ định rõ, có phạm vi; không cấp thêm toàn bộ quyền của role khác.
- Quyền xem, tải, nhận xét, sửa, AI đọc nguồn và quyết định nghiệp vụ được kiểm tra riêng.
- AI Agent chỉ chạy từ thao tác người dùng khởi tạo, dùng quyền hiện tại của người yêu cầu và tạo đề xuất/bản nháp; mọi thao tác ghi và quyết định tiếp theo cần thao tác riêng có quyền.
- Ưu tiên desktop 1280/1440/1920 px. Không thay thiết kế toàn dự án ngoài phần cần làm rõ trách nhiệm và hành động.
- Không commit/push nếu chưa có yêu cầu mới của người dùng.

## 2. Cơ sở đối chiếu

Tên BA, QA, Tester, Developer, Viewer và Admin xuất hiện ở các bảng kiểm thử phía dưới chỉ là nhãn người/fixture của những lượt nghiệm thu đã ghi ngày. Chúng không phải danh mục role cố định hay phân quyền mặc định của sản phẩm.

ISTQB mô tả lập kế hoạch, giám sát/điều chỉnh, phân tích, thiết kế, chuẩn bị, thực thi và hoàn tất. Các hoạt động có thể lặp hoặc song song tùy dự án. Requirement, Plan, Scenario, Case và Run là dữ liệu phục vụ các hoạt động, không phải một tiêu chuẩn bắt buộc mọi tổ chức phải đi qua cùng các màn hình. Nguồn: [ISTQB CTFL, 1.4.1](https://tbok.istqb.org/search?q=FL-1.4.1).

Jira được tham khảo về chính sách quyền theo dự án, role và phạm vi đối tượng. Xray được tham khảo về việc phân biệt tài sản kiểm thử dùng lại, kế hoạch và lần thực thi. Không coi ma trận quyền mặc định của một sản phẩm là quy định quốc tế cho mọi tổ chức. Nguồn: [Atlassian: permission schemes](https://support.atlassian.com/jira-cloud-administration/docs/grant-or-revoke-permissions-in-a-scheme/), [Xray: Test Sets và Test Plans](https://docs.getxray.app/space/XRAY/301474179/Test%20Sets%20vs%20Test%20Plans).

Đối chiếu các nguồn này giúp đánh giá thiết kế, không chứng nhận Veriq tuân thủ một tiêu chuẩn hoặc đã có đầy đủ mọi chức năng của Jira/Xray.

## 3. Luồng và sản phẩm bàn giao

**Thiết lập trách nhiệm → tài liệu → làm rõ/xác nhận Requirement → Test Plan → phân tích điều kiện kiểm thử → Scenario/Test Case → chuẩn bị → Test Run → Defect/retest/hồi quy → đánh giá kết thúc → báo cáo → quyết định phát hành/bàn giao.**

Giám sát, rủi ro, quản lý thay đổi và truy nguyên chạy xuyên suốt. Plan có thể được lập nháp sớm. Ca kiểm thử nằm trong kho dùng lại; Plan và Run chọn đúng phiên bản. Kết quả cũ không được chuyển thành kết quả thực thi mới.

| Hoạt động | Đầu vào chính | Sản phẩm và điều kiện chuyển tiếp |
| --- | --- | --- |
| Thiết lập dự án | Thành viên, phạm vi, cấu hình, trách nhiệm | Người chịu trách nhiệm và người xác nhận/phát hành đủ quyền; cấu hình không mở quyền chéo role |
| Thu thập nguồn | Tệp gốc, phiên bản, quyền đọc/AI | Nội dung đọc được, phần chưa đọc được và vị trí nguồn; không đồng nhất upload thành trích xuất thành công |
| Requirement và BR | Nguồn, câu hỏi làm rõ, tiêu chí chấp nhận | Nội dung được xác nhận nghiệp vụ, đánh giá khả năng kiểm thử, baseline và lịch sử thay đổi |
| Test Planning | Requirement, rủi ro, nguồn lực | Plan có phạm vi, mục tiêu, cách tiếp cận, cấp/loại, trách nhiệm, môi trường/dữ liệu, lịch, entry/exit criteria, ước lượng, xử lý lỗi và bàn giao |
| Test Analysis | Test basis, tiêu chí/rủi ro | Điều kiện kiểm thử, nghĩa vụ bao phủ, phần chưa rõ và người cần trả lời |
| Test Design | Điều kiện, kỹ thuật, nguồn đã xác nhận | Scenario/Case có hành động, dữ liệu, kết quả mong đợi, nguồn, reviewer độc lập và phiên bản |
| Test Implementation | Plan, phiên bản ca, nguồn lực | Bộ ca, dataset, build, môi trường sẵn sàng, lịch/phân công; không chạy khi điều kiện bắt đầu bắt buộc chưa đạt |
| Test Execution | Run đã chuẩn bị | Kết quả từng ca/bước, bằng chứng, sai lệch và Defect; ghi đúng người chạy và phiên bản |
| Defect và hồi quy | Bằng chứng lỗi, build sửa | Triage, sửa, retest, reopen/close, ca hồi quy; người sửa không tự xác nhận retest khi policy yêu cầu độc lập |
| Completion | Kết quả, exit criteria, lỗi/rủi ro còn lại | Báo cáo hoàn tất, bàn giao, tồn đọng, bài học; quyết định phát hành tách khỏi việc đánh giá chất lượng |

## 4. Ma trận trách nhiệm mục tiêu

| Capability/trách nhiệm | Chịu trách nhiệm | Giới hạn |
| --- | --- | --- |
| Requirement | Người được giao nội dung nghiệp vụ tạo/sửa; người có capability rà soát/duyệt | Không tự duyệt revision mình tạo/sửa; quyền nền tảng không thay quyền dự án |
| Test Plan và Test Analysis | Người được giao lập kế hoạch/phân tích; reviewer được chỉ định độc lập | Không sửa dữ liệu nguồn nếu không có capability riêng |
| Test Design | Người được giao tạo Scenario/Case; reviewer có capability tương ứng | Không sửa baseline đã duyệt; thay đổi qua revision |
| Test Execution | Người được phân công và có capability ghi kết quả | Không ghi thay hoặc tự xác nhận kết quả người khác |
| Defect và hồi quy | Người được giao xử lý; người retest độc lập khi policy yêu cầu | Người sửa không tự xác nhận retest/đóng lỗi nếu thiếu quyền |
| Dữ liệu dự án và nền tảng | Capability quản trị dự án/nền tảng được cấp riêng | Không tự mở quyền đọc riêng tư, duyệt nghiệp vụ hoặc xem dữ liệu tài chính |
| Người quyết định phát hành | Chấp nhận/từ chối phát hành dựa trên hồ sơ chất lượng | Không sửa kết quả kiểm thử; nêu lý do và rủi ro khi quyết định vượt khuyến nghị |
| AI Agent | Yêu cầu người dùng, nguồn được phép, đề xuất/bản nháp có dẫn chứng | Không tự duyệt/phát hành/ghi PASS-FAIL hoặc tăng quyền bằng tài khoản dịch vụ |

## 5. Kiểm kê mã hiện có

Kiểm kê tĩnh ban đầu đếm được 653 khai báo route HTTP trong `backend/testing/src/modules/*/api/*.py` bằng AST. Đây là số khai báo decorator, không phải số URL duy nhất, số chức năng độc lập hoặc số luồng đã nghiệm thu. Chưa bao gồm route của authentication, AI, cloud, content, notification và các service ngoài module testing; các service đó phải được nối vào chương trình nghiệm thu khi kiểm tra luồng xuyên suốt.

| Nhóm API | Số khai báo ban đầu | Mã/màn hình đã xác định | Trọng tâm cần nghiệm thu |
| --- | ---: | --- | --- |
| Projects | 61 | projects, work_items, collaboration, attachments; Dashboard, Planning, Settings | Thành viên, quyền, công việc/Sprint/backlog/roadmap, tiến độ, dữ liệu riêng, nhận xét/tệp |
| Requirements | 88 | requirements, records, imports, documents, templates, analysis; Requirements, DocumentReader, Knowledge | Upload/đọc/tóm tắt, consent AI, Requirement/BR, trùng, làm rõ, xác nhận, baseline, phiên bản |
| Design | 116 | test_analysis, test_design, test_repository, test_strategy, data_sets, adequacy; TestAnalysis, TestDesign, TestGovernance | Phân công Tester, nháp, độc lập duyệt, nguồn, phiên bản/kho ca, điều kiện và độ phủ |
| Execution | 146 | execution, context, monitoring, reporting, status_reports, completion; Execution, Releases, Monitoring, Reports, Completion | Plan/Run, build/environment, kết quả, report, lịch, xuất/phát hành, người nhận, quality gate |
| Quality | 156 | reviews, review_sessions, traceability, changes, risk, measurements, evaluations, NFR, improvement; Defects, Changes, Traceability, ReviewQueue | Defect/retest, nguồn/coverage, quyết định rủi ro, thay đổi, review và bàn giao |
| Integrations | 53 | API artifacts, scripts/execution, CI/CD, JUnit, connectors, webhooks | Chủ sở hữu kỹ thuật, quyền tích hợp, idempotency, xác thực nguồn kết quả và không thay thế duyệt của con người |
| Operations | 33 | jobs, bulk, notifications, operations, internal jobs/admin | Quyền khi xử lý nền, scope bulk, Admin, retry/hủy, thu hồi quyền và chống lộ dữ liệu |

Các service `skill_profiles.py`, `project_complexity.py`, hệ nhân lực/chi phí trong operations và capability AI cần kiểm tra cùng nguồn CV/lương, quyền tài chính và phạm vi chia sẻ. AI-12 hiện có API lấy phạm vi, xem lần rà soát gần nhất, tạo rà soát theo phạm vi đã chọn và giao diện tại Dashboard; thử gọi mô hình trên dữ liệu thật vẫn cần nghiệm thu riêng.

Kiểm kê bổ sung cùng cách đếm trong `backend/*/src/api/**/*.py` nhận diện 305 khai báo ở các service sau. Tổng 958 khai báo của hai lượt đếm là mốc kiểm kê mã, không bao gồm route có thể khai báo trực tiếp ở entrypoint hay được tạo động.

| Service ngoài testing | Số khai báo ban đầu | Trọng tâm nối vào nghiệm thu |
| --- | ---: | --- |
| Authentication | 112 | Phiên, passkey, tài khoản, thao tác nền tảng, thu hồi phiên và quyền Admin |
| AI | 76 | Capability, Agent, sự kiện cũ, nguồn truy xuất, embedding/index, quyền và vòng đời tác vụ |
| Cloud | 75 | Upload/download, share, folder/file/version, chunk, trash, search và internal access |
| Content | 35 | Nội dung, metadata, hierarchy/tag, bulk, version và quyền dữ liệu |
| Notification | 7 | Announcement và thông báo; không đồng nhất đọc thông báo với xem báo cáo |

Màn hình workspace đã nhận diện: Dashboard, Planning, Requirements, DocumentReader, Knowledge, TestAnalysis, TestDesign, TestGovernance, Execution, Releases, Defects, Changes, Monitoring, Traceability, ReviewQueue, Reports, Completion, Settings. Luồng xác thực, thông báo, vận hành và trang công khai nằm ngoài danh sách workspace này và vẫn thuộc chương trình kiểm tra.

## 6. Phát hiện ban đầu cần xử lý

Các mục dưới đây là phát hiện khi đọc mã ở đầu lượt triển khai, chưa phải kết luận từ API/UI thật. Khi mã được sửa phải ghi lại bằng chứng tại mục 8, không xóa lịch sử phát hiện rồi mặc định đạt.

| Mã | Phát hiện tĩnh | Căn cứ ban đầu | Điều kiện đóng |
| --- | --- | --- | --- |
| AUTH-01 | Nhiều domain ghi được gom về QA; chưa phân biệt hành động soạn nháp, kỹ thuật, thực thi và quyết định | `backend/testing/src/core/auth.py`, `required_business_role()` | Ma trận capability cụ thể; kiểm tra được phép/bị cấm trên UI, API, worker và AI |
| AUTH-02 | Quyền chịu ảnh hưởng của grants, settings, override và bước bổ sung lúc startup; cần chứng minh cùng chính sách | `core/auth.py`, `repositories/project_access.py`, `main.py` | Chính sách hiệu lực thống nhất, không cấp lại quyền đã bị thu hồi, migration có đối chiếu |
| AUTH-03 | BREAK_GLASS grant có nhánh bỏ qua thành viên thiếu/không active cho quyền đọc | `core/common.py`, `get_project()` | Tách rõ quy trình khôi phục vận hành khỏi truy cập nghiệp vụ; thử tài khoản rời dự án và Admin |
| REVIEW-01 | Helper duyệt ban đầu kiểm tra người tạo/người gửi nhưng chưa thể hiện đầy đủ người tham gia sửa theo revision | `core/human_decisions.py`, `require_independent_review()` | Người soạn/sửa bị chặn; người chỉ gửi hộ không bị nhầm tác giả; sửa/duyệt revision cũ bị từ chối |
| DESIGN-01 | Scenario chuyển trạng thái dùng cùng quyền update và action policy QA cho cả gửi/duyệt | `modules/design/services/test_scenario.py`, `transition_test_scenario_record()` | Tester gửi nháp được giao, QA khác người duyệt; mọi hành động có điều kiện riêng |
| RELEASE-01 | Quyết định quality gate và đóng release dựa trên capability; chưa thấy kiểm tra người quyết định phát hành được chỉ định trong đường gọi đã đọc | `modules/quality/services/quality_gate.py`, `modules/execution/services/execution_context.py` | Có chỉ định và kiểm tra scope/role hiện tại; QA không mặc nhiên phát hành |
| REPORT-01 | BA được coi là managing để đọc/sửa work report ngoài danh sách owner/editor | `modules/execution/services/reporting.py`, `report_for_user()` | Quyền quản lý cấu hình không tự cấp sửa nội dung; thử BA không được phân công và BA được phân công |
| REPORT-02 | Người duyệt work report chấp nhận BA hoặc QA chung; cần đối chiếu loại báo cáo và trách nhiệm | `modules/execution/services/reporting.py`, `participants()` | Phân biệt báo cáo công việc/kiểm thử; Viewer không Editor và reviewer khác người tham gia soạn |
| AI-01 | Hợp đồng AI manual đã có thay đổi trong working tree; build/static check không chứng minh luồng triển khai thật | `backend/ai/src/api/agents.py`, `services/automation.py`, `runtime/automation_worker.py` | Người bấm → job → tool → nháp/kết quả đúng quyền; kiểm tra thu hồi nguồn giữa lượt chạy |

### Tiến độ chỉnh sửa nguồn sau kiểm kê

| Phát hiện | Thay đổi đã quan sát trong working tree | Trạng thái nghiệm thu |
| --- | --- | --- |
| AUTH-01, AUTH-02 | Capability có `business_roles` và `responsibility`; auth đọc chính sách tập trung thay quy tắc gom domain về QA; migration policy chạy trong startup | 25 kiểm tra API ký JWT + MongoDB riêng đạt; còn phải đối chiếu mọi capability, mọi service và đường worker |
| AUTH-03 | Thành viên thiếu/không active bị chặn kể cả có grant | 25 kiểm tra API gồm Admin không có membership, Viewer chéo dự án và thành viên bị thu hồi đạt |
| REVIEW-01 | Theo dõi `content_author_ids`; người gửi hộ không thành tác giả; lịch sử thiếu thì không tự duyệt | 25 kiểm tra API kiểm tra người gửi/tác giả độc lập; 26 assertion bổ sung về revision, sửa nội dung và khôi phục lịch sử đạt; chưa rà hết đường ghi |
| DESIGN-01 | Tester sửa nháp được giao; QA duyệt độc lập | 42 kiểm tra API ký JWT + MongoDB riêng cho phân công Scenario/Case, chuyển giao, deny và trạng thái dự án đạt |
| RELEASE-01 | Capability có trách nhiệm `release_decision`; người quyết định được chỉ định riêng | 6 kiểm tra API trên MongoDB riêng: QA/BA/Viewer không được chỉ định bị chặn; QA được chỉ định ghi và retry idempotent thành công. Chưa chạy thao tác đóng release toàn luồng |
| REPORT-01, REPORT-02 | Báo cáo đọc/sửa theo owner/editor/reviewer/recipient; BA quản lý phân công nhưng không tự có quyền nội dung | 26 assertion cô lập về quyền đọc/sửa/duyệt và gán người nhận đạt; chưa nghiệm thu API phát hành đầy đủ |

Các trạng thái trên chỉ ghi việc đọc được sửa đổi trong mã. Chưa chuyển phát hiện thành đạt và chưa tick nghiệm thu toàn nhóm.

## 7. Thứ tự chỉnh sửa và yêu cầu kỹ thuật

1. Chốt danh mục capability theo từng hành động và ma trận role/trạng thái/phân công. Quyền đọc không kéo theo tải, comment, edit hoặc AI đọc.
2. Dùng cùng chính sách cho request, bulk/import/export, worker và AI. Thành viên phải active; project/object đúng phạm vi; trạng thái và revision hợp lệ.
3. Theo dõi tác giả/người tham gia sửa revision. Chỉ người đủ quyền, được phân công và độc lập mới duyệt. Quyết định cũ không áp dụng cho bản nội dung đã sửa.
4. Nối UI với quyền hành động hiệu lực; ẩn điều hướng không được phép, chặn URL trước khi trả nội dung và hiện cách xử lý thiếu phân công.
5. Chuẩn hóa trách nhiệm nghiệp vụ/phát hành; chặn quyền cộng thêm vô tình từ cấu hình hoặc token dịch vụ.
6. Bổ sung khoảng trống nghiệp vụ đã xác nhận: baseline/truy nguyên, coverage đã cũ, entry/exit criteria, dữ liệu/môi trường/build, exploratory charter nếu chưa có, bàn giao/tồn đọng và AI-12.
7. Migration giữ ID/tệp/lịch sử/kết quả. Xem trước tác động, chạy lặp an toàn và có phục hồi; không tự gán người duyệt để hợp thức hóa dữ liệu cũ.
8. Nghiệm thu tổng hợp sau ghép; lỗi sửa xong phải chạy lại phạm vi bị ảnh hưởng và luồng liên quan.

Không thêm nhãn kỹ thuật, đổi thiết kế hàng loạt hoặc xây hệ dữ liệu thứ hai chỉ để phục vụ phân quyền.

## 8. Chương trình nghiệm thu và bằng chứng

### Bằng chứng triển khai hiện có

- Đã bổ sung API chỉ đọc `GET /kiem-thu/du-an/{project_id}/quyen-hieu-luc`, dùng envelope hiện có và đăng ký trong projects router. API yêu cầu quyền đọc dự án cùng membership ACTIVE.
- API trả role của người gọi, quyền dự án hiện hành, lý do không được phép và trạng thái trách nhiệm chỉ ở dạng đã cấu hình/có phải người gọi hay không. Không trả ID người được phân công khác hoặc nội dung grants.
- Phạm vi kết quả là `PROJECT_CAPABILITY`, kèm `object_checks_required=true`: vẫn phải kiểm tra đối tượng, phân công, revision, trạng thái và độc lập duyệt tại API hành động. Không dùng danh sách này để coi mọi Test Case đều được sửa.
- Kiểm tra cục bộ 15 tình huống cho quyền role, override trái role, deny, chỉ định trách nhiệm, archive/read policy, không lộ ID người khác và từ chối membership thiếu đã đạt. Harness dùng các hàm auth hiện tại và dependency giả, không gọi database/provider; đây chưa phải bằng chứng API/Docker thật.
- `py_compile` các module mới và `git diff --check` đạt. Các checkbox luồng xuyên suốt dưới đây tiếp tục chờ nghiệm thu.
- Trên Docker sau khi ghép: 25 kiểm tra API dự án/Requirement, 42 API Scenario/Test Case/Defect và 6 API quyết định phát hành dùng JWT ký thật cùng MongoDB riêng; đều đạt. Thêm 26 assertion mục tiêu về tác giả revision, duyệt độc lập và quyền báo cáo. Index ngữ nghĩa được thay bằng no-op trong các fixture; không gọi provider AI ở các bộ này.
- Kiểm tra AI event: 3 yêu cầu domain event không có thao tác người dùng hợp lệ bị chặn, không tạo lượt chạy và không gọi provider; API năng lực `/tac-tu` sau khi đăng ký router trả 200 cho tài khoản QA.
- Smoke test đăng nhập UI bằng tài khoản QA hiện có đạt. Điều hướng trực tiếp qua 23 route workspace và 8 route công khai/tài khoản/vận hành/thông báo, kiểm tra ở 1280/1440/1920 px: không tràn ngang, không lỗi JavaScript hoặc HTTP 5xx. Bảng “Quyền của tôi” và Dashboard mở được. AI-12 scope hiển thị 1 Requirement đã đặt chuẩn trong dự án có dữ liệu; AI Agent endpoint trả 200. Ảnh lưu ngoài repository tại `/tmp/veriq-access-panel-live.png`, `/tmp/veriq-project-dashboard-role-1440.png` và `/tmp/veriq-dashboard-with-requirement-1440-clean.png`.
- Smoke test phát hiện API năng lực Agent `/tac-tu/du-an/{id}/nang-luc` trả 404 do `agents.router` chưa được đăng ký. Đã đăng ký router trong `backend/ai/src/main.py`, dựng lại riêng service AI; xác minh lại API trả HTTP 200 và Dashboard không còn lỗi 404.
- AI-12 chưa chạy inference trên tài liệu thật trong lần smoke này; Dashboard đang dùng dự án không có tài liệu/Requirement đủ điều kiện. Không đánh dấu kết quả AI hoặc chất lượng gợi ý là đạt dựa trên việc API scope trả 200.
- Đã có component `ProjectAccessPanel` và API client để xem vai trò, trách nhiệm của chính người gọi, chức năng được phép và lý do chưa được phép. Chi tiết chức năng thu gọn theo nhóm; nhãn kỹ thuật và ID không hiện cho người dùng. ESLint/Prettier phạm vi component/client đạt; ghép vào trang cài đặt và kiểm tra browser thuộc lượt nghiệm thu chung.

Chuẩn bị hai dự án, BA, hai QA, hai Tester, Developer, Viewer, Admin, người bị thu hồi quyền, tài liệu riêng tư, người xác nhận nghiệp vụ và người quyết định phát hành. Dùng dữ liệu có nội dung đầu/cuối, tên dài, phiên bản thay đổi, kết quả lỗi và rủi ro tồn đọng.

| Nhóm nghiệm thu | Tình huống bắt buộc | Trạng thái bằng chứng |
| --- | --- | --- |
| Luồng xuyên suốt | Tài liệu → Requirement → Plan → phân tích → Scenario/Case → chuẩn bị → Run → Defect/retest → Report → quyết định phát hành | Đã kiểm một số chặng Requirement, Scenario/Case, Defect; chưa chạy một lượt xuyên suốt toàn bộ |
| Quyền | Được phép/bị cấm bằng UI và API; đổi ID, chéo dự án, bulk, download, import, worker và AI | API đã kiểm một số role, chéo dự án và thu hồi thành viên; còn bulk/download/import/worker và toàn bộ capability |
| Duyệt độc lập | Tác giả, người sửa, gửi hộ, revision cũ, sửa sau duyệt, thiếu reviewer | API Requirement và assertion revision/tác giả đạt; còn các loại đối tượng và tất cả đường duyệt |
| Phân công | Tester ngoài scope; Developer tự retest/đóng lỗi; BA sửa report không được giao; QA lấn quyền quản trị/tài chính | API Scenario/Case/Defect đạt các trường hợp chính; quyền báo cáo qua assertion mục tiêu; còn mọi route vai trò |
| Viewer/Admin | Viewer chỉ xem/comment/tải đúng chia sẻ; không Editor; Admin không mặc nhiên đọc/duyệt | Chờ chạy trên mã đã ghép |
| Phiên bản/số liệu | Thay Requirement/Case không đổi kết quả cũ; coverage, tiến độ và report khớp nguồn | Chờ chạy trên mã đã ghép |
| Khôi phục | Nhấp lặp, revision conflict, provider/API lỗi, worker restart, thu hồi quyền giữa lượt chạy | Chờ chạy trên mã đã ghép |
| AI | Yêu cầu thủ công, đúng người/quyền/nguồn/ngôn ngữ; không tự quyết; trích dẫn không lộ nguồn bị thu hồi | Agent capabilities và AI-12 scope đã smoke trên Docker; chưa chạy inference/thu hồi quyền giữa lượt |
| Desktop | 1280/1440/1920 px, dữ liệu dài, trạng thái tải/rỗng/lỗi, từng role | QA điều hướng 31 route đạt không tràn ngang ở ba kích thước, không JS error/HTTP 5xx; chưa kiểm dữ liệu dài và từng role khác |

Mỗi bằng chứng cần ghi mã kiểm tra, phiên bản mã, môi trường, tài khoản/role, scope, đầu vào, thao tác, kết quả mong đợi/thực tế và đường dẫn ảnh/log đã khử dữ liệu nhạy cảm. Số unit test hoặc route không thay cho bằng chứng xuyên suốt.

## 9. Checklist hoàn tất

- [x] Ghi quyết định role/phân công/duyệt độc lập đã được người dùng chốt.
- [x] Kiểm kê tĩnh các nhóm route API testing và các màn hình workspace hiện có.
- [x] Ghi các phát hiện ban đầu cùng đường mã cần đối chiếu.
- [ ] Đóng toàn bộ phát hiện bằng sửa mã và bằng chứng kiểm thử liên quan.
- [ ] Đối chiếu chính sách hiệu lực UI/API/bulk/worker/AI cho mọi capability được dùng.
- [ ] Hoàn tất kiểm tra các service ngoài testing trong luồng xuyên suốt.
- [ ] Migration có xem trước, chạy lặp và phục hồi đã được thử.
- [ ] Luồng thật trên Docker đạt với đúng dữ liệu, quyền, phiên bản và khôi phục.
- [ ] Có ảnh desktop theo role và báo cáo kết quả thực tế.

Chỉ tick cả chức năng khi tất cả điều kiện liên quan đạt. Không lấy việc sửa một helper để đánh dấu hoàn tất toàn bộ nhóm nghiệp vụ.
