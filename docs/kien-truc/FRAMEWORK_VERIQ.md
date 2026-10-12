# Framework Veriq

## Phạm vi và nguồn đối chiếu

Tài liệu này mô tả hành vi đang có trong mã nguồn Veriq tại thời điểm tạo tài liệu

Nó không coi ảnh tham khảo là tài liệu kiến trúc và không suy diễn thêm chức năng từ ảnh đó

Các điểm được đối chiếu gồm

- Định nghĩa services và route trong `docker-compose.yml`
- Router Testing trong `backend/testing/src/main.py`
- Router Requirements trong `backend/testing/src/modules/requirements`
- Router AI và graph điều phối trong `backend/ai/src/api` và `backend/ai/src/agents/runner`
- Luồng evidence trong `backend/ai/src/knowledge`
- Worker và hàng đợi trong `backend/worker/src/main.py`

## Nguyên tắc nghiệp vụ

- Mọi đối tượng nghiệp vụ nằm trong một dự án và được kiểm tra quyền dự án trước khi đọc hoặc thay đổi
- Tài liệu nguồn giữ quyền truy cập riêng và cờ cho phép AI sử dụng riêng
- Requirement import tạo bản xem trước trước khi xác nhận nhập
- Template chỉ hỗ trợ thu thập và chuẩn hóa Requirements Không tạo test case trong luồng template
- Test case được xử lý tại giai đoạn Thiết kế kiểm thử sau khi Requirement đã được xác nhận
- Thay đổi do AI đề xuất không được áp dụng khi chưa có quyết định phê duyệt
- Kết quả AI chỉ được coi là hoàn tất khi vượt qua kiểm tra phạm vi bằng chứng và kết quả áp dụng nếu có

## Luồng nghiệp vụ tổng quát

Sơ đồ này dùng các điểm kiểm tra làm mốc quay lại Khi một bước không đạt điều kiện hệ thống không đi tiếp xuống bước sau và cũng không tự bỏ qua lỗi

```mermaid
flowchart TD
    S([Bắt đầu]) --> A[Người dùng xác thực]
    A --> B{Có quyền vào dự án}
    B -->|Không| X1[Trả từ chối quyền truy cập] --> E1([Kết thúc không thay đổi])
    B -->|Có| C[Chọn hoặc quản lý tài liệu nguồn]
    C --> D[Chuẩn hóa Requirements]
    D --> Q{Requirement đã được xác nhận}
    Q -->|Chưa| R[Giữ bản nháp và yêu cầu người dùng hoàn thiện]
    R --> C
    Q -->|Có| F[Phân tích kiểm thử]
    F --> G[Thiết kế kiểm thử]
    G --> H[Lập kế hoạch và thực thi]
    H --> I[Giám sát chất lượng thay đổi và truy vết]
    I --> J{Có thay đổi hoặc finding cần xử lý}
    J -->|Có| F
    J -->|Không| K[Báo cáo trạng thái hoặc hoàn tất]
    K --> E2([Kết thúc thành công])
```

### Luồng điều khiển cho một thao tác có thay đổi dữ liệu

Mỗi hình thoi là một quyết định có nhánh Có và Không rõ ràng Mỗi nhánh phải đi đến một kết thúc hoặc quay về đúng checkpoint Không có nhánh lỗi nào tự rơi xuống nhánh thành công

