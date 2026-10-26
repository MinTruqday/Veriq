# Bằng chứng nâng cấp Veriq theo kế hoạch tổng thể

Ngày kiểm chứng: 24/10/2026, múi giờ Việt Nam.

Đây là nhật ký triển khai và nghiệm thu của kế hoạch tổng thể người dùng đã chốt, **không phải kế hoạch thay thế**. Không đánh dấu toàn hệ thống hoàn tất bằng số bài kiểm thử của một module.

Inventory hiện trạng AI và Frontend, gồm hành vi theo từng sự kiện, thiếu triển khai, thiếu kiểm thử và điều kiện nghiệm thu tích hợp, nằm tại [TON_DONG_AI_VA_FRONTEND.md](TON_DONG_AI_VA_FRONTEND.md). Inventory được đối chiếu với code; trạng thái test của từng lát cắt được cập nhật phía dưới.

## Phạm vi thực sự đã nâng cấp trong đợt này

### Quyền và vòng duyệt

- Quyền dự án được đọc từ mô hình typed `ProjectAccessControl` trong collection `project_access_control`, không còn lấy quyền chạy thực tế trực tiếp từ `runtime_policies`.
- Migration chuyển danh mục quyền, grant theo role và điều kiện cấu hình; kiểm tra tham chiếu hợp lệ trước khi ghi. Bản quyền cũ được giữ nguyên để đối chiếu/phục hồi. Membership không bị thay đổi.
- Bản chuyển đổi và migration audit được ghi trong cùng transaction. Chạy lại không tạo bản sao. Chưa kiểm chứng chèn lỗi giữa transaction trong lượt này.
- Ràng buộc nghiệp vụ được kiểm tra sau override/grant: Tester không sửa/import/bulk-update/duyệt định nghĩa ca; BA không tự duyệt Requirement; QA không tự sửa Requirement nghiệp vụ. Tài khoản BA+QA giữ cả hai phần quyền.
- API trả danh sách quyền cho frontend cũng loại grant không hợp lệ với ràng buộc nghiệp vụ. Chưa kiểm chứng toàn bộ frontend theo role.
- AI nhập tài liệu chạy dưới BA phù hợp; AI thiết kế ca chạy dưới QA phù hợp. Đây là danh tính chuẩn bị dữ liệu, không phải quyền ra quyết định thay người dùng.
- Luồng tài liệu, thay đổi Requirement, bảo trì, cập nhật trace và thay đổi Test Plan không còn tự gọi API duyệt. API cũng từ chối danh tính AI khi duyệt, đóng phiếu làm rõ hoặc quyết định phát hành.
- Requirement nháp không được dùng để AI sinh ca. QA duyệt Requirement phát sự kiện riêng theo ID phiên bản, revision và trạng thái; không bị sự kiện lưu nháp trước đó chiếm khóa chống trùng.
- Phiếu đã có câu trả lời vẫn chờ QA kiểm chứng; việc câu trả lời xuất hiện trong nguồn không tự đóng phiếu.
- Prompt và trạng thái chờ đã được chỉnh theo cùng nguyên tắc, không chỉ chặn API rồi để luồng báo lỗi.

### Nguồn tài liệu và chỉ mục

- PDF/DOCX đi qua API Docling hiện có; cả lần nhập và retry dùng cùng đường chuyển đổi. Không dựng hệ import thứ hai.
- MongoDB lưu `source_structure` và `parse_report` cùng nội dung chuẩn hóa: ID khối, khối cha, loại, thứ tự, trang/tọa độ nếu có, phần chưa trích xuất, tên/phiên bản parser.
- API chuyển đổi trả số trang không xác định là `null`; không gán trang 1 cho DOCX không có thông tin trang.
- Chia đoạn giữ tham chiếu khối, đường dẫn mục, vùng nguồn và khoảng ký tự. `offset_basis=normalized_block` nghĩa là khoảng ký tự thuộc văn bản chuẩn hóa của khối, không phải byte offset trong PDF.
- Đoạn giống nhau ở hai trang/khối khác nhau không bị gộp mất dấu vết. Bảng lấy nội dung bảng đầy đủ thay vì chỉ dùng phần văn bản rút gọn của item.
- Không còn cắt nội dung lập chỉ mục tại 50.000 ký tự ở client Testing hoặc service AI.
- Chỉ mục cũ chỉ được xóa sau khi Qdrant và BM25 đều nhận bản thay thế. Đây **không phải transaction phân tán**: lỗi giữa hai kho vẫn có thể để lại bản mới lẫn bản cũ cho đến lần retry; kiểm thử hiện xác nhận không xóa bản cũ khi ghi mới thất bại.
- ID điểm mới dựa trên project, phiên bản, hash nội dung và thứ tự đoạn để retry ổn định.
- Qdrant vẫn là chỉ mục, không phải cây tài liệu. Quan hệ cha–con được lưu qua ID và metadata của ứng dụng.

## Hợp đồng API được tái sử dụng/mở rộng

Nguồn hợp đồng chạy thực tế vẫn là schema FastAPI trong mã nguồn và `/openapi.json`, không có file cấu hình nghiệp vụ rời.

| API nội bộ | Hợp đồng liên quan |
|---|---|
| `POST /tri-thuc/chuyen-doi` | Giữ `data` dạng base64 và `filename`; bổ sung/giữ `structure`, `unprocessed_blocks`, `parser`, `parser_version`; `page_count` có thể `null`. Cần `X-Internal-Token`. |
| `POST /tri-thuc/du-an/{project_id}/doi-tuong` | Bổ sung trường tùy chọn `source_structure`; giữ dữ liệu và metadata hiện có. Không cắt nội dung âm thầm. |
| `POST /kiem-thu/noi-bo/quan-tri/tu-dong-hoa/du-an/{project_id}/nguoi-thuc-thi` | Bổ sung `required_role` chỉ nhận BA hoặc QA, mặc định QA để tương thích caller cũ. |
| Các API duyệt hiện hữu | Danh tính AI nhận `403 HUMAN_APPROVAL_REQUIRED`; không đổi URL hay định danh bản ghi. |

> **Đối chiếu lại luồng hiện hành ngày 25/10/2026:** các gạch đầu dòng trên là bằng chứng của một mốc triển khai cũ và không mô tả hành vi hiện tại của nhánh nhập tài liệu. Mã nguồn hiện tại trong `backend/ai/src/tools/automation_publication.py` gọi API gửi Requirement đi rà soát/chốt chuẩn và Test Case gửi rà soát/duyệt; `requirement_document_workflow.py` gọi các hàm này sau kiểm tra nguồn, câu hỏi làm rõ, baseline, lint và grounding, rồi đọc lại dữ liệu đã công bố. Điều này khớp với quyết định mới nhất của người dùng: luồng AI không dừng để chờ người dùng duyệt từng artifact. Các API duyệt thông thường vẫn giới hạn theo role; automation dùng quyền sự kiện nội bộ có scope. Không suy rộng điều này thành quyền tự quyết phát hành Release. Dòng cũ “không còn tự gọi API duyệt” và bảng hợp đồng API ở trên cần được coi là lịch sử, không phải trạng thái runtime. Phần cần hoàn thiện còn lại là chứng minh API/outbox/worker thật, quyền scope, rollback/idempotency, UI phản ánh kết quả và đầu-cuối tới execution/Release.

Mất kết nối converter không trả nội dung thay thế giả thành công. Luồng nhập hiện hữu ghi `PARSE_FAILED` để retry; chưa chuyển việc parse thành job nền/checkpoint từng trang.

## Kết quả đã chạy

| Kiểm chứng | Kết quả | Giới hạn của bằng chứng |
|---|---|---|
| Toàn bộ thư mục test AI hiện có trong Docker | 142 bài đạt | Có mock cho một số nhánh provider/service; không phải 142 luồng AI thật |
| Toàn bộ thư mục test Testing hiện có trong Docker | 60 bài đạt | Không thay cho ma trận hồi quy toàn ALM |
| Smoke HTTP qua API Testing đang chạy | 20 trường hợp đạt | BA, QA, Tester, Developer, Viewer, Admin không membership và BA+QA; quyền đọc/tạo/duyệt và từ chối AI sinh từ Requirement nháp |
| Migration quyền trên MongoDB thật | Lần đầu `MIGRATED`, lần sau `ALREADY_MIGRATED`; một audit; bản cũ còn nguyên | Chưa thử lỗi transaction hoặc nhiều process migration đồng thời |
| Client Testing → API AI → Docling thật | DOCX có đoạn văn và bảng được trích xuất, còn ID khối, không có trang giả | Tài liệu nhỏ tự sinh; không phải PDF scan 200 trang |
| Docling → API chỉ mục → Qdrant/BM25 → API tìm kiếm thật | Tìm lại đúng phiên bản và `source_spans.block_id` | Không chứng minh mọi cấu trúc PDF/bảng/hình hoặc mọi trường hợp thu hồi quyền |
| Lỗi kết nối converter thật | Cổng không có dịch vụ gây `ConnectError`, không fallback | Không giả lập timeout dài, HTML lỗi hoặc mọi loại lỗi upstream |
| Giữ chỉ mục cũ khi Qdrant/BM25 lỗi | Kiểm thử tự động đạt | Kiểm thử chèn lỗi bằng mock, không phải gây lỗi kho thật |
| `git diff --check` | Đạt | Không thay cho lint/build frontend |

### Kiểm chứng bổ sung: so sánh/ghép và duyệt nhóm ca kiểm thử

- Màn so sánh có ba vùng: bản gốc/đặc tả nguồn chỉ đọc, snapshot AI bất biến và bản kết quả có thể chỉnh sửa; bước được ghép theo ID ổn định thay vì vị trí mảng.
- Lưu bản ghép tạo lại nháp, giữ snapshot AI và nguồn; QA phải gửi rà soát/duyệt lại. Lựa chọn ghi là AI/bản gốc bị từ chối nếu giá trị kết quả không khớp đúng nguồn được chọn.
- Chỉnh phần mô tả/expected/step hoặc liên kết truy vết làm mất hiệu lực các khẳng định coverage/hypothesis; đổi phân loại như priority/impact không xóa bằng chứng bao phủ.
- So sánh liệt kê ca gần trùng theo ngưỡng cấu hình dự án, không tự gộp hoặc tự xóa ca.
- Duyệt nhóm tiền kiểm tra toàn bộ thành viên; cập nhật phiên bản, trạng thái nháp và audit trong cùng Mongo transaction. Trùng khóa phiên bản trả `409 TEST_CASE_VERSION_CONFLICT`; kiểm thử xác nhận toàn bộ nhóm rollback, retry bằng cùng operation ID thành công và phát lại không tạo phiên bản/audit thứ hai.
- Docker HTTP smoke đạt: QA xem/lưu/duyệt nhóm; Tester, BA, Developer, Viewer và platform Admin không có membership bị `403` khi ghép/duyệt; membership BA+QA ghép được và khi vào bước duyệt thì revision sai bị chặn `409` không đổi dữ liệu. QA được phép hoàn tất duyệt nhóm. Cùng lượt kiểm tra ca gần trùng, lựa chọn nguồn giả, rollback, retry và idempotency. Dữ liệu thử còn lại: 0.
- Browser smoke cho workspace QA đạt tại 1920, 1440, 1280, 768 và 390 px, không tràn ngang hoặc lỗi JavaScript. Khi mới mở, nút lưu ở trạng thái tắt và đóng không hỏi bỏ thay đổi; khi người dùng sửa tên ca, nút lưu bật và đóng có cảnh báo bản ghép chưa lưu. Đã mở modal so sánh, xem snapshot AI và hộp xác nhận duyệt nhóm. API dữ liệu là thật; hồ sơ đăng nhập được giả lập để cô lập kiểm tra UI. Đây chưa phải browser E2E cho mọi vai trò hoặc thao tác toàn ứng dụng.
- Unit Test Case Merge bổ sung kiểm tra nguồn AI giả mạo, bước theo ID và quy tắc khi nào cần xóa dấu bao phủ. Tổng Testing suite: 60 bài đạt.

Dữ liệu MongoDB tạm của smoke quyền được dọn theo project ID riêng; kiểm tra còn 0 bản ghi. Chỉ mục tạm của smoke nguồn được xóa qua API hiện có. Không xóa dữ liệu demo hoặc lịch sử của người dùng, không commit.

### Kiểm chứng bổ sung: tính nguyên tử của Sprint

- Phạm vi Sprint và liên kết hai chiều tới Work Item giờ được cập nhật trong một transaction MongoDB. Thay đổi phạm vi bỏ liên kết cũ đúng Sprint, thêm liên kết mới, từ chối Work Item đang thuộc Sprint khác và kiểm tra revision ngay trong giao dịch.
- Kết thúc Sprint cùng thao tác đưa việc dang dở về backlog, chuyển sang Sprint kế tiếp hoặc đổi trạng thái được xử lý trong cùng transaction; lỗi xung đột giữa chừng không để một phần Work Item bị chuyển.
- Smoke trực tiếp trên MongoDB Docker đạt: thêm/bỏ Work Item khỏi phạm vi; Work Item thuộc Sprint khác bị từ chối 409; stale revision trả 409 và giữ nguyên scope; lỗi được tiêm sau lần cập nhật Work Item đầu tiên làm rollback cả cập nhật Sprint lẫn Work Item; kết thúc Sprint đưa việc dang dở về backlog, chuyển sang Sprint kế tiếp hoặc hủy đúng liên kết/trạng thái.
- Với thao tác kết thúc và chuyển Sprint kế tiếp, lỗi được tiêm sau khi cập nhật hai Sprint làm transaction khôi phục trạng thái nguồn, phạm vi Sprint đích và Work Item.
- Toàn bộ Testing suite sau thay đổi: 61 bài đạt. Container Testing healthy. Dữ liệu thử Sprint và Work Item còn lại: 0.
- Chưa có browser E2E Planning theo vai trò, kiểm tra thao tác kéo thả/bàn phím và lịch tổng hợp. Không đánh dấu toàn bộ Planning là hoàn tất.

### Kiểm chứng bổ sung: tái sử dụng phiên bản Test Case qua nhiều Test Run

- Smoke qua service thực và MongoDB Docker với cùng một Test Case version trong hai Test Run khác nhau đạt: mỗi Run giữ kết quả riêng, người thực hiện, build và môi trường riêng; PASS ở Run thứ nhất không ghi đè FAIL ở Run thứ hai.
- Phát lại cùng `idempotency_key` trả đúng kết quả đã ghi, không tạo bản thứ hai. Ghi lại cùng ca trong cùng Run với key mới bị `409 RESULT_ALREADY_RECORDED`; ghi ca ngoài snapshot bị `422 TEST_NOT_IN_RUN_SNAPSHOT` và không phát sinh kết quả.
- Dữ liệu Test Run và kết quả dùng trong smoke còn lại: 0.

### Kiểm chứng bổ sung: thời gian dự án và lịch Work Item

- Project có `planned_start_at` và `planned_end_at`; API tạo/cập nhật từ chối ngày kết thúc bằng hoặc trước ngày bắt đầu. Khi cập nhật không hợp lệ, dữ liệu và revision giữ nguyên.
- Màn tạo dự án cho phép nhập hai mốc ngày; phần cài đặt dự án cho phép cập nhật lịch; Lộ trình hiển thị hai mốc tổng thể song song với lịch Initiative/Epic/Release. Thẻ dự án hiển thị khoảng thời gian dự kiến. Mốc trống được hiển thị là `chưa đặt`, không tự điền từ ngày tạo.
- Work Item có cùng hai trường lịch dự kiến; kiểm tra riêng xác nhận ngày kết thúc sai bị từ chối, patch sai không tăng revision, patch hợp lệ giữ mốc còn lại và tăng revision đúng.
- Smoke service với MongoDB Docker thật đạt cho cả Project và Work Item; mọi bản ghi tạm đã được xóa và xác nhận còn 0.
- Đã build Docker Testing và Frontend; Frontend qua Prettier, ESLint, Next.js production build và tạo đủ 15 route.
- Sau khi build và khởi động lại Frontend, request chưa đăng nhập tới `/du-an` được chuyển hướng đúng `307` tới `/dang-nhap`; không kiểm chứng thao tác có phiên đăng nhập trong browser ở lượt này.
- Bộ kiểm thử hiện có sau bổ sung: Testing 68 bài đạt, AI 142 bài đạt, kiểm thử ghép Test Case bằng Node 3 bài đạt. Đây là kiểm thử module/hợp đồng, không phải nghiệm thu browser toàn ứng dụng.
- Docker stack hiện có MongoDB, Testing và Frontend healthy tại thời điểm kiểm tra; các service không nằm trong tập vừa build/restart không được dùng kết quả này để suy ra đã khỏe lại.

LangSmith trả 429 vì quota trace theo tháng đã hết. Không coi trace đã được gửi thành công; việc này không làm các bài test nêu trên bị thất bại. Benchmark nghiên cứu không được dùng làm điều kiện tự duyệt dữ liệu.

## Ma trận chưa được phép đánh dấu hoàn tất

| Hạng mục trong kế hoạch chung | Trạng thái sau đợt này |
|---|---|
| Quyền và vòng duyệt | Đã nâng cấp và có smoke API; còn browser theo role, xử lý mọi điểm UI lệ thuộc cấu hình quyền cũ, kiểm chứng lỗi transaction và kiểm chứng tiếp tục checkpoint sau tất cả loại quyết định duyệt |
| Tài liệu/metadata | Đã nối converter → lưu cấu trúc → chỉ mục → tìm kiếm; vừa kiểm chứng PDF văn bản 200 trang, OCR scan một trang và bảng số hóa nhỏ. Còn PDF scan dài, bảng nhiều trang thực, ảnh/vùng cắt, job nền/checkpoint và migration metadata cũ |
| So sánh gốc–AI–bản ghép | Đã triển khai ba vùng, chọn/ghép trường và step theo ID, snapshot bất biến, cảnh báo trùng và duyệt nhóm nguyên tử; đã test API/Docker/browser hẹp. Còn E2E đầy đủ nhiều ca/role, stale-source end-to-end qua giao diện và retry mạng ngay trên UI |
| Trường Test Case | Đã thêm cấp/loại kiểm thử và ảnh hưởng dự kiến, mang qua draft/frozen version và UI tạo/ghép. Còn kiểm kê trường mở rộng typed và kiểm thử hồi quy import/maintenance trên dữ liệu cũ |
| Hồ sơ năng lực/CV và tự phân công | Đã có hồ sơ theo dự án, CV upload tạm/AI preview có nguồn, UI để sửa/xác nhận, gán kỹ năng cho Test Case và phân công tự động có snapshot. Còn E2E authenticated dùng API/model thật, phép đo phân công với ground truth, và xử lý vận hành/retry đồng thời xuyên suốt |
| Cấp kiểm thử/tái sử dụng qua các đợt | Đã xác minh bằng MongoDB Docker: cùng Test Case version có kết quả/assignee/build/environment độc lập giữa hai Run; idempotency, từ chối ghi trùng trong cùng Run và từ chối ngoài snapshot đều đạt. Còn test cả luồng Plan được duyệt → nhiều Run qua API/UI, rerun/retest và browser E2E |
| Planning và timeline | Đã làm nguyên tử cập nhật phạm vi/kết thúc Sprint, từ chối Work Item thuộc Sprint khác và kiểm tra scope/revision trong Docker; `BACKLOG`, `NEXT_SPRINT`, `CANCEL` cùng rollback giữa chừng đều đạt. Project/Work Item có ngày dự kiến và được kiểm tra với Mongo thật. Giữ List/Scrum/Kanban hiện có. Còn browser theo vai trò, lịch tổng hợp, bàn phím, kéo thả và cùng bộ lọc theo kế hoạch mới |
| Toàn frontend | Không tuyên bố đã refactor xong; chưa có ma trận mọi route và browser E2E đủ 5 kích thước trong đợt này |
| Ba luồng đầu-cuối tổng thể | Chưa nghiệm thu đầy đủ từ upload đến execution/defect/release; không suy ra từ smoke quyền, nguồn hay Test Case |

Không suy ra chức năng cũ bị thiếu chỉ vì chưa kiểm chứng trong đợt này. Khi làm tiếp phải nâng cấp đúng module hiện hữu, giữ version, execution, audit và trace link; không thay hệ thống bằng bản mới song song.

### Kiểm chứng bổ sung: trường mở rộng có kiểu cho Test Case

- Bổ sung cấu hình trường theo dự án với kiểu văn bản, số, có/không, ngày và danh sách lựa chọn; khóa trường duy nhất theo dự án và mã trường. Không sửa cấu trúc Test Case cũ hoặc tạo collection Test Case thứ hai.
- Chỉ QA của dự án (hoặc quản trị nền tảng có quyền cập nhật dự án) tạo được định nghĩa trường; Tester không tạo được. API GET yêu cầu quyền đọc Test Case.
- Giá trị lưu trên bản nháp và được sao chép vào phiên bản Test Case bất biến; clone và tạo phiên bản kế tiếp giữ nguyên giá trị hiện có. So sánh/ghép có trường dữ liệu mở rộng; chỉnh giá trị nháp theo đúng kiểu.
- Khi AI đề xuất phiên bản bảo trì từ một ca hiện có mà không trả trường mở rộng, hệ thống giữ lại giá trị người dùng đã nhập, không làm rỗng metadata chỉ vì AI không biết trường riêng của dự án.
- Kiểm tra kiểu không ép ngầm `true` thành số, lựa chọn ngoài danh sách, ngày sai định dạng, khóa trường lạ và giá trị không hữu hạn đều bị từ chối. Trường bắt buộc được kiểm tra khi gửi rà soát và khi QA duyệt, không làm hỏng việc tạo nháp AI cần biên tập.
- Bộ Testing suite sau thay đổi cuối: 76 bài đạt trong container Docker. MongoDB Docker smoke tạo/đọc định nghĩa trường và xác nhận unique index từ chối mã trùng; dữ liệu thử còn lại: 0.
- Frontend truyền/hiển thị giá trị mở rộng ở tạo nháp, biên tập, so sánh/ghép và xem chi tiết. Prettier, ESLint và Next.js production build trong Docker đạt; frontend/testing healthy; request chưa đăng nhập tới `/du-an` chuyển hướng 307 tới `/dang-nhap`.
- Chưa có API sửa/ẩn định nghĩa trường sau khi tạo; chưa có browser E2E đăng nhập xác nhận luồng QA tạo trường → Tester bị từ chối → QA nhập giá trị → phiên bản đã duyệt giữ snapshot. Không đánh dấu quản trị trường mở rộng hoàn tất toàn bộ.

Ma trận cập nhật: **trường Test Case** đã có schema, lưu trữ, phân quyền, giao diện cơ bản và kiểm thử kiểu; còn quản lý vòng đời định nghĩa trường, kiểm thử API có phiên đăng nhập qua nhiều role, kiểm thử import/maintenance dữ liệu cũ và E2E của luồng này.

## Kiểm kê tổng thể còn lại trước nghiệm thu kế hoạch lớn

