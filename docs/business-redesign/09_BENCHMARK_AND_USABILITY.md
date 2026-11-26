# Đối chiếu sơ bộ sản phẩm quản lý kiểm thử

**Trạng thái:** Đã mở đầu bằng tài liệu chính thức của nhà cung cấp. Đây là căn cứ so sánh tác vụ và quan hệ, không phải danh sách tính năng Veriq phải sao chép. Chưa hoàn tất đánh giá usability thực tế.

## Bằng chứng từ tài liệu sản phẩm

### Azure Test Plans

- Tài liệu mô tả các thực thể Test Plan, Test Suite, Test Case, Test Run và Test Result với quan hệ riêng. Suite có thể là tĩnh, theo requirement hoặc theo query; test case được thêm vào suite trong plan. [Tổng quan Azure Test Plans](https://learn.microsoft.com/azure/devops/test/overview?preserve-view=true&view=azure-devops)
- Hệ thống ghi kết quả từng bước/test trong Test Runner; có thể đính kèm chẩn đoán và tạo hoặc cập nhật bug ngay trong lúc chạy. [Chạy manual test](https://learn.microsoft.com/en-us/azure/devops/test/run-manual-tests?view=azure-devops)
- “Test point” là tổ hợp Test Case, Suite, Configuration và Tester. Vì vậy việc cùng một ca xuất hiện trong cấu hình/tester khác nhau có thể tạo đơn vị thực thi khác nhau. [Câu hỏi thường gặp về Test Plans](https://learn.microsoft.com/en-us/azure/devops/test/reference-qa?toc=%2Fazure%2Fdevops%2Ftroubleshoot%2Ftoc.json&view=azure-devops)
- Tài liệu có Progress report, Runs hub, chart và dashboard widget; các metric được dùng để trả lời tiến độ, pass/fail/blocked và khu vực cần chú ý. [Báo cáo và theo dõi](https://learn.microsoft.com/en-us/azure/devops/test/?view=azure-devops)
- Pipeline có thể chạy và xuất kết quả tự động mà không cần định nghĩa Test Plan, Test Suite và Test Case theo cách manual-test. Điều này cho thấy quy trình test-management không nên bị mặc định là điều kiện cho mọi loại test. [Tổng quan Azure Test Plans](https://learn.microsoft.com/azure/devops/test/overview?preserve-view=true&view=azure-devops)

### TestRail

- Test Plan gom nhiều Test Run; Run giữ tập case để thực thi trên browser, OS hoặc cấu hình khác nhau. [TestRail Plans API](https://support.testrail.com/hc/en-us/articles/7077711537684-Plans)
- Trang tạo plan phân biệt plan, run và milestone; run được mô tả là phần xác định ca nào chạy và trong điều kiện nào. [Tạo Test Plan](https://support.testrail.com/hc/en-us/articles/30765296499604-Create-new-test-plans)
- Plan summary cho xem trạng thái/tiến độ và danh sách run liên kết. [Plan Summary report](https://support.testrail.com/hc/en-us/articles/9352373017364-Plan-Summary-report)

### Xray

- Tài liệu Xray phân biệt Test Set và Test Plan: Test Set là nhóm danh sách test; Test Plan có ý nghĩa lập kế hoạch/thực thi. [Test Sets vs Test Plans](https://docs.getxray.app/space/XRAY/301474179/Test%20Sets%20vs%20Test%20Plans)

## Câu hỏi thiết kế cần đối chiếu với Veriq

1. Veriq cần đơn vị nào để nhóm ca, đơn vị nào để xác định phạm vi kế hoạch, và đơn vị nào để ghi mỗi lần chạy?
2. Một ca được dùng lại ở nhiều plan/suite/run thế nào mà không nhân đôi ca hay cộng trùng metric?
3. Cấu hình môi trường/build/người chạy thuộc plan hay execution instance; lịch sử cần giữ context nào?
4. Có loại chạy nào hợp lệ khi không có Requirement hoặc Test Plan không? Nếu có, cách biểu diễn traceability thiếu là gì?
5. Report cần tổng hợp theo plan, theo run hay theo lần thử mới nhất; mẫu số nào tránh đếm trùng?
6. Lỗi phát hiện lúc chạy liên kết hoặc tạo mới thế nào để hỗ trợ tái hiện mà không tạo duplicate?
7. Cycle/period trong Veriq là gì so với milestone/release/sprint; chức năng nào cần nó và chức năng nào không phụ thuộc nó?

## Giới hạn

- Nguồn trên mô tả capability và cách tổ chức của từng sản phẩm; không chứng minh toàn bộ nhóm dùng quy trình giống nhau.
- Chưa thực hiện usability test hoặc đo số bước trên các sản phẩm này.
- Chưa benchmark đầy đủ các chức năng, quyền, workflow, trường dữ liệu hoặc giới hạn phiên bản.
- Chưa kết luận Veriq cần có Test Point, Requirement-based Suite, milestone, hay bất kỳ capability cụ thể nào. Mỗi quyết định phải dựa trên task đã xác minh và scope đồ án.