```mermaid
flowchart TD
    S([Bắt đầu request]) --> A[Checkpoint A<br/>Xác thực phiên quyền dự án dữ liệu đầu vào revision và idempotency]
    A --> AD{A hợp lệ}

    AD -->|Không| AERR[Backend trả lỗi trước khi ghi<br/>Frontend giữ nội dung người dùng đã nhập]
    AERR --> ARETRY{Có thể sửa và gửi lại}
    ARETRY -->|Có| A
    ARETRY -->|Không| END_NO_CHANGE([Kết thúc không thay đổi dữ liệu])

    AD -->|Có| B[Checkpoint B<br/>Thực hiện đúng một thay đổi nghiệp vụ]
    B --> BD{B đã ghi đầy đủ}

    BD -->|Có| C[Checkpoint C<br/>Đọc lại revision trạng thái và kết quả đã ghi]
    C --> CD{Kết quả xác minh đúng}
    CD -->|Có| AUDIT[Ghi audit trả dữ liệu và operation metadata]
    AUDIT --> END_SUCCESS([Kết thúc thành công])
    CD -->|Không| CERR[Trả trạng thái không hoàn tất<br/>Kèm trạng thái quan sát được]
    CERR --> CRETRY{Có đường phục hồi an toàn}
    CRETRY -->|Sửa dữ liệu đầu vào| A
    CRETRY -->|Retry idempotent| B
    CRETRY -->|Không| END_INTERVENTION([Kết thúc cần can thiệp])

    BD -->|Lỗi trước khi có ghi bền vững| BPRE[Giữ trạng thái cũ và trả lỗi]
    BPRE --> BPRE_RETRY{Backend đánh dấu retryable hoặc người dùng sửa dữ liệu}
    BPRE_RETRY -->|Có| A
    BPRE_RETRY -->|Không| END_NO_CHANGE

    BD -->|Lỗi sau khi đã ghi một phần| BPARTIAL{Workflow có compensation đã định nghĩa}
    BPARTIAL -->|Có| COMP[Chạy compensation của chính workflow<br/>Không chạy rollback toàn cục]
    COMP --> COMP_OK{Compensation đã xác minh}
    COMP_OK -->|Có| A
    COMP_OK -->|Không| END_MANUAL([Kết thúc cần can thiệp thủ công])
    BPARTIAL -->|Không| END_MANUAL
```

Không có một cơ chế compensation chung cho toàn hệ thống Mỗi workflow phải tự xác định trạng thái có thể phục hồi và thao tác đảo ngược tương ứng Mã hiện có các rollback riêng cho vòng đời Requirement phiên bản Test Case kết quả AI áp dụng vào Requirement và lệnh thực thi tự động Các workflow không có rollback riêng phải trả lỗi có cấu trúc và giữ trạng thái quan sát được thay vì tuyên bố đã hoàn tác

### Luồng Requirements chi tiết

```mermaid
flowchart TD
    S([Bắt đầu]) --> A[Người có quyền Requirement chọn dự án]
    A --> Z{Có quyền dự án và quyền đọc nguồn}
    Z -->|Không| Z1[Trả từ chối không tạo dữ liệu] --> E1([Kết thúc không thay đổi])
    Z -->|Có| T{Nguồn đầu vào}
    T -->|Mẫu khởi đầu| T1[Mẫu Web Mobile hoặc API]
    T -->|Mẫu dự án| T2[Mẫu bản nháp có phiên bản]
    T -->|Tài liệu| T3[User Story SRS hoặc tệp nguồn]
    T -->|Định nghĩa API| T4[API Definition]
    T -->|Tự tạo| T5[Biểu mẫu template và trường mở rộng]

    T1 --> PRV[Xem trước template hoặc import]
    T2 --> PRV
    T3 --> X[Rút nội dung thành requirement ứng viên]
    T4 --> X
    T5 --> PRV
    PRV --> X

    X --> V[Kiểm tra nguồn dẫn và quyền đọc nguồn]
    V --> V1{Nguồn dẫn hợp lệ}
    V1 -->|Không| E[Giữ ở bản xem trước và nêu phần cần hoàn thiện]
    V1 -->|Có| C[So sánh với requirement hiện có]
    C --> D{Có trùng hoặc xung đột cần quyết định}
    D -->|Có| R[Người dùng chọn gộp tách từ chối hoặc phân giải]
    R --> Q[Kiểm tra lại bản xem trước]
    D -->|Không| Q
    Q --> K{Mỗi mục được chọn có nội dung và nguồn dẫn}
    K -->|Không| E
    K -->|Có| F[Xác nhận nhập]
    F --> G[Kiểm tra khóa requirement và trạng thái đối chiếu]
    G --> H{Hợp lệ}
    H -->|Không| E
    H -->|Có| I[Claim import job từ preview ready sang confirming]
    I --> J[Tạo Requirement và phiên bản theo từng mục]
    J --> L{Tất cả mục được tạo}
    L -->|Có| M[Xác nhận import và ghi audit]
    M --> N[Đưa Requirement đã xác nhận vào cơ sở phân tích kiểm thử]
    N --> E2([Kết thúc thành công])
    L -->|Không| O[Compensation xóa các Requirement Version và artifact version của đúng lượt xác nhận]
    O --> RESET[Đặt import job về preview ready và ghi audit thất bại]
    RESET --> E
    E --> U{Người dùng tiếp tục}
    U -->|Sửa nguồn hoặc bản xem trước| T
    U -->|Hủy| E3([Kết thúc không thay đổi])

    subgraph TP[Quản lý phát hành template]
        M1[Mẫu riêng tư theo dự án]
        M2[Đề nghị phát hành]
        M3[Chủ tài liệu đồng ý]
        M4[QA hoặc quản trị viên duyệt phát hành]
        M5[Mẫu dùng chung]
        M1 --> M2 --> M3 --> M4 --> M5
    end
```