Kiểm kê này đối chiếu mã nguồn ngày 24/10/2026 với kế hoạch tổng thể đã chốt. “Có mã” không đồng nghĩa đã nghiệm thu. Image Docker không cài `pytest`, nên test được chép tạm vào đúng container và `pytest` được cài trong `/tmp` của container; không đổi requirements/Dockerfile trong repository. Kết quả mới nhất của suite backend được ghi ở cuối tài liệu (Testing 87, AI 165); hai suite là test module/hợp đồng, không phải E2E toàn ALM. Frontend `pnpm quality` và Docker production build đạt. Ma trận dưới đây vẫn mô tả khoảng trống còn lại; các kết quả mới được bổ sung theo thời gian ở cuối tài liệu.

### Ma trận tồn đọng có bằng chứng

| Mảng | Đã xác nhận có trong code/runtime | Còn phải hoàn thiện hoặc chứng minh | Nghiệm thu còn thiếu |
|---|---|---|---|
| AI: nhập tài liệu → blueprint → Requirement → Test Case | Sự kiện `DOCUMENT_INGESTED` gọi `process_ingested_requirement_document`; workflow gọi `compile_testability_blueprint`, tổng hợp template, tạo/đối chiếu Requirement, tạo phiếu làm rõ, tìm trùng, sinh Test Case nháp, lint và đọc lại kết quả. Gate đủ căn cứ có thể tự chốt Requirement/Test Case trong quyền sự kiện đã ký; điểm mơ hồ, mâu thuẫn hoặc thiếu thông tin nghiệp vụ vẫn tạo clarification, không tự trả lời. | Unit tests chứng minh từng nhánh và signed permission; chưa chứng minh sự kiện thật chạy từ outbox qua worker, AI/Testing API và Mongo/Qdrant đến readback. Chưa E2E từ tài liệu mới qua Test Plan, Run, Defect đến Release hoặc xác minh retry/idempotency trên dữ liệu runtime. | Chưa có một lượt E2E Docker toàn chuỗi. Không kết luận AI tự xử lý toàn bộ chuỗi chỉ từ unit tests.
| AI: sự kiện sau nhập | Có nhánh riêng cho `REQUIREMENT_CHANGED`, `TEST_CASE_CHANGED/APPROVED`, `TEST_PLAN_CHANGED/APPROVED`, `TEST_EXECUTION_RECORDED`, `DEFECT_RECORDED`, `WORK_ITEM_CHANGED`, `RELEASE_CHANGED` và mô phỏng thay đổi. | Một số nhánh chỉ quan sát/lint/refresh assurance hoặc trả đề xuất; chưa phải mọi thay đổi đều tự sửa artifact nghiệp vụ. Cần phân biệt quan sát, đề xuất và ghi dữ liệu cho từng trigger, không gọi tất cả là tự động hóa hoàn tất. | Chưa có bảng trigger × hành động × quyền × hậu điều kiện được chạy qua outbox/worker và kiểm tra bản ghi Mongo thật cho mọi trigger.
| AI: benchmark | Bộ `pilot-testability-compiler-2026-10-21` có 3 tình huống; lượt chạy thật `TBR-15080fb52e804dcdbff53402fe15f639` qua API hoàn tất trong 210,454 ms (khoảng 3 phút 30 giây); cả ba pipeline thật được gọi và report lưu lại. Compiler đạt 1.0 trên quote validity/precision/recall, clarification precision/recall, obligation precision/recall và priority nDCG trên pilot. Sinh trực tiếp bị từ chối một case `AI_UNGROUNDED_OUTPUT`; baseline hỏi làm rõ có quote validity 0.6667. | Chỉ 3 tình huống và đáp án cần chuyên gia rà soát; một lượt không chứng minh tính ổn định hoặc ưu thế tổng quát. `null` không áp dụng/không có kết quả không được tính là 0 hay 1. | Lượt chạy thật đã được chứng minh; trước khi dùng làm kết luận nghiên cứu, cần chuyên gia xác nhận answer key, tăng bộ tình huống và chạy lặp. Benchmark không tự duyệt dữ liệu dự án.
| AI: benchmark chạy lặp | Thêm route nội bộ `POST /suy-luan/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/chay-lap?repetitions=N` (N từ 1 đến 5). Mỗi lượt gọi lại ba pipeline thật qua service hiện hữu và lưu report độc lập; summary trả mean, population standard deviation (chỉ có từ hai lần quan sát), min/max và số case lỗi/từ chối theo pipeline. Lượt chạy lỗi bất ngờ được ghi bằng mã lớp lỗi, không đẩy thông điệp provider ra ngoài và không ngăn lượt sau chạy. Hai lượt model thật trên pilot (`TBR-18781db25eb649d587b85a1389bf1748`, `TBR-227be17dbf6e403ab46663a807bf6f2a`) đều COMPLETE, không có pipeline failure; mỗi lượt direct-generation bị từ chối một ca do grounding validation. Compiler quote recall là 0.8889/1.0 và obligation recall 0.8334/1.0; pilot cho thấy đầu ra thay đổi giữa lần chạy. | Docker chạy 15 test benchmark liên quan (service, schema, API persistence và report) pass; Python compile pass; report hai lượt được đọc lại từ Mongo. | Chỉ có 3 tình huống và answer key chưa được chuyên gia xác nhận; chưa thể kết luận ưu thế. LangSmith 429 quota khiến hai lượt không có cloud trace thành công. Cần chuyên gia kiểm định nhãn và bộ tình huống rộng hơn; thời lượng API lặp cần vận hành theo dõi khi triển khai route trên server.
| AI: MCP/LangSmith | Runtime probe ngày 24/10 đạt kết nối Postman và GitHub; tool allowlist trong DB chỉ chứa thao tác đọc; cả hai đang ở phạm vi toàn cục (`project_id=null`). Sau khi bổ sung typed `intent_arguments` từ yêu cầu chạy đến tác vụ agent, đã chạy một Automation Run thật trên project có quyền QA: `call_mcp_read_tool` gọi `getAuthenticatedUser` và quan sát công cụ ghi nhận `COMPLETED`; run kết thúc `COMPLETED`, dữ liệu run/checkpoint/fact/receipt/trace liên quan đã được dọn và kiểm tra không còn bản ghi theo run ID. Kiểm tra tiếp phát hiện planner thấy MCP tool nhưng validator loại lời gọi vì `connection_id` không phải source-artifact ID; giờ chỉ cho qua đúng cặp kết nối/công cụ vừa discovery sau kiểm tra ACL. Discovery cũng được đổi để chỉ expose cấu trúc tên/tham số đã lọc, không gửi mô tả/chuỗi tự do từ MCP vào prompt; tránh một lượt inference guardrail cho từng công cụ. Bộ planner/gateway đạt 41/41. Thêm runtime smoke qua nhánh event-replan trong graph: discovery gọi server MCP Postman thật, planner nhận kế hoạch có cặp tool được discovery trả về, executor gọi `getAuthenticatedUser` thật, output qua guardrail và được giữ thành evidence; không in nội dung. Trong smoke này LLM planner và kiểm tra project ACL được stub; API/outbox/worker không chạy.
| Smoke event-replan này xác nhận đường planner → validator → MCP gateway → server thật → output guardrail/evidence, nhưng chưa chứng minh event outbox/worker đầy đủ hoặc model tự chọn đúng tool trong một run tự nhiên. Một Automation Run có chủ đích trước đó vẫn là bằng chứng riêng. LangSmith vẫn trả 429 quota nên chưa có trace đám mây thành công. | Còn E2E event outbox → worker → Agent tự chọn → MCP call/result/audit/readback với session/quyền thật; lỗi/timeout/thu hồi quyền/allowlist đổi lúc xếp hàng; LangSmith cần quota hợp lệ để xác minh trace. Không in credential.
| AI: tổ chức prompt và bảo trì | Có `backend/ai/src/prompts/README.md` và prompt được tách theo nhóm nhiệm vụ. | Cần rà từng prompt đang được import để bảo đảm một source of truth, không prompt trùng/đã chết, output schema và prompt không lệch hợp đồng; hiện chưa có danh mục import-use tự sinh/kiểm thử. | Chưa có kiểm tra tự động bao phủ toàn bộ prompt đang dùng và các nhánh provider/retry.
| Tài liệu, metadata, Qdrant | Parser hiện lưu cấu trúc, source spans, trang/tọa độ khi parser cung cấp; tìm kiếm lai có kiểm quyền và thay thế index có giữ index cũ khi lỗi. | Chưa có job parse nền checkpoint theo trang/khối, chưa kiểm tra PDF scan lớn, bảng nhiều trang/hình/vùng cắt; metadata cũ chưa được migrate/đối chiếu đầy đủ. | Chưa chạy bộ tài liệu dài có ground truth vị trí; chưa test restart worker, quyền bị thu hồi trong lúc index và khôi phục lỗi giữa Mongo/Qdrant/BM25.
| Quyền và vai trò | Mô hình quyền typed, ràng buộc BA/QA/Tester/Developer/Viewer/Admin và hỗ trợ một người giữ nhiều role đã có; API duyệt chặn danh tính AI. | Chưa kiểm chứng đủ API/UI cho tất cả role và mọi đường tắt (bulk/import/AI/internal), cũng như lỗi transaction được tiêm và tiếp tục checkpoint sau quyết định nghiệp vụ. | Smoke API hẹp đã có; chưa có suite E2E phiên đăng nhập qua từng role.
| So sánh/ghép Test Case | Màn ba vùng, snapshot AI, chọn field/step theo ID, lưu nháp, phát hiện gần trùng và duyệt nhóm nguyên tử đã được smoke. | Đường stale Requirement/source/revision và lỗi mạng cần chạy từ UI thật; quản lý custom-field definition chưa hỗ trợ vòng đời chỉnh/ẩn. | Chưa có E2E browser cho người dùng đăng nhập, quyền nhiều role, nhiều ca, conflict, retry và hồi phục UI.
| Test Plan/Test Run/Defect/Release | Có snapshot Test Plan, tái sử dụng Test Case version qua Run, kết quả tách biệt, Defect và release/completion gates. | Chưa nghiệm thu một Release thật đi qua đủ exit criteria, blocked defect, evidence, assurance, retest/rerun và completion report; nối plan → nhiều run còn chủ yếu mới có smoke service. | Cần E2E API và browser trên dữ liệu dự án tạm, bao gồm đường bị chặn và rollback.
| Planning | List/backlog, Scrum/Kanban, Work Item, workflow, sprint, WIP và lịch dự án hiện có; cập nhật Sprint và lịch đã có smoke. | Timeline tổng hợp, thống nhất bộ lọc giữa List/board/timeline, thao tác kéo-thả có rollback và phương án bàn phím chưa được kiểm chứng xuyên role. | Chưa có browser E2E cho Scrum và Kanban theo BA/Developer/Viewer ở các kích thước đã chốt.
| Hồ sơ năng lực/CV và tự phân công | Đã có hồ sơ năng lực theo dự án; CV PDF/DOCX/TXT được trích tạm bằng AI với trích dẫn và trang/khối nguồn, không lưu hoặc lập chỉ mục CV; UI preview → đưa ứng viên vào bản nháp → thành viên xác nhận/sửa/xóa; Test Case có trường kỹ năng yêu cầu; tạo Run có thể tự gán theo kỹ năng đã xác nhận, availability và tải, lưu quyết định cùng revision hồ sơ. | Chưa có benchmark gán người với ground truth được rà độc lập; cần chứng minh lại E2E qua phiên đăng nhập thật cho upload/quyền/preview/xác nhận và Run assignment, lỗi parser/provider, cạnh tranh thay đổi hồ sơ và retry. | Unit/regression hiện có cho CV extraction, profile, assignment và snapshot; browser CV flow hiện giả lập API. Các test trước đã smoke model cho trích xuất nhưng dùng override danh tính/quyền; chưa phải E2E authenticated/transaction đầy đủ. Không gọi phân công là “AI tự hiểu CV” — đầu vào phân công là kỹ năng người dùng đã xác nhận.
| Trường Test Case mở rộng | Trường typed text/number/boolean/date/choice đã có ở nháp, merge, frozen version; kiểm tra kiểu và unique key đã được smoke. | Chưa có cập nhật/ẩn định nghĩa trường, migration/import dữ liệu cũ và kiểm thử phiên đăng nhập đầy đủ qua các role. | Chưa có E2E QA tạo field → Tester bị từ chối → QA nhập → approval/version giữ snapshot.
| Toàn frontend | AppShell điều hướng theo nhóm/quyền; có 15 entry routes Next.js, Playwright `test:e2e` và ba tệp browser spec; có ma trận route/viewport và một số luồng compare/merge, AI, CV. | Coverage E2E còn pha trộn mock API và một số smoke API thật; chưa chứng minh toàn bộ action của mọi route theo session thật BA/QA/Tester/Developer/Viewer/Admin, các failure path và cleanup trong cùng harness. Audit trực quan toàn trang và responsive cũng chưa nghiệm thu đầy đủ. | Playwright suite hiện có không đồng nghĩa bao phủ toàn hệ thống. Cần lượt E2E authenticated/live API với report/trace và matrix route/action/role ở 1920/1440/1280/768/390 px.
| Ba luồng xuyên suốt | Có nhiều smoke hẹp: index/search thật, Test Case merge/batch, Sprint transaction, Run result isolation. | Các smoke chưa được nối thành ba câu chuyện đầu-cuối: tài liệu mới; tài liệu trùng/mâu thuẫn; Requirement thay đổi sau khi Test Case đã chạy. | Chưa có một lượt nghiệm thu tích hợp toàn hệ thống với dữ liệu tạm, cleanup xác nhận và báo cáo case-by-case.

### Kiểm tra công cụ hiện tại

- Docker stack healthy; image runtime không đóng gói `pytest`, nên test suite được chép tạm vào container và chạy bằng `pytest` cài trong `/tmp`: kết quả cập nhật mới nhất Testing 82 đạt, AI 144 đạt. Thư mục test tạm chỉ nằm trong container.
- Frontend khai báo Playwright và `pnpm test:e2e`; hiện có ba browser spec. Đây là hạ tầng kiểm thử có thể lặp lại, nhưng nhiều nghiệp vụ vẫn mock API và chưa phủ đầy đủ session/role/live service.
- `pnpm quality` với `NEXT_PUBLIC_API_URL=http://localhost:8000` đạt format, ESLint và Next production build, gồm 15 route Next.js.
- Hồ sơ CV/kỹ năng đã có implementation cho preview riêng tư, xác nhận hồ sơ và phân công theo kỹ năng; không còn xếp đây là hạng mục chưa được triển khai. Khoảng trống nổi bật còn lại là nghiệm thu browser/API có phiên thật theo role, benchmark assignment có ground truth, và ba luồng end-to-end tích hợp.

Ma trận này là danh sách công việc còn lại, không phải tuyên bố kế hoạch lớn đã hoàn thành. Các hạng mục bên trên phải được đóng bằng implementation nếu đang thiếu, hoặc bằng chứng test tương ứng nếu code đã có.

### Kết quả kiểm chứng bổ sung trong lượt rà soát ngày 24/10/2026

- Backend AI: 144 test đạt, 12 subtest đạt. Có cảnh báo khóa JWT fixture quá ngắn; test không fail. LangSmith trả 429 quota tháng, nên không ghi nhận trace thành công.
- Backend Testing: 82 test đạt, 38 subtest đạt; 7 cảnh báo pytest do lớp schema có tên bắt đầu bằng `TestCase` bị nhận diện như test class. Không ảnh hưởng kết quả.
- Frontend: `pnpm format:check`, ESLint và `next build` đạt với `NEXT_PUBLIC_API_URL=http://localhost:8000`; production build tạo đủ 15 route.
- Browser smoke dùng Chrome/Playwright của workspace ở 1920, 1440, 1280, 768 và 390 px: 25 lượt điều hướng tới đăng nhập, đăng ký, quên mật khẩu, điều khoản và dự án. Không có lỗi HTTP từ 400 trở lên hoặc tràn ngang. `/du-an` chưa đăng nhập chuyển về `/dang-nhap`; chưa kiểm tra workspace theo role.
- Test logic ghép Test Case bằng Node: 3/3 đạt (ghép step theo ID, sắp xếp/bỏ bước giữ ID, khôi phục bước chỉ có ở bản gốc).
- Benchmark live hoàn tất 3 tình huống: 0 pipeline failure, 1 rejection grounding. Đây là pilot nhỏ; không phải độ chính xác phổ quát.
- MCP probe live đạt `connected` cho Postman và GitHub. Cả hai khai báo ở phạm vi toàn cục; allowlist chỉ đọc đã được xác minh trong MongoDB. Chưa chứng minh Agent thực sự gọi tool MCP trong event workflow.
- Outbox Testing có 86 sự kiện ở trạng thái `DELIVERED` tại thời điểm kiểm tra; đây là số tổng hợp runtime, không thay cho kiểm tra từng trigger hoặc ba luồng nghiệp vụ đầy đủ.

### Kiểm chứng bổ sung: hồ sơ năng lực và gợi ý phân công

- Bổ sung collection hồ sơ năng lực có unique key theo dự án/người dùng; cập nhật dùng `expected_revision`, tạo mới cạnh tranh trả conflict. Hồ sơ chỉ đọc/sửa qua API của chính người dùng trong dự án; API trả allowlist trường, không trả các khóa riêng tư khác nếu có.
- Hồ sơ lưu kỹ năng, mức tự đánh giá, minh chứng, xác nhận của chủ hồ sơ, kinh nghiệm có trách nhiệm/công nghệ/minh chứng, xác nhận và trạng thái khả dụng. Chỉ kỹ năng được chủ hồ sơ xác nhận được dùng để so khớp; chưa xác nhận không được coi là năng lực đã có.
- Gợi ý chỉ xét thành viên ACTIVE có vai trò chính TESTER (đúng điều kiện mà API gán hiện có chấp nhận), lọc tạm thời không khả dụng, so khớp kỹ năng đã xác nhận và xếp theo số lần chạy đang được giao. Phản hồi nêu kỹ năng khớp/chưa khớp, tải đang giao, phương pháp; không ghi thay đổi phân công. UI chỉ thêm người vào các ca chưa được giao, giữ nguyên các phân công đang có.
- Tạo hồ sơ, đọc lại, cập nhật revision cũ bị `409`, bảo vệ trường ngoài allowlist, kiểm tra ứng viên chỉ gồm Tester, không dùng kỹ năng chưa xác nhận và không áp dụng tự động: 6/6 kiểm thử mới đạt; toàn Testing suite: 82 bài đạt và 38 subtests đạt trong Docker.
- API thật chạy qua ASGI/MongoDB Docker: tạo hồ sơ từ revision 0, đọc lại, revision stale bị `409`, dữ liệu tạm được dọn. Endpoint mới xuất hiện trong OpenAPI; health và readiness `200`; gọi không token tới API hồ sơ và gợi ý trả `401`.
- Frontend profile và màn gợi ý vượt qua Prettier, ESLint, Next.js production build (15 route); ba kiểm thử ghép hiện có tiếp tục đạt. Browser E2E đăng nhập theo role cho giao diện mới chưa chạy.
- Giới hạn rõ: đây hiện là bộ gợi ý theo quy tắc có căn cứ người dùng xác nhận, **không phải AI**, không parse CV và không tự phân công. Chưa hoàn tất hạng mục hồ sơ năng lực/CV theo kế hoạch lớn.

### Kiểm chứng bổ sung: không render trang dự án khi thiếu quyền

- Sidebar vốn đã lọc liên kết theo quyền, nhưng kiểm tra mã cho thấy URL được mở trực tiếp vẫn có thể mount nội dung trang trước khi API của trang trả `403`. Đây là thiếu sót UX/quyền hiển thị, dù backend vẫn là lớp quyết định cuối.
- Thêm phân giải route theo liên kết có quyền cụ thể nhất. Với route dự án, AppShell chờ API trả quyền dự án trước khi render nội dung; route không được phép không hiện màn hình nghiệp vụ hay thông báo “không có quyền”, mà chuyển về tổng quan nếu có `project.read`, nếu không thì về danh sách dự án. Khi chưa có quyền, chỉ hiện khung tải trung tính.
- Bổ sung 4 kiểm thử logic cho route con chọn đúng quyền cụ thể, yêu cầu đồng thời nhiều quyền, quyền thay thế theo bất kỳ quyền nào và fallback quyền đọc dự án cho URL khác chưa khai báo. Kết hợp 3 kiểm thử ghép Test Case: 7/7 đạt bằng Node.
- Trên Chrome headless với frontend Docker production: mở URL `/du-an/{id}/yeu-cau` bằng phiên UI giả lập có `project.read` nhưng không có `requirement.read`; API chi tiết dự án được giả lập trả quyền đó, các API xác thực bị ngắt để dùng fallback UI. Kết quả chuyển về `/du-an/{id}`. Lượt được phép có cả `project.read` và `requirement.read` vẫn ở trang yêu cầu. Thử tại 390 px và 1440 px, không tràn ngang; lượt từ chối ở 1440 px không hiện nội dung từ chối truy cập và không có lỗi JavaScript. Đây là kiểm tra hành vi giao diện, không phải kiểm thử xác thực backend.
- `pnpm lint` và Next.js production build đạt; Docker frontend healthy và trả HTTP 200. API Testing vẫn healthy/ready, MongoDB healthy sau khi dọn riêng Build Cache đã được người dùng cho phép. Không xóa image, container dữ liệu hay volume.
- Giới hạn: chưa chạy kiểm thử browser bằng tài khoản đăng nhập thật cho từng role, chưa duyệt mọi route con và chưa làm E2E thao tác nghiệp vụ toàn hệ thống. Route lạ trong phạm vi project vẫn yêu cầu `project.read`, sau đó để cơ chế route/404 hiện hành xử lý.

### Kiểm chứng bổ sung trong lượt tiếp tục ngày 24/10/2026

