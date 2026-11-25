# Rà soát lại sản phẩm Veriq

**Trạng thái:** Khởi động lại phần phân tích nghiệp vụ. Tài liệu này chưa phải đặc tả đã được duyệt và chưa xác nhận chức năng nào đã hoạt động đúng.

**Nguyên tắc:** Code hiện tại chỉ dùng để tìm chỗ cần sửa, phụ thuộc và dữ liệu cần bảo toàn. Không suy ra nghiệp vụ đúng từ code đang có. Căn cứ nghiệp vụ gồm yêu cầu người dùng đã nêu, tài liệu ISTQB trong repo và tài liệu chính thức của ứng dụng tham khảo.

## 1. Mục đích sản phẩm nhìn từ người dùng

Veriq cần giúp một nhóm kiểm thử làm trọn các việc sau:

1. BA ghi yêu cầu và giữ được các phiên bản đã chốt.
2. Tester biết yêu cầu nào cần kiểm tra, tạo ca có thể thực hiện và truy được căn cứ.
3. Người phụ trách lập kế hoạch kiểm thử ngắn gọn, chọn phạm vi và điều kiện phù hợp.
4. Tester chạy các ca, lưu kết quả theo từng lần chạy, tạo hoặc nối lỗi khi cần.
5. Người xem biết phạm vi nào đã chạy, kết quả ra sao, còn ca hoặc lỗi nào chưa xử lý; có thể mở từ số liệu về dữ liệu gốc.
6. Khi yêu cầu đổi, người phụ trách biết Test Plan và Test Case nào cần xem lại; AI đưa đề xuất có căn cứ để người dùng quyết định.

Đây là mô tả nhu cầu sản phẩm suy ra từ các quyết định trong hội thoại, không phải kết quả khảo sát người dùng.

### Thứ tự dùng căn cứ khi có mâu thuẫn

1. Quyết định mới nhất mà người dùng đã chốt cho Veriq.
2. Nhu cầu và thao tác cần giải quyết trong luồng người dùng cụ thể.
3. ISTQB: dùng để kiểm tra thuật ngữ và nguyên tắc kiểm thử phù hợp ngữ cảnh; không biến mọi mục trong syllabus thành trường bắt buộc của sản phẩm.
4. Jira, Xray, TestRail: dùng làm ví dụ về cách giải quyết tác vụ; không sao chép toàn bộ mô hình hoặc mặc định mọi tính năng của họ đều cần cho Veriq.
5. Code và tài liệu nội bộ cũ: chỉ dùng để tìm dependency, dữ liệu, hành vi lệch và rủi ro khi sửa. Không dùng để quyết định nghiệp vụ đúng.

Tài liệu `LUONG_NGHIEP_VU_KIEM_THU.md` hiện có đề xuất nhập tài liệu thành Requirement, đưa Actor/Risk vào Requirement và dùng nhiều lớp tài sản kiểm thử. Các đề xuất đó mâu thuẫn với quyết định mới nhất ở mục 2. Chúng không được xem là yêu cầu hiện hành nếu chưa được người dùng xác nhận lại.

## 2. Những quyết định người dùng đã nêu

| Khu vực | Quyết định đang giữ làm căn cứ |
| --- | --- |
| Requirement | Không có Actor. Có lưu nháp và lưu yêu cầu. Tên, nội dung, AC, quy tắc nghiệp vụ và liên kết thiết kế/tài liệu thuộc phần tạo yêu cầu; AC, quy tắc và liên kết không được gọi là tùy chọn. Nhập danh sách bằng từng dòng có nút thêm/bớt. Ưu tiên và trạng thái nằm trong phần “Tùy chọn”. |
| Test Plan | Kế hoạch kiểm thử gọn cho dự án. Các phần mở rộng chỉ để tùy chọn khi có ích. Không thêm nội dung giải thích/tagline để lấp form. |
| Test Case | Không chia chế độ rút gọn/đầy đủ. Trường phụ để trong “Tùy chọn”. Không lặp Test Data hoặc Expected Result ở nhiều nơi. Luồng chính, thay thế và ngoại lệ là nội dung nhập; nếu không có thì để “-”. Không có trường rủi ro. |
| Test Run | Lưu kết quả theo lần chạy; khi Fail, có thể tạo Defect hoặc nối Defect có sẵn. Chạy lại phải giữ lịch sử lần trước. |
| Báo cáo | Có báo cáo tiến độ và hoàn tất; xuất PDF và Word. Mục Báo cáo đặt cạnh Thực thi kiểm thử. |
| Vai trò | BA, Tester, Admin. Không có Dev hoặc PM riêng. Admin/chủ dự án có toàn quyền và tự chốt nội dung do họ tạo theo quy tắc đã nêu. |
| AI | Giữ tóm tắt tài liệu và phân tích ảnh hưởng khi phiên bản Requirement đổi. Không tạo Requirement từ tài liệu; các luồng AI khác đã bị yêu cầu loại khỏi sản phẩm. |

Nếu tài liệu cũ hoặc code trái với bảng này, chúng là đối tượng cần rà, không phải căn cứ để tự khôi phục hành vi cũ.

## 3. Mô hình nghiệp vụ đề xuất

Đây là mô hình sản phẩm cần kiểm chứng với use case. Nó không được suy ra từ cách chia thư mục backend.

| Đối tượng | Việc người dùng cần làm | Ranh giới cần giữ |
| --- | --- | --- |
| Requirement và phiên bản | Ghi nội dung yêu cầu, lưu nháp hoặc chốt phiên bản, xem lịch sử. | Không có Actor. Tài liệu nguồn có thể đính kèm/tóm tắt; không tự biến nội dung tài liệu thành Requirement. |
| Test Plan | Ghi mục tiêu, phạm vi, các điều kiện và lựa chọn kiểm thử cần thiết. | Là tài liệu kế hoạch gọn. Không phải bảng điều khiển tiến độ hoặc nơi nhập lại kết quả đã chạy. Không có ô “Cách tiếp cận” chung chung. |
| Test Case | Mô tả kiểm tra có thể thực hiện lại, gồm bước và kết quả mong đợi, liên kết Requirement khi có căn cứ. | Là tài sản có thể dùng lại ở nhiều lần chạy hoặc phạm vi. Kết quả Pass/Fail không thuộc bản mô tả ca. |
| Test Run và kết quả | Chọn ca trong phạm vi, thực hiện tại một thời điểm/bối cảnh, ghi kết quả. | Mỗi lần chạy có dữ liệu riêng; không ghi đè kết quả cũ khi chạy lại. |
| Defect | Ghi nhận lỗi, trạng thái xử lý, mức độ và liên kết đến kết quả phát hiện lỗi. | Có mã và vòng đời riêng; Fail không bắt buộc tạo lỗi trùng. |
| Test Report | Tổng hợp theo phạm vi và thời điểm rõ ràng. | Số liệu phải lần được về Test Plan, Run, Case và Defect nguồn. |
| Tài liệu dự án | Lưu, đọc và tóm tắt nguồn tham khảo. | Là căn cứ cho người dùng; không tự tạo Requirement nếu người dùng chưa yêu cầu. |

## 3.1. Sơ đồ cần chốt trước khi build

Các sơ đồ sau là bản làm rõ nghiệp vụ để chuẩn bị thiết kế. Mũi tên là quan hệ cần có về mặt người dùng; chưa khẳng định API hay schema hiện tại đã đáp ứng.

### A. Luồng người dùng đầu-cuối

```mermaid
flowchart LR
  BA[BA ghi Requirement] --> RV{Lưu nháp hay chốt phiên bản?}
  RV -->|Nháp| R0[Requirement nháp]
  RV -->|Chốt| R1[Requirement version đã chốt]
  R1 --> TP[Tester lập Test Plan gọn]
  R1 --> TC[Tester tạo Test Case có căn cứ]
  TP --> CASES[Chọn Test Case trong phạm vi]
  TC --> CASES
  CASES --> RUN[Test Run theo lần thực thi]
  RUN --> RES[Kết quả từng Case]
  RES -->|Fail| DEF[Liên kết Defect mới/có sẵn]
  RES --> REPORT[Báo cáo tiến độ/hoàn tất]
  R1 -->|Có phiên bản mới| IMP[AI so sánh phiên bản và đề xuất ảnh hưởng]
  IMP --> HUMAN[Người dùng xem, sửa, chấp nhận hoặc bỏ đề xuất]
  HUMAN --> TP
  HUMAN --> TC
```

**Đã chốt:** lưu nháp/lưu chính cho Requirement, Test Plan, Test Case; kết quả Run giữ lịch sử; AI phân tích thay đổi đề xuất, không tự sửa tài liệu liên quan. **Cần đặc tả tiếp:** ai được chốt từng loại nội dung theo BA/Tester/Admin và trạng thái nào cho phép sửa sau khi chốt.

### B. Phân biệt các nghĩa của “giai đoạn”

```mermaid
flowchart TB
  P[Dự án] --> PERIOD[Chu kỳ kiểm thử, nếu cần<br/>Đợt 1 / Đợt UAT]
  PERIOD --> PLAN[Test Plan theo phạm vi chu kỳ]
  PLAN --> CASE[Test Case dùng lại]
  CASE --> RUN[Test Run ghi lần thực thi]
  RUN --> RESULTS[Kết quả gắn với Case version]
  RESULTS -->|Chưa xong và được chọn| NEXT[Plan ở chu kỳ tiếp theo]
  NEXT --> CASE
  LEVEL[Cấp kiểm thử: Component / Integration / System / Acceptance] -. phân loại phạm vi .-> TP[Test Plan hoặc Run]
  TYPE[Loại kiểm thử: Functional / Performance / Security] -. phân loại mục tiêu .-> TP
  RELEASE[Release/Milestone] -. mốc bàn giao, nếu cần .-> PLAN
```

**Nguyên tắc chốt:** Chu kỳ kiểm thử là nhóm tùy chọn để gom các Test Plan của một đợt kiểm thử. Tên như “Đợt 1” hoặc “UAT tháng 11” do người dùng đặt. Có thể ghi tên Sprint của nhóm nếu cần đối chiếu, nhưng đối tượng này không phải Sprint Scrum và không quản lý backlog, mục tiêu Sprint, năng lực hay velocity. Cấp và loại kiểm thử là cách phân loại hoạt động, không phải chu kỳ thời gian.

### C. Quan hệ dữ liệu nghiệp vụ

```mermaid
erDiagram
  PROJECT ||--o{ REQUIREMENT : contains
  REQUIREMENT ||--|{ REQUIREMENT_VERSION : versions
  REQUIREMENT_VERSION }o--o{ TEST_CASE_VERSION : validates
  PROJECT ||--o{ TEST_PERIOD : schedules
  TEST_PERIOD ||--o{ TEST_PLAN : contains
  TEST_PLAN ||--|{ TEST_PLAN_VERSION : versions
  TEST_PLAN_VERSION }o--o{ REQUIREMENT_VERSION : covers
  TEST_PLAN_VERSION }o--o{ TEST_CASE_VERSION : selects
  TEST_CASE ||--|{ TEST_CASE_VERSION : versions
  TEST_PLAN_VERSION ||--o{ TEST_RUN : authorizes
  TEST_RUN ||--|{ TEST_RESULT : records
  TEST_CASE_VERSION ||--o{ TEST_RESULT : executed_as
  TEST_RESULT }o--o{ DEFECT : reports
  TEST_RUN ||--o{ TEST_REPORT : summarizes
  TEST_PERIOD ||--o{ TEST_REPORT : summarizes
```

`TEST_PERIOD` là đối tượng **Chu kỳ kiểm thử** có thật trong mô hình, không phải nhãn tự nhập trên Test Case. Một chu kỳ có tên bắt buộc; mục tiêu và ngày dự kiến có thể để trống. Chu kỳ chứa các Test Plan theo phạm vi kiểm thử của đợt đó; Test Run thuộc Test Plan nên tự biết chu kỳ. Dự án vẫn có thể chạy Plan độc lập khi chưa dùng chu kỳ. Veriq quản lý chu kỳ kiểm thử, không giả làm công cụ Scrum đầy đủ.

### D. Ví dụ phần chưa xong ở đợt 1

```mermaid
flowchart LR
  C1[Test Case version X] --> R1[Run đợt 1]
  R1 --> P[Pass]
  R1 --> F[Fail]
  R1 --> N[Chưa chạy hoặc Blocked]
  F --> D[Defect được liên kết]
  D --> FIX[Defect được sửa]
  FIX --> RETEST[Run mới: retest Case X]
  N --> NEXT[Người dùng chọn vào Run đợt 2]
  P --> REG{Có thay đổi ảnh hưởng?}
  REG -->|Có| NEXT
  REG -->|Không| KEEP[Giữ kết quả đợt 1 làm lịch sử]
  RETEST --> HIST[Giữ cả kết quả cũ và mới]
  NEXT --> HIST
```

**Cách đọc:** ca Pass không tự chuyển đợt. Ca chưa chạy/Blocked có thể được chọn lại nếu vẫn nằm trong phạm vi. Ca Fail có Defect; sau khi sửa thì chạy lại cùng ca trong Run mới. Nếu thay đổi có thể ảnh hưởng ca đã Pass, người có trách nhiệm chọn thêm ca hồi quy. Không có thao tác nào xóa kết quả đợt 1.

### E. Bốn lớp dữ liệu không được nhập nhằng

| Lớp | Ví dụ | Câu hỏi nó trả lời |
| --- | --- | --- |
| Tài liệu chuẩn bị | Requirement, Test Plan, Test Case | Cần kiểm tra điều gì và dự định kiểm tra ra sao? |
| Tổ chức kiểm thử | Chu kỳ kiểm thử, nếu dự án dùng | Test Plan này thuộc đợt kiểm thử nào? |
| Thực thi | Test Run | Ai chạy ca nào, trên build/môi trường nào, vào lần nào? |
| Kết quả lịch sử | Test Result, Defect, Report | Lần chạy đó ra sao, lỗi nào phát sinh, tổng hợp theo phạm vi nào? |

Không đặt trạng thái Pass/Fail lên bản Test Case dùng lại; đó là trạng thái của kết quả trong một Run cụ thể.

### F. Ví dụ nghiệp vụ dùng để chốt cách xử lý đợt

Ví dụ này biến khái niệm “đợt 1/đợt 2” thành các quy tắc có thể kiểm tra. Nó là đề xuất để chuẩn bị build, không phải bằng chứng rằng code hiện tại đã làm đúng.

**Phạm vi:** một Test Plan đã chốt chọn 5 phiên bản Test Case cho một Requirement. Dự án tự đặt “Đợt 1” và “Đợt 2”. Nhóm Scrum có thể đặt tên đợt theo Sprint để tiện đối chiếu, nhưng Veriq không biến chu kỳ kiểm thử thành Sprint Scrum.

| Kết quả ở Run thuộc đợt 1 | Xử lý khi kết thúc đợt 1 | Có xuất hiện ở đợt 2 không? | Báo cáo phải thể hiện |
| --- | --- | --- | --- |
| 3 ca Pass | Giữ kết quả và phiên bản ca của Run 1. | Chỉ thêm lại nếu có lý do, như thay đổi liên quan cần regression. | Pass của Run 1; không tính thành kết quả Run 2. |
| 1 ca Fail, có Defect mở | Giữ Fail và liên kết Defect. Không coi ca đã đạt. | Khi có bản sửa, chọn cùng Test Case vào Run mới để retest; giữ liên kết đến Defect và Run nguồn. | Fail ở Run 1 và kết quả retest riêng ở Run 2; không ghi đè. |
| 1 ca chưa chạy | Giữ trạng thái chưa chạy của Run 1. | Người lập phạm vi Run 2 chọn lại nếu ca vẫn cần kiểm tra. | Chưa chạy ở Run 1; trạng thái mới chỉ đổi theo Run 2. |
| Ca bị Blocked (nếu có) | Giữ trạng thái, lý do và điều kiện chặn. | Chọn lại khi điều kiện chặn được xử lý; không tự chuyển khi chưa sẵn sàng. | Blocked theo Run nguồn và lần xử lý sau. |

**Quy tắc đếm:** báo cáo của Run 1 dùng đúng kết quả Run 1. Báo cáo của Run 2 dùng đúng kết quả Run 2. Tổng quan mới nhất theo Test Plan có thể dùng kết quả mới nhất của mỗi Test Case version, nhưng phải nói rõ đây là “mới nhất”, không cộng kết quả nhiều Run như thể đó là nhiều ca khác nhau. Báo cáo theo đợt tổng hợp các Run thuộc đợt ấy và vẫn cho mở chi tiết từng Run.

**Không làm trong phạm vi giai đoạn đầu:** tự động đưa toàn bộ Fail sang đợt sau; tự quyết định Pass Run 1 có cần regression không; tự gán ngày/Sprint theo lịch; quản lý backlog phát triển, velocity hoặc burndown kiểu Jira. Những việc này cần quy tắc dự án hoặc tích hợp riêng.

### G. Phạm vi tối thiểu có thể build cho “đợt”

| Câu hỏi sản phẩm | Hướng tối thiểu đề xuất | Vì sao |
| --- | --- | --- |
| Có xây giai đoạn không? | Có. Chu kỳ kiểm thử là đối tượng có thật trong sản phẩm. Cho phép Run độc lập cho kiểm tra ad hoc. | Người dùng cần lập kế hoạch theo đợt và biết phần nào tiếp tục ở đợt sau. |
| Chu kỳ nằm ở đâu? | Chu kỳ chứa một hoặc nhiều Test Plan; mỗi Test Plan thuộc tối đa một chu kỳ. | Chu kỳ thể hiện phạm vi thời gian; Test Plan mô tả kế hoạch cho phạm vi đó. |
| Test Case gắn với chu kỳ không? | Không gắn cứng. Test Plan chọn các Case cần dùng; cùng Case có thể xuất hiện trong nhiều Plan/chu kỳ. | Cho phép tái sử dụng và giữ lịch sử. |
| Một Test Plan cho mỗi đợt? | Có thể có nhiều Plan trong một chu kỳ, theo mục tiêu/phạm vi khác nhau. Khi sang chu kỳ mới, tạo Plan mới từ Plan cũ rồi rà lại. | Azure thường lập Plan cho Sprint/milestone; TestRail dùng Plan để gom nhiều Run/cấu hình. Không có một cấu trúc duy nhất cho mọi sản phẩm. |
| “Chuyển ca” nghĩa là gì? | Chọn lại phiên bản Test Case vào Run mới, có tham chiếu Run nguồn. Không xóa ca hoặc kết quả cũ. | Bảo toàn lịch sử và vẫn cho người dùng quyết định phạm vi. |
| Có tự chuyển ca chưa đạt sang đợt sau không? | Không. Khi đóng Sprint, người dùng quyết định ca nào cần chạy tiếp; hệ thống tạo/chọn Run mới và giữ kết quả cũ. | Jira/Azure chuyển work item chưa xong về backlog hoặc Sprint sau theo lựa chọn; không có nghĩa mọi Test Case Fail tự động chuyển. |
| Sprint Scrum có được quản lý không? | Không. Sprint Scrum thuộc backlog và work item; Chu kỳ kiểm thử chỉ gom kế hoạch kiểm thử. Nếu cần Scrum đầy đủ thì cần sản phẩm quản lý backlog và luật Sprint riêng. | Chỉ có ô “Sprint 1” không tạo thành hỗ trợ Scrum. |