### Điểm dừng của template

```mermaid
flowchart TD
    S([Bắt đầu template]) --> A[Template và tài liệu nguồn]
    A --> B[Requirement ứng viên có nguồn dẫn]
    B --> C[Người dùng rà soát]
    C --> D{Xác nhận nhập}
    D -->|Không| A
    D -->|Có| E[Requirement có phiên bản]
    E --> F[Phân tích kiểm thử]
    F --> G[Thiết kế test case]
    G --> E1([Kết thúc luồng template])

    X[Không tạo test case trong template] -. ranh giới nghiệp vụ .-> E
```

## Luồng từ Requirement đến báo cáo

```mermaid
flowchart TD
    S([Bắt đầu]) --> R[Requirement phiên bản đã xác nhận]
    R --> A[Phân tích kiểm thử]
    A --> A1[Tạo điều kiện kiểm thử]
    A --> A2[Ghi nhận finding và phân công xử lý]
    A1 --> A3[Gửi rà soát phê duyệt hoặc lưu trữ]
    A2 --> A4[Giải quyết và xác minh finding]
    A3 --> D[Thiết kế kiểm thử]
    A4 --> D
    D --> D1[Tạo hoặc sinh kịch bản]
    D --> D2[Tạo bản nháp test case]
    D2 --> D3[Kiểm tra bản nháp]
    D3 --> D4[Gửi rà soát yêu cầu chỉnh sửa hoặc phê duyệt]
    D4 --> P[Lập chiến lược kế hoạch suite và dữ liệu]
    P --> E[Thực thi và ghi kết quả]
    E --> Q[Giám sát kiểm soát chất lượng lỗi và thay đổi]
    Q --> T[Truy vết requirement test case kết quả]
    T --> O[Báo cáo trạng thái hoặc hoàn tất]
    O --> E1([Kết thúc thành công])

    Q -->|Thay đổi ảnh hưởng| A
    A2 -->|Finding chưa được xác minh| A4
    A4 -->|Cần làm rõ Requirement| R
    D4 -->|Yêu cầu chỉnh sửa| D
```

## Luồng hoạt động AI agent

AI agent hiện là một workflow điều phối duy nhất cho mỗi lượt chạy Không có cơ chế nhiều agent tự chạy song song trên cùng một lượt