- Phạm vi quyền công bố tự động của AI được ký trong JWT theo `automation_run_id`, dự án và allowlist theo sự kiện. `DOCUMENT_INGESTED`/`REQUIREMENT_CHANGED` có quyền gửi rà soát/chốt chuẩn Requirement, Test Case và áp dụng maintenance proposal; riêng `TEST_PLAN_CHANGED` chỉ có `testplan.approve`. Action đóng Release không được cấp.
- `TEST_PLAN_CHANGED` tự khóa snapshot và tạo Test Run sau khi completeness đạt, approval permission được cấp theo event, approval revision thành công và hash/snapshot đọc lại khớp. `RELEASE_CHANGED` tự yêu cầu đóng Release ACTIVE qua endpoint nghiệp vụ; endpoint giữ lại gate completion/assurance, AI không tự bỏ qua khi gate lỗi. Ngoài unit tests cho đường đạt, gate fail, thiếu quyền, sự kiện sai dự án và trạng thái không hợp lệ, đã chạy smoke E2E thật qua Testing outbox → AI worker → API đóng Release → readback: với completion report `APPROVED`, Test Plan scope đã duyệt và Requirement Assurance `ASSURED`, run kết thúc `COMPLETED`, Release đổi `ACTIVE` revision 1 → `CLOSED` revision 2; thiếu completion report đã được smoke trước đó chặn đúng. Fixture và dữ liệu AI tạm, gồm automation run, checkpoint, agent run và long-term memory, đã được xóa theo ID; xác minh outbox/run và mọi collection liên quan không còn record của project tạm. Lưu ý fixture APPROVED được seed trực tiếp vào DB, nên smoke này chỉ kiểm tra nhánh đóng sau khi có các trạng thái được duyệt; nó không kiểm chứng quy trình tạo completion report hay tiêu chí/evidence bên trong báo cáo qua API/UI.
- Đổi lại mô tả planner/executor để không yêu cầu duyệt con người cho các bước được event ký quyền; clarification do thiếu hoặc mâu thuẫn dữ liệu vẫn chờ thông tin nghiệp vụ, không tự bịa. Kết quả maintenance change trả mã phiên bản Test Case thay vì object proposal.
- Backend Testing và AI được build lại từ source hiện tại; container AI/Testing healthy, OpenAPI trả HTTP 200. `git diff --check` và Python `compileall` đạt.
- AI suite: 156 bài đạt. Testing suite: 85 bài và 38 subtest đạt. Lượt chạy dùng đúng test source mới chép vào container; thư mục test tạm đã được xóa sau chạy. Testing không còn cảnh báo thu thập schema. AI còn cảnh báo khóa HS256 cấu hình hiện tại chỉ dài 14 byte; không đổi secret trong lượt này vì sẽ làm token/session đã cấp mất hiệu lực.
- Docker readiness: AI báo MongoDB/Redis/RabbitMQ/Qdrant/Neo4j/knowledge/object storage/model đều ready; Testing báo ready. Các container AI và Testing đang running. LangSmith tiếp tục báo HTTP 429 quota unique traces khi suite khởi tạo tracing.
- Siết readback sau tự công bố: Requirement phải trả về đúng Requirement/project và trạng thái `BASELINED`; Test Case phải `ACTIVE`, là current version, thuộc đúng project/ca và giữ các Requirement version được yêu cầu. Thêm test từ chối readback sai.
- Smoke benchmark thực dùng bộ pilot hiện lưu trong Mongo: run `TBR-84c911c8116c41c8b8ca7d7250d54b42`, HTTP 200, `COMPLETE`, 3 tình huống, 0 pipeline failure, 1 direct-generation rejection (`AI_UNGROUNDED_OUTPUT`, `MANUAL_REVIEW_REQUIRED`). Compiler đạt precision/recall/validity 1.0 cho source quote và obligation, precision/recall clarification 1.0 trên chính bộ này; direct generation có 0 quote/obligation được xác nhận do bị từ chối ở một ca; baseline clarification có quote precision/recall 0.6667/0.6667, clarification precision/recall 0.6667/1.0 và obligation unlock 0.6667. Đây chỉ là pilot 3 ca, không phải kết luận độ chính xác ngoài bộ thử.
- Probe MCP thật: cấu hình toàn cục Postman `connected` (41 tool khả dụng, đủ allowlist) và GitHub `connected` (49 tool khả dụng, đủ allowlist). Đây mới là xác minh kết nối/list tool, chưa chứng minh Agent gọi MCP trong event nghiệp vụ thật.
- LangSmith vẫn trả 429 do vượt quota unique trace tháng; không có bằng chứng trace thành công. Model benchmark vẫn trả kết quả độc lập với lỗi LangSmith.
- Chưa chạy event integration thật từ outbox qua RabbitMQ worker tới Requirement/Test Case và Mongo; chưa chạy E2E toàn bộ UI/role. Vì vậy kế hoạch lớn vẫn chưa hoàn tất.

### Kiểm chứng bổ sung: sự kiện Release đủ điều kiện đóng

- Dựng fixture tạm với project và thành viên QA riêng, Release `ACTIVE`, Test Plan `APPROVED` chứa Requirement version, Assurance `ASSURED` và completion report `APPROVED`; phát `RELEASE_CHANGED` qua hàm phát Testing outbox hiện dùng trong ứng dụng.
- Outbox trả `DELIVERED`; AI worker thật hoàn thành Run `AUT-b8fb8e8e2a4d496eb0c3af6328008e18`; tool `process_changed_release` gọi API `POST /ban-phat-hanh/{id}/dong`, backend kiểm tra completion gate và assurance gate, sau đó công cụ đọc lại trạng thái. Kết quả: Run `COMPLETED`, Release `ACTIVE` revision 1 → `CLOSED` revision 2, với các xác minh project scope, completion gate, assurance gate và closed readback.
- Kiểm tra và dọn fixture theo ID. Lượt kiểm tra cleanup đầu phát hiện một Project còn sót do Project dùng `_id` (không có trường `project_id`) và worker để lại agent run/long-term memory. Đã xóa chính xác Project tạm, agent run và memory theo các ID đã thu được; xác minh không còn dữ liệu project trong Testing/AI collections, outbox event, Automation Run hay memory.
- Giới hạn quan trọng: completion report, plan và assessment ở trạng thái đã duyệt được seed trực tiếp vào DB, không đi qua quy trình tạo/duyệt UI/API. Vì vậy đây là bằng chứng tích hợp cho nhánh `RELEASE_CHANGED` sau khi prerequisites được duyệt, không phải nghiệm thu các tiêu chí/evidence bên trong completion report hoặc toàn bộ quy trình QA phát hành. Kịch bản thiếu completion vẫn được kiểm chứng trước đó và giữ Release ACTIVE.

### Siết điều kiện trùng lặp khi QA duyệt nhóm Test Case

- Khi rà code màn so sánh/ghép và API duyệt nhóm, phát hiện API batch kiểm tra cấu trúc, nguồn, lint, revision và transaction nhưng chưa bắt buộc xử lý các ca gần trùng mà màn so sánh đã trả về.
- Bổ sung chặn ở service backend: ca có bản đang hiệu lực gần trùng cần có `duplicate_reason` hoặc là phiên bản tiếp nối một Test Case hiện có; các ca gần trùng nhau ngay trong cùng nhóm cũng cần lý do trước khi được duyệt. Tester vẫn bị từ chối ở quyền `testcase.approve`; không dựa vào việc ẩn nút UI.
- Build lại Testing từ source và healthcheck `veriq_testing` vẫn `healthy`. Chạy 16 test tập trung cho so sánh/ghép, nhận diện trùng trong batch và duyệt nhóm; tất cả đạt. Trong đó 3 regression mới chứng minh bản trùng hiện hữu không có quyết định và hai draft gần trùng trong cùng nhóm bị chặn trước transaction, còn Tester không thể dùng quyền QA.
- Trên MongoDB Docker thật, duyệt nhóm hai draft QA chạy bằng transaction: inject lỗi ngay lần tạo phiên bản thứ hai; sau lỗi đọc lại được 0 Test Case, 0 version, cả hai draft vẫn `IN_REVIEW` revision 1. Chạy lại fixture riêng không inject lỗi thì tạo đúng 2 Test Case/2 version, hai draft thành `APPROVED`; phát lại cùng operation trả `idempotent=true`, không tạo thêm bản ghi. Fixture được xóa; kiểm tra mọi collection xác nhận không còn dữ liệu project tạm.
- AI regression tập trung gồm release-close gate và event-task planner đạt 24 test. LangSmith vẫn trả HTTP 429 do hết hạn mức unique trace tháng; không coi đó là trace cloud thành công. `compileall` và `git diff --check` đạt.
- Chạy toàn bộ Testing suite mới nhất trong container dùng source nghiệp vụ đã build và tests mount read-only: **98 passed, 40 subtests passed**. `pytest` được cài trong filesystem tạm của container chạy, không đổi requirements hay thêm dependency vào image.
- Giới hạn: smoke batch gọi service trực tiếp với danh tính QA và fixture DB, chưa gọi route HTTP bằng token đăng nhập thật hoặc browser. Không phải nghiệm thu toàn bộ luồng so sánh/ghép và duyệt nhóm theo mọi role.

### Kiểm chứng bổ sung: parser tài liệu dài, OCR và bảng số hóa

- Phép thử runtime trong Docker cho PDF văn bản 200 trang trước đó mất nhiều phút khi đi qua Docling. Đã bổ sung fast path PyMuPDF chỉ cho trang PDF có đủ văn bản trích xuất được, không có ảnh và các hình dạng có thể là bảng; trang/vùng phức tạp vẫn chuyển sang Docling, còn trang scan/mixed bật OCR. Bảng đường kẻ được nhận diện riêng và lưu thành khối `table` có trang, tọa độ và Markdown; nội dung ô không bị lặp lại thành khối văn bản thường.
- Tạo PDF văn bản tạm 200 trang ngay trong container: parse thành công trong 0,6 giây, giữ 200/200 trang, 200 khối có dấu vết, marker đầu/cuối và trang 1–200. Bộ chuyển đổi ghi `parser=pymupdf_text`, `ocr_enabled=false`, 0 khối chưa xử lý.
- Tạo PDF scan một trang bằng ảnh chữ: Docling bật OCR; nhận ra `SCANNED REQUIREMENT LOGIN` và câu quy tắc `Account remains locked after five failures.`, 1 trang, 0 khối chưa xử lý. Thêm kiểm tra quyết định OCR cho PDF trộn chữ có sẵn và hình ảnh; hình ảnh khiến OCR vẫn bật.
- Tạo PDF bảng số hóa có đường kẻ: kiểm thử Docker nhận đúng hai dòng `REQ-LOGIN`/`REQ-RESET`, giữ tọa độ bảng ở trang 1 và phần văn bản ngoài bảng, không lặp các ô bảng vào khối text. Các trường hợp fast path, OCR decision và provenance hiện có unit coverage.
- Sau thay đổi: AI 165 test đạt; Testing 87 test và 40 subtest đạt trong Docker. `compileall` và `git diff --check` đạt; AI và Testing readiness đều `ready`.
- Giới hạn: đây không phải benchmark 200 trang scan hoặc bảng qua nhiều trang. Chưa kiểm chứng crop/hình, OCR nhiều ngôn ngữ, job nền/checkpoint/restart, quyền bị thu hồi trong khi lập chỉ mục hoặc khôi phục đồng bộ Qdrant/BM25. Không đánh dấu nhóm tài liệu đa phương thức hoàn tất.

### Kiểm chứng bổ sung: trích xuất kỹ năng từ CV riêng tư

- Thêm schema và prompt riêng cho trích xuất ứng viên kỹ năng/kinh nghiệm. Mỗi mục phải gắn câu trích nguyên văn, ID khối và trang nếu parser có thông tin; dịch vụ từ chối quote không có trong nguồn hoặc trang không khớp. Không suy ra level/số năm thành thạo.
- Thêm API upload PDF/DOCX/TXT trong Testing. Nội dung được chuyển đổi trong bộ nhớ qua parser hiện có rồi gửi tới AI; API trả `cv_persisted=false`, `indexed_in_project_knowledge=false`. Không ghi CV vào MongoDB, object storage, Qdrant hoặc BM25. Giới hạn số khối và tổng văn bản được báo bằng warning thay vì âm thầm coi toàn bộ CV đã xử lý.
- Docker test đầy đủ AI: **172 passed, 13 subtests**; Testing: **91 passed, 40 subtests**. Đã build lại image `ai` và `testing`, containers healthy. `compileall` và `git diff --check` đạt.
- Runtime smoke thật: Testing ASGI route nhận một CV TXT tạm, gọi AI conversion thật, gọi model thật qua endpoint trích xuất, trả 1 kỹ năng + 1 kinh nghiệm có quote thuộc nội dung; xác nhận cờ không lưu CV/không index đều false. Smoke dùng dependency override cho danh tính/quyền dự án và không ghi database; chưa phải kiểm thử đăng nhập/membership đầy đủ hoặc UI.
- Readiness sau khi hoàn thành retrieval warmup: AI `200 ready`, gồm MongoDB, Redis, RabbitMQ, Qdrant, Neo4j, knowledge, object storage và model; Testing readiness `200`. LangSmith tiếp tục trả HTTP 429 quota trong một số test trace, không ảnh hưởng kết quả suite.
- Giới hạn còn lại tại lần smoke này: CV flow UI/API chưa được chạy cùng phiên đăng nhập/membership thật trong browser; browser coverage hiện mô phỏng API. Test Case có trường kỹ năng yêu cầu do người dùng/QA cung cấp, nhưng benchmark chưa chứng minh cách gán có ground truth độc lập. Không đánh dấu năng lực CV/phân công hoàn tất chỉ từ smoke trích xuất model.

### Kiểm chứng bổ sung: Work Item event qua outbox và AI worker

- Tạo project, membership QA và Work Item có ID kiểm thử ngẫu nhiên trong MongoDB Docker; phát sự kiện bằng chính `emit_work_item_changed` để đi qua outbox Testing, HTTP nội bộ sang AI, RabbitMQ và AI worker.
- Outbox trả `DELIVERED`; AI run có `source_event_verified=true`, trạng thái `COMPLETED`, không có lỗi; bước thực thi có một task hoàn tất và observation `get_work_item_impact_context=COMPLETED`; kiểm chứng cuối báo evidence đã phân giải, kết quả có căn cứ và đúng phạm vi dự án.
- Phát lại cùng thay đổi lần hai vẫn trả thành công idempotent và chỉ có một Automation Run cho source event. Project, membership, Work Item, outbox và các bản ghi AI liên quan được xóa theo đúng ID kiểm thử; truy vấn sau dọn xác nhận không còn project/run/outbox.
- Giới hạn: đây là smoke tích hợp thật cho riêng `WORK_ITEM_CHANGED` với Work Item chưa liên kết Requirement; chưa chứng minh đúng impact khi có nhiều Requirement/Test Case, chưa tiêm lỗi/retry/restart, và không đại diện cho các trigger khác hay nghiệm thu toàn bộ AI.

### Kiểm chứng bổ sung: truyền tham số MCP qua Automation Run

- Bổ sung hợp đồng typed `intent_arguments` xuyên suốt request → Automation Run → trạng thái worker → tác vụ MCP; trước khi xếp hàng, API kiểm tra capability, quyền `project.read`, project/global scope, allowlist tool và schema tham số.
- Chạy toàn bộ AI suite trong image Docker: **175 passed**. Chạy toàn bộ Testing suite: **91 passed, 40 subtests**. Image Testing thiếu `pytest`, nên chỉ cài package này tạm trong container để chạy suite; không đổi dependency của repository. Dữ liệu test tạm được xóa sau khi chạy.
- Smoke runtime gọi tool Postman chỉ-đọc `getAuthenticatedUser` qua Automation Run thật trên project QA được cấp quyền. Observation của `call_mcp_read_tool` là `COMPLETED`, run kết thúc `COMPLETED`. Không ghi nội dung tài khoản hoặc credential vào báo cáo. Run, checkpoint, fact, receipt, trace và bản ghi agent đúng run ID đã được dọn; truy vấn xác nhận không còn tham chiếu run.
- `git diff --check` đạt; AI, Testing, MongoDB và RabbitMQ vẫn healthy.
- Giới hạn: smoke là lời gọi MCP có chủ đích, chưa phải `DOCUMENT_INGESTED` hoặc trigger nghiệp vụ tự chọn MCP; chưa kiểm thử lỗi MCP/timeout/quyền bị thu hồi giữa lúc xếp hàng. LangSmith vẫn trả 429 quota, nên chưa xác nhận trace đám mây.

### Kiểm chứng bổ sung: BA nhập tài liệu → QA tự động thiết kế Test Case

- Tạo dữ liệu tạm riêng trong Docker cho BA và QA khác nhau; phát `DOCUMENT_INGESTED` qua outbox. Outbox giao sự kiện một lần; AI worker đọc tài liệu theo quyền BA, rút nguồn có dấu vết, tạo Requirement, chốt đúng một version baseline và sinh blueprint có ba nghĩa vụ từ acceptance criteria/business rule.
- Khi BA không có quyền thiết kế Test Case, worker tạo event con `REQUIREMENT_CHANGED` bằng ID ổn định theo Requirement version, kèm nội dung đọc lại đúng từ version đã baseline và `parent_automation_run_id`. Event được resolve tới QA của đúng project; quyền execution là QA và artifact evidence giữ cùng project/version.
- QA worker đã thực sự chạy pipeline thiết kế Test Case: blueprint, kiểm tra tiêu chí, đối chiếu trùng, lint, công bố theo gate API và kiểm chứng kết quả cuối. Lần kết thúc đạt `COMPLETED`, `verification.verified=true`, nguồn/project được xác minh; ba nghĩa vụ của bộ smoke có Test Case liên kết. Phát lại source event không tạo Automation Run thứ hai. Retry cuối không thêm Test Case mới.
- Lượt đầu phơi bày lỗi thật: API Test Case trả payload đã tháo lớp `data`, còn AI chờ lớp này lần nữa. Test Case đã được API ghi thành công nhưng worker báo `TEST_CASE_PUBLICATION_READBACK_INVALID`/`INSUFFICIENT_EVIDENCE`. Đã sửa `publish_grounded_test_case` để chấp nhận đúng payload thực và phản hồi chưa unwrap; thêm regression test. Cũng đã vá tương thích định danh task khi phục hồi snapshot cũ để lần retry có đủ `run_id`/`project_id`.
- Đã retry một `TEST_CASE_CHANGED` run cũ từ checkpoint: tác vụ đọc draft, lint và duplicate check hoàn tất; run kết thúc `COMPLETED`. Đây là xác nhận một trường hợp resume, chưa phải kiểm tra crash ở mọi ranh giới hoặc mọi trigger.
- Kiểm thử sau bản vá: AI **186 passed, 13 subtests**; Testing **91 passed, 40 subtests**; phần regression nhắm vào readback/checkpoint/BA→QA **41 passed, 2 subtests**. Docker AI mới được build lại và `healthy`. LangSmith ghi nhận 429 vượt quota trace tháng; không tính trace cloud là đạt.
- Sau khi chụp số liệu, ba project smoke có ID kiểm thử tường minh đã được xóa qua service quản trị dự án (khớp chính xác project key và chủ thể thử nghiệm). Đã xóa các bản ghi AI có `project_id` đúng ba ID đó, checkpoint theo đúng Automation Run ID, 6 điểm Qdrant và 12 artifact graph Neo4j; truy vấn sau dọn xác nhận không còn project-scoped record, Qdrant point hay graph node cho các ID này. Không xóa volume, collection hay dữ liệu của project khác.
- Giới hạn: smoke chỉ dùng một tài liệu đăng nhập ngắn và một project tạm; chưa nghiệm thu nguồn trùng/mâu thuẫn, thay đổi Requirement sau execution, mọi event trigger, provider outage/retry, quyền bị thu hồi, hay UI. Kết quả không chứng minh độ chính xác tổng quát của AI.

### Kiểm chứng bổ sung: event Test Plan và Release qua worker AI thật

- Tạo Test Plan draft không có Requirement/Test Case scope trong project tạm bằng service Testing; outbox `TEST_PLAN_CHANGED` đã `DELIVERED`, AI worker thực thi `process_changed_test_plan` và kết thúc `DEGRADED` với `TEST_PLAN_TEST_CASE_SCOPE_EMPTY`. Test Plan vẫn `DRAFT`, không có Test Run được tạo.
- Phát lại cùng event Test Plan trả thành công nhưng giữ đúng một outbox record; không sinh run trùng.
- Smoke Release làm lộ lỗi quyền thật: token run đã ký chứa `release.close`, nhưng allowlist ở Testing loại quyền đó. Bổ sung đúng quyền vào allowlist, giữ nguyên ràng buộc project/run/token nội bộ; kiểm thử xác nhận token này được chấp nhận và run AI không có scope vẫn nhận `HUMAN_APPROVAL_REQUIRED`.
- Rebuild và khởi động riêng container Testing. Retry hai Release event qua hàng đợi AI thật; cả hai worker đã gọi endpoint đóng. Endpoint từ chối vì chưa có completion report được duyệt (`RELEASE_COMPLETION_GATE_FAILED`) và Release vẫn `ACTIVE`; đây là kết quả an toàn đúng, không phải gate thành công.
- Hồi quy sau sửa: Testing **81 test đạt**; AI **186 test và 13 subtest đạt**. Ghi trace LangSmith bị giới hạn quota tháng (429), không tính là đạt.
- Project thử `PRJ-AI-REL-4AFFBDC5F1` được xóa bằng thao tác purge có xác nhận đúng key; AI records/checkpoints đúng project/run được dọn; Qdrant có 0 point, Neo4j có 0 artifact. Không xóa volume hay dữ liệu project khác.

### Kiểm chứng bổ sung: Requirement retry và khử trùng dấu vết nguồn

- Trong project tạm `PRJ-df31929a672d4004abe552b6b22feb5f`, event thật `REQUIREMENT_CHANGED` cho cùng một phiên bản từng lỗi khi blueprint ghi nhận nhiều bí danh `artifact_id` cho cùng version/quote. Hai lần retry qua API dịch vụ retry và worker RabbitMQ kết thúc `COMPLETED`; blueprint/biên nhận được ghi, Test Case trùng bị bỏ qua, Test Case cần thiết được công bố và readback xác nhận phiên bản/project. Đây chứng minh đúng các event đã thử, không phải mọi loại tài liệu hoặc thay đổi.
- Bổ sung canonical hóa `artifact_id` chỉ từ bằng chứng sự kiện đã xác thực và loại bí danh trùng theo loại nguồn, version, span và quote; không ghép hai quote khác vị trí/nội dung. Thêm unit regression cho checkpoint resume, hai bí danh trong evidence và ưu tiên ID cha khi có cả ID cha lẫn ID version.
- Hồi quy AI sau thay đổi: **188 passed, 13 subtests passed**. Test dùng source hiện hành bind read-only vào container tạm; pytest cài vào `/tmp` của container, không thêm dependency hay file fixture vào repository. LangSmith tiếp tục trả 429 do vượt hạn mức unique trace tháng; không tính cloud trace là đạt.
- Build lại image AI và khởi động container; Docker cho thấy AI đang `running` (healthcheck cần thời gian khởi động), các dịch vụ dữ liệu không bị thay đổi. Hồi quy Testing gần nhất trong cùng lượt công việc trước đó: **81 test đạt**.
- Project kiểm thử `PRJ-df31929a672d4004abe552b6b22feb5f` được xóa bằng service purge sau khi xác nhận chính xác key `AIEX257E3B1E58`. Dọn theo đúng project ID: 8 Automation Run, 129 checkpoint, 73 source fact, 8 receipt, 2 blueprint, 8 agent run; Qdrant 6 point và Neo4j 10 node. Kiểm tra sau dọn không còn bản ghi nghiệp vụ/AI project-scoped trong các kho đã liệt kê; audit events có gắn project ID được giữ nguyên theo chính sách lưu vết. Không xóa dữ liệu hoặc volume của dự án khác.
- `git diff --check` và trạng thái Docker cần được kiểm tra lại trước khi bàn giao. Các phần còn thiếu về benchmark nhiều bộ dữ liệu, độ chính xác change impact, fault injection/restart, MCP trong trigger nghiệp vụ, LangSmith, E2E frontend theo đủ role và viewport vẫn còn mở; không đánh dấu kế hoạch tổng thể hoàn tất.

### Kiểm chứng bổ sung: Test Plan hợp lệ → snapshot → Test Run