**Quyết định thiết kế:** Chu kỳ kiểm thử là nhóm tùy chọn trong khu vực Thực thi kiểm thử. Chu kỳ gom các Test Plan; Plan chọn Requirement và Test Case; Run ghi nhận lần chạy và kế thừa chu kỳ qua Plan. Sang chu kỳ tiếp, người dùng tạo Plan mới, chọn lại các Case cần tiếp tục và xác nhận. Run ad hoc không gắn chu kỳ vẫn được phép. Veriq không nhận là công cụ quản lý Scrum đầy đủ.

### Quyết định chốt: Bộ kiểm thử, chu kỳ và quan hệ dữ liệu

| Khái niệm | Quyết định cho Veriq | Quan hệ và giới hạn |
| --- | --- | --- |
| Bộ kiểm thử / thư mục (Test Suite) | Tùy chọn. Dùng để nhóm Test Case theo chức năng như Đăng nhập hoặc Thanh toán. Người dùng có thể tạo ngay từ danh sách ca; không cần chuyển màn trước. Nếu có thư mục thì không tạo thêm một lớp nhóm thứ hai làm cùng việc. | Không chứa kết quả chạy, không thay Test Plan. Test Case vẫn được liên kết trực tiếp với Requirement và có thể được chọn vào nhiều Plan/Run. |
| Chu kỳ kiểm thử (Test Period) | Tùy chọn. Dùng khi cần gom kế hoạch theo một đợt như Đợt 1, UAT hoặc hồi quy. Không yêu cầu mọi dự án phải tạo chu kỳ. | Một chu kỳ có thể có nhiều Test Plan. Một Plan có tối đa một chu kỳ. Run lấy chu kỳ từ Plan. Requirement và Test Case không gắn cứng vào chu kỳ. |
| Test Plan | Tài liệu xác định mục tiêu và phạm vi sẽ kiểm thử. Đây là điểm chọn Requirement và phiên bản Test Case cho một đợt. | Có thể để ngoài chu kỳ. Không chứa kết quả thực thi. |
| Test Run | Một lần thực thi phạm vi đã chọn, ghi lại môi trường/build, người chạy và kết quả. | Kết quả cũ được giữ. Retest là lần chạy mới; không ghi đè kết quả trước. |
| Sprint Scrum | Không phải Chu kỳ kiểm thử. Veriq hiện không quản lý backlog hoặc vòng đời Sprint. | Có thể dùng tên Sprint trong tên chu kỳ để người dùng đối chiếu, nhưng không suy ra quan hệ Scrum hay tự chuyển Requirement. |
| Phase cũ | Dữ liệu lịch sử chưa được phân loại. Không hiện nó như Chu kỳ và không tự chuyển thành chu kỳ. | Chỉ migrate khi người quản trị xác nhận đích đến cụ thể. Giá trị `1` không đủ căn cứ để tạo “Chu kỳ 1”. |

**Luồng đã chốt:** Requirement ↔ Test Case để truy vết căn cứ; Test Plan chọn phạm vi; Test Suite/thư mục chỉ giúp sắp xếp Case; Chu kỳ tùy chọn gom Plan; Test Run ghi kết quả theo từng lần chạy; Báo cáo lọc từ Chu kỳ → Plan → Run. Không có quan hệ tự động Chu kỳ → Requirement hay Chu kỳ → Test Case.