```mermaid
flowchart TD
    S([Bắt đầu lượt chạy AI]) --> U[Người dùng chọn capability và gửi mục tiêu]
    U --> A[API kiểm tra xác thực và quyền dự án]
    A --> A1{Được phép chạy trong dự án}
    A1 -->|Không| E1[Trả từ chối không tạo lượt chạy] --> X1([Kết thúc không thay đổi])
    A1 -->|Có| B[Khởi tạo Agent Run gồm project user role quyền và metadata model]
    B --> C[Nạp ngữ cảnh]

    subgraph EV[Thu thập evidence cùng project]
        C1[Evidence do người dùng cung cấp]
        C2[Truy hồi artifact qua Testing service]
        C3[Vector retrieval qua Qdrant]
        C4[Quan hệ artifact qua Neo4j]
        C5[Bộ nhớ dài hạn đã được xác minh]
        C1 --> C6[Đóng gói lọc trùng và giới hạn evidence]
        C2 --> C6
        C3 --> C6
        C4 --> C6
        C5 --> C6
    end

    C --> C2
    C6 --> D{Capability được chọn có tool hợp lệ và đủ quyền}
    D -->|Có| E[Tạo trực tiếp một task của capability]
    D -->|Không| F[Mô hình tạo plan có cấu trúc]
    F --> F1{Provider phản hồi hợp lệ}
    F1 -->|Lỗi tạm thời và còn lượt thử| F
    F1 -->|Hết lượt thử hoặc lỗi không phục hồi| Z1[Đánh dấu AI provider unavailable]
    Z1 --> X2([Kết thúc thất bại])
    F1 -->|Có| G[Kiểm tra task tool schema tham số quyền phạm vi project và định danh]
    G --> H{Có task hợp lệ}
    H -->|Không| Z[Trả kết quả không đủ bằng chứng hoặc task không hợp lệ]
    Z --> X3([Kết thúc có kết quả hạn chế])
    H -->|Có| E
    E --> I[Thực thi tool theo task]
    I --> I1{Tool thực thi được}
    I1 -->|Không| Z2[Thu thập lỗi tool và xác minh thất bại]
    Z2 --> X2
    I1 -->|Có| J[Tạo kết quả đề xuất quan sát và evidence references]
    J --> K[Tổng hợp proposal]
    K --> L{Có hành động thay đổi cần phê duyệt}
    L -->|Không| V[Xác minh kết quả evidence và phạm vi project]
    L -->|Có| W[Trạng thái chờ phê duyệt]
    W --> X{Quyết định của người dùng}
    X -->|Sửa đề xuất| W
    X -->|Từ chối| V
    X -->|Duyệt| Y[Áp dụng tool thay đổi]
    Y --> V
    V --> N{Đạt điều kiện xác minh}
    N -->|Có và task COMPLETED| O[Hoàn tất và ghi bộ nhớ dài hạn đã xác minh]
    O --> X4([Kết thúc thành công])
    N -->|Có nhưng task INSUFFICIENT EVIDENCE| Z
    N -->|Không| Z2
```

### Các ràng buộc AI đang thực thi

- Capability trả về giao diện chỉ là capability mà vai trò hiện tại có quyền dùng
- Evidence phải cùng `project_id` với lượt chạy
- Bằng chứng từ vector và graph chỉ được giữ khi tham chiếu khớp artifact có thẩm quyền từ nguồn dự án
- Plan và tool call bị kiểm tra schema tham số quyền tool phạm vi dự án và định danh trước khi thực thi
- Workflow giới hạn một task được xử lý cho một lượt chạy
- Tool cần phê duyệt chỉ tạo đề xuất trước khi quyết định duyệt
- Khi áp dụng có xác minh lại kết quả áp dụng
- Kết quả hoàn tất phải có kiểm tra evidence phạm vi project và số lượng hành động được áp dụng
- Bộ nhớ dài hạn chỉ ghi khi lượt chạy hoàn tất và xác minh thành công