- Phát `TEST_PLAN_CHANGED` từ Testing qua client/outbox thật bằng một fixture tạm trong Docker. Lần đầu cố ý thiếu hash snapshot chiến lược; AI từ chối đúng `TEST_PLAN_INCOMPLETE`/`TEST_PLAN_STRATEGY_REQUIRED` và không tạo Run. Sau khi bổ sung chiến lược đã duyệt vào fixture, retry cùng Automation Run đi tiếp.
- Kết quả retry: Automation Run `AUT-9dafa15870824b48a050f25d63ab0c4a` kết thúc `COMPLETED`; Test Plan `TP-AI-POS-20261024` chuyển `APPROVED`, `approved_snapshot_hash` khớp `baseline_hash`; Test Run `TRUN-b2886e96152c4b6d81686ced4a1a514e` được tạo và bắt đầu `IN_PROGRESS`, đúng Test Case version `TCV-AI-POS-20261024`. Đây là bằng chứng một ca hợp lệ; chưa chứng minh fault injection/restart hoặc nhiều Run.
- Fixture project `PRJ-AI-TP-POS-20261024`, key `AIPOS1024`, được purge qua service Testing sau khi xác minh chính xác ID/key. Đã xóa AI run, 22 checkpoint, receipt, memory, source fact, agent run, Qdrant point và Neo4j node thuộc đúng project; không còn project hoặc dữ liệu nghiệp vụ/AI theo project trong DB. Giữ audit events theo cơ chế lưu lịch sử của service (các event này có project ID của fixture); không xóa audit/volume hay dữ liệu dự án khác.
- Docker AI và Testing hoạt động sau khi dọn. AI suite mới nhất: **188 passed, 13 subtests passed**; Testing suite mới nhất: **91 passed, 40 subtests passed**. Cả hai suite chạy với source hiện tại, pytest được cài tạm trong container; `git diff --check` sẽ được chạy sau các cập nhật tài liệu.

### Kiểm chứng bổ sung: Defect mới → RCA có kiểm soát

- Tạo project tạm và Defect `DEF-2ea5bc9fe73044dca0a55ba797c0dee7` qua Testing service thật; event `DEFECT_RECORDED` được đẩy qua outbox tới AI worker.
- Worker kết thúc `COMPLETED`, tạo causal analysis `RCA-57a75289718d4b3186d5c719204d3002` ở `DRAFT` và một kết quả giả thuyết; readback xác minh project và nguồn Defect. Trạng thái Defect giữ `NEW`; không tự xác nhận nguyên nhân hay đóng Defect.
- Dữ liệu kiểm thử được purge bằng service theo đúng project `PRJ-AI-DEF-20261024`/key `AIDEF1024`; xóa theo scope đúng project 1 Defect, 1 RCA, 1 ai result, 1 run, 11 checkpoint, 2 source fact, 1 receipt/memory/agent run, 1 Qdrant point và 1 Neo4j node. Audit events được giữ lại theo cơ chế lưu vết; không còn project hoặc dữ liệu nghiệp vụ/AI theo project.
- Phạm vi còn mở: liên kết Defect với Test Result, retest, report/release gate; kiểm tra retry/duplicate/restart và quyền. Không xem smoke một Defect là nghiệm thu toàn bộ lifecycle.

### Kiểm chứng bổ sung: mô phỏng thay đổi Requirement chỉ đọc và theo đúng phạm vi

- Chọn một Requirement version đã baseline và có Test Case liên kết trong bộ dữ liệu QA hiện có. Gửi `CHANGE_SIMULATION` qua Automation worker và model thật; nội dung đề xuất chỉ nằm trong yêu cầu chạy, không được ghi thành Requirement.
- Lượt đầu chạy được trước khi thu hẹp ma trận truy vết và trả đúng một Test Case cần rà soát, nhưng endpoint đưa toàn ma trận của project vào quan sát AI. Đã thay đổi contract truy vết để mô phỏng truyền `requirement_version_id`; phản hồi chỉ chứa Requirement, acceptance criteria, trace links và Test Case version của baseline đó. Không đổi response mặc định cho các màn ma trận toàn dự án.
- Rebuild AI và Testing, sau đó chạy lại luồng thật: ba thao tác đọc (`get_requirement_version`, `get_traceability_links`, `get_test_case_version_by_id`) đều `COMPLETED`; trace scope là đúng 1 Requirement, 1 acceptance criterion, 1 Test Case version và 1 link; Agent phân loại `NEEDS_UPDATE`, dẫn đúng hai phiên bản và verification đạt `verified=true`.
- Gọi API Testing trực tiếp với danh tính QA đã ký: baseline thuộc project trả HTTP 200 cùng đúng một nhánh liên kết; mã Requirement version không tồn tại trả HTTP 404. Không thêm membership, session hoặc dữ liệu nghiệp vụ để thực hiện phép thử này.
- So sánh dữ liệu trước/sau: Requirement vẫn `BASELINED`, revision 3 và hash `430bd878d75685c85020231f3694744076b57f28b295e8a6fe89b6906e29e110`; Test Case version vẫn `ACTIVE`, cùng hash; Trace Link vẫn `CONFIRMED`, revision 1; không phát sinh audit event nghiệp vụ. Automation Run/checkpoint/fact/receipt/memory thử được xóa theo đúng Run ID sau khi ghi nhận kết quả; không xóa dữ liệu dự án hoặc audit.
- Bổ sung 2 regression test cho việc thu hẹp phản hồi theo đúng baseline và từ chối baseline không thuộc ma trận. Hồi quy source hiện tại trong Docker: AI **188 passed, 13 subtests**; Testing **93 passed, 40 subtests**. Docker image AI/Testing được build lại; cả hai healthcheck `healthy`; `compileall` và `git diff --check` đạt.
- Giới hạn: đây là một ca có một Test Case liên kết. Chưa kiểm thử giới hạn nhiều ca, retry/restart, baseline không có link trong runtime, các nhãn ảnh hưởng khác, hoặc biên dịch/cập nhật artifact; mô phỏng vẫn chỉ đọc. LangSmith tiếp tục từ chối ingest với HTTP 429 do hết quota trace tháng, nên không tính trace cloud là đạt.

### Kiểm chứng bổ sung: sự kiện Test Case đã duyệt qua Testing outbox

- Phát `TEST_CASE_APPROVED` bằng hàm phát sự kiện đang được gọi sau khi duyệt đơn lẻ/duyệt nhóm, dùng một phiên bản Test Case `ACTIVE` có sẵn trong project QA và tài khoản thành viên hợp lệ. Đây là sự kiện qua `Testing outbox` thật, không gọi API nội bộ AI trực tiếp. Outbox xác nhận `DELIVERED`; worker hoàn tất Automation Run `AUT-d7226b5d3ca94820a8a2f4dcc27b1821`.
- Gọi lại cùng một phát sự kiện trong cùng revision trả `DELIVERED` thành công; kiểm tra AI tìm thấy đúng một Automation Run cho cùng `source_event_id`, không tạo run thứ hai.
- Readback của worker xác nhận `refresh_assurance_after_test_case_approval=COMPLETED`, event/version cùng project đúng phạm vi và snapshot được đọc lại. Fixture không có Requirement liên kết (`requirement_version_ids` rỗng), nên kết quả đúng là 0 Assurance cần làm mới.
- Đối chiếu trước/sau: Test Case vẫn `ACTIVE`; không có assessment mới, không có Testing audit event mới và không có thay đổi nghiệp vụ. Đã xóa đúng outbox event test ở trạng thái `DELIVERED` cùng Automation Run, 11 checkpoint, source fact và receipt theo định danh; không xóa/sửa Test Case, project, membership hay audit hiện có.
- Giới hạn: vì fixture không có Requirement/Assurance liên kết, ca này chưa chứng minh snapshot Assurance được làm mới khi có liên kết; kiểm tra trùng mới xác nhận idempotency ở lần gửi lặp sau khi giao thành công, chưa phải retry lỗi mạng hoặc worker restart. Không tính nhánh `TEST_CASE_APPROVED` hoàn tất trên cơ sở ca này.

### Kiểm chứng bổ sung: thu hẹp truy vết cho Test Case đổi

- Sửa nhánh tác động `TEST_CASE_CHANGED` để chỉ yêu cầu ma trận theo các Requirement version gắn trên bản nháp; nếu không có version liên kết thì không gọi endpoint truy vết. Không gửi ma trận toàn project cho Agent ở nhánh này.
- Mở rộng API truy vết giữ tương thích query đơn `requirement_version_id` và nhận query lặp `requirement_version_ids`. Kết quả nhiều phiên bản gồm liên kết Requirement và Acceptance Criteria có trạng thái `CONFIRMED`/`SUGGESTED`, chỉ giữ Test Case version được nối trong tập đó; phiên bản thiếu hoặc ngoài project làm cả yêu cầu bị từ chối 404.
- Docker runtime sau khi dựng lại Testing: QA có quyền đọc gửi hai Requirement version hợp lệ cùng project, nhận HTTP 200 đúng hai version và không có link source ngoài tập; khi gửi một version hợp lệ cộng một version không tồn tại, API trả HTTP 404. Đây là phép đọc, không thay đổi dữ liệu.
- Regression sau thay đổi: AI **190 passed, 13 subtests passed**; Testing **95 passed, 40 subtests passed**. AI/Testing images được dựng lại; `compileall` và `git diff --check` đạt. LangSmith test trace vẫn báo HTTP 429 hết hạn mức; không tính đó là trace cloud thành công.
- Smoke event thật `TEST_CASE_CHANGED` qua Testing outbox với draft tạm, source revision 2 và parent version đang hiệu lực: outbox `DELIVERED`, AI worker hoàn tất `AUT-a140c56dac1d46528892fcdb22f81924`. Worker chạy lần lượt đọc draft/lint/duplicate, đọc parent version, rồi đọc ma trận truy vết đã scope; kết quả chứa đúng Requirement version liên kết với cả draft và parent (`REQV-502960692beb4356b5df5026004690a7`), 0 trace link và không có cảnh báo/ghi thay đổi nghiệp vụ. Đây chứng minh một ca update có chung liên kết trước/sau, không chứng minh trường hợp gỡ/thêm link hoặc nhiều Requirement có liên quan.
- Draft tạm, outbox event, Automation Run, 19 checkpoint, 12 source fact và receipt của smoke trên được xóa theo ID; đã xác minh không còn các bản ghi đó và không phát sinh audit nghiệp vụ. Không xóa Test Case version, Requirement, project hoặc dữ liệu khác.

### Kiểm chứng bổ sung: không tự chọn Defect khi kết quả FAIL mơ hồ

- `process_recorded_test_execution` trước đây chỉ lấy `linked_defects[0]`; khi một Test Result FAIL liên kết nhiều Defect, hành vi đó có thể gắn feedback vào sai Defect.
- Đã thêm nhánh `needs_review` với mã `MULTIPLE_LINKED_DEFECTS_REQUIRE_REVIEW`, giữ nguyên các liên kết nhận được và không gọi API ghi feedback cho Assurance. Nếu chỉ có một Defect, luồng hiện có tiếp tục kiểm tra đúng Test Case version/Coverage Item và đọc lại phản hồi đã lưu.
- Unit kiểm chứng trong container AI trên source mount chỉ đọc: 2 test pass (nhiều Defect không ghi dữ liệu; một Defect ghi đúng Coverage Item đã map và xác minh readback). Đây chưa phải Docker outbox smoke với dữ liệu nghiệp vụ thật.
- Sau guard: AI 192 test + 13 subtest pass; Testing 95 test + 40 subtest pass. `compileall` và `git diff --check` pass; image AI được build lại. LangSmith vẫn trả 429 do hết monthly unique-trace quota trong lượt hồi quy trước nên chưa có trace đám mây thành công.
- Giới hạn: mới một event update qua outbox có một Requirement version chung trước/sau. Chưa nghiệm thu thay đổi gỡ/thêm liên kết, retry lỗi/restart, stale/cross-project hoặc toàn bộ nhánh tác động.

### Kiểm chứng Docker: Test Result FAIL cập nhật feedback Assurance

- Tạo project ID ngẫu nhiên riêng trong Testing DB cùng một Requirement version, một Test Case version, một Test Run có tên, một Assessment/Coverage Item, một Defect liên kết và một Test Result `FAIL`; phát đúng `TEST_EXECUTION_RECORDED` qua Testing outbox với thành viên QA.
- Smoke lần cuối ghi nhận outbox `DELIVERED`, Automation Run `COMPLETED`, một execution feedback trong Coverage Item đúng `CAUGHT_DEFECT`, đúng Test Case version và đúng Defect. Readback từ Assessment đã xác nhận nội dung; API tổng quan project trả HTTP 200.
- Lần chạy thử đầu dùng Test Run thiếu trường `name`, làm API tổng quan trả 500; sửa fixture và chạy lại từ đầu. Harness đầu cũng có assertion phụ sai về cách lưu tool observation và phép đếm async không hợp lệ; harness đã được sửa để kết luận dựa vào trạng thái Automation Run + dữ liệu feedback/readback, không yêu cầu shape observation suy đoán.
- Dọn tất cả record Testing/AI có project ID ngẫu nhiên; kiểm tra cả hai DB không còn document theo project ID, sau đó xóa chính xác outbox record (outbox không có `project_id` ở trường top-level) và xác nhận event không còn. Không đụng dữ liệu dự án đang có.

### Kiểm tra tự động: tính nhất quán catalog prompt

- Thêm `test_prompt_catalog.py`: kiểm tra mọi module prompt có owner trong README, catalog không tham chiếu module thiếu và mọi import từ package prompts đều trỏ module thực/được lập mục lục; không chạy model hay thay dữ liệu runtime.
- Lần đầu chạy phát hiện README trỏ `automation_assurance.py` không tồn tại; mục tiêu đồng bộ snapshot thực nằm trong `automation_events.py`. Đã sửa catalog về module đúng; kiểm tra hiện đạt **3/3**.
- Hồi quy AI sau khi thêm bộ kiểm tra catalog đạt **195 test + 13 subtest**; Testing không có thay đổi code trong lượt này và lần chạy gần nhất vẫn là **95 test + 40 subtest**.
- Giới hạn: đây là kiểm tra sở hữu/import, chưa chứng minh prompt tương thích schema đầu ra hoặc mọi provider/retry/capability có test tương ứng.

### Hồi quy tổng hợp AI, Testing và browser smoke frontend

- Chạy toàn bộ Testing suite từ source đang chạy trong Docker: **103 passed, 40 subtests passed**. Bộ test tạm được chép vào `/tmp` trong container; cảnh báo duy nhất là pytest cache không ghi được vào thư mục mount chỉ đọc, không ảnh hưởng kết quả.
- Chạy toàn bộ AI suite: **196 passed, 13 subtests passed**. Tắt LangSmith tracing riêng trong tiến trình test vì quota cloud đã hết; có 5 cảnh báo JWT về khóa HMAC ngắn trong test, không thay đổi secret môi trường đang dùng.
- Frontend `NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm quality`: Prettier, ESLint và production build đều đạt. Lần chạy đầu thiếu biến môi trường bắt buộc nên build dừng ở prerender; chạy lại với đúng cấu hình môi trường đã đạt.
- Chạy Node unit tests cho ghép Test Case và route permission: **7/7 đạt**.
- Dùng Chromium/Playwright có sẵn trong worker để duyệt trang công khai (trang chủ, đăng nhập, đăng ký, khôi phục mật khẩu, điều khoản) tại 390, 768, 1280, 1440 và 1920 px: **25/25 kiểm tra đạt**, không có tràn ngang hoặc `pageerror`. Kiểm tra không xác thực toàn bộ **27 mục workspace dự án** và xác nhận đều chuyển về `/dang-nhap`.
- Docker frontend, AI và Testing vẫn `healthy`; `git diff --check` đạt.
- Giới hạn: đây là hồi quy suite và browser smoke không xác thực. Chưa đăng nhập bằng từng vai trò; chưa kiểm tra quyền chồng BA+QA, thay đổi quyền trong phiên, form thao tác, ghép/duyệt nhóm, lỗi API và responsive bên trong workspace. Không xem kết quả này là nghiệm thu toàn frontend hay toàn Unified ALM.

### Bổ sung quản lý vòng đời trường mở rộng Test Case

- Thêm API/list quản lý trường cho QA, cập nhật nhãn, bắt buộc và trạng thái dùng/ngừng dùng bằng `expected_revision`; update dùng một câu lệnh CAS MongoDB và ghi audit trước/sau. Trường legacy chưa có revision được đọc như revision 1; key, kiểu và lựa chọn không bị sửa ngầm. Admin nền tảng không tự có quyền QA.
- Khi trường ngừng dùng, trường bị ẩn khỏi form tạo mới nhưng `custom_values` lịch sử vẫn được nhận diện/kiểm tra kiểu, không bị xóa và không còn bị yêu cầu ở ca cũ. Giao diện QA có danh sách trường, cập nhật và bật/ngừng dùng; hỗ trợ thành viên có đồng thời vai trò BA+QA.
- Kiểm tra tập trung trong Docker bằng source hiện hành read-only: **13 test và 14 subtest đạt** cho typed value, giữ giá trị cũ của trường ngừng dùng, cập nhật, audit, xung đột revision và từ chối Tester/Admin không là QA. Kiểm tra JavaScript điều hướng/ghép Test Case **11/11 đạt**; ESLint các file frontend liên quan và `py_compile` các file Python sửa đều đạt.
- Giới hạn: đây là kiểm tra tập trung sau thay đổi, chưa chạy lại full Testing suite hoặc production build sau khi thêm panel, chưa có browser session thật QA/Tester/Admin và chưa kiểm chứng CAS cạnh tranh trên MongoDB đang chạy. Sẽ đưa các case này vào lượt nghiệm thu tích hợp cuối; không xem hạng mục này hay kế hoạch tổng là hoàn tất.

### Kiểm chứng tiếp: outbox AI của duyệt nhóm Test Case

- Phát hiện khoảng hở giữa lúc transaction duyệt nhóm commit và lúc API ghi sự kiện `TEST_CASE_APPROVED`: nếu tiến trình dừng ở khoảng giữa, Test Case đã duyệt nhưng worker không có sự kiện để tiếp tục.
- Bổ sung ghi sự kiện `PENDING` vào `ai_automation_outbox` ngay trong transaction duyệt nhóm. Sau commit, API vẫn thử dispatch; nếu dispatch lỗi hoặc tiến trình dừng, dispatcher nền có thể tiếp tục từ outbox. Sự kiện của chính AI Automation không tạo vòng lặp sự kiện mới.
- Kiểm chứng trực tiếp trên MongoDB Docker: abort transaction làm outbox event biến mất; commit giữ lại event `PENDING` với project và nguồn đúng. Database thử riêng đã được drop sau kiểm tra.
- Hồi quy tại thời điểm duyệt nhóm: Testing **112 passed**. AI **196 passed** (tracing LangSmith tắt trong tiến trình test do quota cloud đã hết). Frontend `pnpm quality` đạt Prettier, ESLint và production build; Node tests ghép Test Case/route permission **11/11 đạt**.
- Rebuild và deploy Testing + Worker; `/san-sang` của Testing, Worker và AI trả trạng thái sẵn sàng, MongoDB healthy. Không xóa image, container hoặc volume; cache được giữ nguyên trong lượt này.
- Giới hạn còn nguyên: chưa chạy lại browser E2E workspace bằng session xác thực thật theo toàn bộ role; chưa nghiệm thu tích hợp Unified ALM đầu-cuối. Mục này chỉ đóng khe hở durability cho outbox trong duyệt nhóm, không làm kế hoạch lớn thành hoàn tất.

### Kiểm chứng tiếp: outbox AI của duyệt lẻ Test Case

- Phát hiện duyệt lẻ có cửa sổ lỗi tương tự: tạo phiên bản/đổi trạng thái xong mới ghi sự kiện AI. Chuyển sang một Mongo transaction gồm kiểm tra revision và nguồn hiện hành, tạo hoặc cập nhật Test Case version, đóng băng draft, và ghi `TEST_CASE_APPROVED` vào outbox. Chỉ sau commit mới chạy lập chỉ mục/trace/audit suy diễn và thử dispatch; các dữ liệu suy diễn không làm rollback phiên bản đã duyệt.
- Sửa payload sự kiện duyệt dùng `plain_text_projection` trong version thay các tên trường legacy không tồn tại (`description`, `test_steps`); kiểm thử xác nhận Agent nhận đủ nội dung ca đã lưu.
- Bỏ trạng thái trung gian `APPROVING` ở luồng duyệt lẻ. Xung đột revision, version cha hoặc khóa duy nhất trả conflict và transaction không công bố một phần.
- Thêm hai kiểm thử hồi quy: một xác nhận bản ghi Test Case/version/draft/outbox đều cùng session transaction; một xác nhận revision cũ không tạo ca, version hay event.
- Docker ephemeral test runner, source hiện hành được mount read-only: **toàn bộ Testing suite 114 passed**. Kiểm tra bổ sung qua Testing service thật + replica set MongoDB tạm: transaction commit lưu bản duyệt và event PENDING; tiêm lỗi sau khi insert event rollback cả event, Test Case, version lẫn trạng thái draft. DB thử có tên ngẫu nhiên được drop và truy vấn xác nhận không còn.
- AI suite: **196 passed** với test source mount đúng vị trí dự án; 5 cảnh báo JWT khóa ngắn chỉ trong unit tests. Một lượt đầu đặt test ở `/tests`, làm 3 catalog tests không tìm thấy README; chạy lại ở `/app/tests` đạt đầy đủ.
- Frontend `NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm quality`: Prettier, ESLint, production build (15/15 route) đều đạt. Node tests logic merge/permission **11/11 đạt**. Lượt build đầu thiếu biến API bắt buộc, chạy lại với cấu hình hiện tại thì đạt.
- `docker compose build testing` thành công, cập nhật Testing; endpoint nội bộ `/san-sang` HTTP 200. Testing, Worker, AI, Frontend và MongoDB healthy sau kiểm tra.
- Không xóa hoặc tạo volume dữ liệu. `pytest` chỉ được cài trong container chạy một lần, sau đó container đó tự xóa.
- Giới hạn còn nguyên: chưa chạy browser E2E theo các role hoặc toàn bộ các luồng của kế hoạch Unified ALM. Lượt này xác nhận hồi quy mã nguồn và tính nguyên tử của thao tác duyệt, không nghiệm thu kế hoạch lớn hoặc benchmark AI.

### Kiểm chứng tiếp: Requirement và sự kiện AI cùng giao dịch

- Tạo Requirement, phiên bản nháp và Acceptance Criteria trước đây dùng chuỗi ghi rồi bù trừ; sửa Requirement nhiều phần cũng thay Acceptance Criteria riêng, sau đó mới phát `REQUIREMENT_CHANGED`. Tiến trình dừng giữa các bước có thể để lại dữ liệu dở dang hoặc mất kích hoạt AI.
- Chuyển tạo Requirement, sửa bản nháp (gồm identity và Acceptance Criteria) và tạo phiên bản mới/đổi phiên bản hiện hành sang Mongo transaction. Cùng transaction ghi sự kiện `PENDING` bằng helper outbox idempotent; worker nền dispatch sau commit. Audit và indexing tiếp tục sau commit; sự kiện của run AI không tạo vòng lặp.
- Kiểm thử hồi quy Testing trên source hiện tại: **114 passed, 40 subtests passed**. Docker replica-set smoke dùng database ngẫu nhiên: lỗi tiêm sau ghi Requirement/version/outbox rollback cả ba; commit tạo đủ hai bản ghi và event `PENDING` với evidence đúng nội dung. Database tạm được drop trong `finally`.
- Rebuild riêng image Testing, triển khai container và xác nhận `/san-sang` HTTP 200, trạng thái container healthy. Không xóa image, container hay volume dữ liệu.
- Giới hạn tại thời điểm kiểm chứng Requirement: smoke transaction kiểm chứng helper outbox và tính nguyên tử trên Mongo thật; chưa chạy API E2E tạo/sửa Requirement theo BA/QA hoặc dispatcher sau restart. `TEST_CASE_CHANGED` và `DEFECT_RECORDED` được xử lý trong các mục kiểm chứng tiếp bên dưới; event `TEST_EXECUTION_RECORDED`, `TEST_PLAN_*`, `RELEASE_CHANGED` và tài liệu vẫn cần rà tính nguyên tử. Không xem riêng phần Requirement là hoàn tất luồng AI hoặc Unified ALM.