**Căn cứ từ sản phẩm tham khảo:** Jira đặt Sprint quanh backlog và work item. Xray tách Test Set khỏi Test Plan/Execution. TestRail dùng suite/section để tổ chức Case và Plan để gom các Run. Zephyr dùng Test Cycle để gom Case cho thực thi và giữ lịch sử chạy. Đây là những cách khác nhau, không phải một chuẩn duy nhất. Veriq chọn suite/folder để sắp xếp Case, Plan để chọn phạm vi, và Chu kỳ kiểm thử tùy chọn để gom Plan. [Jira: Sprints](https://support.atlassian.com/jira-software-cloud/docs/enable-sprints/), [Xray: Test Sets và Test Plans](https://docs.getxray.app/space/XRAY/301474179/Test%20Sets%20vs%20Test%20Plans), [TestRail: Test suites](https://support.testrail.com/hc/en-us/articles/33359301314708-Test-suites), [TestRail: Test plans](https://support.testrail.com/hc/en-us/articles/30765296499604-Create-new-test-plans), [Zephyr: Test Cycles](https://support.smartbear.com/zephyr/docs/dc/test-cycles/).

**Dữ liệu dự án “Thư viện” trong ảnh:** Test Plan `TP-5918aecf08be48d48df3af91ecdccfa6` có `phase = "1"`, nhưng không có `test_period_id`; dự án không có bản ghi Test Period. Vì vậy `1` là dữ liệu Phase cũ, không phải chu kỳ đã tạo. Bảng kế hoạch trước đây lấy `phase` làm dự phòng cho cột “Chu kỳ kiểm thử”, gây hiển thị nhầm. Giao diện đã được sửa để chỉ hiện tên chu kỳ thật; nếu chưa liên kết thì hiện “—”. Phase cũ được giữ nguyên cho lịch sử và không tự migrate.

**Giao diện chu kỳ đã chốt:** trang mở ở danh sách chu kỳ; nút “Tạo chu kỳ” mở biểu mẫu ngay trên trang. Tên là trường chính duy nhất; mục tiêu và ngày dự kiến nằm trong “Tùy chọn”. Khi tạo từ một chu kỳ đã đóng, nguồn được lấy từ thao tác “Tạo chu kỳ tiếp theo”, không bắt người dùng chọn lại trong form. Chu kỳ thuộc mục Thực thi kiểm thử. Trạng thái rỗng vẫn giữ nút tạo ở đầu trang; không hiển thị form dài khi người dùng chỉ muốn xem danh sách.

**Cách chuyển phần việc sang đợt sau:** khi đóng chu kỳ, người dùng xem kết quả từng Run rồi chọn Case cần tiếp tục hoặc chạy hồi quy. Hệ thống đưa lựa chọn vào Plan/Run mới, lưu tham chiếu đến nguồn và giữ kết quả chu kỳ trước. Không tự chuyển tất cả Case Fail, không tự chuyển Requirement, không di chuyển Test Case khỏi thư mục và không xóa kết quả cũ.

```mermaid
flowchart LR
  DOC["Tài liệu nguồn<br/>(nếu có)"] --> REQ["Requirement<br/>và phiên bản"]
  REQ --> PLAN1["Test Plan<br/>kế hoạch kiểm thử"]
  REQ --> CASE["Test Case<br/>tái sử dụng"]
  PLAN1 --> CASE
  CASE --> RUN1["Test Run 1"]
  RUN1 --> RESULT1["Kết quả lần 1"]
  RESULT1 -->|Fail| DEFECT["Defect mới hoặc đã có"]
  RESULT1 -->|Cần tiếp tục ở đợt sau| RUN2["Test Run ở đợt sau"]
  CASE --> RUN2
  RUN2 --> RESULT2["Kết quả lần sau"]
  RESULT1 --> REPORT["Báo cáo theo Run<br/>và trạng thái mới nhất"]
  RESULT2 --> REPORT
```

Sơ đồ thể hiện hướng nghiệp vụ được đề xuất. Đợt sau tham chiếu lại Test Case; nó không xóa ca hoặc kết quả của đợt trước. Cách tổ chức Đợt kiểm thử vẫn cần được chốt ở mục 4.

## 4. Mô hình giai đoạn kiểm thử cần xây

Yêu cầu cần giải quyết là lập kế hoạch kiểm thử theo từng chu kỳ, xem phần nào đã chạy/chưa chạy/bị chặn/lỗi, rồi quyết định phần nào tiếp tục ở chu kỳ sau. Đây là năng lực cốt lõi cần có trong Veriq. Không gắn chu kỳ vào Test Case vì cùng một ca có thể được dùng trong nhiều chu kỳ.

| Khái niệm | Nghĩa trong quy trình | Dữ liệu thường được tổ chức |
| --- | --- | --- |
| Giai đoạn dự án (Phase) | Một chặng lớn do dự án định nghĩa, có thể theo phạm vi hoặc mốc bàn giao. Không nhất thiết có Sprint. | Có thể có nhiều Requirement, kế hoạch và đợt kiểm thử. |
| Chu kỳ kiểm thử (Veriq) | Một khoảng lập kế hoạch/kiểm thử do dự án đặt tên, có thể tương ứng Sprint, iteration, UAT hoặc một mốc bàn giao. | Chứa Test Plan của chu kỳ; Plan chọn Requirement và Test Case trong phạm vi. Người dùng quyết định phần nào tiếp tục ở chu kỳ sau. |
| Sprint Scrum | Một Sprint theo Scrum có mục tiêu và phạm vi công việc của nhóm. | Veriq có thể ghi nhận tên/mốc Sprint cho kiểm thử, nhưng không quản lý backlog, năng lực hay velocity nếu chưa xây các chức năng Scrum tương ứng. |
| Cấp kiểm thử (Test Level) | Nhóm hoạt động theo đối tượng kiểm tra, như Component, Integration, System, Acceptance. Đây không phải số thứ tự Sprint hay giai đoạn dự án. | Test Plan/Run có thể ghi cấp kiểm thử nếu cần phân biệt phạm vi. |
| Loại kiểm thử (Test Type) | Mục tiêu chất lượng như Functional, Performance, Security. Có thể diễn ra ở nhiều cấp kiểm thử. | Gắn với kế hoạch hoặc hoạt động kiểm thử, không dùng làm tên giai đoạn. |
| Test Run / Test Cycle | Một hoạt động chạy tập ca trong một bối cảnh cụ thể. Retest là lần chạy mới sau thay đổi; không phải Sprint mới. | Ca được chọn, người thực hiện, môi trường/build và kết quả thời điểm đó. |
| Release/Milestone | Mốc bàn giao hoặc phiên bản sản phẩm. Có thể bao gồm nhiều đợt và nhiều Test Run. | Gom tiến độ, phạm vi và báo cáo theo mốc khi dự án cần. |

ISTQB phân biệt cấp kiểm thử với loại kiểm thử. Jira quản lý Sprint ở cấp work item; Azure hướng dẫn lập Test Plan cho Sprint/milestone và dùng lại Test Case ở chu kỳ tiếp; TestRail dùng Test Plan để gom nhiều Run/cấu hình; Xray tách Test Plan khỏi Test Execution. Những mô hình này cho thấy cần có cách tổ chức theo chu kỳ và giữ lịch sử, nhưng không cho thấy một cấu trúc duy nhất. Veriq chọn mô hình phù hợp với tác vụ người dùng: Chu kỳ kiểm thử → Test Plan theo phạm vi chu kỳ → Test Case dùng lại → Test Run và kết quả. [Jira: Sprints](https://support.atlassian.com/jira-software-cloud/docs/enable-sprints/), [Azure: Test Plans by sprint/milestone](https://learn.microsoft.com/en-us/azure/devops/test/create-a-test-plan?view=azure-devops), [Azure: end-of-sprint work](https://learn.microsoft.com/en-us/azure/devops/boards/sprints/end-sprint-activities?view=azure-devops), [TestRail: plans and runs](https://support.testrail.com/hc/en-us/articles/7076810203028-Introduction-to-TestRail), [Xray: test workflows](https://docs.getxray.app/space/XRAYCLOUD/44567832/Using%2BJira%2Bworkflows%2Bfor%2Btesting%2Bpurposes).

### Quyết định thiết kế đề xuất cho Veriq

1. Chu kỳ kiểm thử là chức năng chính thức trong Thực thi kiểm thử, không phải trường text ở Test Case. Tên chu kỳ do người dùng đặt; không bắt chọn Scrum/Waterfall.
2. Mỗi Test Plan thuộc tối đa một Chu kỳ kiểm thử. Plan được tạo trong chu kỳ; có thể bắt đầu từ Plan trước bằng thao tác “Tạo kế hoạch cho chu kỳ mới”, sau đó người dùng rà lại phạm vi và tiêu chí. Không tự sao chép kết quả.
3. Test Case được dùng lại qua các Plan/chu kỳ. Khi chuyển sang chu kỳ mới, tạo Plan mới cho phạm vi chu kỳ đó và chọn lại các Case cần kiểm tra; không di chuyển hoặc sửa lịch sử Case cũ.
4. Test Run được tạo từ Plan, lưu môi trường/build và kết quả của lần chạy. Retest sau khi sửa lỗi vẫn là Run mới trong chu kỳ hiện tại hoặc chu kỳ sau; không ghi đè kết quả cũ.
5. Khi kết thúc chu kỳ, hệ thống tổng hợp Case Pass, Fail, Chưa chạy, Blocked và Defect mở. Người dùng chọn từng Case cần tiếp tục; Pass chỉ đưa sang chu kỳ tiếp nếu cần hồi quy. Hệ thống chuẩn bị Plan mới và danh sách Case được chọn để người dùng xác nhận.
6. Nếu dự án cần quản lý Sprint Scrum thật, phải có backlog, Requirement/công việc thuộc Sprint, mục tiêu và luật đóng Sprint. Nếu chưa xây các phần đó, giao diện chỉ gọi là “Chu kỳ kiểm thử”, không tuyên bố quản lý Scrum.
7. Báo cáo lọc theo Chu kỳ → Test Plan → Test Run; luôn giữ kết quả từng Run và thể hiện riêng trạng thái mới nhất. Không cộng nhiều lần chạy thành nhiều Test Case khác nhau.

Luồng đề xuất: đóng Chu kỳ 1 → xem tổng hợp và lý do chưa hoàn tất → tạo Chu kỳ 2 → tạo Test Plan mới từ kế hoạch trước → chọn lại các Case cần tiếp tục → tạo Run mới. Kết quả Chu kỳ 1 giữ nguyên. Không thêm `phase` dạng text vào Test Case và không tự chuyển tất cả ca.

## 5. Đối chiếu tác vụ với ứng dụng đang có

| Tác vụ người dùng | Cách ứng dụng tham khảo giải quyết | Điều Veriq cần học | Điều không nên sao chép máy móc |
| --- | --- | --- | --- |
| Nối yêu cầu, ca kiểm thử và lỗi | Jira cho phép liên kết các work item với loại quan hệ rõ và xem liên kết từ hai phía. Xray nối Requirement với Test và kết quả. | Liên kết phải mở được, truy ngược được và giải thích được độ bao phủ/tác động. | Không cần tạo một trang “truy vết” riêng nếu người dùng chỉ cần xem quan hệ trong Requirement, Case hoặc Report. |
| Tách thiết kế ca với kết quả chạy | Xray để Test mô tả ca và Test Execution lưu hoạt động chạy. TestRail cũng tách Case, Run, Test Result. | Giữ định nghĩa Test Case tách khỏi Result của Run; chạy lại tạo Result mới. | Không thêm toàn bộ Test, Precondition, Test Set, Data Set và automation nếu use case Veriq không cần. |
| Gắn kiểm thử với Sprint/Iteration | Azure Test Plans có Test Plan, Test Suite và Test Case; suite có thể gom theo Sprint, Feature, Milestone hoặc Requirement. Requirement-based suite lọc work item theo Iteration Path. | Nếu Veriq cần Scrum thật, phạm vi Sprint nên lấy từ đối tượng Sprint/Iteration và Requirement/Work Item; không tạo trường Sprint nhập tự do ở Test Case. | Không sao chép cấu trúc nhiều tầng Plan/Suite nếu người dùng Veriq chỉ cần kế hoạch gọn và Run. |
| Chia hoạt động kiểm thử thành đợt | Zephyr dùng Test Cycle làm tập ca theo mục tiêu; cycle có thể nằm dưới Test Plan/release hoặc không gắn release, và lần thực thi lưu riêng để xem lịch sử. Một số bản Zephyr hỗ trợ chạy ad hoc không cần Cycle. | Một “Đợt kiểm thử” chỉ đáng có nếu cần nhóm nhiều Run, phân công hoặc báo cáo theo đợt; chạy lại vẫn là execution mới của cùng Test Case. | Không bắt buộc mọi thao tác tạo Cycle trước khi chạy test; không thêm cycle nếu một Run đáp ứng use case. |
| Chia phạm vi theo đợt | Jira chuyển work item chưa xong sang backlog/Sprint khác; Xray theo dõi Test qua nhiều Test Execution; TestRail có Milestone và Plan để nhóm Run theo những cách riêng. | Không xóa lịch sử Test Case/Result. Cần báo cáo được đợt trước và tiếp tục chọn Case trong Run đợt sau. | Không đồng nhất Phase/Sprint/Test Level/Test Type/Run; không bắt mọi dự án theo Scrum; không sao chép nguyên cấu trúc Plan của hãng khác. |
| Báo cáo | Xray/TestRail hiển thị trạng thái theo Plan/Run và cho lần từ tổng quan đến ca/lỗi. | Mỗi báo cáo ghi rõ phạm vi, thời điểm, kết quả chưa chạy/đang chặn/lỗi mở và đường về dữ liệu nguồn. | Không tạo nhiều dashboard/báo cáo nếu chúng lặp cùng một số liệu nhưng dùng phạm vi khác nhau. |

### Tài liệu tham khảo chính thức

- ISTQB, [CTFL Syllabus v4.0.1](https://www.istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf), đặc biệt mục 5.1.1–5.1.2 về Test Plan và iteration/release planning, cùng mục 5.3 về theo dõi và báo cáo.
- Atlassian, [Enable sprints and complete a sprint](https://support.atlassian.com/jira-software-cloud/docs/enable-sprints/).
- Microsoft, [Create and manage test suites in Azure Test Plans](https://learn.microsoft.com/en-us/azure/devops/test/create-test-suites?view=azure-devops) và [Test Plans overview](https://learn.microsoft.com/azure/devops/test/overview?preserve-view=true&view=azure-devops).
- Xray, [Test Sets vs Test Plans](https://docs.getxray.app/space/XRAY/301474179/Test%20Sets%20vs%20Test%20Plans), [Planning Tests](https://docs.getxray.app/space/XRAY/301403858), [Adopting Xray for Hardware Testing](https://docs.getxray.app/space/XRAYCLOUD/1853849616/Adopting%2BXray%2Bfor%2BHardware%2BTesting).
- Zephyr/SmartBear, [Test Cycles](https://support.smartbear.com/zephyr/docs/dc/test-cycles/), [Executing in Test Cycles](https://support.smartbear.com/zephyr/docs/essential-dc/executing-tests/executing-in-test-cycles/), [Zephyr test planning](https://support.smartbear.com/zephyr/docs/enterprise/zephyr-enterprise/zephyr-user-guide/test-planning/).
- TestRail, [Introduction to TestRail](https://support.testrail.com/hc/en-us/articles/7076810203028-Introduction-to-TestRail), [Test plans](https://support.testrail.com/hc/en-us/articles/30765296499604-Create-new-test-plans), [Test runs and results](https://support.testrail.com/hc/en-us/articles/32784099933844-Best-Practices-Guide-Test-Runs-and-Results).

## 6. Rà hiện trạng code — chỉ ghi lệch, không lấy làm yêu cầu

Các điểm dưới đây là vị trí cần điều tra/sửa. Chúng không chứng minh thiết kế hiện tại là đúng.

| Khu vực | Bằng chứng trong working tree | Vấn đề cần giải quyết từ góc nhìn người dùng |
| --- | --- | --- |
| Điều hướng | `navigation.js`, `AppShell.jsx`, `ProjectWorkspacePage.jsx` khai báo nhóm menu và route cho Requirement, Plan, Case, Run, Defect, Report, tài liệu; đồng thời còn route cho phân tích, dữ liệu, bộ kiểm thử, automation, giám sát, truy vết, release và cài đặt. | Người dùng có thể thấy nhiều khu vực hoặc vào được route cũ dù chức năng đã bị yêu cầu thu gọn. Cần chốt màn hình theo tác vụ rồi lần mọi đường vào, không chỉ ẩn một mục menu. |
| Requirement | Form trong `RequirementCreateModal.jsx` đánh dấu Tên, AC, quy tắc và liên kết tài liệu là bắt buộc; nội dung chưa có dấu bắt buộc. `RequirementCreate` còn `risk`, và `type` vẫn bắt buộc trong schema dù form không cho chọn (form tự đặt “Chưa phân loại”). Backend lưu chính hiện kiểm tra AC, quy tắc, liên kết; chưa kiểm tra nội dung rỗng. | Lệch giữa quyết định bỏ Risk, biểu mẫu, schema và validation. Cần làm rõ `type` chỉ là phân loại mặc định hay trường người dùng cần; bỏ Risk tận gốc sau khi rà caller/lịch sử; đồng bộ nội dung và dấu `*` với lưu chính. |
| Test Plan | `TestPlanEditor.jsx` có textarea `Cách tiếp cận`; một input môi trường tự do, ghi chú browser/device và Test Data, đồng thời có dropdown `Môi trường đã cấu hình` bị giấu trong phần Liên kết. Schema lưu cả text environment lẫn environment ID. Form còn có trường phase, lựa chọn Case, ca chuyển tiếp từ Run và gợi ý AI. Backend còn nhiều trường kế hoạch mở rộng. | Có dữ liệu môi trường nhập hai cách và thông tin lặp; dữ liệu test bị nhập ở Plan dù đã có trong Case; selector môi trường khó thấy; “Cách tiếp cận” mơ hồ và lặp với lựa chọn loại/kỹ thuật. Người dùng báo khó tìm Cài đặt dự án. Cần một selector môi trường duy nhất, dữ liệu môi trường cấu hình một lần và được chọn lại. Bỏ textarea riêng và Test Data Plan sau khi rà phụ thuộc. |
| Test Case | `TestCaseCreateForm.jsx` có Cách viết ca ở trước phần “Tùy chọn”; trong tùy chọn còn loại, ưu tiên, cấp kiểm thử, điều kiện, luồng, kỹ thuật và liên kết. Schema còn `risk`, `flow_type`, Test Data cấp ca và Expected Result cấp ca ngoài cấu trúc từng bước. | Có lệch rõ với vị trí Cách viết ca, yêu cầu bỏ Risk/enum luồng và tránh dữ liệu lặp. Xóa field chỉ sau khi rà generator, serializer, linter, query, transfer, import/export và dữ liệu lịch sử. |
| Test Run | `ExecutionPage.jsx`, `RunExecutionWorkspace.jsx` và `test_run.py` tạo Run từ Plan, lưu kết quả, tạo/nối Defect và có luồng chạy lại ca Fail. | Cần phân biệt tạo Run, chạy tiếp, chạy lại sau sửa và chuyển phạm vi sang giai đoạn mới. Không được dùng cùng một thao tác cho cả bốn việc. |
| Phase/carry-over | Schema/service có `phase` ở Plan, lưu phase vào snapshot Run, và cho thêm ca từ Run nguồn sang Plan khác. Một nhánh rerun riêng chỉ nhận ca Fail được chọn. | Hai luồng “chạy lại ca Fail” và “chuyển ca chưa xong sang phạm vi tiếp theo” đang khác nhau. Cần thiết kế lại quanh hành động người dùng và lịch sử; code hiện tại không phải đáp án nghiệp vụ. |
| Báo cáo | Báo cáo gọn tạo Tiến độ/Hoàn tất và xuất PDF/Word. API, service và AI của các workflow Status Report/Completion cũ đã được gỡ. Giữ quyền đọc tệp đính kèm lịch sử và không xóa collection/dữ liệu cũ. | Còn rà quyền lưu trong ACL cũ và xác nhận màn xuất chỉ lấy dữ liệu từ nguồn hiện hành. Không để workflow cũ quay lại qua route hay chức năng AI. |
| AI và tài liệu | Còn nhiều module/API/UI AI ngoài tóm tắt tài liệu và phân tích phiên bản; import Requirement từ tài liệu vẫn còn trong mã. | Cần call graph và dependency map trước khi gỡ tận gốc. Giữ đọc/tóm tắt tài liệu; không tạo Requirement từ tài liệu và không giữ AI phụ đã bị loại. |
| Quyền và vai trò | API giới hạn vai trò dự án ở `BA`, `TESTER`, `SYSTEM_ADMIN`; quyền cụ thể được nạp từ cấu hình DB. Chủ dự án và system admin được mở rộng quyền trong `project_membership_permissions`. Phê duyệt tự động dựa vào system admin/chủ dự án. Màn quản lý quyền đang liệt kê nhiều mã permission theo nhóm kỹ thuật; phần quyền chi tiết nằm trong một disclosure lồng nhau. | Tên quyền khó hiểu và không cho thấy ngay người dùng làm được việc gì. Cần lập ma trận theo tác vụ BA/Tester/Admin, kiểm tra từng API với ma trận đó và tách “vai trò”, “người chịu trách nhiệm” khỏi quyền kỹ thuật. Không nên chỉnh ma trận bằng cách đoán từ giao diện hoặc dữ liệu quyền cũ. |
| Tài liệu nội bộ | `LUONG_NGHIEP_VU_KIEM_THU.md`, `TOM_TAT_QUY_TRINH_VERIQ.md`, `FRAMEWORK_VERIQ.md` viết ở các thời điểm/phạm vi khác nhau. | Có mô tả AI, vai trò và quy trình cũ trái với lựa chọn mới. Phải đánh dấu lịch sử hoặc cập nhật; không trộn thành một quy trình bắt buộc. |

## 7. Kế hoạch làm lại để người dùng dùng được

### Bước 1 — Chốt mô hình nghiệp vụ và sơ đồ

Vẽ một sơ đồ duy nhất cho các đối tượng và vòng đời: Requirement/version → Test Plan/phạm vi giai đoạn → Test Case → Run/Result → Defect/Report. Ghi rõ đối tượng nào là tài liệu, đối tượng nào là lần chạy, quan hệ nào tái sử dụng, trạng thái nào cho phép chuyển tiếp.

**Điều kiện hoàn tất:** mỗi quan hệ trả lời được người dùng cần làm gì, dữ liệu thuộc đâu, ai cập nhật, lịch sử nào được giữ. Không thêm trường chỉ để khớp tên trong ISTQB hoặc ứng dụng khác.

### Bước 2 — Dựng lại luồng người dùng bằng ví dụ thật

Đi qua một ví dụ xuyên suốt: BA tạo Requirement; Tester lập kế hoạch cho phạm vi/giai đoạn 1; chọn và chạy Case; một số ca chưa chạy hoặc Fail; mở phạm vi/giai đoạn tiếp theo; chạy lại; xem báo cáo tiến độ và hoàn tất. Thêm ví dụ Requirement đổi phiên bản và xem tác động đến Plan/Case.

**Điều kiện hoàn tất:** người dùng biết bước tiếp theo ngay trên màn hiện tại; không phải nhập một dữ liệu hai lần; có đường đi cho nháp, lỗi, hủy, thử lại và dữ liệu chưa có.

### Bước 3 — Chốt hợp đồng backend và dữ liệu

Cho từng hành động, ghi route, permission, input/output, trạng thái trước/sau, validation, nguồn dữ liệu, snapshot/version, idempotency và migration. Lần tất cả caller, query, report, export, AI, worker và dữ liệu cũ trước khi xóa field/module.

**Điều kiện hoàn tất:** field nào cũng có chủ sở hữu; lưu nháp và lưu chính có quy tắc rõ; kết quả Run cũ không bị thay đổi; quyền BA/Tester/Admin nhất quán.

Riêng quyền truy cập, đặc tả cần dùng động từ nghiệp vụ dễ hiểu như “Tạo yêu cầu”, “Chốt yêu cầu”, “Soạn kế hoạch”, “Chạy ca kiểm thử”, “Ghi nhận lỗi”, “Xuất báo cáo”. Mã permission chỉ là cách thực thi ở backend, không phải nội dung chính trên màn hình người dùng. Phải xác định rõ System Admin toàn nền tảng, chủ dự án và thành viên có vai trò BA/Tester là các khái niệm nào; không gộp chúng thành một cột “Admin” nếu quyền và phạm vi khác nhau.

### Bước 4 — Sửa theo luồng đầu-cuối

Ưu tiên theo thứ tự người dùng làm việc: Requirement và phiên bản; Test Plan và chia phạm vi; Test Case; Run/Defect/chuyển tiếp; Report; quyền/tài liệu/AI. Với mỗi luồng, sửa backend contract, frontend, migration và tài liệu trong cùng lát cắt.

**Điều kiện hoàn tất:** màn hình, API và dữ liệu thể hiện cùng một workflow. Chỉ ẩn route không được tính là đã bỏ tính năng. Chỉ gỡ code sau khi không còn dependency và dữ liệu lịch sử vẫn đọc được.

### Bước 5 — Kiểm tra nghiệm thu

Sau khi người dùng yêu cầu kiểm tra, xác minh từng tác vụ đầu-cuối trên giao diện và API, gồm quyền, dữ liệu nháp, lưu chính, phiên bản, chuyển tiếp, rerun, defect, report/export và lỗi dịch vụ. Ghi kết quả quan sát được, không dùng test tự viết làm bằng chứng thay cho workflow thực.

## 8. Trạng thái chắc chắn hiện nay

- Đã xác định được những quyết định sản phẩm người dùng đã nêu và một số mâu thuẫn rõ giữa quyết định, tài liệu cũ và code.
- Đã đối chiếu CTFL v4.0 trong repo với tài liệu chính thức Jira, Xray, Azure Test Plans, Zephyr và TestRail về Test Plan, Sprint/Iteration, Cycle, Run, kết quả và chạy lại.
- Chưa hoàn tất kiểm kê mọi form/API/schema/worker, quyền, migration, report aggregation và hành vi giao diện đang chạy.
- Chưa có sơ đồ nghiệp vụ cuối cùng được duyệt; chưa sửa code trong lượt rà soát này.

**Không được kết luận sản phẩm đã dùng được hoặc đã sẵn sàng sửa hàng loạt.** Bản phân tích chỉ được coi là hoàn tất khi các phần còn thiếu trong Bước 1–3 có bằng chứng và mâu thuẫn được giải quyết trước khi triển khai.

## 9. Xác minh cách các công cụ xử lý giai đoạn

Đối chiếu tài liệu chính thức của ISTQB, Azure Test Plans, Zephyr, TestRail và Jira cho thấy không có một cấu trúc duy nhất gọi là “giai đoạn” áp dụng cho mọi dự án.

| Nguồn | Cách tổ chức được tài liệu mô tả | Bài học áp dụng cho Veriq |
| --- | --- | --- |
| ISTQB CTFL v4.0 trong repo | Phân biệt cấp kiểm thử, loại kiểm thử và kỹ thuật. Kiểm thử có thể kết thúc tại mốc release, cuối iteration hoặc khi hoàn tất một cấp kiểm thử; khi kết thúc, nhóm ghi nhận defect/backlog còn lại và báo cáo hoàn tất. | “Giai đoạn” theo thời gian không đồng nghĩa với Test Level. Tạo báo cáo ở mốc kết thúc là hợp lý; bắt mọi dự án theo cùng chuỗi giai đoạn thì không có căn cứ. |
| Azure Test Plans | Test Plan chứa Test Suite; suite có thể nhóm theo Requirement, Sprint/Iteration, Feature hoặc dùng bộ lọc. Test Case có thể được dùng lại; Test Run và kết quả lưu từng lần thực thi. | Với nhóm Scrum, Requirement/Work Item có thể nối với Iteration, còn Case gắn với Requirement và Run. Không cần gắn cứng Test Case vào duy nhất một Sprint. |
| Zephyr | Test Cycle là tập ca cho một mục tiêu thực thi; kết quả liên kết với cycle. Có thể tạo lần execution mới cho cùng ca và xem dữ liệu execution cũ. Một số luồng hỗ trợ thực thi ad hoc không cần cycle. | “Đợt kiểm thử” hữu ích để nhóm các lần chạy có kế hoạch, nhưng không nên bắt buộc cho chạy nhanh hoặc mọi dự án. |
| TestRail | Test Plan có thể nhóm nhiều Run/cấu hình; Milestone có thể đại diện mốc release. Tài liệu khuyên dùng Case cũ trong Run mới thay vì copy Case chỉ để chạy vòng khác. | Giữ Case ổn định, mỗi lần chạy có Result riêng. Test Plan của hãng là container Run, khác lựa chọn Test Plan gọn của Veriq. |
| Jira Scrum | Khi đóng Sprint, work item chưa hoàn tất được đưa về backlog hoặc Sprint khác. | Nếu Veriq hỗ trợ Scrum đầy đủ thì Sprint quản lý Requirement/công việc; không coi Test Case là work item để chuyển khỏi Sprint cũ. |

### Kết luận thiết kế cho Veriq

1. Chu kỳ kiểm thử là đối tượng cấp một và có khu vực riêng trong Thực thi kiểm thử. Mỗi chu kỳ gom các Test Plan theo mục tiêu/phạm vi của chu kỳ.
2. Test Plan trong chu kỳ xác định Requirement và Test Case cần kiểm tra. Với chu kỳ mới, tạo Plan mới từ Plan cũ để tái dùng liên kết và nội dung phù hợp; người dùng rà phạm vi trước khi lưu.
3. Test Case không thuộc độc quyền một chu kỳ. Cùng Case có thể được chọn trong nhiều Plan/chu kỳ mà không bị sao chép.
4. Test Run lưu một lần thực thi thuộc Plan; Test Result lưu kết quả theo Test Case version. Không nhập Pass/Fail vào bản Test Case dùng lại.
5. Khi kết thúc chu kỳ, hệ thống tổng hợp trạng thái; người dùng chọn ca chưa chạy/Blocked/Fail cần tiếp tục. Retest sau sửa lỗi vẫn tạo Run mới và liên kết Defect. Ca Pass chỉ chọn lại nếu cần regression.
6. Không tự chuyển ca hoặc tự tạo chu kỳ kế tiếp. Hệ thống có thể chuẩn bị danh sách đề xuất từ trạng thái cũ, nhưng người dùng xem và xác nhận Plan mới.

## 10. Luồng sản phẩm từ đầu đến cuối và giao diện đề xuất

Đây là bản thiết kế nghiệp vụ/UX để review trước khi code. Dấu `*` là trường chặn thao tác chính; trường khác được lưu khi có dữ liệu và không chặn luồng nếu dự án không dùng.

### 10.1 Điều hướng chính

```text
Dự án
├── Tổng quan
├── Yêu cầu
├── Kế hoạch kiểm thử
├── Ca kiểm thử
├── Thực thi kiểm thử
├── Báo cáo
├── Tài liệu
└── Cài đặt dự án (qua biểu tượng bánh răng, theo quyền)
```

- **Thực thi kiểm thử** chứa danh sách Đợt, Test Run, kết quả và Defect liên kết; không tách màn “Theo dõi” riêng.
- **Chu kỳ kiểm thử** là dữ liệu để gom Plan/Run, nhưng không đặt thành mục điều hướng chính riêng. Người dùng quản lý chu kỳ và lọc Plan ngay từ khu vực **Kế hoạch kiểm thử**.
- **Tài liệu** là nơi tải và đọc tài liệu; AI tóm tắt nằm ngay trong chi tiết tài liệu.
- **Cài đặt dự án** cần có lối vào nhìn thấy được từ tiêu đề dự án. Khu vực này giữ danh mục môi trường và thành viên; không để cấu hình môi trường nằm ở một route khó tìm hoặc trong Quản lý tài khoản nền tảng.
- **Phân tích ảnh hưởng** nằm trong trang phiên bản Requirement. Tạo phiên bản mới sẽ tự chạy so sánh văn bản; chỉ khi khác nội dung mới gọi AI. Kết quả gắn với đúng phiên bản, Plan, Case và bằng chứng nguồn. Người dùng quyết định có cập nhật tài liệu liên quan hay không.
- Không để menu riêng cho Test Analysis, Test Data, Test Scenario, AI Runs, Automation hay Traceability nếu các tác vụ đó không nằm trong phạm vi Veriq đã chốt. Truy vết cần thiết hiển thị ngay tại Requirement, Case, Run, Defect và Report.

### 10.2 Trang Yêu cầu

| Khu vực | Trường / thao tác | Quy tắc hiển thị |
| --- | --- | --- |
| Danh sách | Mã hệ thống, tên, trạng thái hiện hành, phiên bản, ưu tiên nếu có, người cập nhật | Tìm kiếm/lọc trong trang; không cần tách một trang truy vết. |
| Nội dung chính | Tên*; Nội dung* | Hai trường đủ để tạo yêu cầu dùng được. Không có Actor. |
| Tiêu chí chấp nhận | Danh sách dòng, nút `+` thêm và `−` xóa | Hiện ngay trên form, không giấu trong accordion “Tùy chọn”. Khi có tiêu chí thì từng dòng có thể truy vết và kiểm thử; không tự bịa tiêu chí. |
| Quy tắc nghiệp vụ | Danh sách dòng, `+`/`−` | Giữ riêng khi Requirement có quy tắc rõ; không gộp trùng vào nội dung. |
| Thiết kế/tài liệu liên quan | Chọn tài liệu hoặc nhập liên kết | Hiện ngay trên form để người viết bổ sung căn cứ; không tạo nguồn giả nếu không có. |
| Tùy chọn | Ưu tiên; trạng thái theo quy trình | Ưu tiên High/Medium/Low hoặc chưa đánh giá. Trạng thái do workflow quản lý, không phải chuỗi tự nhập. Không có Risk tại Requirement. |
| Lưu | `Lưu nháp`; `Lưu yêu cầu` | Nháp không trở thành baseline. Lưu yêu cầu tạo bản chính/đưa vào rà soát theo quyền; Admin/chủ dự án tự chốt nội dung của họ như người dùng đã chọn. |

**Điểm cần thể hiện rõ:** sau “Lưu yêu cầu”, trang phải nói chính xác trạng thái là “Đã chốt” hay “Chờ rà soát”; không được lưu thành nháp rồi gọi là bản chính.

AC, Quy tắc nghiệp vụ và Thiết kế/tài liệu liên quan phải hiện trực tiếp trên form, không nằm trong nhóm “Tùy chọn” và không có chữ “Tùy chọn” gắn cạnh tiêu đề. Chỉ Tên và Nội dung có `*` mặc định. Người viết thêm AC/quy tắc/link khi yêu cầu có thông tin tương ứng; không chặn lưu chỉ vì tài liệu nguồn không có AC hoặc không có link thiết kế.

### 10.3 Trang Kế hoạch kiểm thử

| Khu vực | Trường | Quy tắc |
| --- | --- | --- |
| Chính | Chu kỳ kiểm thử; Tên kế hoạch*; Mục tiêu*; Yêu cầu trong phạm vi* | Khi tạo trong Chu kỳ, chu kỳ được gắn tự động. Nếu tạo từ danh sách chung, chọn một Chu kỳ hoặc chọn “Không thuộc chu kỳ” cho kế hoạch ad hoc. Chọn Requirement version có sẵn làm phạm vi chính. |
| Mở rộng | Phạm vi ngoài | Chỉ ghi phần bị loại khỏi phạm vi, nếu có. |
| Phân loại (Tùy chọn) | Loại kiểm thử; cấp kiểm thử; kỹ thuật thiết kế test | Loại và kỹ thuật có thể chọn nhiều giá trị vì một kế hoạch có thể bao phủ nhiều mục tiêu/phương pháp. Hiển thị lựa chọn trực tiếp, không cho nhập tự do. Loại (Functional, Non-functional, White-box, Change-related) khác kỹ thuật cụ thể (Equivalence Partitioning, Boundary Value Analysis, Decision Table, State Transition, Statement/Branch Coverage, Error Guessing). Không có ô văn bản “Cách tiếp cận kiểm thử” chung chung; không bắt chọn đủ các trường. |
| Môi trường dự kiến | Chọn một hoặc nhiều môi trường đã cấu hình trong dự án | Không nhập tên môi trường, trình duyệt, thiết bị hoặc cấu hình bằng văn bản tự do ở đây. Môi trường được tạo một lần trong Cài đặt dự án và được chọn lại. Nếu chưa có môi trường, ô hiển thị `-` và vẫn dùng được; có đường dẫn tới nơi cấu hình nếu người dùng có quyền. |
| Điều kiện | Entry Criteria; Exit Criteria | Nội dung theo dòng, thêm/bớt khi cần. Không tự đặt tiêu chí Critical/High nếu kế hoạch không có. |
| Lịch và người phụ trách | Bắt đầu/kết thúc dự kiến; người phụ trách | Phần mở rộng, không bắt điền nếu nhóm chưa lập lịch. Mỗi nhãn và ô nhập ở dòng riêng, cùng chiều rộng hợp lý. |
| Rủi ro | Rủi ro ↔ Cách ứng phó | Phần mở rộng; thêm cặp dòng bằng `+`/`−`. Không dùng Risk ở Requirement hoặc Test Case. |
| Lưu | `Lưu nháp`; `Lưu kế hoạch` | Lưu chính tạo trạng thái dùng được hoặc chờ duyệt theo quyền; không hiển thị “đã duyệt” giả. |

Mình rút lại đề xuất có trường nhập riêng “Cách tiếp cận kiểm thử”. CTFL nêu test approach trong nội dung thường gặp của Test Plan, nhưng không bắt sản phẩm phải có một textarea riêng. Trong Veriq, mục tiêu, Requirement nằm trong phạm vi, lựa chọn loại/cấp/kỹ thuật và điều kiện mô tả kế hoạch đủ rõ hơn, không cần thêm một ô văn bản chung dễ lặp lại. [CTFL 4.0.1, mục 5.1](https://www.istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf), [Azure configurations](https://learn.microsoft.com/en-us/azure/devops/test/new-test-plans-page?view=azure-devops), [TestRail configurations](https://support.testrail.com/hc/en-us/articles/23043143013268-Configurations)

Danh mục loại kiểm thử và kỹ thuật lấy theo CTFL, không phải tên tự nhập. `White-box` là một trong các test types được syllabus dùng; `Black-box` không phải một loại riêng trong danh sách test types đó. Các kỹ thuật hiển thị bằng tên kỹ thuật cụ thể để tránh đưa checkbox “Black-box/White-box” vào cả hai nhóm. [CTFL 4.0, mục 2.2 và 4](https://www.istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf)

### 10.4 Trang Thư viện ca kiểm thử

| Khu vực | Trường / thao tác | Quy tắc |
| --- | --- | --- |
| Chính | Tiêu đề*; các bước*; kết quả mong đợi* | Data nằm cùng bước thực hiện để tránh lặp cột Test Data; kết quả mong đợi nằm ở bước tương ứng, không có bản thứ hai ở cuối form. |
| Luồng | Luồng chính; luồng thay thế; luồng ngoại lệ | Đều là nội dung nhập. Nếu không có luồng thay thế/ngoại lệ thì hiển thị `-`; không dùng dropdown chọn loại luồng. |
| Liên kết | Requirement/AC liên quan | Chọn nguồn đã có để biết ca này kiểm tra điều gì; không nhập lại nội dung Requirement. |
| Tùy chọn | Tiền điều kiện; hậu điều kiện; loại kiểm thử nếu ca đặc thù; cấp kiểm thử; ưu tiên; cách viết Manual/BDD; người phụ trách | Nằm trong một vùng “Tùy chọn” duy nhất. Chỉ giữ field có tác vụ sử dụng cụ thể. Không có Risk. |
| Mã và trạng thái | Mã ca do hệ thống định danh; trạng thái vòng đời của bản ca nếu dùng phê duyệt | Mã không phải ô nhập trong form. Pass/Fail/Blocked thuộc kết quả Run, không thuộc trạng thái định nghĩa Test Case. |
| Lưu | `Lưu nháp`; `Lưu ca kiểm thử` | Giữ bản nháp tách với phiên bản ca được dùng trong Test Run. |

### 10.5 Trang Thực thi kiểm thử — gợi ý bố cục

```text
Thực thi kiểm thử                         [+ Tạo lần chạy]

[Đợt kiểm thử ▼] [Kế hoạch ▼] [Trạng thái ▼] [Tìm ca / mã Run]

ĐỢT 2 · Kiểm thử đăng nhập bản 1.2                 [Mở đợt]
  RUN-08  Kế hoạch xác thực  ·  Staging  ·  8/10 hoàn tất  [Tiếp tục]
  RUN-09  Kiểm tra hồi quy       ·  Chrome   ·  5/5 hoàn tất  [Xem]

ĐỢT 1 · Phạm vi đăng nhập bản 1.1                   [Xem lịch sử]
  RUN-04  3 Pass · 1 Fail · 1 Chưa chạy                     [Xem]
```

**Tạo Chu kỳ kiểm thử:** tên chu kỳ*; mục tiêu/phạm vi ngắn; ngày bắt đầu/kết thúc dự kiến nếu đã biết. Không bắt chọn loại Scrum/Waterfall và không bắt đặt ngày. Trạng thái hiển thị `Sắp diễn ra / Đang thực hiện / Đã đóng`; lần chạy đầu đưa chu kỳ sang “Đang thực hiện”, còn “Đã đóng” chỉ xảy ra khi người dùng chủ động đóng sau bước rà soát. Quá ngày không tự đóng. Có thể liên kết Release/Milestone đã cấu hình nếu dự án dùng.

**Tạo Test Plan trong chu kỳ:** tên*; mục tiêu*; Requirement/phiên bản trong phạm vi; Test Case version được chọn; tiêu chí kiểm thử/hoàn tất. Với chu kỳ tiếp theo, nút `Tạo từ chu kỳ trước` sao chép phần khung và liên kết nguồn; người dùng phải rà rồi lưu Plan mới. Không sao chép kết quả Run.

**Đóng Chu kỳ:** hệ thống hiện tổng kết theo Plan/Run và nhóm ca `Pass`, `Fail`, `Chưa chạy`, `Blocked`, Defect đang mở. Người đóng chọn `Tạo chu kỳ tiếp theo` và chọn các ca cần tiếp tục. Ca Pass không được chọn sẵn; ca Fail chỉ đưa vào retest theo xử lý Defect; ca chưa chạy/Blocked được chọn sau khi rà nguyên nhân. Tạo bước tiếp theo sẽ tạo Chu kỳ và Plan mới ở trạng thái nháp, giữ liên kết tới chu kỳ/Run nguồn. Không di chuyển hoặc ghi đè kết quả cũ.

**Tạo Test Run:** tên Run*; Test Plan*; môi trường thực tế chọn từ môi trường đã cấu hình; build/release chọn từ danh mục nếu có; người chạy chọn từ thành viên đang hoạt động. Run nhận Chu kỳ từ Test Plan. Nếu danh mục chưa có giá trị thì hiển thị `-`, không khóa form và không bắt nhập nhãn thay thế. Danh sách Case kế thừa từ Plan; cho phép rà và bỏ/chọn ca trước khi tạo Run.

**Trong Run:** mỗi dòng hiển thị mã/tên Case, bước và kết quả mong đợi ở chế độ đọc, trạng thái thực thi, Actual Result và liên kết Defect. Khi Fail, cho `Tạo lỗi` hoặc `Liên kết lỗi có sẵn`; không tự tạo Defect trùng. Bằng chứng là phần mở rộng. Khi sửa lỗi xong, `Chạy lại ca` tạo execution mới, giữ execution trước đó.

### 10.6 Trang Báo cáo

Hai báo cáo đã được người dùng chọn: **Tiến độ** và **Hoàn tất**. Bộ lọc trên cùng: Chu kỳ kiểm thử, Test Plan, khoảng thời gian/Run. Nút xuất: PDF, Word.

| Báo cáo | Nội dung tối thiểu |
| --- | --- |
| Tiến độ | Phạm vi, số Case cần chạy, Pass/Fail/Blocked/Chưa chạy, tiến độ theo Run hoặc Chu kỳ, Defect đang mở; bấm từng số mở danh sách nguồn đã lưu cùng báo cáo. |
| Hoàn tất | Phạm vi và thời điểm chốt, Run được tính, kết quả, Defect còn mở, điều kiện Exit Criteria của Plan và kết luận. Nếu điều kiện chưa đạt, nêu rõ; không tự kết luận cho phép phát hành. Số liệu có thể mở danh sách Case/Defect nguồn. |

Khi xem báo cáo đã lưu, API chi tiết trả về danh sách Case theo trạng thái và Defect liên kết, gồm Test Run nguồn khi có. Danh sách báo cáo chỉ trả phần tóm tắt để tránh tải lặp các hàng chi tiết. Báo cáo giữ snapshot nguồn tại thời điểm tạo; giới hạn 5.000 Case và 5.000 Defect chi tiết cho mỗi báo cáo để tránh tạo tài liệu vượt dung lượng lưu trữ. Báo cáo cũ chưa lưu danh sách nguồn vẫn mở được nhưng không thể dựng lại chính xác từ dữ liệu đã thay đổi.

Không tạo thêm báo cáo AI, tổng quan trùng số liệu hoặc luồng ký duyệt release mới nếu chưa có quyết định nghiệp vụ tương ứng.

### 10.7 Trang Tài liệu và AI

```text
Tài liệu
[Tải tài liệu lên]

Tên tài liệu | Loại | Ngày cập nhật | Trạng thái xử lý | Tóm tắt
```

Tải tài liệu không sinh Requirement. AI chỉ tóm tắt tài liệu và phân tích ảnh hưởng khi Requirement có phiên bản mới. Phân tích thay đổi chạy Text Diff trước; bỏ qua thay đổi chỉ do khoảng trắng/format; nếu nội dung đổi, tìm Plan/Case có liên kết trực tiếp rồi mới gọi AI. AI trả về đề xuất theo đối tượng, kèm phần Requirement đổi và căn cứ liên kết. Người dùng mở từng đề xuất để cập nhật hoặc bỏ; AI không tự ghi đè Plan/Case.

### 10.8 Ma trận vai trò ở mức tác vụ

Đây là ma trận ban đầu theo ba vai trò đã chốt; cần kiểm tra lại từng API và scope trước khi triển khai. Admin/chủ dự án có quyền toàn dự án theo quyết định của người dùng.

| Tác vụ | BA | Tester | Admin/chủ dự án |
| --- | --- | --- | --- |
| Tạo/sửa Requirement nháp | Có | Xem/nhận xét | Có |
| Chốt Requirement | Gửi rà soát | Xem/nhận xét | Chốt; nội dung do chính họ tạo được tự chốt |
| Tạo/sửa Test Plan | Xem/nhận xét | Có | Có và tự chốt nội dung mình tạo |
| Tạo/sửa Test Case | Xem/nhận xét | Có | Có và tự chốt nội dung mình tạo |
| Tạo Run, ghi kết quả | Xem | Có | Có |
| Tạo/liên kết Defect, retest | Xác nhận nghiệp vụ khi cần | Có | Có |
| Xem/xuất Report | Xem | Có | Có |
| Tải tài liệu/tóm tắt/impact | Theo quyền dự án | Theo quyền dự án | Có |

**Quy tắc chống tự duyệt:** Admin/chủ dự án được tự chốt nội dung của họ theo quyết định đã nêu. Tác giả BA/Tester không tự duyệt nội dung của chính mình nếu quy trình cần duyệt độc lập; nếu dự án không có người duyệt phù hợp thì trạng thái phải nói rõ đang chờ ai, không lặng lẽ cho tự duyệt.

### 10.9 Kiểm tra từng trường: chọn danh mục hay nhập nội dung?

| Dữ liệu | Cách nhập đúng | Không nên làm |
| --- | --- | --- |
| Môi trường | Select từ môi trường đã cấu hình trong dự án. Test Plan chọn môi trường dự kiến; Run ghi môi trường thực tế và có thể lấy mặc định từ Plan. | Hai ô trùng nghĩa “Môi trường” tự nhập và “Môi trường đã cấu hình”; bắt viết lại browser/device nếu đã nằm trong cấu hình. |
| Browser/device/platform | Chọn từ cấu hình đã đặt tên, chỉ khi cần chạy cùng ca trên nhiều nền tảng. Nếu không quản lý nhiều tổ hợp, chỉ chọn môi trường. | Nhập đoạn văn bản khác nhau ở mỗi Plan/Run, khiến báo cáo không lọc hoặc so sánh được. |
| Test Data | Ghi tại bước Test Case tương ứng. Nếu dùng lại dữ liệu bảo mật, tham chiếu kho được bảo vệ thay vì dán secret vào tài liệu. | Trường Test Data cấp Plan và trường thứ hai cấp Test Case cùng chứa một dữ liệu. |
| Build/Release | Select từ build/release đã đăng ký; giữ ID và snapshot tên vào Run. Nếu chưa có, hiển thị `-` và cho phép tiếp tục theo chính sách dự án. | Textbox tự do ở mỗi Run khiến cùng một build bị ghi bằng nhiều tên khác nhau. |
| Người phụ trách/người chạy | Select thành viên đang hoạt động trong dự án; chưa phân công thì `-`. | Nhập tên tùy ý, người ngoài dự án hoặc tài khoản không hoạt động. |
| Ngày | Date/time picker; kế hoạch ghi ngày dự kiến, Run giữ thời gian thực tế. | Nhập ngày tự do hoặc dùng một khoảng lịch chung thay cho thời điểm từng lần chạy. |
| Trạng thái | Chọn giá trị workflow được định nghĩa. Kết quả thực thi do Run cập nhật. | Một trạng thái nhập tay hoặc gộp Draft/Approved của tài liệu với Pass/Fail của Run. |
| Loại/kỹ thuật/cấp kiểm thử | Select từ danh sách chuẩn; chỉ chọn khi cần phân loại/lọc/báo cáo. | Textbox tùy ý tạo nhiều biến thể thuật ngữ; đưa Black-box/White-box ở hai trường mà không phân biệt cách dùng. |
| Requirement, AC, Test Case | Tìm và chọn object/version có sẵn, hiển thị ID và tên. | Nhập ID bằng tay hoặc chọn tên mà không cố định version nguồn. |

### 10.10 Những điểm cần sửa khỏi bản thiết kế trước

- Bỏ ô nhập tay Môi trường, ô ghi chú browser/device trùng cấu hình và ghi chú Test Data trên Test Plan. Dùng môi trường đã cấu hình; Test Data nằm ở bước Case.
- Bỏ textarea “Cách tiếp cận kiểm thử” riêng. Giữ bộ chọn loại/kỹ thuật/cấp nếu thật sự dùng; để trống nếu chưa xác định.
- Dùng Requirement version đã chọn làm phạm vi chính của Test Plan; tránh vừa gõ Phạm vi trong vừa chọn lại các Requirement đó.
- Bỏ checkbox cứng “0 lỗi Critical/High”; nếu nhóm muốn ngưỡng đó thì ghi thành Exit Criteria của đúng kế hoạch.
- Không bắt tạo Test Suite nếu nó chỉ là thư mục. Không chọn Suite lẫn toàn bộ Case con vào cùng Plan nếu gây đếm đôi.
- Môi trường, build, release, người dùng, trạng thái và liên kết nội bộ lấy từ danh mục. Nếu chưa có dữ liệu, hiện `-`; không disable ô hoặc buộc nhập nhãn thay thế.

### 10.11 Giao diện cấu hình và chọn môi trường

```text
Cài đặt dự án  >  Môi trường                       [+ Thêm môi trường]

Tên môi trường       Địa chỉ (nếu có)       Tình trạng
Test                 https://test.example   Sẵn sàng
UAT                  https://uat.example    Bảo trì
```

Từ tiêu đề dự án có biểu tượng cài đặt mở thẳng `Cài đặt dự án`; đây không phải trang “Quản lý tài khoản”. Trong cấu hình ban đầu chỉ cần tên môi trường*, URL nếu có và tình trạng chọn từ danh sách. Không bắt người dùng nhập JSON hoặc một chuỗi `environment_type` tùy ý. Chỉ thêm các chi tiết như hệ điều hành, thiết bị hay trình duyệt nếu một dự án thật sự cần lọc/chạy cùng Test Case trên các cấu hình đó. Khi cần nhiều biến thể, biểu diễn chúng thành các cấu hình có tên để chọn, không ghi thành văn bản tự do ở mỗi Run.

Trong form Test Plan, một bộ chọn `Môi trường dự kiến` có thể chọn nhiều cấu hình trực tiếp. Trong form Run, chọn đúng một `Môi trường thực thi`; nếu cần chạy cùng tập ca trên hai môi trường thì tạo hai Run trong cùng Đợt. Khi danh mục rỗng, select vẫn hoạt động và hiện `-`, kèm đường dẫn “Cấu hình môi trường” cho người có quyền. Không tự tạo sẵn Dev/Staging/Prod vì như vậy có thể bịa môi trường không tồn tại trong dự án.

Tài liệu công cụ xác nhận cách làm này: Azure gán cấu hình ở Test Suite và có thể để cấu hình ở cấp Test Case ghi đè; TestRail tạo nhóm cấu hình trong phạm vi dự án rồi chọn chúng cho Run; Zephyr quản lý Environment qua cấu hình và liên kết Environment với hoạt động test. Đây là bằng chứng để dùng danh mục chọn lại, không phải yêu cầu sao chép hết cấu hình nâng cao của họ. [Azure](https://learn.microsoft.com/en-us/azure/devops/test/new-test-plans-page?view=azure-devops), [TestRail](https://support.testrail.com/hc/en-us/articles/23043143013268-Configurations), [Zephyr](https://support.smartbear.com/zephyr/docs/cloud/configuration/advanced-customization-options/environments-labels-and-iterations/)

### 10.12 Rà thêm những điểm dễ làm giao diện rối

- Chỉ để một nhóm “Tùy chọn” cho mỗi form; không đặt thêm nhóm tùy chọn lồng bên trong.
- Mỗi quan hệ dữ liệu phải là picker có tìm kiếm và hiển thị mã + tên + phiên bản; không dùng input text để nhập ID.
- Danh mục chưa có dữ liệu phải hiện `-` và đường dẫn cấu hình phù hợp; người không đủ quyền vẫn xem được trạng thái nhưng không thấy nút quản lý.
- Tách “người phụ trách kế hoạch”, “người chạy Run” và “người được giao sửa Defect”; ba vai trò này là ba tác vụ khác nhau, nhưng đều chọn từ thành viên dự án.
- Tách trạng thái vòng đời tài liệu khỏi kết quả chạy; kết quả được lưu ở từng execution, không sửa Test Case gốc.
- Chỉ cho nhập tay dữ liệu người dùng thực sự định nghĩa như tên, mục tiêu, nội dung, bước test, actual result, lý do và ghi chú; các danh mục dùng chung phải được cấu hình một lần rồi chọn lại.
- Nếu một trường không giúp tạo, thực thi, truy vết, ra quyết định hoặc báo cáo thì bỏ khỏi màn hình; không giữ chỉ vì backend hiện có field đó.

### 10.12.1 Kiểm tra vị trí Chu kỳ qua công cụ thực tế

Không có một quy ước chung rằng Chu kỳ/Sprint phải là tab điều hướng riêng trong mọi công cụ:

- Jira đặt Sprint trong Backlog/board; người dùng tạo, lập kế hoạch, bắt đầu và hoàn tất Sprint tại đó.
- Azure Test Plans gắn Test Plan với iteration path và khuyến nghị tạo Plan theo Sprint/release; chu kỳ là ngữ cảnh của Plan, không phải một tab “Cycle” độc lập.
- Xray có Test Plan như một thực thể kiểm thử riêng; Plan bao các Test Execution và gắn với version/sprint context.
- TestRail có Milestones riêng ở dự án và cho liên kết Test Plan/Test Run với Milestone.

Các công cụ khác nhau về mô hình và cách đặt menu. Vì vậy Veriq giữ quan hệ Chu kỳ trong dữ liệu, nhưng bỏ Chu kỳ khỏi điều hướng chính; người dùng vào **Quản lý chu kỳ** từ trang Kế hoạch và chọn Chu kỳ tại bộ lọc/biểu mẫu Plan. Đây là lựa chọn giao diện cho luồng đã chốt, không phải tuyên bố rằng mọi sản phẩm đều thiết kế như vậy.

Nguồn chính thức: [Jira Sprints](https://support.atlassian.com/jira-software-cloud/docs/use-your-scrum-backlog/), [Azure Test Plans theo Sprint/iteration](https://learn.microsoft.com/en-us/azure/devops/test/create-a-test-plan?view=azure-devops), [Xray Test Sets và Test Plans](https://docs.getxray.app/space/XRAY/301474179/Test%20Sets%20vs%20Test%20Plans), [TestRail Milestones](https://support.testrail.com/hc/en-us/articles/15545364561044-Milestones).

### 10.13 Đối chiếu màn hình, hợp đồng API và quyết định trường

Phần này là kiểm tra trên các form và schema chính trong working tree tại thời điểm rà soát. Nó trả lời trường đang xuất hiện ở đâu và phải xử lý thế nào. Schema cũ là bằng chứng có dữ liệu/phụ thuộc cần rà; không phải lý do giữ trường trên giao diện. Mục 6 là ảnh chụp hiện trạng ban đầu trước các thay đổi sau đó; khi hai mục khác nhau, dùng mục 10.13 và bảng tiến độ 12.6 làm trạng thái mới nhất.

| Màn hình | Hiện trạng giao diện và API | Quyết định nghiệp vụ | Hành động thiết kế/backend |
| --- | --- | --- | --- |
| Tạo Requirement | Form hiện giữ Tên, Nội dung, AC, Quy tắc và Liên kết ở phần chính; AC/Quy tắc/Liên kết không còn bắt buộc ở giao diện và bước lưu/chốt; Nội dung và Tên bắt buộc. Đã bỏ Risk khỏi form, write contract, luồng import và version writer. `type` vẫn được gán mặc định “Chưa phân loại” và dùng để lọc custom fields. | Không có Actor/Risk. AC, quy tắc và link được nhập khi có; không chặn lưu nếu thiếu. Ưu tiên là lựa chọn; trạng thái theo dõi do người dùng cập nhật. | Quyết định bỏ `type`/custom field phân loại hay cung cấp danh mục có ý nghĩa; hiện giá trị mặc định ẩn chưa giải thích. Dọn reader legacy của Risk và cập nhật đúng nhãn * cho Tên/Nội dung ở các màn sửa/version. Xem riêng việc chuyển link sang nhiều dòng và gắn tài liệu đã tải lên. |
| Chu kỳ kiểm thử | Entity, schema/API, quyền và trang Chu kỳ đã có. Plan/Run mới đọc `test_period_id`; chuỗi phase cũ còn ở compatibility reader/hash và script kiểm kê. Đóng chu kỳ chặn khi còn Run mở, lưu số liệu tổng kết tại thời điểm đóng và danh sách ca được chọn chuyển; Plan chưa duyệt không được đưa vào tổng kết. Sửa kết quả hoặc liên kết/trạng thái Defect trong chu kỳ mở làm tăng revision để ngăn chốt trên dữ liệu cũ. | Chu kỳ là đối tượng riêng, Plan thuộc Chu kỳ, Case có thể dùng lại. Đóng Chu kỳ phải tổng hợp rồi để người dùng chọn Case sang Plan mới. | Hoàn thiện quy tắc khóa sau khi đóng qua mọi endpoint liên quan; rà retry/concurrency với DB thực tế. Rà và chạy migration dry-run trên bản sao dữ liệu trước backfill. |
| Tạo Test Plan | Form hiện có Tên, Chu kỳ, Mục tiêu, Requirement trong phạm vi, Ngoài phạm vi; nhóm Phân loại kiểm thử (Loại, Cấp, Kỹ thuật); môi trường chọn từ danh mục; tiêu chí bắt đầu/kết thúc; các phần mở rộng về phạm vi Case, ước lượng, lịch, rủi ro và liên lạc. Khi chọn Chu kỳ có ca chuyển tiếp, form đưa các ca đó vào phạm vi Case. Không còn ô Phase tự nhập, Cách tiếp cận chung, Test Data ở Plan hay môi trường tự nhập. | Giữ Chu kỳ là đối tượng; Plan lưu Requirement version và Case version; môi trường lấy từ cấu hình. Loại/Cấp/Kỹ thuật là trường riêng, có danh mục. Ca chuyển tiếp phải theo quyết định đóng Chu kỳ. | Rà xem các trường mở rộng ở Plan có đang tạo tác vụ cần thiết hay chỉ làm form dài; xác nhận tiêu chí chặn gửi duyệt và snapshot các phiên bản. Kiểm tra việc tạo nhiều Plan trong một Chu kỳ và ca chuyển tiếp tự thêm vào Plan. |
| Tạo Test Case | Form có Tên, Ước lượng và bước kiểm thử ở phần chính. Cách viết, loại, module, ưu tiên, cấp kiểm thử và liên kết nằm trong Tùy chọn. Data/Kết quả mong đợi nhập theo bước. Khi chọn BDD, form hiện Feature/Scenario/Given/When/Then riêng. Contract tạo/sửa không còn nhận `test_data` và `expected_result_doc` cấp Case. Reader chuyển dữ liệu lịch sử vào bước đầu; writer dọn dữ liệu cấp Case khi người dùng sửa, duyệt hoặc tạo phiên bản. `scenario_id` cùng entity Scenario riêng vẫn tồn tại, gồm Risk/Ưu tiên bắt buộc. | Data/Expected chỉ có một nguồn theo bước; không bắt entity Scenario riêng trong luồng tạo thông thường; Risk và luồng chính/thay thế/ngoại lệ không thuộc trường Test Case mới theo quyết định đã chốt. | Rà bỏ tận gốc field cấp Case trùng bước; quyết định giữ hay gỡ Scenario entity và đường `scenario_id`; kiểm tra generator, BDD, review, import/export, search và lịch sử trước khi xóa schema cũ. |
| Tạo Test Run | Form cho chọn Plan, chu kỳ có thể lấy theo Plan; môi trường chọn từ danh mục; có luồng chọn phạm vi và tạo/retest Run. Danh sách cũ còn hiển thị `phase` làm fallback tương thích. Backend vẫn cho phép Run không gắn Plan và nhận một số trường legacy. | Run kiểm thử theo kế hoạch cần giữ snapshot Plan/Cycle/Case; kết quả thuộc lần chạy. Rerun tạo execution mới. | Chốt và đồng bộ đường Run độc lập với mục tiêu của Veriq; rà field legacy text/ID, nguồn Suite/Case, quyền và thay đổi Plan/Run khi Chu kỳ đóng. Chỉ bỏ fallback phase sau khi dữ liệu cũ được đối soát. |
| Thực thi từng Case và Defect | `TestResultInput` lưu status, kết quả thực tế, kết quả từng bước, attachments và note; có API nối Defect. | Đây là dữ liệu động riêng của mỗi Run. Fail có thể tạo Defect hoặc nối Defect hiện có. Retest tạo execution mới. | Giữ kết quả theo Test Case version và Run; không ghi lên Test Case gốc. Đảm bảo nguồn retest/carry-over và Defect được truy ngược ở report. |
| Báo cáo | Màn hiện có Tiến độ/Hoàn tất, lọc Chu kỳ/Plan/Run, xuất PDF/Word; số liệu trong màn xem mở được danh sách Case/Defect snapshot. API ghi mới của workflow Monitoring/Completion cũ đã gỡ; collection và reader tệp đính kèm lịch sử còn giữ. | Giữ hai loại báo cáo đã chốt và nguồn số liệu snapshot. | Rà ACL cũ; kiểm tra nội dung PDF/Word và quyền export; kiểm tra report cũ chưa có snapshot chi tiết. |
| Cài đặt môi trường | Form cấu hình chỉ nhập Tên*, URL nếu có và tình trạng khả dụng. API và giao diện không còn yêu cầu loại môi trường, JSON capabilities hoặc secret refs; giá trị cũ vẫn nằm trong DB nhưng bị ẩn khỏi phản hồi. | Người dùng cấu hình môi trường một lần, rồi chọn trong Plan/Run. Không ép họ nhập JSON hoặc tự nghĩ ra loại môi trường. | Form cấu hình trước mắt chỉ cần Tên*; URL và tình trạng nếu có tác vụ. Các trường capabilities và secret refs không có consumer ở luồng môi trường; đã bỏ khỏi form, API ghi mới và route cập nhật secret refs. Giá trị legacy vẫn được che khi đọc; chưa xóa dữ liệu lịch sử. |

#### Quy tắc trường sau khi đối chiếu

- Dấu `*` chỉ đặt ở trường chặn thao tác chính. Trường có thể thiếu theo nghiệp vụ thì không ép bằng HTML `required`, validator hoặc rule ẩn.
- Danh mục rỗng hiển thị `-`; cho phép tiếp tục nếu trường không bắt buộc. Có quyền thì hiện lối vào cấu hình ngay cạnh selector.
- ID liên kết không gõ tay. Backend nhận ID; giao diện hiển thị mã/tên/phiên bản. Tên snapshot chỉ dùng để giữ lịch sử.
- Không lưu cùng ý nghĩa ở nhiều cấp: Environment ID và text environment; Requirement links và scope text; Test Data/Expected Result theo bước và cấp Test Case; phase text ở Plan và Run.
- Khi một trường bị loại, trước tiên lập danh sách reader/writer: form, create/patch schema, service, database query/index, AI prompt/output, import/export, report, search, audit event, role permission và migration. Chỉ xóa tận gốc sau khi từng phụ thuộc có phương án thay thế hoặc được xác nhận không dùng.

#### Luồng Requirement → Chu kỳ → Plan → Case → Run cần có trước khi sửa code

```text
Tạo Requirement và chốt phiên bản
  → Tạo Chu kỳ 1
  → Tạo Test Plan nháp, chọn Requirement versions và tiêu chí
  → Thiết kế Test Case từ Requirement/Plan, chọn Case versions vào Plan
  → Gửi duyệt Plan, tạo Run, chạy Case và ghi Result/Defect
  → Đóng chu kỳ: xem tổng kết và tự chọn Case cần tiếp tục
  → Tạo Chu kỳ 2 và Plan mới từ Plan 1
  → Rà lại phạm vi, tạo Run mới, giữ nguyên toàn bộ lịch sử cũ
```

**Phần rà soát đã hoàn tất ở mức thiết kế:** đã đối chiếu các form chính của Requirement, Test Plan, Test Case, Test Run, Result/Defect, Report và Environment với schema/API tương ứng; đã ghi quyết định giữ/bỏ/chuyển và các phụ thuộc cần kiểm tra. **Chưa hoàn tất để bắt đầu xóa code:** chưa lần hết mọi reader/writer, worker, truy vấn báo cáo, quyền, import/export, index và dữ liệu lịch sử của từng trường. Đó là bước kiểm kê kỹ thuật tiếp theo, không được suy đoán từ form.

### 10.14 Kết quả rà phụ thuộc lần đầu

Tìm kiếm tham chiếu trong frontend/backend cho thấy một số trường chạm nhiều luồng. Không được xóa bằng cách chỉ bỏ input hoặc bỏ field khỏi schema.

| Trường/khái niệm | Nơi đang được đọc/ghi | Cách xử lý an toàn |
| --- | --- | --- |
| `phase` | Contract mới không nhận `phase` trong Test Plan/Run. Snapshot/hash tương thích và dữ liệu cũ vẫn có thể chứa trường này; UI chỉ hiển thị fallback cho Run cũ. Script dry-run kiểm kê các nhóm phase. | Không ghi phase mới. Chỉ chuyển phase cũ sang Cycle sau khi người quản trị xác nhận mapping; giữ snapshot/hash cũ cho đến khi không còn cần đọc. Không nhầm `phase` nội bộ của AI/document job. |
| `carry_over_items` | Chọn ca ở trang đóng Chu kỳ; Plan mới lấy các lựa chọn đã chốt từ Cycle. Ca có Run dùng nguồn Run; ca chưa có kết quả dùng Run chứa ca nếu có, nếu chưa có Run thì dùng Plan nguồn. Backend kiểm tra nguồn, Cycle và phiên bản Case. | Giữ nguồn, Case version, lý do và trạng thái nguồn trong Cycle; Plan nhận danh sách đó và không yêu cầu nhập lại trạng thái Run. Cần xác minh giao diện Plan hiển thị đúng toàn bộ Case chuyển tiếp trước khi lưu. |
| `risk` ở Requirement | Requirement schema và `requirement_records.py` còn lưu/đọc. Risk xuất hiện ở các luồng chuyển/import và có thể dùng trong phân tích. | Bỏ khỏi nội dung Requirement theo quyết định người dùng, nhưng rà importer, bản cũ, AI prompt, API response và report trước. Không áp quyết định này lên Risk Register của Test Plan hoặc residual risk của báo cáo nếu hai tác vụ đó vẫn được duyệt. |
| `risk` ở Test Case/Scenario | Test Case query/transfer/lifecycle/generation và monitoring snapshot còn đọc/ghi risk; Scenario có risk/priority bắt buộc trong schema và bộ lọc riêng. | Bỏ Risk khỏi form/schema Test Case theo quyết định trước; xác định Scenario có còn là thực thể trong sản phẩm hay sẽ bị gộp/bỏ. Nếu bỏ Scenario thì dọn toàn bộ risk/priority/actor/route/query của nó cùng luồng Scenario, không chỉ xóa field trên Test Case. |
| `risk_register` ở Test Plan | Plan snapshot/service/AI context; risk-register pair được dùng ở form Plan. | Giữ Risk ↔ Cách ứng phó ở Test Plan nếu đúng yêu cầu đã chốt. Không nhầm nó với Risk của Requirement/Test Case hoặc rủi ro còn lại ở báo cáo hoàn tất. |
| `test_data` và `expected_result` | Test Case mới ghi theo bước; draft cũ được chuẩn hóa ở màn sửa, so sánh, sao chép, tạo phiên bản và import. Một số schema/reader cấp Case còn để tương thích BDD và dữ liệu lịch sử. | Tiếp tục rà BDD, review và các consumer còn đọc field cấp Case. Chỉ xóa schema sau khi mọi bản cũ có adapter; không xóa dữ liệu lịch sử bằng migration suy đoán. Dataset chỉ giữ nếu còn tác vụ tái sử dụng rõ. |
| `environment` và `environment_id` | Form/API Plan, Run và Defect chọn `environment_id`; service lấy tên từ cấu hình. Kết quả và Defect lịch sử vẫn đọc nhãn snapshot cũ. | Không nhận tên môi trường tự nhập ở write API; giữ nhãn lịch sử để báo cáo cũ không đổi theo cấu hình. Khi cập nhật bản ghi cũ mà không đổi môi trường, giữ nguyên nhãn snapshot cũ. |
| `test_approach`, `scope_in`, `environment_notes` | Contract/form Plan mới không dùng các trường này. Reader chỉ còn compatibility hash, Requirement Impact snapshot cũ, và fallback để đọc/hiển thị báo cáo từ Plan lịch sử. | Giữ reader lịch sử cho đến khi xác nhận không còn snapshot/báo cáo phụ thuộc; phạm vi báo cáo mới lấy nhãn từ Requirement versions trong Plan snapshot. Không thêm lại vào form Plan. |
| `test_suite_ids` cùng `test_case_version_ids` | Plan/Run nhận cả hai; service mở Suite thành các Case version rồi khử trùng lặp, kiểm tra Case nằm trong snapshot Plan. | Đây chưa phải lỗi đếm đôi ở service hiện tại. Nhưng UI không nên bắt người dùng chọn cả Suite lẫn Case. Chốt Suite có còn là thư mục hữu ích không; nếu bỏ thì giữ trực tiếp Case version và cập nhật API/export sau khi thay scope. |
| Báo cáo rủi ro/giám sát cũ | Monitoring snapshot tính risk coverage; Completion có residual-risk decisions; status report có period/evidence/review workflow. | Đây là các workflow tách biệt và đang rộng hơn hai báo cáo Tiến độ/Hoàn tất đã chốt. Trước khi dọn, xác định chính xác phần nào xuất hiện trong hai report và phần nào là màn/menu/API dư; bảo toàn dữ liệu đã tạo nếu còn được report đọc. |

Đây mới là **bản đồ phụ thuộc lần đầu**, không phải xác nhận có thể xóa ngay. Các vùng Scenario, Dataset, AI generation, Monitoring và Completion có luồng độc lập; phải rà route/API/permission và dữ liệu trước khi quyết định gộp hay bỏ. Các mục đang dùng field `phase` trong xử lý tài liệu AI là checkpoint nội bộ, không liên quan Chu kỳ kiểm thử và không được đổi nhầm.

## 11. Phạm vi build sau khi chốt UX

Thực hiện theo lát cắt đầu-cuối, không xóa module hàng loạt trước khi dò dependency:

1. **Requirement và phiên bản:** form, lưu nháp/lưu chính, quyền/trạng thái, lịch sử và AI impact từ Text Diff.
2. **Chu kỳ kiểm thử:** entity, API, quyền, vòng đời, trang danh sách/chi tiết và bước đóng/chọn chuyển tiếp; không lưu tên chu kỳ bằng text tự do ở Plan/Run.
3. **Test Plan:** form gọn theo Chu kỳ, validation khớp dấu `*`, phiên bản/snapshot và phạm vi Requirement/Case; tạo Plan mới từ Plan chu kỳ trước.
4. **Test Case:** thư viện, phiên bản, luồng và trường một nguồn dữ liệu; bỏ field bị lặp và trường không có người dùng.
5. **Test Run/Defect:** tạo Run từ Plan, gắn chu kỳ qua Plan, lưu Result theo lần, retest và Defect liên kết.
6. **Report:** hai báo cáo đã chọn, đối chiếu số liệu theo Chu kỳ/Plan/Run, xuất PDF/Word.
7. **Tài liệu và AI:** tóm tắt; dọn các luồng AI bị loại sau khi map call graph và bảo toàn dữ liệu cần thiết.
8. **Quyền/menu:** ma trận BA/Tester/Admin theo tác vụ; bỏ menu/API/route không còn dùng sau khi kiểm tra dependency.

Mỗi lát cắt phải ghi trước: thao tác người dùng, trường nhập và `*`, điều kiện lưu, trạng thái sau lưu, quyền, endpoint/data, lỗi có thể gặp, dữ liệu cũ cần đọc và tiêu chí nghiệm thu. Chỉ sau đó mới sửa backend và frontend cho lát cắt đó.

## 12. Đối chiếu thiết kế với toàn bộ luồng code và dữ liệu

### 12.1 Kết luận về mức hoàn tất

Đối chiếu thiết kế với các form và contract chính đã hoàn tất ở mức **bản đồ thay đổi đầu-cuối**. Rà phụ thuộc đã mở rộng tới service, API, snapshot, xuất báo cáo, điều hướng, quyền và khởi tạo chỉ mục. Đây vẫn là kiểm kê tĩnh từ source code; chưa chạy đối soát dữ liệu thật trong MongoDB và chưa thể coi là kế hoạch migration đã được nghiệm chứng trên bản sao dữ liệu. Không sửa nghiệp vụ hiện tại chỉ vì code đã có nó.

Các quyết định nghiệp vụ là căn cứ để thay đổi. Code hiện tại là bằng chứng cho biết phạm vi ảnh hưởng và dữ liệu nào cần xử lý.

### 12.2 Bản đồ phụ thuộc theo lớp

| Lớp | Hiện có | Thay đổi cần làm | Điều không được làm |
| --- | --- | --- | --- |
| Điều hướng dự án | navigation.js có Phân tích kiểm thử, Ca, Dữ liệu, Bộ kiểm thử, Kế hoạch, Lần chạy, Tự động hóa, Lỗi, Giám sát, Truy vết, Báo cáo, Nhật ký, Tài liệu, Cài đặt. | Điều hướng chính giữ Yêu cầu, Kế hoạch, Ca, Thực thi (Run/Defect), Báo cáo, Tài liệu, Cài đặt. Quản lý Chu kỳ mở từ trang Kế hoạch, không thêm mục riêng. Dữ liệu, Suite, Scenario và Automation chỉ còn menu nếu rà người dùng xác nhận chúng có tác vụ độc lập; nếu không, bỏ route, trang, quyền và API cùng nhau. | Chỉ ẩn tab nhưng để route trực tiếp, API mồ côi hoặc quyền không dùng. |
| Trang workspace và phân quyền trang | ProjectWorkspacePage.jsx ánh xạ slug → page, kiểm tra quyền rồi redirect; Reports cho vào bằng nhiều quyền phân tích/báo cáo; Monitoring/Traceability là page riêng. | Cập nhật đồng thời slug, page map, guard, fallback redirect và link cũ. Mỗi route mới phải có một quyền xem phù hợp; thao tác ghi vẫn được backend kiểm quyền. Hai loại Report chỉ dùng quyền đọc/xuất Report cần thiết, không phụ thuộc quyền AI/analytics chung. | Bỏ kiểm tra UI mà quên guard backend; đổi URL mà để route cũ mở được. |
| Requirement | Form, RequirementCreate/patch, service ghi record/version, phân tích tác động, tài liệu nguồn, import và AI đều có thể đọc cùng record. | Giữ version, trạng thái nháp/chốt và liên kết tài liệu. Bỏ risk; sửa AC/rules/link thành nội dung thêm được nhiều dòng và không required. Giải quyết rõ type: bỏ khỏi form/schema nếu không dùng để lọc hoặc xử lý, hoặc định nghĩa danh mục thực sự thay vì giá trị giả “Chưa phân loại”. | Xóa field khỏi response khi AI impact, lịch sử version hay dữ liệu cũ còn cần nó. |
| Chu kỳ | Đã có collection, schema, service, API, index, trang quản lý và liên kết từ Plan/Run. Lối vào chu kỳ nằm trong Kế hoạch. | Summary lấy cả Case trong phạm vi Plan chưa chạy và kết quả Run mới nhất. Khi đóng, ca đã chạy lấy nguồn từ Run; ca chưa chạy lấy nguồn từ Plan. Kiểm tra luồng tạo Plan kế tiếp trên giao diện. `phase` cũ chỉ được đọc để giữ lịch sử; không nhận ghi mới. | Chỉ thêm field test_period_id ở form mà không tạo lifecycle, quyền, index và màn quản lý chu kỳ. |
| Test Plan | Contract, test_plan.py, snapshot, completeness gate, self-review, approved snapshot, AI sinh Case và Report cùng dùng Plan. | Gắn Plan vào Chu kỳ; giữ mục tiêu, Requirement versions, Case versions, tiêu chí bắt đầu/kết thúc thực sự được dùng và Risk ↔ ứng phó nếu người dùng đã chốt. Bỏ phase text, scope trùng Requirement picker, Test Data cấp Plan, free-text environment, test_approach, gate cố định Critical/High và carry-over nhập ở form Plan. Thay readiness check bằng các trường và liên kết nghiệp vụ còn lại. | Xóa field khỏi write contract khi snapshot/hash cũ, generation, completion và báo cáo đã có reader tương thích. |
| Quyền/chốt Plan | test_plan.py gọi require_independent_review; các endpoint submit/approve yêu cầu testplan.approve. Người dùng đã chốt Admin/chủ dự án toàn quyền và nội dung họ tự làm được tự chốt. | Phân biệt BA/Tester/Admin theo tác vụ; Admin/chủ dự án có thể tự chốt nội dung họ tạo. Không áp quy tắc tự duyệt độc lập cứng cho Admin/chủ dự án. Với BA/Tester, chỉ yêu cầu người khác chốt nếu thiết kế workflow thật sự có người được giao; nếu không có người đó, không được làm kẹt tài liệu. Sửa service/API và nhãn trạng thái cùng lúc. | Chỉ đổi checkbox ở UI hoặc thêm ngoại lệ Admin ở một endpoint. |
| Test Case/Scenario/Dataset | Case version và Case draft là nguồn cho Plan/Run; Scenario, Dataset, kỹ thuật, cấp độ và kiểu viết có route/API, bộ lọc, generator và các liên kết riêng. | Case giữ nội dung có thể thực thi: tên, bước kèm data, expected result, trạng thái kết quả ở Run. Đưa kiểu viết vào Tùy chọn; bỏ Scenario bắt buộc và trường cấp Case bị trùng bước. Quyết định riêng có căn cứ cho Scenario/Dataset/API artifact/Automation: nếu người dùng không có tác vụ cần chúng thì gỡ end-to-end; nếu còn thì nối vào Case/Plan thay vì để thành vùng rời. | Bỏ model Scenario/Dataset chỉ vì form đang rối; còn generator, import/export, selector, index, route hoặc dữ liệu tham chiếu thì sẽ vỡ. |
| Test Run/Result/Defect | Run tạo từ approved Plan snapshot, nhận danh sách Case từ Plan/Suite, giữ trạng thái/actual result theo execution; Defect có record, lifecycle, link và quyền riêng. | Run bắt buộc có Plan trong luồng chính; chu kỳ kế thừa Plan; giữ snapshot Case version và kết quả lịch sử. Fail cho tạo Defect hoặc liên kết Defect có sẵn. Retest tạo execution mới. Chuyển chọn Case carry-over sang đóng chu kỳ/tạo Plan kế tiếp, kèm nguồn và người xác nhận. | Thay kết quả cũ khi retest; tự tạo Defect cho mọi Fail; nhận phase tay từ Run tạo form không nhất quán. |
| Môi trường/build/release | Plan/Run/Defect mới chọn ID từ danh mục; service giữ nhãn môi trường như snapshot. Màn cấu hình Environment chỉ có tên, URL và trạng thái; type/capabilities/secret legacy bị ẩn. | Không cho nhập môi trường tự do. Bản ghi cũ không có ID vẫn giữ nhãn khi sửa trường khác. Build/release vẫn giữ quy tắc hiện hành, chưa đồng bộ toàn bộ sang danh mục. | Không xóa snapshot môi trường cũ hoặc ép dữ liệu cũ phải có ID khi chưa kiểm kê DB. |
| Report và tiến độ Plan | `simple_reports.py` tạo hai báo cáo Tiến độ/Hoàn tất. API Progress của Plan nằm riêng trong `plan_progress.py` và đọc kết quả mới nhất theo từng Case. API/service/AI cũ cho Completion, Status Report, Monitoring và Quality Gate đã bị gỡ; Dashboard đếm báo cáo mới. Attachment reader giữ khả năng truy cập tệp từ report cũ. | Giữ collection cũ để bảo toàn dữ liệu/tệp đính kèm, nhưng không tạo index hay ghi bản ghi mới cho workflow đã bỏ. Rà ACL cũ khi có migration quyền. | Không xóa dữ liệu lịch sử; không để endpoint cũ được include vào router hoặc hiển thị như một tác vụ mới. |
| Database và migration | Collection Chu kỳ và index đã có; repo không có framework migration chung. Có script read-only dry-run để kiểm kê chuỗi phase cũ theo dự án. | Chạy dry-run trên bản sao dữ liệu; lập mapping thủ công cho nhóm mơ hồ; chỉ backfill ID Plan/Run khi mapping được xác nhận; giữ snapshot cũ và ghi số bản ghi xử lý/bỏ qua. | Dùng index để tự gộp tên phase giống nhau mà không có kiểm tra; xóa field cũ ngay trong cùng đợt deploy đầu tiên. |
| Export/import | Import Requirement, import/export Case, AI/document ingestion và export Report/Defect đọc/ghi hợp đồng riêng. | Cập nhật định dạng import/export cùng schema; version và link phải dùng ID nội bộ được tra cứu/đối chiếu, không suy ra bằng tên đơn thuần. Tài liệu tải lên không tạo Requirement. | Chỉ cập nhật form/API CRUD mà bỏ import/export, AI context và template dữ liệu. |

### 12.3 Danh sách cần rà trước khi xóa từng khái niệm

| Định xóa/đổi | Reader/writer bắt buộc rà | Dữ liệu cần bảo toàn | Điều kiện cho phép xóa khỏi schema |
| --- | --- | --- | --- |
| phase | Plan/Run create+patch, snapshot/hash, carry-over validator, rerun, report/export và UI fallback. Không nhầm phase nội bộ của document job. | Tên phase cũ của Plan/Run và hash snapshot đã duyệt. | Đã bỏ ghi mới và chuyển carry-over sang Cycle ID. Chỉ xóa reader/hash compatibility sau khi xác nhận dữ liệu cũ và snapshot vẫn đọc được. |
| carry_over_items | Plan create/update/approval, approved snapshot, Case membership, Run, form, close/reopen, report. | Nguồn Run với Case đã chạy hoặc nguồn Plan với Case chưa chạy; Case version, lý do, người quyết định, thời điểm. | Flow đóng Chu kỳ/tạo Plan mới lưu đầy đủ lịch sử; không còn client/API gửi carry-over ở Plan thường. |
| test_approach và scope_in | Completeness gate, Plan snapshot/hash, AI generation, completion decision, status/completion report, export và API response. | Giá trị trong Plan cũ và phê duyệt/snapshot đã lưu. | Thay thế bằng Requirement versions/Case versions và tiêu chí rõ; các report cũ vẫn render từ snapshot tương thích. |
| Risk tại Requirement/Case/Scenario | CRUD, versioning, import/export, AI prompts, query/filter, generator, monitoring, completion, list/detail. | Giá trị rủi ro lịch sử nếu còn hiển thị báo cáo hoặc giải thích quyết định cũ. | Đã phân biệt risk register của Plan và residual risk; toàn bộ reader/writer đã chuyển hoặc có legacy adapter. |
| Scenario/Dataset/Automation/Analysis | Menu/route, API, quyền, service, index, Case editor/generator, import/export, Run, report. | Case/step và execution phụ thuộc; lịch sử đã tạo và liên kết. | Chốt từng module là tác vụ người dùng cần hay bỏ; nếu bỏ phải có chuyển đổi dữ liệu hoặc xác nhận loại bỏ có chủ đích. |
| Monitoring/Traceability/Changes/Review | Navigation, route guard, APIs, permissions, collections, reports, notifications, AI runs, background jobs. | Snapshot/decisions/audit và các report đã xuất. | Nội dung cần thiết đã vào Run/Report/Requirement; không consumer, scheduler hoặc link còn sử dụng. |
| environment_notes, test_data_notes, Case-level test_data/expected_result_doc | Plan/Run environment context, Case step parsing, BDD, generator, cloning, import/export, API schema. | Bản cũ phải đọc được; bước và expected result giữ nguyên thứ tự. | Một nguồn dữ liệu rõ ràng đã nhận đủ dữ liệu chuyển đổi; kiểm tra truy xuất không còn field cũ. |

### 12.4 Thứ tự đổi backend/frontend để không tạo trạng thái nửa vời

1. **Chốt contract và trạng thái:** định nghĩa Cycle/Plan/Case/Run/Result/Defect, trạng thái mỗi đối tượng, quy tắc chốt BA/Tester/Admin, và các ID snapshot. Không sửa form trước khi contract này rõ.
2. **Thêm Cycle tương thích ngược:** collection/index/API/quyền; đọc chu kỳ mới, đồng thời đọc được phase cũ. Chạy migration dry-run trên bản sao dữ liệu, lập danh sách phase ánh xạ duy nhất và phase mơ hồ.
3. **Chuyển Plan:** hỗ trợ test_period_id, snapshot Plan mới và kiểm tra duyệt mới. Trong giai đoạn chuyển, adapter đọc các Plan cũ; sửa AI/report/completion consumer trước khi bỏ scope/approach cũ khỏi write contract.
4. **Chuyển Case:** chuẩn hóa nội dung Test Data/Expected theo bước và phiên bản; giữ đọc lịch sử; bỏ Scenario/field lặp chỉ sau call graph và import/export đã chuyển.
5. **Chuyển Run/carry-over:** Run lấy Cycle từ snapshot Plan; giữ kết quả từng lần. Xây flow đóng Cycle và tạo Plan mới từ Case được chọn. Không viết đè kết quả Run.
6. **Chuyển Report và export:** lọc theo Cycle/Plan/Run, tính mỗi Case một lần theo quy tắc kết quả mới nhất; vẫn có trang lịch sử từng Run. Xuất PDF/Word từ cùng một payload đã kiểm tra quyền.
7. **Chuyển điều hướng/quyền:** đưa các tác vụ vào nhóm đã chốt; bỏ menu/page/API/permission cùng một thay đổi khi đã hết consumer. Backend luôn kiểm quyền độc lập với UI.
8. **Backfill rồi dọn field:** chạy migration idempotent, so sánh số lượng và liên kết trước/sau; chỉ gỡ compatibility reader sau khi không còn bản ghi/consumer cũ. Không xóa collection cũ nếu report/history còn tham chiếu.

### 12.5 Quy tắc cho dữ liệu cũ và rollback

- Migration phải có chế độ chỉ đọc/dry-run, báo tổng số Plan/Run theo phase, số chuỗi trùng sau chuẩn hóa, số không có phase và số không thể ánh xạ.
- Chỉ tự tạo Cycle khi nhóm phase trong cùng dự án ánh xạ rõ ràng và không có khác biệt ngữ nghĩa. Các tên như Sprint 1, Phase 1, Đợt 1 không tự gộp dù nhìn giống nhau.
- Ghi mapping nguồn → Cycle cùng thời điểm, nguồn, phiên bản migration; chạy lại không sinh Cycle/Mapping trùng.
- Tạo bản sao lưu trước migration có ghi dữ liệu. Rollback chuyển ứng dụng về reader cũ trước; không rollback bằng cách xóa Cycle đã sinh hoặc kết quả thực thi mới.
- Đối chiếu số Plan, Run, Result, Defect link, version và báo cáo trước/sau. Mọi chênh lệch phải giải thích được bằng bản ghi cụ thể.
- Mọi snapshot/phê duyệt lịch sử giữ nguyên nội dung đã chốt. Thay đổi mô hình mới không làm sửa lại snapshot cũ trong im lặng.

### 12.6 Tình trạng kiểm kê

| Phần | Trạng thái | Còn phải làm khi bước sang triển khai |
| --- | --- | --- |
| Thiết kế tác vụ, trường và luồng | Đã có bản đồ end-to-end trong mục 10. | Dùng làm căn cứ; chỉnh tài liệu nếu phát hiện mâu thuẫn mới. |
| Form và contract chính | Đã đối chiếu Requirement, Plan, Case, Run, Result, Environment, Report ở mục 10.13. | Mỗi PR kiểm lại hợp đồng thực tế vì working tree đang có thay đổi chưa commit. |
| Requirement | AC, Quy tắc nghiệp vụ và Liên kết vẫn hiện ở phần chính, không còn bắt buộc khi lưu/chốt. Tên/Nội dung bắt buộc; backend kiểm tra nội dung ở create, sửa draft, tạo version và chuyển sang trạng thái sẵn sàng. Risk đã bị loại khỏi contract và write path manual/import/version. | Quyết định tiếp theo: bỏ phân loại `type`/custom-field theo type hoặc đưa ra danh mục có ý nghĩa; chuyển liên kết tài liệu sang danh sách nếu cần; giữ dữ liệu Risk cũ ở trạng thái đọc tương thích hay lập kế hoạch dọn dữ liệu. Rà template/import resolution và sửa luồng submit/auto-approve theo role. |
| Chu kỳ | Trang tổng kết snapshot số liệu khi đóng; chỉ Plan đã duyệt được tính; Run mở chặn đóng; ca được chọn chuyển tiếp lưu kèm nguồn và lý do. Các sửa Result/Defect trong chu kỳ mở cập nhật revision để tránh chốt trên dữ liệu cũ. | Hoàn tất rà các writer liên quan và concurrency trên MongoDB; kiểm tra hành vi của chu kỳ cũ đã đóng nhưng không có snapshot; chạy dry-run migration phase trên bản sao dữ liệu. |
| Dependency backend/frontend | Đã rà đầu-cuối tới service, snapshot, permission, routes, indexes, AI/report consumers và migration concerns ở mục 12. | Trước khi code một field/module cụ thể, rà chi tiết call graph của chính field đó và các fixtures/import/export liên quan. |
| Môi trường | Form cấu hình chỉ còn tên, URL và trạng thái. Plan, Run và Defect ghi ID môi trường đã chọn; service lấy tên cấu hình. Legacy metadata bị ẩn, nhãn môi trường cũ được giữ khi sửa bản ghi khác trường môi trường. | Chạy kiểm kê chỉ đọc trên bản sao DB để biết số bản ghi còn text-only/metadata cũ; chưa xóa hay backfill dữ liệu. |
| Dữ liệu đang chạy | Chưa đọc hoặc migration trên MongoDB; tài liệu code không đủ để kết luận dữ liệu thật có thể tự chuyển hết. | Chỉ chạy dry-run trên snapshot database khi chuẩn bị rollout. |
| Thay đổi code | Đã thêm Cycle contract/API/trang quản lý, liên kết Plan, snapshot và tự kích hoạt khi tạo Run đầu. Chu kỳ không nằm ở điều hướng chính; lối vào đặt tại Kế hoạch. Plan form và gate duyệt đã chuyển phạm vi chính sang Requirement version; bỏ ô Cách tiếp cận, nhập tự do môi trường và chọn carry-over tại form Plan. Môi trường lấy từ cấu hình; loại kiểm thử, cấp và kỹ thuật là lựa chọn có danh mục. Đã gỡ luồng AI gợi ý Test Plan khỏi form, API và AI contract; đã đổi ngữ cảnh AI sinh Case để đọc Requirement/Case links cùng các thuộc tính Plan còn dùng. Báo cáo Tiến độ lấy phạm vi hiển thị từ Requirement version. Case form nhập Data và kết quả mong đợi theo từng bước; dữ liệu Case cũ được chuyển vào bước đầu trong các adapter sửa, sao chép, tạo version, so sánh và import. **Contract tạo/sửa đã bỏ hai trường cấp Case. Writer mới lưu nội dung theo bước; khi sửa hoặc duyệt Case cũ, nội dung legacy được chuyển vào bước rồi làm rỗng trường cũ. Phiên bản mới không ghi hai trường này. Dữ liệu lịch sử vẫn có reader tương thích.** Đã bỏ Risk/loại luồng khỏi contract ghi mới, bản Case mới, sao chép, index tìm kiếm và export; dữ liệu lịch sử vẫn có đường đọc tương thích. Đã bỏ checkbox bắt buộc “không còn lỗi Critical/High” khỏi Test Plan và không ghi `quality_targets` vào Plan mới; legacy hash vẫn đọc field này cho snapshot cũ. ReportsPage chỉ còn hai báo cáo Tiến độ/Hoàn tất và xuất PDF/Word; bỏ lối vào màn Tổng quan/báo cáo cũ, màn Giám sát độc lập, tab truy vết trong Phân tích kiểm thử và API độ phủ điều kiện trùng. Truy vết Requirement vẫn được xem ngay trong khu vực Requirement; route cũ chuyển hướng tới nơi liên quan. Release không còn gate yêu cầu Completion report cũ; readiness chỉ hiển thị trạng thái Release và Defect chặn. Endpoint đóng Release cũng kiểm tra Defect chặn phía backend trong transaction; gate revision chỉ còn làm khóa đồng bộ nội bộ. Các helper/repository query chỉ phục vụ gate Completion cũ đã bị xóa. Plan/Run mới không còn nhận hoặc ghi `phase`; chuyển ca cần có Cycle nguồn và Cycle đích khác nhau. `phase` cũ chỉ còn ở compatibility hash/đọc dữ liệu cũ và công cụ kiểm kê dry-run; Run mới/rerun không sao chép nhãn phase. | Rà các consumer đọc legacy cấp Case trong BDD, review, import/export và template; contract đã bỏ hai trường, còn giữ adapter đọc đến khi dữ liệu lịch sử được đối soát. Rà Scenario/Dataset/API artifacts/Automation và các màn thiết kế kiểm thử chưa có tác vụ rõ. Đã gỡ API/service/AI và index ghi mới của Monitoring, Quality Gate, Status Report và Completion cũ; còn giữ collection lịch sử cùng reader tệp đính kèm. Rà và dọn quyền cũ trong ACL bằng migration có đối soát. Rà hash và dữ liệu Plan cũ; xác minh carry-over khi tạo/cập nhật Plan; rà migration phase trước backfill; rồi tiếp tục theo thứ tự Run/Defect → Report. |

**Kết luận:** phần đối chiếu thiết kế với mã nguồn đã xong cho các luồng chính đã nêu; các sửa đổi backend/frontend hiện nằm trong working tree và chưa được xác minh trên dữ liệu thật. Plan, Cycle, Case, Run/Defect và Report vẫn cần xác nhận bằng kiểm tra nghiệp vụ trên môi trường có dữ liệu mẫu. Workflow Completion/Monitoring cũ không còn API ghi mới; collection và attachment reader lịch sử vẫn giữ. `scope_in` và nhãn/field legacy chỉ giữ để đọc snapshot cũ. Dry-run đã có nhưng chưa chạy trên bản sao MongoDB; vì vậy chưa thể cam kết mapping/backfill tự động cho dữ liệu dự án. Scenario, Dataset, API artifact và Automation vẫn là các khu vực cần quyết định phạm vi trước khi xóa tận gốc vì còn consumer và dữ liệu tham chiếu.

### 12.7 Tệp code đã đối chiếu trong lượt này

Các điểm sau là nơi bắt đầu lần theo khi triển khai; chúng không thay thế việc rà lại theo symbol trước mỗi thay đổi:

| Tác vụ | Tệp nguồn chính đã thấy | Phụ thuộc cần sửa đồng bộ |
| --- | --- | --- |
| Điều hướng, route, guard | frontend/shared/components/layout/navigation.js; frontend/features/testing/pages/ProjectWorkspacePage.jsx; frontend/features/testing/routes.js | Menu item, slug, page map, permission guard, redirect URL và API router. |
| Requirement | frontend/features/testing/pages/workspace/requirements/RequirementCreateModal.jsx; backend/testing/src/schemas/contracts/requirements.py; backend/testing/src/modules/requirements/services/requirement_records.py; backend/testing/src/modules/requirements/api/requirements.py | Contract, lưu version, import, tài liệu nguồn, impact worker và list/detail. |
| Plan, snapshot, readiness, phê duyệt | frontend/features/testing/components/TestPlanEditor.jsx; backend/testing/src/schemas/contracts/planning.py; backend/testing/src/schemas/contracts/execution.py; backend/testing/src/modules/execution/services/test_plan.py | Snapshot/hash, completeness, carry-over validation, create/update/submit/approve, AI generation, completion, report. |
| Chu kỳ mới | backend/testing/src/core/database.py; backend/testing/src/modules/execution/router.py; backend/testing/src/modules/execution/services/test_period.py; backend/testing/src/modules/execution/api/test_periods.py; frontend/features/testing/pages/workspace/TestPeriodsPage.jsx | Entity, index, API và trang đã có. Đóng chu kỳ kiểm tra Run mở và revision trong transaction; tạo/sửa/chốt Plan và tạo/chạy lại Run khóa revision chu kỳ để không ghi vào chu kỳ đã đóng. Tổng kết tính Defect từ cả Result cũ lẫn mới. Còn đối soát dữ liệu cũ bằng dry-run. |
| Case và Scenario | frontend/features/testing/pages/workspace/test-design/TestCaseCreateForm.jsx; backend/testing/src/schemas/contracts/design.py; backend/testing/src/modules/design/services/test_case_records.py; test_case_lifecycle.py; test_case_transfer.py; test_case_query.py; test_scenario.py; generation.py | Draft/version, approve/review, copy/import/export, filters, Scenario link và AI generator. |
| Run, Result, Defect | frontend/features/testing/pages/workspace/ExecutionPage.jsx; frontend/features/testing/pages/workspace/execution/RunExecutionWorkspace.jsx; backend/testing/src/modules/execution/services/test_run.py; backend/testing/src/modules/execution/api/execution.py; backend/testing/src/modules/quality/services/defect_lifecycle.py | Tạo Run từ snapshot, selection từ Suite, Result mới theo mỗi lần chạy, defect create/link, retest, permissions. |
| Environment | backend/testing/src/schemas/contracts/environment.py; cấu hình dự án và execution context | Plan/Run/Defect chỉ ghi ID được chọn; snapshot giữ tên; form cấu hình gọn tên/URL/trạng thái. Legacy metadata được che và chưa bị xóa khỏi DB. |
| Report và tiến độ kế hoạch | frontend/features/testing/pages/workspace/ReportsPage.jsx; frontend/features/testing/components/SimpleTestReports.jsx; backend/testing/src/modules/execution/api/simple_reports.py; api/plan_progress.py; services/test_plan_progress.py; modules/execution/router.py | Hai báo cáo Tiến độ/Hoàn tất, PDF/Word, bộ lọc Chu kỳ → Plan → Run. Báo cáo một Run chỉ dùng các Case trong Run đó; báo cáo Plan dùng toàn bộ phạm vi đã duyệt. Tiến độ lấy kết quả mới nhất theo từng Case, kể cả trạng thái chưa chạy của Run mới. Báo cáo lưu snapshot Case/Defect để mở danh sách nguồn; danh sách báo cáo tải bản tóm tắt, chi tiết tải riêng theo quyền. Giới hạn 5.000 Case/Defect chi tiết mỗi báo cáo. Các workflow cũ đã gỡ, dữ liệu và attachment reader lịch sử được giữ. |
| Index, snapshot và dữ liệu cũ | backend/testing/src/core/database.py; backend/testing/scripts/inspect_test_period_migration.py; các repository/service nêu trên | Index Cycle và công cụ kiểm kê dry-run đã có. Chưa chạy trên bản sao dữ liệu thật; mapping/backfill chưa được thực hiện. |

**Giới hạn kiểm kê:** tìm kiếm toàn repo không thể chứng minh vắng phụ thuộc được tạo động qua tên field, dữ liệu JSON, script vận hành ngoài repo hoặc dữ liệu MongoDB. Trước khi xóa module/collection phải rà thêm scripts, scheduled jobs, cấu hình triển khai, fixtures, export template và database snapshot tương ứng. Vì vậy bản đồ đủ để định phạm vi và thứ tự sửa; nó không phải xác nhận an toàn để chạy DROP field/collection ngay.

### 12.8. Tiếp tục triển khai và phần còn lại

Đã hoàn tất trong lượt tiếp tục:

- Bỏ tên môi trường nhập tự do khỏi payload tạo Run và Defect; Plan chỉ gửi ID môi trường đã chọn.
- Bỏ ô nhập tay môi trường khỏi form Defect. Select để `-` khi chưa chọn hoặc danh mục rỗng.
- Giữ nhãn môi trường của Run/Defect cũ khi cập nhật trường khác; chỉ thay đổi nhãn khi chọn môi trường mới.
- Sửa kiểm tra chất lượng Case để dữ liệu và kết quả legacy cấp Case chỉ được đọc như nội dung bước đầu. Thiếu Test Data không còn sinh cảnh báo, vì dữ liệu này được nhập trong bước khi cần.
- Cập nhật phần đối chiếu môi trường và tình trạng kiểm kê trong tài liệu này.

Đã kiểm tra ESLint/Prettier và production build frontend; cú pháp 59 tệp Python; `git diff --check`; build và khởi động lại backend Testing. Smoke test HTTP/OpenAPI đạt: frontend và backend health trả 200; OpenAPI có route Chu kỳ, Kế hoạch, Lần chạy, Báo cáo; route Giám sát và Completion cũ không còn đăng ký. Repo không có unit/integration test suite riêng. Đã chạy kiểm kê chỉ đọc trên MongoDB đang dùng; tài liệu không lưu nội dung tài liệu hay định danh bản ghi.

Phần còn lại cần làm trước khi tuyên bố triển khai hoàn tất:

1. Đã kiểm kê dữ liệu legacy trên DB hiện dùng. Một Test Plan còn Phase `1` chưa gắn Chu kỳ; không thể suy ra ý nghĩa hoặc tự chuyển đổi an toàn. Cần chủ dự án xác nhận chu kỳ tương ứng trước khi backfill.
2. Đã chốt phạm vi mặc định và gỡ lối vào giao diện cho Scenario, Dataset và Automation; API artifact cũng không nằm trong quy trình kiểm thử thủ công. Backend và dữ liệu các phần này được giữ tương thích vì đang có dữ liệu thật (xem 12.9); không xóa dữ liệu/route hàng loạt.
3. Đã build và smoke test các service/API. Chưa xác nhận thủ công các luồng có đăng nhập: trình duyệt đang ở trạng thái đăng xuất nên không thể kiểm chứng thao tác người dùng Requirement/Plan/Case, đóng Chu kỳ, Run/Defect, retest và xuất Report. Đây là phần còn lại cần một phiên đăng nhập hợp lệ; repo cũng chưa có test suite tự động để thay thế bước này.
4. Đã đối chiếu role grants: chỉ còn BA, TESTER và SYSTEM_ADMIN; quyền môi trường `environment.secret_ref.manage` đã được gỡ ở revision 23. Không sửa thêm grant nghiệp vụ nếu chưa có bằng chứng quyền nào đang sai.

### 12.9. Chốt phạm vi Scenario, Dataset và công cụ nâng cao

Đối chiếu tài liệu Xray cho thấy Test Set chỉ gom danh sách Test; Test Plan lập phạm vi kiểm thử theo phiên bản/đợt; Test Execution ghi lần chạy và kết quả. Xray mô tả Test là đặc tả dùng để kiểm tra yêu cầu; không bắt buộc một thực thể Scenario riêng. Dataset có ích khi cần chạy cùng ca với nhiều bộ dữ liệu, nhưng đây là cách mở rộng, không phải ô cần có trong luồng manual mặc định. [Xray: Test Sets và Test Plans](https://docs.getxray.app/space/XRAY/301474179/Test%20Sets%20vs%20Test%20Plans), [Xray: Planning Tests](https://docs.getxray.app/space/XRAY/301403858), [Xray: xuất Dataset](https://docs.getxray.app/space/XRAYCLOUD/44578241/Exporting%2Bdatasets%2B-%2BREST%2Bv2).

Quyết định sản phẩm cho luồng chính:

- Test Case giữ tiêu đề, tiền điều kiện, bước kèm Test Data và kết quả mong đợi; không cần một Scenario bắt buộc riêng.
- Test Suite vẫn là nhóm/folder tùy chọn để sắp xếp Case. Nó không thay Test Plan.
- Test Data nhập tại bước. Dataset tái sử dụng chỉ là phần mở rộng khi có ca parameterized thật sự cần nhiều bộ dữ liệu.
- API artifact và Automation không nằm trong luồng mặc định của đồ án kiểm thử thủ công. Không tạo thêm AI để sinh ca API hoặc script tự động trong luồng này.
- Đã bỏ lối vào điều hướng của Dữ liệu kiểm thử, Scenario và Automation; các URL cũ chuyển về Ca kiểm thử. Bộ kiểm thử vẫn được giữ như công cụ gom Case.

Đây là bước giảm bề mặt thao tác. Kiểm kê DB có 912 dự án; các collection liên quan còn 235 Scenario, 65 Dataset/124 phiên bản, 77 API import/54 API operation, 18 bản nháp Automation và 16 lần chạy Automation. Các bản ghi có thể được liên kết hoặc dùng bởi luồng cũ, nên chưa xóa collection/API/backend. Route giao diện cũ chuyển về Ca kiểm thử. Việc xóa tận gốc cần migration có lưu trữ/rollback và rà soát đầy đủ liên kết trước khi làm.

Kiểm kê legacy trên DB: có 518 Test Case draft và 434 Test Case version còn dữ liệu `test_data` cấp Case; có 914 draft và 653 version còn `expected_result_doc` cấp Case. Đây là nội dung lịch sử; reader giữ tương thích, writer mới đã chuyển sang dữ liệu theo bước. Có 57 môi trường còn `environment_type` và 3 môi trường còn `capabilities`; API mới không nhận các field này và response đã che metadata cũ. Không có Test Period đã đóng thiếu snapshot. Không còn grant role ngoài BA/TESTER/SYSTEM_ADMIN. Không chạy cập nhật hàng loạt các field này vì cần giữ nguyên lịch sử và chưa có yêu cầu xóa dữ liệu.

Phân tích Phase trên 470 Plan và 439 Run cho thấy chỉ một Plan có Phase `1`; các Plan/Run còn lại không có Phase, và không bản ghi nào đã liên kết Chu kỳ. Giá trị `1` không đủ để map sang một Chu kỳ cụ thể. Không tạo Chu kỳ giả định và không chạy migration cho đến khi ý nghĩa được xác nhận.

Quyền môi trường `environment.secret_ref.manage` không còn consumer trong mã nguồn. Đã gỡ một mục capability và hai role grant bằng migration revision-check từ 22 lên 23 và ghi audit event. Quyền `secret_ref.manage` của Dataset không bị thay đổi. Prettier, ESLint, production build frontend, build backend Testing và HTTP/OpenAPI smoke test đều đạt. Repo không có test suite tự động riêng; kiểm tra authenticated UI còn chờ do trình duyệt đang đăng xuất.

### 12.10. Quyết định nghiệp vụ và UX: Nhóm ca kiểm thử và Đợt kiểm thử

Phần này là quyết định mới nhất và thay thế các mô tả giao diện trước đây về vị trí/luồng tạo Chu kỳ, gồm các đoạn 10.5, 10.12.1 và “Giao diện chu kỳ đã chốt”. Những đoạn cũ mô tả lẫn “chu kỳ” như nhóm Plan, nhóm Case và trang riêng; không dùng chúng làm căn cứ triển khai.

#### Hai khái niệm khác nhau

| Khái niệm trong Veriq | Tên kỹ thuật | Việc người dùng cần làm | Vòng đời |
| --- | --- | --- | --- |
| **Bộ kiểm thử** | Bộ sưu tập Test Case; gần với Xray Test Set hơn TestRail Suite | Gom các ca được chọn theo mục tiêu như Smoke, Hồi quy, hoặc một nhóm chức năng. | Tùy chọn và tái sử dụng qua nhiều kế hoạch. Không chứa kết quả chạy. Một Case có thể thuộc nhiều bộ hoặc chưa thuộc bộ nào. Không phải cây thư mục. |
| **Kế hoạch kiểm thử** | Test Plan | Chốt mục tiêu và chọn Requirement/phiên bản cùng các Test Case cần kiểm tra cho một mục tiêu hoặc giai đoạn. | Có thể tạo kế hoạch mới từ kế hoạch trước; chọn lại phạm vi phù hợp. Không lưu Pass/Fail. |
| **Lần chạy kiểm thử** | Test Run / Execution | Thực thi phạm vi của một Test Plan trên môi trường/build cụ thể và ghi kết quả thực tế. | Mỗi lần chạy lưu kết quả riêng; chạy lại không ghi đè lần trước. |
| **Đợt kiểm thử** | Test Period (Veriq) | Tùy chọn gom nhiều Test Plan thuộc cùng một mốc/chiến dịch để lọc và tổng hợp, ví dụ “UAT bản 1.2”. | Không bắt buộc. Không phải Scrum Sprint và không tự chuyển Requirement/Case. Tên “Đợt kiểm thử” rõ nghĩa hơn “Chu kỳ”. |

“Bộ kiểm thử” của Veriq **không phải folder kiểu TestRail Suite/Section**. Nó là danh sách ca được chọn để dùng lại; về vai trò gần với Xray Test Set. TestRail Suite có cấu trúc phân cấp, còn TestRail Milestone là mốc có thể gắn với Plan/Run. Zephyr gọi tập ca phục vụ mục tiêu thực thi là Test Cycle và hiển thị tiến độ Cycle. Jira Sprint quản lý work item/backlog. Các tên này không thay thế cho nhau; Veriq không ghép chúng thành một loại dữ liệu. [Xray: Test Sets vs Test Plans](https://docs.getxray.app/space/XRAY/301474179/Test%20Sets%20vs%20Test%20Plans), [TestRail: Test suites](https://support.testrail.com/hc/en-us/articles/33359301314708-Test-suites), [TestRail: Milestones](https://support.testrail.com/hc/en-us/articles/15545364561044-Milestones), [Zephyr: Test Cycles](https://support.smartbear.com/zephyr/docs/dc/test-cycles/), [Jira: Sprints](https://support.atlassian.com/jira-software-cloud/docs/use-your-scrum-backlog/).

#### Mô hình Veriq được chọn

```mermaid
flowchart LR
  REQ[Yêu cầu / phiên bản] <--> CASE[Test Case / phiên bản]
  GROUP[Nhóm ca, tùy chọn] -. sắp xếp .-> CASE
  PLAN[Test Plan: mục tiêu + phạm vi] --> RUN[Test Run: một lần thực thi]
  PLAN -. chọn .-> REQ
  PLAN -. chọn .-> CASE
  RUN --> RESULT[Kết quả theo từng Case]
  PERIOD[Đợt kiểm thử, tùy chọn] --> PLAN
  RESULT --> REPORT[Báo cáo theo Plan / Run / Đợt]
```

- **Bộ kiểm thử** là danh sách ca tái sử dụng, không theo thời gian. Không bắt buộc đưa mọi Case vào bộ; một Case có thể có mặt trong nhiều bộ và không cần nhân bản để dùng trong nhiều Plan.
- **Test Plan** là đơn vị mô tả phạm vi công việc kiểm thử. Nếu chỉ có một kế hoạch cho một giai đoạn thì Plan đó đủ dùng; người dùng không cần tạo thêm Đợt.
- **Đợt kiểm thử** chỉ cần khi có nhiều Plan cần xem/tổng hợp chung theo một mốc. Đây là nhóm tùy chọn ở tầng Plan, không phải một bước tiền đề bắt buộc để tạo Plan hay Run.
- **Test Run** luôn là một lần chạy có kết quả. Không đặt Case trực tiếp vào “Đợt” để rồi bỏ qua Plan; phạm vi Run đến từ Plan và người dùng rà danh sách Case trước khi chạy.
- Yêu cầu, Test Case và Test Suite không thuộc độc quyền một Đợt. Case có thể được dùng lại ở các Plan khác nhau; kết quả cũ luôn nằm trong Run đã tạo.
- “Giai đoạn 1/2” là cách nhóm công việc theo thời gian/phạm vi, không phải một Test Level, Test Type, Suite hay trạng thái Pass/Fail. Khi sang giai đoạn mới, tạo Plan mới và chọn những Case cần tiếp tục. Giữ Plan/Run trước đó làm lịch sử.

#### Giao diện đề xuất trước khi code

**Thư viện Test Case:** mở thẳng vào danh sách ca. Ngay trên danh sách hiện các lựa chọn “Tất cả ca” và tên từng Bộ kiểm thử kèm số ca; chọn một bộ sẽ lọc danh sách. Nút `Tạo bộ kiểm thử` mở form chọn tên và các Case đưa vào bộ. Tạo Case không yêu cầu chọn bộ; có thể thêm Case vào bộ sau từ danh sách. Không dùng một trang quản lý bộ riêng làm luồng chính và không gọi các bộ là thư mục.

**Kế hoạch kiểm thử:** trang chính hiển thị danh sách Plan. Bộ lọc “Mọi đợt” là tùy chọn; không có nút “Quản lý chu kỳ” đứng cạnh nút tạo Plan. Form Plan có trường “Đợt kiểm thử” không bắt buộc: chọn Đợt có sẵn hoặc nhập tên Đợt mới ngay trong form. Backend tạo Đợt và Plan trong cùng giao dịch để không để lại Đợt rỗng nếu Plan không lưu được. Nếu dự án chỉ có một Plan cho một mục tiêu/giai đoạn, bỏ trống trường này.

**Đợt kiểm thử:** không có mục điều hướng chính hoặc trang tạo rỗng trong luồng thường. Người dùng thấy đợt qua bộ lọc và cột Đợt trong danh sách Plan. Mở Đợt từ cột này sẽ thấy Plan thuộc đợt, tổng kết Run và các ca được đề xuất tiếp. Nút “Tạo kế hoạch tiếp theo” đưa sang form Plan; tên đợt mới và các ca được chọn chuyển tiếp được điền sẵn. Người dùng có thể rà nội dung trước khi lưu. Backend tạo Plan và đợt mới cùng giao dịch; không tạo đợt rỗng nếu hủy form. Kết quả Run cũ vẫn được giữ.

#### Ví dụ luồng thực tế

1. Tester mở thư viện, tạo Case “Đăng nhập với mật khẩu hợp lệ”. Có thể thêm Case vào Bộ kiểm thử “Smoke đăng nhập”, nhưng không bắt buộc.
2. Tester tạo Plan “Kiểm thử đăng nhập – giai đoạn 1”, liên kết Requirement và chọn Case. Nếu chỉ có Plan này thì không cần tạo Đợt.
3. Tester tạo Run từ Plan, chọn môi trường và ghi kết quả từng Case. Khi chạy lại, tạo Run mới để giữ lịch sử.
4. Nếu còn Case cần kiểm tra ở giai đoạn 2, tạo Plan mới từ Plan trước, rà phạm vi rồi chọn Case chưa hoàn tất hoặc cần hồi quy. Không di chuyển Case ra khỏi nhóm chức năng, không sửa kết quả Run cũ.
5. Nếu có nhiều Plan cùng thuộc một UAT/release, gắn chúng vào một Đợt để xem và báo cáo chung. Nếu chỉ có một Plan, không thêm Đợt cho đủ hình thức.

**Quyết định này loại bỏ bước tạo Đợt trước Plan và phân biệt Bộ kiểm thử với thư mục:** Case luôn dùng được; Bộ là danh sách Case tái sử dụng; Plan chọn phạm vi; Đợt tùy chọn gom nhiều Plan; Run lưu kết quả theo lần thực thi. Không tự đổi Phase `1` thành một Đợt.

### 12.11. Tái thiết kế giao diện toàn hệ thống

Đây là quyết định UX mới nhất cho toàn bộ khu vực dự án, thay các mô tả điều hướng giao diện trước ở mục 12.10. Không thay đổi mô hình Requirement → Test Plan → Test Case → Test Run → Result/Defect → Report đã chốt ở trên.

#### Vấn đề quan sát được trên giao diện hiện tại

- Điều hướng dự án xuất hiện thành dải ngang cố định trên màn lớn, nhưng biến mất khỏi đầu trang ở màn nhỏ. Người dùng phải mở menu để đổi khu vực.
- Trên màn Ca kiểm thử, khối đề xuất AI nằm trước danh sách và chiếm phần đầu trang dù người dùng thường cần tìm, tạo hoặc sửa ca.
- Bộ lọc kế hoạch bị ép thành các ô ngắn và cắt nhãn ở màn nhỏ.
- Danh sách yêu cầu và kế hoạch đổi từ bảng sang nhiều dòng nhãn/giá trị. Mỗi dòng chiếm nhiều chiều cao, khó quét nhanh.
- Báo cáo có lời giải thích dài trước các số liệu chính; thao tác xuất nằm xa nội dung người dùng cần đọc.
- Một số trang có action “Về dự án” lặp cạnh tiêu đề dù thanh điều hướng trên màn lớn đã cho biết vị trí hiện tại.

#### Khung điều hướng được chọn

- Giữ thanh trên cùng cho tên dự án, tìm kiếm, thông báo và tài khoản.
- Dùng **một thanh điều hướng dọc bên trái** cho các khu vực của dự án. Nhóm theo công việc: Tổng quan, Bảo đảm yêu cầu, Kế hoạch kiểm thử, Thiết kế kiểm thử, Thực thi kiểm thử, Báo cáo và Tài liệu.
- Bỏ dải tab cố định ngang lặp lại điều hướng này. Sidebar giữ được tên đầy đủ, trạng thái đang mở và nhóm chức năng trên desktop. Trên thiết bị nhỏ, drawer dùng cùng cấu trúc để tránh hai sơ đồ điều hướng khác nhau.
- Đặt tên dự án ở đầu danh sách sidebar; action trở về tổng quan vẫn hiện một lần trong nhóm Tổng quan.

#### Quy tắc trình bày màn hình

Mỗi trang dùng cùng thứ tự: tiêu đề và một action chính; nội dung chính; bộ lọc ngay trên danh sách; tùy chọn nâng cao nằm sau thao tác chính. Không đặt mô tả giải thích dài lên trước dữ liệu hoặc tác vụ.

| Khu vực | Nội dung đầu trang | Nội dung chính | Tùy chọn / thao tác phụ |
| --- | --- | --- | --- |
| Dự án | Tên, trạng thái, action mở dự án | Việc cần làm và số liệu dự án có nguồn | Cài đặt, nhật ký và cấu hình |
| Yêu cầu | Tìm kiếm, `Tạo yêu cầu` | Danh sách gọn: mã, tên, trạng thái, phiên bản hiện tại | Trùng lặp, lịch sử và liên kết kiểm thử ở chi tiết yêu cầu |
| Kế hoạch | `Tạo kế hoạch`, `Quản lý chu kỳ`, lọc theo chu kỳ/trạng thái | Danh sách: tên, phạm vi, chu kỳ nếu có, trạng thái, thời gian | Trong form Kế hoạch, chọn chu kỳ đã có hoặc tạo chu kỳ mới ngay tại trường Chu kỳ; kế hoạch vẫn được lưu khi không chọn chu kỳ |
| Ca kiểm thử | `Tạo ca kiểm thử`, tìm kiếm | Danh sách ca và bộ lọc cơ bản; nhóm ca hiện như lựa chọn, không cần trang riêng | Sinh bằng AI thu gọn thành thao tác phụ; bộ lọc nâng cao chỉ mở khi cần |
| Thực thi | `Tạo lần chạy` từ một Plan đã duyệt | Danh sách Run theo trạng thái và tiến độ | Build/môi trường và bộ lọc phụ; lỗi xử lý từ kết quả Fail |
| Báo cáo | Chọn Plan và loại báo cáo | Chỉ số, trạng thái theo từng Case, lần chạy gần nhất | Xuất PDF/Word cạnh báo cáo; mô tả quy tắc tính trong phần thông tin |
| Tài liệu | `Nhập tài liệu` | Kho tài liệu, trạng thái xử lý và liên kết nguồn | Tóm tắt tài liệu ở thao tác rõ ràng, không lẫn với Requirement |
| Tài khoản | `Thêm tài khoản`, tìm kiếm | Tài khoản, vai trò và trạng thái | Xem/sửa/khóa tại chi tiết; quyền theo vai trò có tên người dùng hiểu được |

#### Quy tắc Responsive và dữ liệu

- Màn hình hẹp không được cắt tên trường/lọc. Bộ lọc xếp thành hàng tự xuống dòng; ô tìm kiếm được ưu tiên chiều rộng. Nhãn trường vẫn đọc được sau khi thu gọn.
- Danh sách không biến mỗi cột thành một cặp nhãn/giá trị lặp lại quá dài. Dùng hàng/card gọn: tên là dòng chính; mã và trạng thái là metadata; thao tác gắn với đúng dòng.
- Khi danh sách trống, giữ một câu nêu rõ chưa có gì và action liên quan ngay tại chỗ. Không hiện nhóm form dài trước khi người dùng chọn tạo.
- Form chia trường chính và tùy chọn đúng theo nghiệp vụ. Trường bắt buộc có dấu `*`; không thêm lời nhắc/tagline nếu không giúp người dùng điền hoặc hiểu kết quả.
- Các trang dùng chung quy tắc tiêu đề, nút chính/phụ, trạng thái, bộ lọc, bảng/card, phân trang và thông báo lỗi.

#### Thứ tự triển khai giao diện

1. **Khung và điều hướng:** sidebar dự án thống nhất; bỏ tab ngang lặp; bảo đảm điều hướng desktop/mobile có cùng nhóm và nhãn.
2. **Thư viện dữ liệu:** thống nhất danh sách Yêu cầu, Ca, Plan, Run, Defect, Tài liệu và Tài khoản; chỉnh responsive và bộ lọc để không cắt chữ.
3. **Chi tiết và biểu mẫu:** thống nhất xem/sửa/duyệt; trình bày trường chính trước, tùy chọn sau; giữ liên kết nguồn và trạng thái ở cùng ngữ cảnh.
4. **Thực thi và báo cáo:** làm rõ tạo Run từ Plan, thao tác Fail/Defect và số liệu báo cáo theo kết quả mới nhất.
5. **Kiểm tra thủ công theo vai trò:** BA, Tester, Admin hoàn thành các tác vụ chính trên màn lớn và nhỏ; ghi lỗi thực tế trước khi điều chỉnh tiếp.

#### Căn cứ sản phẩm

Xray tách Test Set để gom Test khỏi Test Plan dùng lập kế hoạch và tổng hợp Execution. Azure Test Plans cho phép Case được đưa thẳng vào Plan mà không cần Suite, và các loại Suite phục vụ nhóm ca theo từng Plan. TestRail phân biệt thư viện Case/Suite với Test Plan và Run. Vì vậy Veriq không bắt buộc người dùng tạo nhóm/đợt để tiếp tục; giao diện phải bắt đầu từ Case, Plan hoặc Run tùy tác vụ. [Xray: Test Sets vs Test Plans](https://docs.getxray.app/space/XRAY/301474179/Test%20Sets%20vs%20Test%20Plans), [Azure: Test objects](https://learn.microsoft.com/en-us/azure/devops/test/test-objects-overview?view=azure-devops), [Azure: Test suites](https://learn.microsoft.com/en-us/azure/devops/test/create-test-suites?view=azure-devops), [TestRail: Test suites](https://support.testrail.com/hc/en-us/articles/33359301314708-Test-suites).