### Hai lớp trạng thái của lượt chạy AI

`run.status` mô tả workflow có chạy đến điểm kết thúc hay không còn `agent_results[].status` mô tả chất lượng của từng kết quả

```mermaid
flowchart TD
    A([Bắt đầu đánh giá kết quả]) --> B{Run status}
    B -->|COMPLETED| C{Result status}
    C -->|COMPLETED| D[Có kết quả đã hoàn tất] --> X1([Kết thúc thành công])
    C -->|INSUFFICIENT EVIDENCE| E[Workflow xong nhưng chưa đủ bằng chứng để trả lời] --> X2([Kết thúc có kết quả hạn chế])
    C -->|FAILED| F[Workflow xong nhưng task thất bại] --> X3([Kết thúc thất bại])
    B -->|FAILED| G[Workflow không vượt qua kiểm tra hoặc provider không sẵn sàng] --> X3
```

Vì vậy frontend không được chỉ hiển thị `run.status` như kết luận chất lượng câu trả lời Nó cần thể hiện đồng thời result status warnings và verification để người dùng phân biệt hoàn tất xử lý với có đủ bằng chứng

## Luồng kiểm soát frontend đến backend

Frontend là điểm khởi tạo thao tác và hiển thị trạng thái Backend mới là nơi quyết định quyền trạng thái dữ liệu idempotency retry fallback và compensation

```mermaid
flowchart TD
    S([Bắt đầu thao tác]) --> U[Người dùng gửi thao tác]
    U --> F[Frontend hiển thị đang xử lý và gửi request]
    F --> G[Traefik định tuyến]
    G --> B[Backend xác thực kiểm tra quyền dự án và kiểm tra dữ liệu]
    B --> A{Request hợp lệ}
    A -->|Không| R1[Trả lỗi có code trace id và giữ nội dung nhập ở frontend]
    R1 --> D1{Người dùng sửa và gửi lại}
    D1 -->|Có| U
    D1 -->|Không| E1([Kết thúc không thay đổi])
    A -->|Có| C[Backend đọc hoặc thay đổi trạng thái nghiệp vụ]
    C --> D{Dependency phản hồi}
    D -->|Thành công| R2[Trả dữ liệu revision và trạng thái operation]
    R2 --> F2[Frontend hiển thị hoàn tất]
    F2 --> E2([Kết thúc thành công])
    D -->|Lỗi retryable hoặc degraded| R3[Trả failure metadata]
    R3 --> D2{Người dùng chọn thử lại}
    D2 -->|Có| U
    D2 -->|Không| E3([Kết thúc cần can thiệp hoặc không hoàn tất])
    D -->|Lỗi không retryable| R4[Trả lỗi có cấu trúc]
    R4 --> E3
```

### Expected path

Đường thành công của backend phải đi qua các lớp sau trước khi thay đổi dữ liệu

- Xác thực phiên và xác định người dùng
- Kiểm tra tư cách thành viên hoặc quyền được cấp trong project
- Kiểm tra trạng thái hiện tại của entity và dữ liệu đầu vào
- Kiểm tra `revision` hoặc cơ chế idempotency ở các luồng có hỗ trợ
- Thực hiện thay đổi nghiệp vụ
- Trả dữ liệu cùng metadata operation để frontend hiển thị
- Ghi audit khi nghiệp vụ đó có audit

Frontend không được tự kết luận thao tác thành công trước response Backend Frontend chỉ chuyển trạng thái `streaming` `complete` hoặc `failed` dựa trên response hay stream nhận được

### Rejection không phải rollback

Các tình huống như không đủ quyền dữ liệu sai `revision` không khớp entity đã đổi trạng thái hoặc idempotency key xung đột được backend từ chối trước khi thay đổi thành công

Đây là cơ chế bảo toàn trạng thái hiện có không phải rollback Sau khi nhận lỗi frontend phải giữ dữ liệu người dùng đã nhập và hiển thị error code trace id cùng khả năng retry nếu response đánh dấu retryable