### Kiểm chứng tiếp: Test Case draft, audit và sự kiện AI cùng giao dịch

- Chuyển tạo ca đơn, tạo ca theo lô và sửa ca nháp sang transaction gồm cập nhật/insert Test Case draft, audit và sự kiện `TEST_CASE_CHANGED`. Tạo lô dùng chung một transaction; lỗi ở ca bất kỳ rollback cả lô và không để outbox event trỏ tới ca đã bị bù trừ/xóa. Emitter bỏ qua sự kiện do chính Automation Run tạo để tránh vòng lặp.
- Mở rộng `audit` và thao tác `optimistic_patch` để nhận Mongo session tùy chọn; caller cũ không truyền session giữ nguyên hành vi.
- Hồi quy toàn Testing suite sau thay đổi: **114 passed, 40 subtests passed**. Docker replica-set smoke trên DB ngẫu nhiên xác nhận tiêm lỗi rollback cả Test Case draft và event; commit giữ draft cùng event `PENDING`, với nội dung bước kiểm thử chính xác. DB tạm được drop.
- Rebuild/deploy image Testing; endpoint `/san-sang` HTTP 200 và Testing, AI, Worker, MongoDB healthy.
- Giới hạn: smoke runtime kiểm tra transaction + emitter, không thay thế browser/API E2E của việc tạo/ghép/duyệt Test Case theo vai trò. Event `TEST_EXECUTION_RECORDED`, `DEFECT_RECORDED`, `TEST_PLAN_*`, `RELEASE_CHANGED` và tài liệu vẫn cần rà tính nguyên tử tương ứng; benchmark, browser E2E toàn route và Unified ALM acceptance chưa hoàn tất.

### Kiểm chứng tiếp: Defect, audit và sự kiện AI cùng giao dịch

- Tạo Defect nay ghi bản ghi Defect, audit và `DEFECT_RECORDED` vào outbox trong cùng Mongo transaction; lập chỉ mục tìm kiếm tiếp tục sau commit. Nếu lỗi xảy ra trước commit, không còn Defect hoặc sự kiện orphan; event do AI Automation tự tạo không tạo vòng lặp.
- Testing suite sau cập nhật: **114 passed, 40 subtests passed**. Replica-set smoke với DB ngẫu nhiên tiêm lỗi để xác nhận Defect/audit/outbox cùng rollback; nhánh commit giữ đủ ba bản ghi và đúng evidence. DB thử đã được drop.
- Image Testing được build/deploy lại; `/san-sang` trả HTTP 200.
- Chưa kiểm thử toàn bộ API/UI tạo Defect theo BA/QA/Tester hoặc chuỗi Defect → retest → báo cáo/Release. Các event execution, Test Plan, Release, tài liệu; benchmark và browser E2E vẫn còn trong inventory.

### Kiểm chứng tiếp: Test Result tạo, cập nhật và hiệu chỉnh cùng outbox

- Test Result mới, chuyển trạng thái kết quả và hiệu chỉnh kết quả nay ghi Result, Test Run revision, bản ghi update/correction, audit và `TEST_EXECUTION_RECORDED` trong cùng Mongo transaction. Nếu kết quả thuộc Release `ACTIVE`, event rà cổng `RELEASE_CHANGED` cũng nằm trong transaction đó. Indexing vẫn chạy sau commit.
- Full Testing suite: **114 passed, 40 subtests passed**. Docker replica-set smoke trên DB ngẫu nhiên kiểm chứng create event và update event: transaction abort giữ nguyên Result/Run, không để lại audit hay outbox; commit lưu Result, audit, `TEST_EXECUTION_RECORDED` và `RELEASE_CHANGED` trạng thái `PENDING`. DB tạm được drop.
- Build/deploy image Testing và xác nhận `/san-sang` HTTP 200; Testing, AI, Worker, MongoDB và Frontend đều healthy.
- Giới hạn: smoke trực tiếp transaction/repository/outbox, chưa gọi API thực với session BA/QA/Tester; worker feedback, duplicate event, restart, transition race và retest/Release E2E vẫn cần nghiệm thu. Test Plan, Release, document ingestion và browser E2E toàn frontend còn lại.

### Kiểm chứng tiếp: Test Plan, Release và Work Item cùng outbox

- Test Plan tạo/sửa/gửi duyệt/duyệt/lưu trữ/sao chép nay ghi trạng thái nghiệp vụ, audit và `TEST_PLAN_CHANGED`/`TEST_PLAN_APPROVED` trong một Mongo transaction. Các chuyển trạng thái trước đây chưa phát event nay cũng được đưa vào outbox; clone chỉ phát event cho bản sao mới.
- Release tạo/sửa/chuyển trạng thái nay ghi Release, `is_current` khi kích hoạt, audit và `RELEASE_CHANGED` trong transaction. Kiểm tra gate đóng Release vẫn chạy trước thao tác chuyển trạng thái; lỗi gate không tạo event đóng Release.
- Work Item tạo/sửa/chuyển trạng thái nay ghi item, audit và `WORK_ITEM_CHANGED` cùng transaction. Repository nhận session tùy chọn; event được dispatcher nền phát sau commit. Việc kiểm tra WIP cạnh tranh vẫn cần nghiệm thu riêng; transaction smoke không chứng minh WIP concurrency.
- Hồi quy source hiện hành trong Docker: **114 passed, 40 subtests passed**; `compileall` và `git diff --check` đạt.
- Docker replica-set smoke trên các database tên ngẫu nhiên xác nhận rollback/commit cho Work Item và Release: rollback không lưu entity/audit/outbox; commit lưu đủ ba loại dữ liệu. Các database tạm được drop trong `finally`.
- Build/deploy Testing thành công; `/san-sang` trả HTTP 200 và container healthy.
- Giới hạn: Test Plan có hồi quy suite; smoke transaction xác nhận helper/repository + emitter trên Mongo thật, chưa chạy toàn bộ API/service bằng session từng role. Chưa chứng minh worker restart/retry, release close gates qua UI, Test Plan nhiều Run hay toàn bộ planning E2E. Đây không phải nghiệm thu Unified ALM.

### Kiểm chứng tiếp: tài liệu được phép AI đọc và outbox

- Khi tài liệu đã được parse, có nội dung chuẩn, được bật quyền AI đọc và lập chỉ mục thành công, hệ thống nay ghi audit `requirement_document_ai_ingestion_queued` và `DOCUMENT_INGESTED` vào outbox trong cùng Mongo transaction. Việc worker giao event tiếp tục do dispatcher nền đảm nhiệm.
- Nếu lập chỉ mục thất bại, nhánh hiện có vẫn tắt AI cho tài liệu và trả trạng thái suy giảm; không ghi event `DOCUMENT_INGESTED` giả.
- Replica-set smoke gọi luồng ghi audit/outbox: lỗi tiêm lúc thêm event rollback cả hai bản ghi; nhánh thành công lưu event `PENDING` có đúng nội dung nguồn. Database tạm được drop.
- Hồi quy sau thay đổi: Testing **114 passed, 40 subtests**; AI **196 passed, 13 subtests**. AI test có 5 cảnh báo khóa JWT ngắn trong unit fixtures và LangSmith cloud trả HTTP 429 do hết quota trace; pytest vẫn pass nhưng lượt này không xác nhận cloud trace.
- `compileall`, `git diff --check`, Docker build/deploy Testing và `/san-sang` đạt.
- Giới hạn: smoke này kiểm tra transaction helper/emitter chứ chưa chạy upload tệp thật xuyên object storage/parser/Qdrant/worker, hoặc thu hồi quyền giữa lúc lập chỉ mục và xử lý. Khoảng thời gian giữa cập nhật chỉ mục bên ngoài và enqueue event vẫn cần recovery/E2E riêng; không đánh dấu toàn bộ ingestion đã nghiệm thu.

### Kiểm chứng bổ sung: transaction QA baseline Requirement và outbox

- Chuyển Requirement sang baseline nay gom cập nhật trạng thái/version hiện hành, phê duyệt Acceptance Criteria, thay thế Assessment cũ, audit và `REQUIREMENT_CHANGED` vào cùng Mongo transaction. Chỉ sau commit mới lập chỉ mục Requirement; lỗi lập chỉ mục không làm mất baseline hoặc event đã xếp hàng, và được phản ánh qua trạng thái degraded hiện có.
- Ghi chú lịch sử về phiên bản luồng trước đó: repository thao tác baseline, Acceptance Criteria và supersede Assessment nhận session tùy chọn; tại thời điểm ghi chú, luồng chưa tự duyệt Requirement. Trạng thái này đã được thay thế bởi nhánh tự công bố có kiểm soát nêu ở phần đối chiếu hiện hành phía đầu tài liệu.
- Hồi quy Testing sau thay đổi: **114 passed, 40 subtests**; `compileall` và `git diff --check` đạt.
- Smoke trên Mongo replica set xác nhận thao tác repository baseline cùng transaction: nhánh rollback không để lại baseline/current pointer, phê duyệt Acceptance Criteria, supersede Assessment, audit hoặc outbox; nhánh commit ghi nhận đầy đủ các bản ghi và event `REQUIREMENT_CHANGED`.
- Giới hạn: smoke gọi repository/service với session Mongo, chưa phải kiểm thử HTTP approval bằng session QA thật; chưa kiểm tra event worker sau restart hoặc lỗi Qdrant trong cùng kịch bản. Phần baseline transaction/outbox đã có bằng chứng, còn API/worker/indexing vẫn mở.

### Kiểm chứng bổ sung: khôi phục event sau khi lập chỉ mục tài liệu

- `reindex_requirement_document_record` sau khi Qdrant index thành công nay xếp lại `DOCUMENT_INGESTED`. Reindex không tăng revision nội dung nên tạo lại đúng event ID đã dùng ở lần nhập ban đầu; outbox idempotency ngăn tạo event/run trùng. Nếu indexing thất bại, AI event không được xếp.
- Regression tests mới cho hai nhánh: `test_successful_reindex_requeues_current_document_revision` và `test_failed_reindex_does_not_enqueue_ai_work`.
- Docker Testing regression sau bản vá: **116 passed, 40 subtests passed**. Docker AI regression sau rebuild từ source hiện tại: **196 passed, 13 subtests passed**. LangSmith test tracing trả HTTP 429 do chạm monthly unique-trace quota; đây là cảnh báo ngoài luồng kiểm thử, không tính là trace cloud thành công.
- Frontend `NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm quality`: Prettier, ESLint và production build đều đạt, 15/15 route được tạo. Hai bộ kiểm thử logic trình duyệt hiện có (`testCaseMerge` và `navigationAccess`) đạt **11/11**. `git diff --check` đạt.
- Giới hạn: đây là kiểm thử unit của đường phục hồi, chưa fault-injection crash thật giữa Qdrant và Mongo outbox; chưa chứng minh Browser E2E toàn route/role. Các mục này vẫn mở trong inventory.

### Frontend E2E nền tảng và smoke các màn công khai

- Thêm Playwright vào frontend với `pnpm test:e2e`; test kiểm tra 7 route công khai/xác thực tại 1920, 1440, 1280, 768 và 390 px, phản hồi lỗi đăng nhập nhưng vẫn giữ nội dung form, và direct URL workspace khi chưa đăng nhập phải chuyển về login.
- Playwright E2E: **3/3 test đạt** (35 tổ hợp route/viewport nằm trong test responsive, cộng hai tương tác). Bộ kiểm thử logic merge/navigation: **11/11 đạt**. Không tạo user, Requirement hoặc dữ liệu nghiệp vụ; lỗi đăng nhập được giả lập ở ranh giới HTTP và không gửi credential đến dịch vụ xác thực.
- `NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm quality`: format, lint và production build 15/15 route đạt. API Testing `/san-sang` trả ready, AI `/suc-khoe` trả healthy; frontend root trả HTTP 200, protected project route anonymous chuyển 307 tới `/dang-nhap`.
- Phạm vi còn mở: chưa dùng session thật của BA, QA, Tester, Developer, Viewer, Admin hoặc BA+QA; chưa kiểm thử trang workspace/action nghiệp vụ, quyền allow/deny theo API, screenshot visual regression hoặc responsive toàn bộ route. Playwright mới là nền tảng ban đầu, FE-14 chưa hoàn tất.
- Regression frontend chạy lại trong lượt này: `NEXT_PUBLIC_API_URL=http://localhost:8017 pnpm quality` đạt Prettier, ESLint và production build 15 route; Playwright 3/3 đạt; merge/navigation logic 11/11 đạt. Đây vẫn là public/auth smoke và unit logic, không mở rộng phạm vi workspace role.

### Runtime hiện hành sau các thay đổi outbox

- Rebuild từ working tree và khởi động lại các container `testing`, `ai`, `worker`; không xóa image/container/volume dữ liệu. MongoDB healthy sau khởi động.
- Kiểm tra runtime: Testing `/san-sang` trả `ready`; Worker `/san-sang` trả `ready` với MongoDB, RabbitMQ và consumers `ready`; AI `/suc-khoe` trả `healthy`. Cả ba container ở trạng thái healthy.
- Hồi quy: Testing **114 passed, 40 subtests**; AI **196 passed, 13 subtests**. LangSmith trả 429 do quota unique trace của tenant; đây là hạn chế telemetry cloud, không làm pytest fail và cũng không phải bằng chứng LangSmith trace hoạt động.
- Kiểm tra các thay đổi backend hiện tại bằng compile và diff hygiene; không có thay đổi frontend trong lượt này.
- Giới hạn: ba health endpoint chứng minh process/dependency sẵn sàng, không chứng minh mọi workflow hoặc UI đã đạt acceptance. Toàn bộ unified AI, benchmark, MCP/cloud tracing, API theo role và frontend E2E vẫn chưa được nghiệm thu xong.

### Mô phỏng tác động có phân loại và căn cứ theo từng phiên bản

- `CHANGE_SIMULATION` nay có báo cáo typed theo từng phiên bản Test Case đang liên kết với đúng Requirement baseline. Phân loại gồm `STILL_VALID`, `POTENTIALLY_AFFECTED`, `NEEDS_UPDATE`, `OBSOLETE` và `INSUFFICIENT_EVIDENCE`.
- Mỗi phân loại phải trích dẫn nguyên văn từ đủ ba nguồn: Requirement baseline, nội dung đề xuất và đúng Test Case version. Backend kiểm tra scope baseline, trùng/thiếu phiên bản, ID nguồn và quote khớp nguồn. `NEEDS_UPDATE` bắt buộc có patch đề xuất; patch không được tự áp dụng. Không đọc hết toàn bộ phạm vi hoặc báo cáo không hợp lệ thì run không thể `COMPLETED`.
- Lượt đọc nhiều Test Case hiện gắn version ID lên từng quan sát; số ca chưa đọc được tính từ kết quả đọc thành công thực tế, không cộng dồn giới hạn của các lượt trước.
- Kiểm thử Docker AI: **205 passed, 13 subtests passed**; Testing regression: **116 passed, 40 subtests passed**. `compileall`, `git diff --check`, image AI rebuild và health `/suc-khoe` HTTP 200 đạt. Tracing LangSmith được tắt riêng trong lượt pytest cuối; các lượt trước báo HTTP 429 hết quota, vì vậy không tính tracing cloud là đã xác nhận.
- Các test mới xác nhận report đầy đủ nhiều Test Case và fail-closed khi quote sai, trùng/thiếu ca, patch thiếu hoặc report vắng mặt.
- Smoke provider/model thật bằng dữ liệu tổng hợp: 1 phiên bản Test Case được phân loại `POTENTIALLY_AFFECTED`; đủ 3 trích dẫn baseline/đề xuất/Test Case qua validator. Đây chỉ là smoke một ca, không phải benchmark và không chứng minh độ chính xác tổng quát.
- Giới hạn: chưa chạy smoke model/provider thật cho báo cáo đa ca và mọi nhánh phân loại; chưa E2E worker/retry/restart/API/UI cho `CHANGE_SIMULATION`. Đây là luồng chỉ đọc, không tự áp dụng patch. Nhánh `REQUIREMENT_CHANGED` riêng đã có code phân tích change set/impact, carry-forward ca còn hiệu lực và áp dụng đề xuất bảo trì có căn cứ, nhưng chưa có E2E chứng minh đúng tập artifact/version được thay đổi và Test Plan/Run lịch sử giữ nguyên. Hai nhánh không được gộp thành một kết luận nghiệm thu. AI-09 vẫn mở.

### Smoke model thật: facts → Testability Blueprint

- Gọi compiler hiện có bằng dữ liệu tổng hợp, không ghi project/artifact vào DB. Với một nguồn “Tài khoản bị khóa sau 5 lần đăng nhập sai”, model trả một nghĩa vụ giữ quote nguồn nguyên văn, compiler trả `SUCCESS`.
- Với hai nguồn giả lập mâu thuẫn (5 lần và 7 lần), model trả hai nghĩa vụ tách biệt, mỗi nghĩa vụ giữ quote của đúng nguồn, cùng clarification `CONTRADICTION` trỏ cả hai source version; compiler kiểm tra và trả `SUCCESS`.
- Đây là smoke trực tiếp compiler/provider, không phải E2E upload/API/worker, không chứng minh độ chính xác tổng quát và không thay benchmark. AI-03 vẫn mở đến khi chạy hết pipeline từ tài liệu tới artifact Requirement/Test Case có lineage.

### Hồi quy tiếp theo ngày 24/10/2026

- Docker AI, dùng unittest discovery trên source/tests hiện tại: **216 test đạt**. Có cảnh báo LangSmith HTTP 429 do chạm quota trace; không tính là tracing cloud thành công.
- Docker Testing, dùng pytest trên source/tests hiện tại: **120 test và 40 subtests đạt**. Bổ sung 4 hồi quy upload tài liệu: lưu/parse/index/xếp event thành công; parser lỗi trả trạng thái degraded và không chạy AI; index lỗi không xếp event giả; upload trùng dùng lại tài liệu mà không ghi lại object.
- Các test upload dùng giả lập cho Object Storage, indexer và event queue; chúng khóa logic nhánh nhưng **không** chứng minh upload qua Object Storage/Qdrant/worker thật. AI-01 vẫn mở.
- Frontend `NEXT_PUBLIC_API_URL=http://localhost:8017 pnpm quality` và `pnpm test:e2e`: Prettier, ESLint, production build và 3/3 Playwright đạt. E2E hiện vẫn chỉ xác minh trang công khai/đăng nhập, form lỗi giữ dữ liệu và redirect protected route; không phải browser nghiệm thu workspace theo role.
- `git diff --check` đạt. Các kết quả trên là hồi quy cập nhật, không đóng ma trận 36 nhóm nghiệm thu AI/frontend/tích hợp.

### Smoke upload multipart thật → Object Storage → parser → Qdrant/BM25

- Gọi endpoint multipart `POST /kiem-thu/du-an/{project_id}/tai-lieu-yeu-cau/tai-len` trong Docker bằng `httpx` ASGI transport với một User Story tổng hợp dạng TXT; HTTP trả `201`, trạng thái `SUCCESS`, tài liệu `READY`, `index_status=INDEXED`.
- Request thực sự ghi object tạm qua Cloud/Object Storage, chạy parser TXT, ghi metadata nguồn vào MongoDB, gọi AI service để lập chỉ mục Qdrant/BM25; truy vấn tìm kiếm theo project/người sở hữu trả đúng `artifact_id` của tài liệu.
- Kết thúc smoke đã xóa artifact vector/lexical/graph, bản ghi tài liệu, audit và object S3; tìm lại sau dọn trả 0 kết quả và `head_object` xác nhận object không còn.
- Giới hạn quan trọng: smoke override dependency đăng nhập và kiểm tra membership, đồng thời thay event queue bằng stub để tránh khởi chạy worker trên một project không có thật. Vì vậy nó chứng minh đường HTTP upload → lưu → parse → index → search, **không** chứng minh quyền/session thật hoặc nối chính upload này qua outbox → worker → Requirement/Test Case. Phần worker đã có smoke riêng tại mục “BA nhập tài liệu → QA tự động thiết kế Test Case”; hai kết quả chưa phải một lượt E2E liên tục.

### E2E thật: upload tài liệu → blueprint → Requirement → Test Case

- Chạy sau khi cập nhật prompt sinh Test Case: một kịch bản tổng hợp có 3 Acceptance Criteria và quy tắc “Only registered accounts can sign in” được tải qua multipart endpoint Testing; Object Storage, parser, MongoDB, Qdrant/BM25, outbox, AI worker/model và API Testing đều chạy thật trong Docker.
- Kết quả run `DOCUMENT_INGESTED`: `COMPLETED`, `error_code=null`, `verified=true`, `evidence_refs_resolved=true`, `completed_claims_grounded=true`, `project_scope_valid=true`. Kết quả đọc lại: 1 Requirement, 3 Test Case version; ca từ chối đăng nhập với email chưa đăng ký liên kết đồng thời `SIGN_IN_UNREGISTERED_EMAIL` và `SIGN_IN_BUSINESS_RULE`, không sinh thêm ca trùng cho quy tắc đó.
- Hai lượt trước khi chỉnh prompt kết thúc `DEGRADED / INSUFFICIENT_EVIDENCE` dù có tạo ca. Thay đổi prompt làm rõ một Test Case được phép bao phủ nhiều obligation key khi cùng các bước/dữ liệu/kết quả mong đợi trực tiếp chứng minh từng nghĩa vụ; không nhập các key làm một và không lặp ca gần trùng. Hồi quy AI suite sau thay đổi: **216/216 đạt**; regression Testing: **106/106 đạt** trong harness có sẵn. Frontend regression cùng lượt: `pnpm quality` (format, lint, production build) và **3/3 Playwright** đạt.
- Dữ liệu tạm được xóa theo project/run ID: 44 ID artefact gửi xóa khỏi chỉ mục Qdrant/graph, project/domain/audit/outbox và AI runs/checkpoints/facts/receipts; object key chính xác bị xóa và `head_object` xác nhận không tồn tại. Kiểm tra lại không còn project/run/document/Test Case trong Mongo. Regression Testing được chạy lại: pytest **120 passed + 40 subtests passed**; unittest discovery riêng **106 passed**. Hai harness có cách thu thập test khác nhau, không cộng gộp hai con số.
- Giới hạn: request chạy qua ASGI API thật nhưng dependency đăng nhập được override cho thành viên BA+QA tạm; chưa chứng minh browser login/session thật hay đủ allow/deny theo sáu role. Đây là một lượt smoke thành công trên nguồn tổng hợp, không phải benchmark độ chính xác hoặc nghiệm thu toàn bộ luồng AI/frontend; AI-01 và AC-01 vẫn mở cho đến khi các nhánh quyền, retry/restart và phần downstream được kiểm chứng.