### Fallback và degradation hiện có

```mermaid
flowchart TD
    S([Bắt đầu gọi dependency]) --> A[Backend cần dependency hoặc model]
    A --> B{Loại phản hồi}
    B -->|Thành công| C[Quay lại expected path] --> E1([Kết thúc thành công])
    B -->|Lỗi tạm thời của model| D[Model runtime thử lần hiện tại]
    D --> E{Có kết quả hợp lệ}
    E -->|Có| C
    E -->|Không còn lượt thử| F[Trả lỗi AI provider unavailable] --> E2([Kết thúc thất bại])
    E -->|Còn lượt thử| D
    B -->|Tri thức không sẵn sàng| G[Gắn degraded flag]
    G --> H[Loại evidence không xác minh được]
    H --> I[Trả kết quả thiếu evidence theo ngữ cảnh] --> E3([Kết thúc có kết quả hạn chế])
    B -->|Worker lỗi tạm thời| J[Worker chạy handler lần hiện tại]
    J --> K{Hoàn tất}
    K -->|Có| C
    K -->|Còn lượt thử tự động| J
    K -->|Hết ba lượt thử| L[Ghi job failed]
    L --> M{Người dùng yêu cầu retry thủ công trong giới hạn}
    M -->|Có| N[Đặt job queued và publish lại hàng đợi]
    N --> J
    M -->|Không| E4([Kết thúc job failed])
```

Các fallback được xác nhận trong mã nguồn

- Model runtime thử lại tối đa ba lần với backoff trước khi báo lỗi
- Structured output có vòng sửa dữ liệu đầu ra trước khi coi là không hợp lệ
- Retrieval ghi degraded flags khi tri thức hoặc graph không sẵn sàng và không coi evidence không xác minh được là nguồn có thẩm quyền
- Worker thử lại handler tối đa ba lần rồi ghi job failed Người dùng có thể yêu cầu retry thủ công cho job failed trong giới hạn đã định
- API Testing trả metadata `retryable` `state_after_failure` và `user_action_required` cho lỗi có cấu trúc

Điều chưa có là fallback frontend tự gửi lại mọi request Việc tự gửi lại các thao tác ghi có thể tạo nhân bản hoặc làm sai ý người dùng Vì vậy frontend chỉ hiển thị retry theo ý người dùng và backend vẫn là nơi xác định thao tác có retry được hay không

### Rollback và compensation hiện có

```mermaid
flowchart TD
    S([Bắt đầu xác nhận import]) --> A[Xác nhận nhập Requirement]
    A --> B[Claim import job từ preview ready sang confirming]
    B --> C[Tạo lần lượt Requirement và phiên bản]
    C --> D{Tất cả mục đã tạo thành công}
    D -->|Có| E[Đánh dấu import confirmed và ghi audit]
    E --> E1([Kết thúc thành công])
    D -->|Không| F[Xóa Requirement và version vừa tạo trong lượt hiện tại]
    F --> G[Xóa artifact version liên quan]
    G --> H[Đặt import job về preview ready]
    H --> I[Ghi audit xác nhận import thất bại]
    I --> J[Trả người dùng về bản xem trước]
    J --> K{Người dùng sửa và xác nhận lại}
    K -->|Có| A
    K -->|Không| E2([Kết thúc không thay đổi thêm])
```

Rollback thật sự đã có trong luồng xác nhận Requirement import Khi một mục tạo thất bại hệ thống xóa các Requirement và version đã được tạo trong chính lượt xác nhận đó gỡ artifact version liên quan rồi trả import job về `PREVIEW_READY`

Ngoài luồng này hệ thống không có một rollback phân tán toàn cục bao phủ tất cả microservice Điều đó không được phép mô tả như đã có

Các luồng còn lại chủ yếu bảo vệ bằng state machine revision idempotency immutable snapshot archive và retry Các cơ chế này ngăn thay đổi sai hoặc phục hồi thao tác có kiểm soát nhưng không tương đương transaction xuyên service

### Cần được bổ sung nếu mở rộng nghiệp vụ có side effect nhiều service

Khi một thao tác mới ghi dữ liệu ở nhiều service phải xác định rõ trước khi build

- Expected state sau từng bước
- Idempotency key và revision dùng để chống gửi lại
- Side effect nào có thể retry và side effect nào phải yêu cầu người dùng xác nhận lại
- Compensation cụ thể của từng bước khi bước sau thất bại
- Trạng thái lỗi cuối cùng có thể quan sát được
- Chủ thể được phép retry resume cancel hoặc discard

Không được dùng rollback giả bằng cách xóa toàn bộ dữ liệu hoặc tự chạy lại thao tác ghi mà chưa xác định idempotency và compensation

## Khung triển khai hệ thống

```mermaid
flowchart LR
    U[Người dùng trên trình duyệt] --> FE[Next.js Frontend]
    FE --> NG[Nginx]
    NG --> TR[Traefik API Gateway]

    TR --> AU[Authentication]
    TR --> TE[Testing]
    TR --> AI[AI]
    TR --> CO[Content]
    TR --> CL[Cloud]
    TR --> NO[Notification]
    TR --> WO[Worker API]

    AU --> MO[(MongoDB)]
    AU --> RE[(Redis)]
    TE --> MO
    CO --> MO
    CL --> MO
    NO --> MO
    WO --> MO
    AI --> MO

    CO --> OS[(S3 compatible object storage)]
    CL --> OS
    AI --> OS
    AI --> QD[(Qdrant)]
    AI --> NE[(Neo4j)]
    TE --> AI
    TE --> CO
    TE --> CL
    TE --> WO

    TE --> MQ[(RabbitMQ)]
    CO --> MQ
    AI --> MQ
    MQ --> WO

    PR[Prometheus] --> AU
    PR --> TE
    PR --> AI
    PR --> CO
    PR --> CL
    PR --> NO
    PR --> WO
    PR --> TR
    GR[Grafana] --> PR
```

### Phân định trách nhiệm service

| Thành phần | Trách nhiệm đã đối chiếu |
| --- | --- |
| Frontend và Nginx | Hiển thị giao diện và phục vụ frontend |
| Traefik | Cổng vào API và định tuyến theo path |
| Authentication | Phiên xác thực khóa bảo mật Google OAuth và quản trị hệ thống |
| Testing | Dự án Requirements thiết kế thực thi chất lượng tích hợp và vận hành kiểm thử |
| AI | Inference agent indexing retrieval tri thức và phê duyệt agent |
| Content | Tài liệu phiên bản metadata và cấu trúc tài liệu |
| Cloud | Tệp thư mục tải lên tải về chia sẻ tìm kiếm và phân đoạn tệp |
| Worker và RabbitMQ | Xếp hàng và xử lý tác vụ nền |
| MongoDB | Dữ liệu nghiệp vụ theo database service |
| Redis | Cache phiên và dữ liệu tạm |
| Qdrant | Vector retrieval |
| Neo4j | Quan hệ artifact và truy vết đồ thị |
| Object storage | Đối tượng tệp |
| Prometheus và Grafana | Thu thập và quan sát metrics |

## Ranh giới không được suy diễn

- Sơ đồ không khẳng định tất cả capability AI đều thành công với mọi dữ liệu đầu vào
- Sơ đồ không coi thông tin chưa được xác nhận là evidence
- Sơ đồ không coi template là test case template
- Sơ đồ không nói AI được quyền tự thay đổi dữ liệu nghiệp vụ
- Sơ đồ không thay thế kiểm thử tích hợp và kiểm thử hồi quy khi có thay đổi mã nguồn