### Chạy lại benchmark thật sau thay đổi prompt

- Gọi endpoint chạy lặp trong Docker trên bộ pilot `pilot-testability-compiler-2026-10-21`, 3 tình huống, 1 repetition; run `TBR-d512800a831840389275ca8f91e66018` kết thúc `COMPLETE`, 0 pipeline failure. Compiler quote validity/precision/recall, clarification precision/recall và obligation precision/recall đều **1.0** trong lượt này; baseline hỏi làm rõ đạt quote precision/recall **0.6667**, clarification recall **1.0**; direct generation bị từ chối **1/3** tình huống bởi grounding validator (`AI_OUTPUT_INVALID`, `MANUAL_REVIEW_REQUIRED`).
- Chỉ là kết quả của một run trên ba tình huống và answer key hiện có; không kết luận compiler tốt hơn tổng quát, không dùng làm gate production. Quota LangSmith vẫn trả 429 trong lúc model chạy; việc này không làm hỏng kết quả benchmark lưu trong Mongo, nhưng cloud tracing chưa đạt.

### Hồi quy toàn bộ backend sau E2E upload

- AI suite được chạy trong container image thật, mount source và tests hiện tại: **216/216 đạt**. LangSmith tiếp tục trả 429 do hết hạn mức trace tháng; toàn bộ bài test kết thúc `OK`, vì vậy ghi riêng đây là lỗi tracing đám mây, không phải test failure của pipeline.
- Testing suite được chạy bằng container tạm từ image Testing, mount source/tests và cài `requirements-test.txt`: **120 passed**. Pytest có cảnh báo collection cho một số Pydantic schema class; đó là warning, không làm test fail.
- Frontend vừa chạy `pnpm quality` (Prettier, ESLint, Next production build) và Playwright **3/3**. Playwright lần này kiểm tra 29 URL workspace yêu cầu đăng nhập; toàn bộ chuyển về login.
- Hai lệnh thử sai trước đó (tests không được mount vào container; gọi pytest không qua module entrypoint) không được tính là regression kết quả. Container test tạm đã tự xóa sau khi chạy; không tạo dữ liệu DB nghiệp vụ.

### Mở rộng browser smoke: chặn workspace khi chưa đăng nhập

- Mở rộng Playwright kiểm tra trực tiếp 29 đường dẫn workspace dự án (planning, Requirement/Assurance, thiết kế kiểm thử, Test Plan/Run, execution, defect, report, audit, knowledge và settings); tất cả đều chuyển khách chưa đăng nhập về trang đăng nhập và hiển thị đúng tiêu đề. Cả 3 bài Playwright đều đạt sau thay đổi.
- Đây chỉ xác nhận ranh giới khách/đã đăng nhập; không xác nhận phân quyền BA/QA/Tester/Developer/Viewer/Admin hoặc bố cục/action bên trong workspace đã đăng nhập. FE-01 và FE-14 vẫn mở.

### Kiểm chứng workspace theo phiên đăng nhập thật — 24/10/2026

- Tạo dự án Scrum và mở bằng tài khoản thử tạm có đồng thời vai trò BA+QA. Chromium duyệt 28 route workspace ở 1440px và 390px (56 lần điều hướng). Tất cả trả HTTP 200, render đúng tiêu đề/nội dung và AppShell desktop/mobile tương ứng; không có overflow ngang, lỗi API ≥400 hoặc lỗi JavaScript.
- Tạo fixture Tester tạm trong cùng dự án. API đọc dự án, danh sách Test Case và trường Test Case trả HTTP 200; yêu cầu tạo trường mở rộng (quyền QA) bị từ chối HTTP 403. Trang Test Design render ở 1440px và 390px, không có lỗi trình duyệt hoặc tràn ngang; giao diện không hiện nút tạo/quản lý trường QA-only.
- Kiểm tra Tester được giới hạn đúng ở API và giao diện cho hai thao tác trên; không suy rộng thành ma trận quyền toàn hệ thống. Chưa kiểm tra mọi API action cho từng BA, QA, Developer, Viewer, Admin, Admin/non-Admin route, thu hồi quyền trong phiên, và mọi luồng so sánh/duyệt.
- Sau khi đăng xuất, xóa chính xác project, membership, audit, account, session và dữ liệu AI liên quan đến hai project thử; kiểm tra MongoDB cho project/account còn lại trả 0. Không tạo tài liệu, artifact Test Case hoặc dữ liệu Qdrant/S3 trong lượt này.
- Kết quả regression ngay sau browser: AI **216/216**; Testing pytest **120 passed** (66 cảnh báo collection Pydantic, không làm test fail); frontend Prettier, ESLint, production build 15 route và Playwright **3/3** đạt. `git diff --check` đạt; Docker frontend, Testing, AI, Worker, Authentication và MongoDB healthy; trang frontend HTTP 200. LangSmith vẫn báo 429 quota trace trong AI suite, vì vậy telemetry cloud chưa được xác minh.
- Đây là nghiệm thu trình bày/đọc và một nhánh từ chối quyền trong phạm vi đã nêu, không phải E2E cho mọi nút hoặc toàn bộ Unified ALM. FE-01/FE-14 và AC-05/AC-06 vẫn mở.

### Hồi quy mã nguồn hiện tại cho so sánh/ghép và duyệt nhóm — 24/10/2026

- Chạy ba bộ unittest trong container Testing tạm, gắn read-only cả `backend/testing/src` và `backend/testing/tests` hiện tại vào image để tránh kiểm tra nhầm mã nguồn cũ đã đóng trong image.
- `test_test_case_merge.py`: **12/12 đạt** (snapshot AI bất biến, ID bước, kiểm tra lựa chọn nguồn, stale/revision conflict, retry idempotent, ranh giới quyết định người dùng).
- `test_test_case_batch_review.py`: **6/6 đạt** (duplicate, quyền Tester, stale revision/token, idempotency key, ngăn mở transaction khi tiền kiểm tra thất bại).
- `test_human_review_boundaries.py`: **8/8 đạt** (BA+QA cùng tài khoản, Tester không thể sửa định nghĩa, không cấp quyền QA cho Admin, quyền AI ký theo dự án/thao tác).
- Tổng lượt tập trung: **26/26 đạt**. Container tạm tự xóa; không ghi dữ liệu nghiệp vụ vào MongoDB.
- Phạm vi còn mở: đây là kiểm thử service/logic theo mã hiện tại; không thay thế browser E2E thao tác thật trên màn so sánh, lưu bản ghép, conflict từ hai phiên UI, hoặc ma trận role đầy đủ. FE-06 và AC-05 vẫn mở.

### Browser E2E Test Design cho so sánh/ghép và quyền Tester — 24/10/2026

- Bổ sung `frontend/e2e/test-case-compare.spec.js`: một lượt QA đi qua ba vùng so sánh, chọn đề xuất, lưu bản ghép, gửi duyệt nhóm và xác nhận payload có revision/token; một lượt Tester kiểm tra các action QA-only bị ẩn, responsive 390px không tràn và yêu cầu tạo trường bị 403.
- Chạy Playwright trên Chromium: **2/2 đạt**; không có lỗi JavaScript.
- API ở lượt browser này được giả lập để cô lập hợp đồng giao diện và không ghi dữ liệu DB. Không tính đây là browser-to-live-API E2E. Bằng chứng API thật về role, duplicate, stale revision, rollback và idempotency được ghi riêng ở phần kiểm chứng so sánh/ghép và duyệt nhóm. Chưa kiểm tra browser conflict giữa hai phiên thật, lỗi mạng/5xx và mọi role/action; FE-06, FE-14, AC-05 vẫn mở.

### Browser conflict/stale và hồi quy source mới nhất — 24/10/2026

- Sửa Compare UI để khi merge nhận `REVISION_CONFLICT` hoặc `TEST_CASE_COMPARISON_STALE`, bản ghép đang nhập vẫn hiện để người dùng đối chiếu, lưu bị khóa, và bắt buộc tải lại nguồn/revision mới trước khi tiếp tục. Thêm trạng thái stale tức thời để giao diện không cho gửi lại bản ghép cũ.
- Playwright Test Design chạy trên production build mới từ source workspace, API giả lập: **3/3 đạt** cho QA compare/save/group-approve, Tester read-only/deny, và stale conflict giữ phần đã nhập → khóa lưu → reload revision mới. `pnpm quality` gồm format, lint và Next production build đạt (15 routes); toàn Playwright đạt **6/6**; Node logic merge/approval **7/7**.
- Backend Testing suite hiện tại được mount dưới đúng package root vào container, xác nhận import từ source mount: **120 passed + 40 subtests**. AI suite hiện tại chạy trong AI image với source/tests mount dưới đúng package root và pytest tạm trong `/tmp`: **218 passed + 13 subtests**. Với AI suite tắt LangSmith tracing để tránh tiếp tục gửi trace vào quota đã hết; kết quả này không xác nhận cloud trace. Có 9 warning (4 pytest collection cho Pydantic schema và 5 JWT fixture key ngắn); không làm test fail.
- Frontend được build lại từ source trong Docker bằng `docker compose build frontend`, sau đó chỉ service frontend được recreate; các backend/DB/volume giữ nguyên. Build chạy format, ESLint, Next production build 15 routes. Trên container mới tại `localhost:3000`, chạy toàn bộ Playwright **6/6 đạt khi tuần tự**. Một lượt thử song song trước đó có 1 test giữ skeleton loading quá timeout; test đó đạt khi chạy tuần tự, phù hợp giới hạn tài nguyên của container. Production build riêng cổng 3002 trước đó cũng đạt 6/6.
- Thử chạy browser trên Next dev trong lúc production build đang ghi cùng `.next` gây nhiễu; lượt đó bị loại. Các container tạm, pytest package tạm, và report Playwright được dọn; không tạo/chỉnh fixture nghiệp vụ trong MongoDB. `git diff --check` đạt.
- Đây vẫn không phải nghiệm thu toàn frontend hay API-live browser. FE-06/FE-14 và AC-05/AC-06 còn mở cho live session role, các action khác, lỗi mạng/5xx, stale giữa hai phiên và tích hợp toàn chuỗi.
- Trong lượt nghiệm thu Docker, MongoDB bị restart với exit 134; log WiredTiger nêu `No space left on device` khi ghi checkpoint. Không xóa/chỉnh volume hoặc collection. Theo quyền đã cấp trước đó, chỉ xóa 7.436 GB Docker build cache reclaimable; không xóa image hay volume. Sau đó MongoDB được restart, health chuyển `healthy`, `mongosh` xác nhận `ping=1` và replica set `ok=1`; frontend, Testing OpenAPI và AI OpenAPI đều trả HTTP 200. Việc ping/replica healthy không thay cho kiểm tra từng bản ghi nghiệp vụ.

### Tự làm mới lượt AI và xác nhận lại browser suite — 24/10/2026

- `AgentRunPanel` trước đây chỉ đọc danh sách lượt chạy khi mở panel hoặc khi một lượt đang chạy được chọn. Vì thế, sự kiện AI tự động tạo run khi người dùng vẫn đang xem màn hình có thể không xuất hiện cho tới khi tải lại trang. Bổ sung làm mới danh sách mỗi 5 giây khi trang đang hiển thị và người dùng có quyền đọc lượt chạy; lỗi đọc được báo qua trạng thái lỗi hiện có, timer được dọn khi component unmount.
- Thêm browser regression: danh sách ban đầu rỗng; backend giả lập trả về một lượt do sự kiện ở lần đọc tiếp theo; người dùng mở tab AI automation nhưng không bấm chạy, và lượt xuất hiện sau lần làm mới nền. Bài này ban đầu phát hiện bài test đang dùng sai hợp đồng API trực tiếp và frontend Docker cũ; sửa mock theo response thật (API AI automation trả trực tiếp danh sách), build lại image frontend từ source mới, rồi test đạt.
- Frontend Docker build mới chạy Prettier, ESLint và Next production build (15 routes) đạt. Trên container mới, toàn bộ Playwright chạy tuần tự **7/7 đạt**: 3 bài public/auth, QA compare/save/group approve, Tester read-only/403, stale revision reload và auto-refresh sự kiện AI. Browser E2E dùng API giả lập cho nghiệp vụ; không tuyên bố đây là kiểm thử live API.
- Sau build, Docker báo AI, Testing, Worker, MongoDB và Frontend healthy; readiness AI/Testing và HTTP trang Frontend đều **200**. `git diff --check` đạt. Không có thao tác xóa hoặc sửa dữ liệu trong volume MongoDB trong lần kiểm tra này.
- Đây là một cải thiện và bằng chứng hẹp cho việc nhìn thấy run do sự kiện; không đóng FE-14 hay các tiêu chí tích hợp AI. Vẫn còn kiểm tra browser với API/session thật, phân quyền đủ role, tương tác lỗi/retry và các luồng đầu-cuối khác theo checklist.

### Thể hiện lượt AI đang chờ làm rõ — 24/10/2026

- Khi run ở trạng thái `AWAITING_INPUT`, `AgentRunPanel` hiển thị câu hỏi, lý do và nguồn từ checkpoint mới nhất; bổ sung hướng dẫn rằng người dùng cập nhật Requirement/tài liệu nguồn để sự kiện mới tự kích hoạt tiếp luồng. Mã lỗi nội bộ không còn lặp như một cảnh báo hay hướng dẫn tiếng Anh; cả trường hợp checkpoint thiếu câu hỏi cũng hiển thị chỉ dẫn tiếng Việt.
- Cập nhật Playwright để khẳng định câu hỏi + nguồn + hướng đi tiếp hiện ra và `AUTOMATION_WAITING_FOR_INPUT` không lộ trong UI. Docker build frontend chạy format, ESLint và production build 15 route đạt; toàn bộ Playwright tuần tự **7/7 đạt** trên container vừa build. API lượt chạy/checkpoint trong browser vẫn được giả lập; đây chưa phải session/backend live E2E.
- Readiness AI và Testing, HTTP Frontend trả 200; `git diff --check` đạt. Không sửa hoặc xóa dữ liệu MongoDB.
- FE-10/FE-14 và AI-16 vẫn mở cho kiểm tra event/backend thật, role/session, lỗi làm mới, retry/checkpoint và toàn bộ các luồng còn lại.

### Retry AI dựa trên checkpoint an toàn — 24/10/2026

- `AutomationService.authorize_retry` trước đây có thể xếp lại một run lỗi mà không khôi phục snapshot đáng tin cậy; trong trường hợp checkpoint cuối bắt đầu thao tác ghi, chạy lại từ đầu có nguy cơ lặp tác dụng phụ.
- Giờ retry đọc checkpoint mới nhất trước khi đổi trạng thái. Nếu checkpoint cuối là `ACTION_STARTED` và thao tác không phải chỉ đọc hoặc đánh dấu tác vụ có mutation, trả HTTP 409 `AUTOMATION_RETRY_REQUIRES_RECONCILIATION` và không chuyển trạng thái hay phát message. Nếu checkpoint an toàn thì snapshot được giữ trong checkpoint `QUEUED` để worker tiếp tục sau phase đã lưu. Không checkpoint chỉ cho phép retry khi đang chờ cấp quyền hoặc lỗi hàng đợi; các lỗi khác bị từ chối fail-closed.
- Thêm regression cho snapshot an toàn, mutation chưa rõ kết quả, lỗi không checkpoint, retry chờ quyền không checkpoint và trạng thái chờ quyền nhưng checkpoint mutation còn sót từ lần chạy trước. Chạy trong AI Docker image với source và test mount tạm, `pytest` cài trong `/tmp`: **13/13 đạt** cùng checkpoint recovery và event enqueue. Có một cảnh báo khóa JWT test ngắn, không làm fail. Một lượt kiểm tra đầu dùng sai package root/image source cũ và fail; sau khi xác nhận đường import trỏ đúng source workspace, lần chạy hợp lệ đạt như trên.
- Phạm vi này chỉ chứng minh các nhánh retry/checkpoint được kiểm thử. Ma trận lỗi provider/outbox/database/MCP, crash ở mọi boundary, idempotency tác dụng phụ và E2E theo tất cả trigger vẫn còn mở; AI-10 và AC-04 chưa đóng.

### Hồi quy toàn bộ AI sau cập nhật retry — 24/10/2026

- Chạy toàn bộ `backend/ai/tests` trong container Docker `veriq_ai`, dùng source và test đã chép vào thư mục tạm dưới package root để chắc chắn test import đúng working tree, không phải mã cũ trong image. `LANGCHAIN_TRACING_V2=false` để không phát sinh thêm request tracing vào quota hết hạn.
- Kết quả mới nhất sau bổ sung xử lý lỗi worker, retry, và lỗi RabbitMQ khi phục hồi: **230 passed, 13 subtests passed**, 9 warning không làm fail (4 pytest collection cho Pydantic schema, 5 JWT test key ngắn). Bộ retry/checkpoint/event/worker-failure chạy riêng **20/20**; lượt riêng còn một cảnh báo JWT fixture key ngắn. `compileall` trên source mount và `git diff --check` đều đạt.
- Một lượt chạy ban đầu đặt test ở ngoài package root làm 6 bài kiểm tra catalog prompt không tìm thấy `src/prompts/README.md`; đây là lỗi bố trí test harness, không phải lỗi ứng dụng. Đưa nguyên bộ test vào đúng root tạm rồi chạy lại toàn bộ: 223/223 đạt.
- Không sửa hoặc dọn dữ liệu MongoDB; file test/source/pytest tạm chỉ nằm trong container. Kết quả này là regression toàn bộ AI, không đóng ma trận lỗi tích hợp provider/outbox/database/MCP, E2E AI theo mọi trigger, benchmark chuyên gia hay các hạng mục frontend và tích hợp cuối.
- Docker build AI/Worker hoàn tất với source workspace. Lượt export AI đầu báo hết chỗ khi giải nén image; theo quyền trước đó chỉ xóa **8,069 GB build cache** không dùng, không xóa image/container/volume. Compose recreate riêng AI và Worker sau đó thành công; AI, Worker, Testing, MongoDB và Frontend đều healthy, endpoint AI `/suc-khoe`, Testing `/suc-khoe` và trang Frontend trả **200**. Không có test data nào được tạo trong MongoDB.

### Regression bổ sung provider, Testing backend và giao diện — 24/10/2026

- Bổ sung `backend/ai/tests/test_model_provider_reliability.py`: provider trả 401 không retry, 429 retry rồi thành công, và stream lỗi sau khi đã phát một phần thì dừng mà không replay token đã phát. Ba ca đều pass trong container AI.
- Chạy lại toàn bộ AI suite từ source/tests hiện tại, đặt đúng package root trong container và tắt LangSmith tracing để không gọi quota hết: **233 passed + 13 subtests passed**; 9 warning không làm fail. Một lượt harness ban đầu để test ngoài package root gây 6 lỗi tìm prompt README; sau khi mount đúng cấu trúc đã chạy lại đầy đủ và đạt.
- Chạy toàn bộ Testing suite từ source/tests hiện tại đã mount trong container: **120 passed**.
- Chạy `NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm quality` cho format, lint và Next production build (15 route): đạt. Playwright chạy lại rõ ràng bằng `pnpm exec playwright test --workers=1`: **7/7 đạt**.
- Docker AI, Testing, Worker, MongoDB và Frontend healthy; AI `/suc-khoe`, Testing `/san-sang` trên host port 8017, và Frontend trả HTTP **200**. `git diff --check` đạt. Không tạo dữ liệu nghiệp vụ thử trong MongoDB.
- Giới hạn: Playwright Test Design vẫn giả lập API cho nghiệp vụ, và bộ test 120 không phải E2E toàn bộ ALM. Những khoảng trống AI-10, role/action browser-to-live-API, các nhóm frontend còn lại và AC-01..06 vẫn mở; không coi lượt regression này là nghiệm thu toàn kế hoạch.
### Duyệt nhóm Test Case qua API thật và xử lý quyết định ca trùng — 24/10/2026

- Kiểm tra từ Testing API và MongoDB Docker bằng project, tài khoản QA/Tester, Requirement và ca kiểm thử tạm được tạo riêng rồi dọn theo project ID.
- Luồng đạt: tạo Requirement `201` → gửi rà soát/chốt baseline → tạo Test Case nháp `201` → mở so sánh `200` → lưu bản ghép `200` → gửi duyệt `200`.
- Phân quyền và tính đồng thời: Tester lưu bản ghép bị từ chối `403`; gửi bản ghép với revision/token cũ bị `409`; QA duyệt nhóm thành công `200`; gửi lại cùng operation idempotent được nhận diện, không tạo version thứ hai.
- Trùng lặp: draft gần giống được trả trong danh sách so sánh; duyệt khi chưa ghi quyết định bị `409 TEST_CASE_DUPLICATE_REVIEW_REQUIRED`. Lượt này phát hiện UI/API merge chưa cho QA lưu `duplicate_reason`, nên không thể xử lý nhánh trùng hợp lệ. Đã thêm trường này vào `TestCaseDraftPatch` và màn so sánh; khi QA ghi lý do, lưu ghép, gửi rà soát lại rồi duyệt thành công `200`.
- Kiểm thử backend tập trung merge: **13/13 đạt**; toàn bộ Testing suite tại thời điểm đó chạy từ source và tests được chép tạm dưới `/tmp` trong container: **121 passed**.
- Production frontend được build trong Docker sau khi thêm trường lý do; `format:check`, ESLint và Next.js production build (15 route) đạt. Playwright tại thời điểm đó: **8/8 đạt** (công khai/xác thực, QA so sánh-ghép-duyệt, Tester read-only/deny, stale revision, ghi lý do trùng, AI event tự làm mới).
- API smoke hoàn tất và xác nhận các collection Project, Requirement, version, draft, Test Case, audit và AI outbox đều không còn bản ghi của project tạm. Chỉ mục Requirement tạm được gọi xóa bằng API nội bộ theo đúng project/version; không dùng dữ liệu dự án thật.
- Đây là bằng chứng đầu-cuối tốt hơn cho compare/merge và batch approval, không đóng toàn bộ FE-06/AI-05 hoặc AC-01..06: chưa kiểm tra hai phiên browser thật đồng thời, rollback giao dịch ở MongoDB trong lượt API này, API production với phiên đăng nhập thật, hoặc toàn bộ các luồng ALM và AI.

### Hồ sơ CV và rollback tạo Test Run — 24/10/2026

- Sửa quyền frontend của khu vực Cài đặt dự án: thành viên chỉ có `project.read` được vào trang để xem/sửa hồ sơ năng lực cá nhân; các tab quản trị vẫn bị lọc theo quyền chuyên biệt, không cấp quyền cấu hình cho Tester/Viewer.
- Playwright CV kiểm tra `upload → preview → thêm ứng viên chưa xác nhận → xác nhận thủ công → lưu`; nhánh lỗi 502 giữ nguyên tệp đã chọn để thử lại, lần thử hai có thể xem preview. Payload lưu chỉ gồm profile đã xác nhận và evidence block/trang, không có CV gốc hoặc văn bản CV thô. API extraction trong browser được giả lập, không khẳng định đã kiểm tra provider/parser thật.
- Phát hiện Test Run tạo record, sau đó tạo Test Result và chỉ bù xóa thủ công khi insert kết quả lỗi; audit nằm ngoài transaction. Chuyển cả insert Test Run, các kết quả ban đầu và audit sang cùng một Mongo transaction; index artifact chỉ chạy sau commit thành công. Repository nhận session tường minh; loại bỏ cơ chế bù xóa có thể để sót bản ghi nếu chính bước cleanup cũng lỗi.
- Thêm hai kiểm thử hợp đồng transaction với session/staged writes giả lập: lỗi sau khi một execution result đã được ghi khiến phần staged của Test Run/kết quả bị loại bỏ, không chạy audit hoặc indexing; đường thành công commit run/result/audit cùng giao dịch rồi mới index. Sau đó fault-injection riêng trong Testing Docker container dùng Mongo replica-set thật: tiêm lỗi sau khi audit đã ghi trong transaction, truy vấn xác nhận còn 0 Run/Result/Audit; đường thành công kế tiếp xác nhận đúng 1 Run + 2 Result + 1 Audit. Dữ liệu thuộc đúng một project ID tạm, được xóa sau smoke. Trong Testing Docker container mới build, toàn bộ suite từ source/tests workspace: **123 passed**. Build Testing thành công; container Testing healthy, `/san-sang` trả 200 sau khi lên lại.
- Build Docker frontend từ source mới chạy Prettier, ESLint, Next production build 15 route; sau recreate container healthy và trang chủ trả 200. Toàn bộ Playwright tuần tự chạy nhắm thẳng `http://localhost:3000` trên container Docker mới: **9/9 đạt**; route dự án chưa đăng nhập trả 307 về trang đăng nhập. Browser nghiệp vụ tiếp tục dùng API giả lập.
- `node --test shared/components/layout/navigationAccess.test.mjs`: **8/8 đạt**; `git diff --check` đạt. Không có CV được ghi vào MongoDB; chỉ Test Run/Result/Audit tạm dùng trong transaction smoke, đã xóa bằng project ID chính xác. Hạng mục AI-15/FE-11/FE-14 chỉ được tăng bằng chứng ở nhánh nêu trên; phân công Test Plan/Run toàn luồng, live API/session, role matrix toàn hệ thống và AC-01..06 vẫn mở.

### Hồ sơ kỹ năng cá nhân và riêng tư CV trên browser — 24/10/2026

- Thêm Playwright cho luồng hồ sơ kỹ năng trên trang Cài đặt dự án: chọn tệp TXT, gọi trích xuất CV, hiển thị kỹ năng cùng trích dẫn/source block/trang, đưa kết quả vào bản nháp với `confirmed=false`, người dùng xác nhận kỹ năng rồi mới lưu profile.
- Test khẳng định payload lưu có kỹ năng đã xác nhận và bằng chứng, nhưng không có CV gốc hay `raw_cv_text`; API extract giả lập trong bài browser nên đây là xác minh giao diện và trạng thái form, không phải bằng chứng parser/model thật.
- Bài test bắt một lỗi quyền frontend: người chỉ có `project.read` được phép xem mục “Năng lực của tôi” theo tab settings, nhưng route `/cai-dat` trước đó lại chỉ mở cho các quyền quản lý cấu hình. Đã thêm `project.read` vào nhóm quyền cho phép vào settings workspace; các tab cấu hình vẫn tự lọc theo permission riêng nên thành viên không được mở quyền quản trị dự án.
- Một lượt browser đầu dùng Docker frontend cũ nên chưa thấy code sửa; chuyển sang local Next dev nhưng thiếu biến `NEXT_PUBLIC_API_URL` khiến runtime không khởi động. Sau khi chạy với biến cấu hình và production build, CV test pass. Auth test ban đầu còn dùng URL đặt lại mật khẩu không có token; đúng hành vi ứng dụng là quay về khôi phục mật khẩu, nên test đã dùng token tổng hợp để kiểm tra trang đặt mật khẩu mới thay vì đổi logic sản phẩm.
- `NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm quality` đạt: Prettier, ESLint, Next production build với 15 route. Một lần gọi build đầu không truyền biến bắt buộc nên Next prerender fail trước khi xác minh; lần kế tiếp với biến hợp lệ đạt. Toàn bộ Playwright chạy tuần tự trên production build hiện tại: **9/9 đạt** (3 public/auth + 6 workspace/Test Design/CV). API nghiệp vụ của các browser test vẫn được route-mock; E2E API thật cho upload CV, model provider và lưu profile chưa chạy trong lượt này.
- Không có dữ liệu CV/project test ghi vào MongoDB. Kết quả này bổ sung một nhánh FE-11/FE-14 và AI-15, nhưng AI-15, FE-01/FE-11/FE-14 và nghiệm thu AC cuối vẫn mở.

### Phân công Test Run theo kỹ năng đã xác nhận trên MongoDB thật — 24/10/2026

- Smoke harness tạm gọi luồng tạo Test Run và bộ phân công hiện có trên MongoDB Docker thật. Hai Tester có hồ sơ kỹ năng đã xác nhận; ba ca yêu cầu lần lượt kỹ năng API, Security và Database.
- Kết quả: ca API được giao `tester-api`, ca Security được giao `tester-security`; ca Database không bị giao đại mà giữ trống với lý do `NO_FULL_SKILL_MATCH`.
- Sau đó thay đổi khả dụng của Tester API rồi gửi lại cùng idempotency key: hệ thống trả lại cùng Run và cùng phân công đã lưu, không tạo Run hoặc kết quả thứ hai và không tính lại phân công. MongoDB xác nhận đúng 1 Run, 3 Result, 1 Audit.
- Lượt harness đầu tiên bị chặn bởi unique index thật của Test Case version do fixture thiếu `test_case_id` và `version`; không phải lỗi sản phẩm. Harness được sửa theo schema/index hiện có và smoke chạy lại đạt. Cả hai lượt dọn dữ liệu theo project ID tạm trong `finally`; container Testing được recreate từ image để gỡ bản harness đã chép tạm.
- Đây là smoke service/repository trên Mongo thật, không phải E2E browser→API với phiên đăng nhập thật; kiểm thử matrix quyền, khả dụng/tải đầy đủ và benchmark phân công vẫn còn mở.

### Khôi phục bản ghép Test Case khi tải lại trang — 24/10/2026

- Bản ghép chưa lưu của màn so sánh được giữ tạm trong `sessionStorage` của thẻ hiện tại, gắn với draft ID, revision và comparison token; không đưa nội dung này vào storage dùng chung giữa các phiên trình duyệt.
- Khi mở lại, bản sửa chỉ được khôi phục nếu server trả cùng revision và token. Nếu khác, nội dung sửa vẫn hiện để không mất công người dùng nhưng nút lưu bị khóa theo cờ stale cho tới khi tải lại và đối chiếu nguồn mới. Sau khi lưu thành công hoặc người dùng xác nhận bỏ thay đổi thì dữ liệu phục hồi tạm được xóa. Storage lỗi không làm sai lệch bản server.
- Playwright chạy trên image Docker frontend build từ source: sửa tên ca → reload trang → mở đối chiếu lại → thấy đúng bản sửa được phục hồi → lưu lên API giả lập; đồng thời kiểm tra responsive khung so sánh ở 1920/1440/1280/768/390 px không tạo tràn trang. Tại thời điểm lượt đầu suite đạt **10/10**; sau đó bổ sung stale-token và toàn route matrix, suite mới nhất đạt **12/12**.
- Đây xác minh khả năng phục hồi phía giao diện cho cùng phiên tab, chưa thay thế E2E với phiên backend thật, kiểm tra xung đột giữa hai browser, hoặc persistence phía server trước khi người dùng bấm lưu.
- Bổ sung nhánh an toàn: sau khi sửa và lưu tạm trong tab, thay comparison token rồi tải lại; bản sửa vẫn đọc được nhưng giao diện chuyển chỉ đọc, hiện cảnh báo nguồn/phiên bản đã đổi và khóa nút lưu. Sau khi bổ sung matrix route, Playwright frontend Docker hiện **12/12 đạt**; Prettier, ESLint và production build đều đạt, `git diff --check` sạch.

### Responsive audit cho toàn bộ route workspace — 24/10/2026

- Thêm bài Playwright duyệt đủ 29 route workspace dự án dưới phiên BA/QA tổng hợp, mỗi route tại 1920/1440/1280/768/390 px; sau navigation đo `documentElement.scrollWidth` và `body.scrollWidth` so với viewport.
- Kết quả Docker frontend hiện tại: 145 lần kiểm tra route/viewport, không phát hiện tràn ngang. Đây mới là kiểm tra hình học ngang với API trả rỗng/đơn giản; không kết luận mọi form/bảng/modal hoạt động đúng hay nội dung từng trang đã được duyệt trực quan.
- Toàn suite đạt **12/12** tuần tự; format và ESLint đạt; Docker production build đã chứa code phục hồi bản ghép. API nghiệp vụ trong browser test được giả lập. 28 route BA/QA có smoke session thật trước đó ở hai viewport, nhưng không thay cho ma trận role và action hoàn chỉnh.

### Sửa lỗi header danh sách Requirement và kiểm tra frontend Docker — 24/10/2026

- Tái hiện lỗi tiêu đề “Danh sách yêu cầu” bị ép thành cột chữ khi toolbar có nhiều thao tác. CSS riêng của panel ghi đè `display:flex` nhưng làm mất `flex-wrap`; bổ sung wrap cho header và duy trì tại breakpoint vừa/màn hẹp.
- Thêm Playwright đo hình học thật cho tiêu đề/toolbar và tràn ngang ở 1440, 1280, 1024, 768, 390 px. Bài mới đạt trên frontend Docker hiện hành.
- Chạy `NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm quality`: Prettier, ESLint và production build 15 route đạt. Build/recreate Docker frontend thành công; container healthy. Chạy lại browser suite nhắm `http://localhost:3000`: **15 passed, 1 live-API fixture case skipped** trong lượt tổng quát.
- Browser smoke compare/merge riêng trong lượt trước đã gọi các endpoint đọc so sánh, lưu bản ghép và đọc lại sau reload qua Testing API Docker thật; dữ liệu fixture tạm được xác nhận dọn khỏi Mongo. Xác thực browser và API ngoài phạm vi so sánh được stub, nên không ghi đây là session thật hoặc nghiệm thu FE-06 toàn phần.
- Đây chỉ sửa/kiểm tra một lỗi bố cục cụ thể và hồi quy frontend đang có. Audit tagline/nội dung toàn trang, form/bảng/modal ở mọi trạng thái, role/action live API và nghiệm thu AI + frontend + ALM 36 tiêu chí vẫn mở.

### Chuẩn hóa thứ tự phần trong prompt benchmark và chạy AI hồi quy — 24/10/2026

- Phản ánh người dùng: prompt có ngôn ngữ/định dạng lẫn lộn. Rà source `backend/ai/src/prompts/*.py`: chỉ dẫn tĩnh trong prompt runtime dùng tiếng Anh; thẻ `<output_language>` yêu cầu nội dung người dùng bằng tiếng Việt và giữ nguyên trích dẫn/định danh. Tiếng Việt trong các module khác chủ yếu là thông báo API, nội dung run, audit note và label công cụ, không phải chỉ dẫn model.
- Tìm thấy prompt `CLARIFICATION_BASELINE` đặt `<question_rules>` trước `<output_language>`, lệch thứ tự chuẩn đã ghi trong `README.md`. Đưa `<output_language>` lên trước quy tắc chuyên biệt và thêm assertion chống hồi quy thứ tự: `system_identity → objective → trust_boundary → output_language → question_rules → output_contract`.
- `pytest==8.3.4` được cài bên trong container Docker tạm `--rm`; source và tests được mount chỉ đọc, LangSmith tracing tắt, test dùng cấu hình placeholder, không ghi database. Prompt catalog: **23 passed**; toàn bộ AI tests: **272 passed**, còn 5 cảnh báo độ dài JWT chỉ phát sinh trong test fixture. Container kiểm thử bị xóa tự động khi lệnh kết thúc; pytest không được cài vào image/runtime AI.
- Các test và dependency test trong workspace được giữ nguyên vì toàn ma trận AI/frontend/tích hợp chưa nghiệm thu; cleanup chỉ thực hiện sau lượt acceptance cuối như người dùng yêu cầu.

### Hiển thị trích dẫn nguồn của AI run và hồi quy giao diện — 24/10/2026

- Bổ sung phần xem source facts trong chi tiết AI run: loại đối tượng, ID artifact/version, trích dẫn nguyên văn và vị trí nguồn nếu backend có lưu. Luồng tải lại chạy và endpoint bằng chứng vẫn chỉ đọc; không tạo hoặc xác nhận nghiệp vụ.
- E2E ban đầu thất bại và phát hiện xung đột tên trong `testingApi`: `projectTestingApi.getAutomationEvidence` bị `executionTestingApi.getAutomationEvidence` ghi đè khi ghép client. Đổi API AI-run thành `getAutomationRunEvidence`; endpoint bằng chứng execution giữ nguyên tên và hành vi. Bổ sung assertion để sau này test bắt cả trích dẫn, version và vị trí, không chỉ câu hỏi làm rõ.
- E2E mục AI event pass **1/1** trên local Next dev sau sửa. Toàn suite trên dev từng có một timeout ở trang public/auth (`page.evaluate`, không liên quan sửa AI); không tính kết quả đó là pass. Build/recreate Docker frontend từ source đạt format, ESLint và production build 15 route; chạy lại toàn suite trên Docker production: **15 passed, 1 live-API fixture case skipped**. Route geometry 29 × 5 viewport và AI-run citation đều pass.
- Đây chỉ xác minh UI đọc và trình bày payload nguồn giả lập; chưa kiểm chứng session/API quyền thật cho AI run hoặc AI-16 toàn phần. Container Docker frontend đã được cập nhật; local dev server tạm được dừng sau test. Các suite test vẫn được giữ tới nghiệm thu tổng thể.

### Khôi phục MongoDB và chạy hồi quy Testing — 24/10/2026

- MongoDB Docker bị restart vì `/data/db/mongod.lock` và WiredTiger checkpoint không ghi được (`No space left on device`), dù host còn dung lượng. Sau khi xác nhận volume `veriq_mongodb_data` chứa dữ liệu còn dùng và không đụng vào volume, đã xóa riêng Docker build cache theo quyền người dùng đã cấp trước đó. MongoDB sau đó tự khởi động healthy và WiredTiger recovery hoàn tất.
- Chạy Testing suite trong container tạm từ image `veriq-testing`, mount source chỉ đọc, đặt `PYTHONPATH=/workspace`, cấp biến môi trường kiểm thử không có credential thật và cài `pytest==8.3.4` trong container. Kết quả: **149 passed**. Container `--rm` tự xóa; pytest không cài vào service runtime và mount chỉ đọc nên không tạo cache trong workspace.
- Hai lần thử đầu không hợp lệ do thiếu `PYTHONPATH`, sau đó thiếu biến cấu hình bắt buộc `PROJECT_NAME`; không tính hai lượt thu thập lỗi này là kết quả test sản phẩm. Lượt đúng cấu hình đạt toàn bộ 149 test.
- Kết quả này chỉ khôi phục và tái xác nhận regression suite Testing. Không đóng các hạng mục E2E session/role thật, luồng AI event, benchmark và frontend theo matrix nghiệm thu tổng.

### Hồi quy Content sau khi khôi phục Docker storage — 24/10/2026

- Chạy `backend/content/tests` trong container tạm từ image `veriq-content`, mount source chỉ đọc, biến cấu hình placeholder và cài `pytest==8.3.4` trong container. Kết quả: **4 passed**, có một cảnh báo deprecation từ thư viện `crypt` của passlib; không có test fail.
- Cùng lượt đã chạy Testing **149 passed** như ghi ở trên. AI **272 passed** và browser Docker **15 passed / 1 live-API fixture skipped** là các lượt độc lập đã ghi nhận phía trên, không gộp thành một end-to-end acceptance.
- Mọi container pytest của hai lượt đều `--rm`; không xóa các suite hoặc dependency test trong workspace vì còn hạng mục AI/frontend/integration chưa nghiệm thu.
- Kiểm tra riêng các service đang chạy sau đó cho thấy `pytest 8.3.4` hiện diện trong writable layer của ba container `veriq_ai`, `veriq_testing`, `veriq_content` (`docker diff` xác nhận các package được thêm trong container); các `requirements.txt` runtime không khai báo pytest. Vì vậy không được hiểu các lần chạy `--rm` mới nhất là đã làm sạch service đang chạy. Ghi nhận đây là nhiễm bẩn runtime còn tồn tại; sẽ gỡ bằng cách build/recreate service từ Dockerfile/dependency production đã kiểm tra sau khi toàn bộ nghiệm thu và hồi quy kết thúc, rồi xác minh `find_spec("pytest")` không còn tìm thấy trong container mới.

### Nối phiên bản nguồn tài liệu có khai báo rõ ràng — 24/10/2026

- Bổ sung cách tạo chuỗi phiên bản nguồn mà người dùng chọn tài liệu trước đó rõ ràng; không ghép theo tên tệp hoặc phỏng đoán nội dung.
- Mỗi tài liệu mới có chuỗi riêng, số phiên bản và liên kết `previous_source_version_id`; khi nối tiếp, tài liệu cũ không bị sửa. Chỉ phiên bản mới nhất được phép làm cha. Cùng nội dung bị từ chối thay vì tạo phiên bản rỗng.
- Điều kiện nối chuỗi yêu cầu cùng dự án, người sở hữu, định dạng và thiết lập loại nguồn/quyền đọc/cho AI. Giao diện sao chép thiết lập từ tài liệu cha và khóa chúng khi đang nối phiên bản; người dùng có thể hủy liên kết để tạo tài liệu độc lập.
- MongoDB dùng unique partial index theo `(project_id, source_series_id, source_version_sequence)` để ngăn hai lượt đồng thời cùng tạo một số phiên bản. Nếu có xung đột thì API trả `409`, không ghi đè.
- Tài liệu cũ chưa có chuỗi được giữ nguyên; khi người dùng chọn rõ một tài liệu cũ làm cha thì chuỗi mới bắt đầu từ tài liệu đó. Không tự suy diễn quan hệ giữa tài liệu cũ.
- Không cho sửa nhãn phiên bản thủ công làm sai lệch thứ tự của chuỗi.
- Hồi quy Testing hiện tại: **154 passed, 40 subtests passed** trong container dùng mã nguồn read-only; pytest được cài trong container tạm và xác nhận không có `pytest` trong runtime Testing service.
- Testing Docker được build/recreate và `/san-sang` trả `ready`. Đã đọc index từ MongoDB thật và xác nhận unique partial index tồn tại. Không sửa hay xóa volume/dữ liệu nghiệp vụ.
- Frontend `pnpm quality` qua format, lint và production build khi đặt `NEXT_PUBLIC_API_URL=http://localhost:8000`. Docker production image có giao diện nối phiên bản nguồn. Playwright trên Docker frontend đạt **16 passed, 1 live-API fixture skipped**; bài mới xác nhận chọn tài liệu cha, khóa trường cấu hình quyền/loại nguồn và hủy liên kết để quay lại tài liệu độc lập. API thật cho thao tác tạo phiên bản vẫn chưa chạy qua session người dùng.
- **AI-02 còn mở**: đây mới là lineage khai báo cho tài liệu nguồn; chưa chứng minh toàn nhánh so sánh nội dung nhiều tài liệu, phát hiện mâu thuẫn, cập nhật tối thiểu artifact bị ảnh hưởng và hồi quy sự kiện đến đầu ra AI trên browser.
- Sau khi dựng lại Testing từ Dockerfile production, xác nhận `pytest` không còn trong runtime Testing. AI và Content vẫn đang chạy các container cũ có gói pytest trong writable layer; phải rebuild/recreate hai service đó sau đợt nghiệm thu cuối rồi mới làm cleanup pytest tổng thể như yêu cầu.

### Rà chuẩn prompt theo phản ánh tiếng Anh/tiếng Việt — 24/10/2026

- Kiểm tra lại mã nguồn từng module prompt và chạy riêng `test_prompt_catalog.py` bằng `unittest` trong container AI tạm, không cần đưa pytest vào runtime: **23/23 passed**.
- Kết quả cụ thể: chỉ dẫn tĩnh trong 23 module runtime là tiếng Anh; nội dung người dùng nhận được được yêu cầu bằng tiếng Việt ở `<output_language>`; trích dẫn, tên kỹ thuật và mã định danh được giữ theo nguồn. Prompt con kế thừa cấu trúc cha khi ghép, không cần lặp nguyên phần chỉ dẫn.
- Catalog `backend/ai/src/prompts/README.md` ghi nơi sở hữu, nơi gọi và mục đích từng prompt. Bốn module tương thích không còn caller runtime; chúng không được tính là prompt hoạt động.
- Vì vậy hiện chưa thấy prompt runtime viết chỉ dẫn bằng tiếng Việt hoặc sai cấu trúc theo các tiêu chí tự động. Phần cần giữ làm quy tắc cho prompt mới là: `system_identity → objective → trust_boundary → output_language (nếu có nội dung hướng người dùng) → rules/evidence → output_contract → dữ liệu đầu vào không tin cậy`.
- Đây là kết quả kiểm tra catalog/prompt, không chứng minh chất lượng đầu ra của model. Hồi quy model đầy đủ sẽ chạy lại ở acceptance tổng; giữ nguyên suite tới lúc đó theo yêu cầu dọn test sau cùng.

### Hồi quy toàn bộ các suite hiện có và truyền lineage vào AI event — 24/10/2026

- Sự kiện `DOCUMENT_INGESTED` từ Testing nay truyền `relationship_path` có thứ tự từ chuỗi nguồn → phiên bản cha → tài liệu hiện tại vào `EvidenceItem`; tài liệu đầu chuỗi tự làm gốc. Schema AI đã có trường này và không đổi hợp đồng API. Thêm regression cho phiên bản kế tiếp và tài liệu độc lập.
- Testing suite chạy trên source hiện tại trong container tạm: **156 passed**. `pytest==8.3.4` được cài trong container dùng một lần; không cài vào runtime Testing. Sau đó Testing Docker được build/recreate từ production Dockerfile, health `/san-sang` trả `ready`, Mongo volume được giữ nguyên, và `importlib.util.find_spec("pytest")` trong service trả `None`.
- AI suite chạy trên source read-only trong Docker: **272 passed**; pytest cài vào `/tmp` của container tạm. Content suite đạt **4 passed**, với một cảnh báo deprecation `crypt` từ thư viện `passlib`.
- Frontend `pnpm quality` đạt format, lint và Next production build đủ 15 route. Frontend Docker được build/recreate; ngay trong build cũng qua format/lint/build. Browser E2E trực tiếp trên `http://localhost:3000`: **16 passed, 1 skipped** (bài compare qua live Testing API cần fixture/credential không có trong lượt tổng quát). Các ca nghiệp vụ khác vẫn có API giả lập; kết quả không đóng FE-14 hoặc ma trận session/role.
- Các lượt trên là hồi quy theo suite hiện có, không phải chạy đủ AC-01..06 và không đóng ma trận 36 tiêu chí. Không dọn suite, thư mục E2E, pytest test dependencies hay báo cáo lúc này; chỉ dọn test tooling/runtime pollution và fixture tạm sau lượt nghiệm thu tích hợp cuối theo yêu cầu.
- Bổ sung kiểm tra hợp đồng AI event: `AutomationEventRequest` giữ nguyên `relationship_path` khi tạo Automation Run; chạy lại full AI suite sau bổ sung: **272 passed**. Phần này chỉ chứng minh truyền lineage qua schema/queue của Agent, chưa chứng minh compiler dùng lineage để quyết định sinh/chỉnh artifact; vì vậy AI-03 vẫn mở.

### Lưu lineage đã xác minh trên SourceFact và dựng lại AI production — 24/10/2026

- Sửa nhánh facts để đường dẫn quan hệ chỉ được lấy từ evidence nguồn đã đối chiếu, không lấy từ dữ liệu do model tự khai; lưu vào `SourceFact.relationship_path` để repository có thể giữ lineage cùng fact. Graph runner cũng giữ đường dẫn khi tạo facts trực tiếp hoặc fallback từ evidence.
- Bài hồi quy bao gồm kiểm tra trích xuất/fallback, chống model giả lineage, kiểm tra round-trip schema `SourceFact` và hợp đồng Automation Run. Toàn bộ AI suite hiện tại: **273 passed**.
- Dựng lại `veriq_ai` từ production Dockerfile, recreate container, chờ khởi tạo xong; `/san-sang` trả `ready` cho MongoDB, Redis, RabbitMQ, Qdrant, Neo4j, knowledge, object storage và model. `pytest` trong runtime trả `None`; `git diff --check` sạch.
- Phạm vi này chứng minh facts có lineage nguồn được xác minh và lưu bền, không chứng minh lineage đã được dùng để điều khiển blueprint/artifact trong pipeline đầu-cuối. Do đó **AI-03 vẫn mở**, và 36 nhóm nghiệm thu chưa được tính hoàn tất.
- Tiếp tục đối chiếu đường vào tool `process_ingested_requirement_document`: runtime fact schema trước đó không khai báo `relationship_path`, nên snapshot Pydantic có thể loại trường trước khi event task nhận facts. Tách model-output `ExtractedAutomationFact` (không cho field lineage do model khai báo) khỏi runtime `AutomationFact`, nơi lineage được gán từ evidence xác nhận; kiểm thử snapshot checkpoint và đối số task đầu-cuối trong code.
- Chạy targeted Docker regression cho ba hợp đồng này: **3 passed** (fact extraction/checkpoint round-trip, cấm lineage do model tạo, và lineage từ source fact tới task nhập tài liệu). Một lượt đầu test task bị từ chối do fixture thiếu quyền/metadata bắt buộc; đã sửa fixture đúng hợp đồng rồi chạy lại đạt. Đây vẫn là regression hẹp, không phải smoke event/runtime hoặc nghiệm thu AI-03.

### Truyền lineage đã được kiểm tra vào blueprint — 24/10/2026

- Tách hàm kiểm tra facts với evidence có quyền; không chấp nhận `relationship_path` từ argument của agent. Path phải đến từ evidence tương ứng sau khi xác nhận artifact và quote. Path lỗi định dạng bị loại bỏ.
- `TestingEvidence` nay có trường typed `relationship_paths`; compiler nhận các đường lineage theo source version cùng quote đã xác minh. Prompt nêu rõ lineage chỉ là metadata định vị nguồn, không thể dùng nó thay cho quote hay làm căn cứ sinh obligation.
- Hàm thu thập tài liệu được phép đọc theo chuỗi phiên bản từ `previous_source_version_id`, chỉ đi qua các tài liệu có trong kết quả API đã ACL-filter; dừng tại nguồn không đọc được, project/series khác, vòng lặp hoặc giới hạn schema. Facts và evidence đưa vào compiler cùng giữ path.
- Kiểm thử Docker nhóm blueprint, document workflow, graph fact extraction, event task, provenance, checkpoint và prompt catalog: **123 passed**. Bao gồm kháng path giả, lineage hợp lệ qua nhiều version, lineage bị ngắt khi parent không có quyền, truyền lineage vào request compiler, và ràng buộc mỗi claim vẫn cần trích dẫn nguyên văn.
- Đây là xác nhận hợp đồng và các nhánh unit/service liên quan; chưa chạy lại luồng upload → event → worker → blueprint → Requirement/Test Case trên dữ liệu nguồn nhiều phiên bản/ACL thật. AI-03 và ma trận 36 nhóm vẫn mở.

### Chỉ nhận chuỗi phiên bản do API xác thực làm lineage — 24/10/2026

- Đối chiếu cho thấy đường dẫn Neo4j biểu diễn lân cận quan hệ tổng quát, không đủ căn cứ để gọi là chuỗi phiên bản nguồn. Không dùng nó làm ancestry của fact.
- Fact chỉ nhận lineage tính từ `previous_source_version_id` trên danh sách tài liệu Testing API đã ACL-filter. Mỗi ID phải thuộc tập tài liệu được phép đọc, không lặp và đường dẫn kết thúc đúng tài liệu được trích. Path sai/không xác minh được bị bỏ; nội dung quote vẫn phải qua kiểm tra nguồn và offset.
- Regression Docker dùng unittest: blueprint **23 passed**, Requirement document workflow **31 passed**, Requirement-change blueprint **11 passed**, benchmark service **12 passed**. Một test ban đầu lộ fixture đang lấy path từ fact thay vì source evidence; đã sửa hợp đồng/test theo hướng tin metadata server-verified, chạy lại đạt. Container chạy với network tắt và biến cấu hình giả, không gọi DB/provider thật.
- Đây là sửa tính đúng đắn của lineage và targeted regression, không phải kiểm thử pipeline upload/event/worker thật. AI-03 và toàn ma trận 36 tiêu chí vẫn mở.

### Chuẩn hóa lineage sự kiện cho tài liệu phiên bản 2 — 24/10/2026

- Sửa `emit_document_ingested`: loại ID trùng nhưng giữ thứ tự chuỗi `source_series_id` → `previous_source_version_id` → tài liệu hiện tại. Phiên bản 2 không còn ghi lặp ID gốc khi series root đồng thời là parent; tài liệu độc lập vẫn có một root, phiên bản 3 giữ đủ ba ID.
- Kiểm tra `backend/testing/tests/test_ai_automation_outbox.py` trong container Docker tạm, source read-only và network tắt: **15 passed**.
- Đây là kiểm thử event payload, không phải upload/outbox dispatcher/worker thực tế; AI-03 chưa đóng.

### Chặn lineage qua parent không hợp lệ — 24/10/2026

- Khi lần `previous_source_version_id`, chỉ nhận parent khi ID bản ghi khớp khóa, cùng project và series; nếu cả hai có sequence thì phải liền kề. Parent thiếu quyền hoặc metadata không khớp làm đường ancestry dừng tại tài liệu hiện tại.
- Kết quả `source_facts`/`source_evidence` cuối của workflow giữ lại đường lineage đã được kiểm tra để người đọc run có thể lần từ citation về đúng chuỗi phiên bản; không thay thế quote hoặc định danh phiên bản nguồn.
- Khi dựng path, cha chỉ được đưa vào nếu cũng thuộc allowlist tài liệu đã cho AI đọc; tài liệu người dùng có thể xem nhưng chưa cấp cho AI sẽ không làm lộ thêm ID trong metadata lineage.
- Thêm hồi quy cho sai ID, khác project, lệch sequence, thiếu source series và lineage trên citation đã lưu. `test_requirement_document_workflow.py`: **33 passed** trong container Docker tạm, network tắt.
- Đây là kiểm tra boundary cho lineage, không thay E2E upload → outbox → worker → artifact.

### Tách định danh phiên bản nguồn khỏi số phiên bản hiển thị — 24/10/2026

- Khi rà compiler, thấy `artifact_version_id` đang dùng `source_version` dạng số hiển thị (ví dụ `1`) làm khóa cho evidence. Hai tài liệu độc lập đều ở phiên bản `1` có thể ghi đè evidence của nhau trong map truyền vào Blueprint.
- Đổi khóa evidence sang ID bản ghi phiên bản tài liệu duy nhất từ Testing API; giữ `source_version` làm metadata hiển thị/đối chiếu, không dùng làm khóa toàn cục.
- Thêm hồi quy cho hai tài liệu độc lập cùng `source_version=1` ở cả `verified_document_facts` và citation Requirement. Nhóm document workflow + blueprint: **58/58 passed**.
- Lần chạy full AI ban đầu lộ một fixture test benchmark thiếu `observed_runs` sau khi schema lặp được siết; fixture được cập nhật theo hợp đồng. Chạy lại toàn bộ AI suite: **301/301 passed** trong container Docker tạm `--network none`, source/tests mount chỉ đọc; container tự xóa khi kết thúc.
- Đây là lỗi lineage khóa evidence được sửa và xác nhận hồi quy. Không đóng AI-03: chưa chạy lại upload → outbox → worker → compiler thật với nhiều tài liệu phiên bản, ACL và artifact downstream.

### Truyền lineage đã xác minh tới prompt Blueprint — 24/10/2026

- Kiểm tra luồng sau `compile_testability_blueprint` phát hiện `TestingEvidence.relationship_paths` và số phiên bản hiển thị không được serialize sang payload của `generate_ai_automation`; model chỉ thấy artifact ID/version và nội dung.
- Bổ sung trường typed `source_version`, truyền `source_version` cùng `relationship_paths` từ evidence đã xác minh sang payload/prompt. Prompt Blueprint đã quy định lineage là metadata định vị, không phải sự thật hay căn cứ thay citation; giữ quy tắc đó.
- Thêm kiểm thử payload/prompt lineage **1/1**; document workflow + blueprint **59/59**; full AI suite trên container Docker tạm `--network none`, source/tests mount read-only: **303/303 passed**.
- Còn phải kiểm chứng qua model/provider và pipeline upload → outbox → worker với nhiều nguồn/phiên bản/ACL rồi đọc lại artifact. Vì vậy AI-03 và ma trận 36 tiêu chí vẫn mở.

### Smoke model thật cho nhiều nguồn cùng số phiên bản — 24/10/2026

- Chạy `compile_testability_blueprint` trên source hiện hành trong container tạm nối Docker network, tracing tắt; chỉ dùng ba tài liệu tổng hợp, không ghi MongoDB/Object Storage/Qdrant.
- Input có hai chuỗi độc lập cùng version `1`, một chuỗi kế tiếp version `2`, với hai quy tắc đăng nhập xung đột và một quy tắc độ dài mật khẩu. Model `google/gemma-4-31B-it` trả `SUCCESS`; validator chấp nhận 3 source reference, 3 obligations và 1 clarification loại `CONTRADICTION`; không có reason code lỗi grounding.
- Container chạy hết và tự xóa. Kết quả chứng minh model thật nhận được source version/lineage qua prompt mới và compiler giữ riêng nguồn trùng nhãn; không phải upload/API/outbox/worker E2E, không kiểm tra ACL hoặc artifact lưu trong Testing. AI-03 vẫn mở.
- Regression Testing phía phát sự kiện (`test_ai_automation_outbox.py`) chạy lại trên image Testing tạm với source/tests hiện tại, network tắt: **15/15 passed**; xác nhận hợp đồng lineage event phía gọi AI vẫn tương thích.

### Full Testing regression trên container tạm — 24/10/2026

- Image production `veriq-testing:latest` không có `pytest`; cài `pytest==8.3.4` chỉ trong container `--rm`, mount source/tests/`pytest.ini` chỉ đọc và dùng cấu hình test giả. Không cài pytest vào service đang chạy hoặc sửa dependency runtime.
- Toàn bộ `backend/testing/tests`: **158 passed**. Container kiểm thử đã kết thúc với `--rm`; không để lại container test.
- Đây là hồi quy Testing unit/service suite, không thay thế API/session E2E hoặc ma trận tích hợp AC-01..06. Các mục AI/FE/AC vẫn mở theo checklist.

### Fail-closed khi nguồn đổi trong lúc AI biên dịch — 24/10/2026

- Sau khi Blueprint model trả về nhưng trước lần ghi Template/Requirement đầu tiên, workflow gọi lại endpoint tài liệu đã ACL-filter và so khớp toàn bộ tập nguồn được phép, trạng thái `READY`, quyền AI, nội dung chuẩn hóa, authority, source series, số phiên bản và liên kết parent. Thu hồi quyền, thay nội dung/metadata hoặc thay đổi tập tài liệu làm run dừng với mã lỗi cụ thể trước khi công bố artifact.
- Thêm regression cho snapshot không đổi, thu hồi quyền, thay nội dung, thay parent lineage và thêm tài liệu mới trong lúc model chạy. `test_requirement_document_workflow.py`: **40/40 passed** trong container `veriq-ai:latest`, source/tests mount chỉ đọc, network tắt. `git diff --check` đạt.
- Chạy toàn bộ Testing suite trên container `veriq-testing:latest` với `pytest==8.3.4` cài riêng trong container `--rm`: **158 passed**. Kiểm tra lại `veriq_testing` đang chạy xác nhận `pytest_runtime_present=False`.
- Guard snapshot đóng một khoảng race trước lần ghi đầu tiên; chưa thay thế quyền kiểm tra của API ở từng thao tác và chưa chứng minh upload → outbox → worker → artifact thật. AI-03 cùng ma trận 36 tiêu chí vẫn mở.
- Bổ sung so khớp revision nguồn để bắt thay đổi metadata/quyền ngay cả khi text hash không đổi; kiểm thử riêng nhánh revision-only. Workflow suite sau cập nhật: **41/41 passed** trong container AI tạm, network tắt; `git diff --check` đạt.

### Đồng bộ AI Docker theo source MCP hiện hành — 24/10/2026

- Đối chiếu chữ ký `discover_project_tools` phát hiện AI container cũ chưa có kiểm tra token/quyền hiện hành dù source đã có. Build và recreate riêng service AI từ source hiện tại; không xóa hoặc khởi tạo lại database/volume.
- Sau recreate, chữ ký trong container khớp source (`project_id`, `permissions`, `token`, `automation_run_id`), container `healthy`, `/san-sang` trả HTTP 200 với toàn bộ dependency ở trạng thái `ready`, và `pytest_runtime_present=False`.
- Đây là sửa lệch source/runtime và readiness, không phải bằng chứng MCP được Agent tự chọn trong event/worker hoặc LangSmith cloud trace thành công. AI-11, AI-13 và ma trận 36 tiêu chí vẫn mở.

### Chặn nguồn tài liệu lẫn project trong Requirement compiler — 24/10/2026

- Khi rà AI-03, thêm kiểm tra fail-closed cho danh sách tài liệu được phép đọc: mọi tài liệu API trả về phải cùng `project_id` với run, cả khi lấy snapshot ban đầu lẫn khi xác minh lại sau model inference. Sai phạm vi dừng với `AI_SOURCE_PROJECT_SCOPE_INVALID` trước khi ghi template/Requirement.
- Thêm hai regression cho phản hồi lộ tài liệu project khác (ở bước lấy nguồn và bước revalidation). Chưa chạy pytest theo yêu cầu giữ lượt kiểm thử tích hợp lớn ở cuối; chỉ `py_compile` và `git diff --check` đã đạt. Runtime đã được build lại sau thay đổi như ghi ở dòng dưới.
- Đây là tăng cường ranh giới project cho AI-03, không phải bằng chứng multi-source runtime; AI-03 và ma trận 36 mục vẫn mở.
- Sau thay đổi guard, build/recreate lại AI Docker từ source mới; hàm guard và hàm discovery MCP cùng import được, MCP signature khớp source, readiness trả 200 với mọi dependency `ready`, và pytest không có trong production runtime. Hai regression project-boundary vẫn được giữ cho lượt test tích hợp cuối.

### Kiểm tra snapshot nguồn trong chính lúc tổng hợp Template — 24/10/2026

- Rà endpoint `synthesize_template` cho thấy API nhận quyền/nguồn trước suy luận nhưng có thể lưu Template sau khi model trả kết quả mà không đọc lại đúng snapshot nguồn. Thêm bước đọc lại quyền project, danh sách tài liệu và Template nguồn sau inference; so revision/nội dung/metadata nguồn, version/revision/trạng thái và nội dung Template. Nếu đổi hoặc thu hồi nguồn, endpoint dừng `409 TEMPLATE_SOURCE_SNAPSHOT_CHANGED` trước khi gọi tạo Template.
- Thêm regression cho nguồn giữ nguyên, tài liệu đổi revision/nội dung và Template nguồn đổi version. Chưa chạy pytest theo yêu cầu gom test vào lượt nghiệm thu cuối; `py_compile` và `git diff --check` đạt. Testing runtime chưa build lại từ thay đổi mới.
- Sửa này đóng thêm một khoảng TOCTOU giữa AI inference và ghi Template, không chứng minh runtime multi-source hoặc đóng AI-03/36 mục.

### Bảo vệ cả nhánh ghép Template chỉ có bối cảnh — 24/10/2026

- Rà lại toàn bộ nhánh của `synthesize_template` phát hiện trường hợp chỉ ghép các Template nguồn chưa có Requirement không gọi model và đi thẳng tới lưu, bỏ qua kiểm tra lại snapshot. Đã thêm cùng bước xác minh quyền/phiên bản/nguồn ngay trước khi lưu nhánh này; nếu snapshot thay đổi, không gọi `create_template`.
- Thêm hai regression cho đường giữ nguyên và đường nguồn thay đổi bị từ chối. Đã `py_compile` các module/test liên quan và `git diff --check`; theo yêu cầu gom test, chưa chạy pytest.
- Build/recreate riêng `veriq_testing` từ source mới; container đạt health `healthy`, `/san-sang` trả `{"status":"ready","service":"testing"}`, và kiểm tra Python runtime xác nhận `pytest` không được đóng gói. Không đụng volume dữ liệu. Đây là bằng chứng build/readiness, không phải bằng chứng hồi quy nghiệp vụ.
- AI-03 và ma trận 36 tiêu chí vẫn mở cho đến lượt nghiệm thu tích hợp cuối.

### Đọc đủ phạm vi Test Case khi Work Item thay đổi — 24/10/2026

- Rà `get_work_item_impact_context` phát hiện endpoint lấy Test Case trước đây chỉ gọi trang đầu, dù API trả metadata trang; trên 500 ca có thể báo cáo impact thiếu mà trạng thái vẫn `completed`. Liên kết Requirement không cùng project cũng bị bỏ qua, và truy vấn nguồn phía Testing có giới hạn 20.000 bản ghi.
- Đã thêm đọc toàn bộ trang với xác minh page/total/ID/project, fail-closed khi metadata đổi hoặc dữ liệu lặp/thiếu, từ chối khi chạm trần 20.000 vì không thể chứng minh danh sách đầy đủ, và không bỏ qua Requirement/version không thể xác minh. Bổ sung thứ tự tie-break ổn định bằng test case key/ID cho phân trang API.
- Bốn regression mới kiểm tra phân trang đầy đủ, metadata thay đổi, ID lặp/project scope và trần truy vấn. Chưa chạy pytest để giữ kiểm thử cho lượt tổng; `py_compile` và `git diff --check` đạt. Chưa build lại Docker AI/Testing sau thay đổi mới.
- Đây là sửa an toàn cho một nhánh AI-08; chưa chứng minh WIP/dependency, outbox/worker, phân trang runtime lớn hoặc các mục còn lại.
- Sau khi hoàn tất các sửa AI-08, build/recreate lại hai service AI và Testing từ source hiện hành. Cả hai đạt Docker healthcheck, `/san-sang` của AI trả `ready` cho MongoDB/Redis/RabbitMQ/Qdrant/Neo4j/knowledge/object storage/model, Testing trả `ready`, và pytest không được đóng gói trong hai runtime production. Đây chưa phải chạy regression test.

### Retry an toàn AI Automation trên giao diện — 24/10/2026

- Rà `authorize_retry` cho thấy backend hỗ trợ tiếp tục lượt `FAILED`/`DEGRADED` nếu có checkpoint cuối an toàn (hoặc lỗi hàng đợi), nhưng `AgentRunPanel` chỉ hiện nút cho `AWAITING_AUTHORIZATION`.
- Thêm hàm kiểm tra UI bám điều kiện backend: chỉ người tạo run; trạng thái hỗ trợ; checkpoint cuối là căn cứ (không lấy checkpoint snapshot cũ hơn); chặn lỗi kết quả thao tác chưa rõ và thao tác ghi đang dở; cho phép trường hợp hàng đợi lỗi được backend cho retry. UI hiển thị lý do cần đối soát thay vì để người dùng tự retry mù; nếu API retry lỗi, tải lại run/checkpoint để không giữ revision cũ.
- Bổ sung 7 kiểm tra logic Node và 2 browser E2E cho quyền người tạo, trạng thái cho phép, checkpoint an toàn/thiếu/cũ, lỗi hàng đợi, kết quả thao tác chưa rõ, dịch lỗi nghiệp vụ và payload revision khi retry. Chưa chạy test/browser suite theo yêu cầu dồn kiểm chứng cuối; chỉ kiểm tra cú pháp, Prettier và `git diff --check`.
- AI-16 vẫn mở: cần chạy test mới, frontend build/browser và xác minh lỗi revision/API retry qua session thật cùng toàn ma trận cuối.

### Kiểm tra lại schema MCP trước khi gọi công cụ — 24/10/2026

- Rà luồng discovery → planner → `call_mcp_read_tool` phát hiện đối số chỉ được kiểm tra với schema chung `{connection_id, tool_name, arguments}`; schema nhập từ server chỉ hướng dẫn planner. Vì vậy schema server có thể thay đổi hoặc AI gửi thiếu/sai kiểu mà vẫn chạm endpoint bên ngoài.
- Trước mỗi lần `call_tool`, adapter nay đọc lại danh sách công cụ/schema hiện tại, kiểm tra tool còn tồn tại và schema được hỗ trợ, rồi xác minh required/type/range/enum/unknown fields cục bộ. Từ chối trước khi gọi tool nếu không khớp; thêm trạng thái lỗi rõ cho discovery, missing tool, unsupported schema và invalid args.
- Thêm ba regression qua adapter/schema cho thiếu trường bắt buộc, boolean thay integer, vượt min/max, trường thừa và schema có pattern chưa hỗ trợ. Chưa chạy test suite; chưa đo độ tương thích với server Postman/MCP thật sau lần sửa. AI-11 vẫn mở cho event worker thật, quyền/audit, LangSmith trace và provider recovery.

### Xác minh API quyền mở rộng Test Case bằng MongoDB thật — 25/10/2026

- Chạy Testing API Docker với project và membership tạm trong MongoDB; dùng JWT ký bởi cấu hình service, không có `sid` nên ca này kiểm tra xác thực token và phân quyền API chứ không xác minh vòng đời phiên đăng nhập.
- Ma trận gồm BA, QA, BA+QA, Tester, Developer, Viewer và Admin không thuộc dự án. Project read trả 200 cho sáu thành viên và 403 cho Admin ngoài membership. Danh sách/quản lý trường Test Case và tạo trường chỉ trả 200/201 cho QA, BA+QA; năm role còn lại bị từ chối 403.
- Sau khi chạy, truy vấn xác nhận không còn project, membership, trường mở rộng hoặc audit thuộc project tạm. Đây là kiểm tra live API/database cho một quyền cụ thể, không đóng FE-01/AC-05 vì chưa bao phủ mọi API/action, phiên có `sid`, revoke hoặc giao diện các role.
