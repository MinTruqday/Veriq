# Framework Veriq

## Mục đích và căn cứ

Tài liệu này thay thế bản framework trước và chỉ mô tả hành vi đã đối chiếu trong mã nguồn Veriq

Nó không suy diễn từ tên service  từ ảnh vẽ hay từ một dependency được khai báo trong Docker

Các nguồn đối chiếu chính

- `docker-compose.yml` và `nginx.conf`
- `frontend/shared/services/api-client.js`
- `backend/testing/src/main.py` và `backend/testing/src/clients`
- `backend/ai/src/main.py`  `backend/ai/src/agents/runner/graph.py` và `backend/ai/src/knowledge/hybrid.py`
- `backend/content/src/clients`
- `backend/worker/src/main.py`  `backend/worker/src/services.py` và `backend/worker/src/jobs/task.py`
- `backend/testing/src/modules/requirements/services/requirement_import_workflow.py`

Tài liệu tách riêng bốn vấn đề để tránh lẫn lộn

- Kiến trúc microservice
- Vòng đời nghiệp vụ kiểm thử
- Hoạt động AI
- Retry  fallback  compensation và các điểm kết thúc

## Quy ước sơ đồ

| Ký hiệu | Ý nghĩa |
| --- | --- |
| Hình bo tròn | Bắt đầu hoặc kết thúc |
| Hình chữ nhật | Hoạt động có chủ thể chịu trách nhiệm |
| Hình thoi | Quyết định  phải có các nhánh đầy đủ |
| Mũi tên liền | Lời gọi hoặc chuyển trạng thái được mã nguồn xác nhận |
| Mũi tên nét đứt | Quan sát  giám sát hoặc quan hệ dữ liệu |
| Không thay đổi | Request bị dừng trước khi có thay đổi bền vững |
| Cần can thiệp | Không có compensation tự động cho tình huống đó |

## Sự thật không được vẽ sai

1  Frontend có cổng trực tiếp `3000`

2  Traefik nhận API ở cổng `8000`

3  Nginx chỉ reverse proxy Frontend khi đi qua route gốc của Traefik  Nginx không nằm trên mọi request API

4  Testing sở hữu Projects  Requirements  Design  Execution  Quality  Integrations và Operations

5  Testing gọi AI qua API nội bộ  Testing không truy cập trực tiếp Qdrant hay Neo4j

6  Luồng tác vụ nền được xác nhận là Testing → Worker API → RabbitMQ → Worker consumer → Testing internal callback

7  Content kích hoạt AI indexing qua HTTP webhook đến event queue trong bộ nhớ của AI  Đây không phải RabbitMQ

8  Không có distributed transaction hoặc rollback chung cho toàn hệ thống

9  Các service dùng cùng MongoDB deployment nhưng có database logic riêng  Không service nào tự sở hữu dữ liệu của service khác

10  AI không tự baseline  approve  publish  archive hoặc áp dụng thay đổi nghiệp vụ thay người dùng

## 1  Bối cảnh triển khai và điểm vào

```mermaid
flowchart LR
    U[Người dùng trên trình duyệt]
    FE[Next Frontend cổng 3000]
    GW[Traefik API Gateway cổng 8000]
    NX[Nginx reverse proxy]

    U -->|Giao diện phát triển| FE
    U -->|API theo NEXT_PUBLIC_API_URL| GW
    U -->|Route gốc qua gateway| GW
    GW -->|Route gốc| NX
    NX --> FE

    GW --> AU[Authentication]
    GW --> TE[Testing]
    GW --> AI[AI]
    GW --> CO[Content]
    GW --> CL[Cloud]
    GW --> NO[Notification]
    GW --> WO[Worker API]
```

Không được vẽ đường Frontend → Nginx → Traefik → Backend như một đường bắt buộc  Frontend gọi API qua URL cấu hình và Traefik định tuyến API theo path

## 2  Luồng microservice đã xác nhận

```mermaid
flowchart TB
    subgraph Edge[Điểm vào]
        FE[Frontend]
        TR[Traefik]
    end

    subgraph Services[Backend services]
        AU[Authentication]
        TE[Testing]
        AI[AI]
        CO[Content]
        CL[Cloud]
        NO[Notification]
        WO[Worker]
    end

    FE -->|Bearer token request| TR
    TR --> AU
    TR --> TE
    TR --> AI
    TR --> CO
    TR --> CL
    TR --> NO
    TR --> WO

    TE -->|X Internal Token<br/>AI assistance stream hoặc result| AI
    TE -->|X Internal Token<br/>index search delete project artifact| AI
    TE -->|X Internal Token<br/>requirement source read write| CL
    TE -->|X Internal Token<br/>enqueue get retry cancel job| WO
    TE -->|X Internal Token<br/>session and account checks| AU

    CO -->|X Internal Token<br/>document indexing webhook and delete index| AI
    CO -->|X Internal Token<br/>create in app notification| NO
    CO -->|X Internal Token<br/>session and account checks| AU

    CL -->|X Internal Token<br/>session and account checks| AU
    AI -->|X Internal Token<br/>session checks| AU
    AI -->|X Internal Token<br/>read permitted document exchange| CO
    NO -->|X Internal Token<br/>session and account checks| AU
    WO -->|X Internal Token<br/>background job callback| TE
```

Mỗi mũi tên trên là client nội bộ hoặc callback có trong mã nguồn

Không thêm mũi tên giữa hai service chỉ vì chúng cùng dùng Docker network  MongoDB hoặc Redis

## 3  Hai loại xác thực

```mermaid
flowchart TD
    S([Bắt đầu request]) --> A{Nguồn request}
    A -->|Trình duyệt| B[Bearer access token]
    B --> C[Service xác minh token]
    C --> D[Authentication xác minh session khi service yêu cầu]
    D --> E{Có quyền hệ thống và quyền project}
    A -->|Service nội bộ| F[X Internal Token]
    F --> G{Token nội bộ hợp lệ}
    G -->|Không| X1([403 kết thúc không thay đổi])
    G -->|Có| H[Kiểm tra điều kiện nghiệp vụ]
    E -->|Không| X2([Từ chối quyền kết thúc không thay đổi])
    E -->|Có| H
    H --> I{Dữ liệu và trạng thái hợp lệ}
    I -->|Không| X3([Lỗi hợp lệ kết thúc không thay đổi])
    I -->|Có| J[Thực hiện nghiệp vụ]
    J --> X4([Trả kết quả])
```

Bearer token và X Internal Token là hai cơ chế khác nhau  Không được gộp thành một ô JWT chung

## 4  Sở hữu dữ liệu và hạ tầng

```mermaid
flowchart TB
    AU[Authentication] -. database xác thực .-> MO[(MongoDB)]
    TE[Testing] -. database kiểm thử .-> MO
    AI[AI] -. database AI .-> MO
    CO[Content] -. database tài liệu .-> MO
    CL[Cloud] -. database lưu trữ .-> MO
    NO[Notification] -. database thông báo .-> MO
    WO[Worker] -. database job .-> MO

    AU -. cache session .-> RE[(Redis)]
    TE -. cache hoặc rate state .-> RE
    AI -. cache hoặc rate state .-> RE
    CO -. cache hoặc rate state .-> RE
    CL -. cache hoặc rate state .-> RE
    NO -. cache hoặc rate state .-> RE

    AI --> QD[(Qdrant vector store)]
    AI --> NE[(Neo4j artifact graph)]
    CL --> OS[(S3 compatible object storage)]
    AI --> OS

    TE -->|Gọi Worker API| WO
    WO -->|Publish durable message| MQ[(RabbitMQ)]
    MQ -->|Consumer nhận message| WO

    PR[Prometheus] -. scrape metrics .-> AU
    PR -. scrape metrics .-> TE
    PR -. scrape metrics .-> AI
    PR -. scrape metrics .-> CO
    PR -. scrape metrics .-> CL
    PR -. scrape metrics .-> NO
    PR -. scrape metrics .-> WO
    PR -. scrape metrics .-> TR[Traefik]
    GR[Grafana] --> PR
```

Qdrant và Neo4j thuộc đường tri thức AI  Object storage giữ bytes của tệp còn Cloud quản lý thao tác và metadata file

## 5  Tác vụ nền  retry và dead letter

```mermaid
flowchart TD
    S([Bắt đầu tác vụ nền]) --> A[Testing tạo yêu cầu job]
    A --> B[Worker API tạo job queued bằng idempotency key]
    B --> C{Publish RabbitMQ thành công}
    C -->|Không| C1[Đánh dấu job failed queue unavailable]
    C1 --> X1([Kết thúc không xếp hàng])
    C -->|Có| D[RabbitMQ durable queue]
    D --> E[Worker consumer nhận message]
    E --> F{Payload hợp lệ}
    F -->|Không| G[Reject không requeue vào dead letter queue]
    G --> X2([Kết thúc failed])
    F -->|Có| H[Đánh dấu job running]
    H --> I[Chạy handler]
    I --> J{Handler thành công}
    J -->|Có| K[Ack message và ghi completed]
    K --> X3([Kết thúc thành công])
    J -->|Không và lỗi vĩnh viễn| L[Ghi failed và reject không requeue]
    J -->|Không và lỗi tạm thời| M{Còn trong ba lần thử của consumer}
    M -->|Có| I
    M -->|Không| L
    L --> N{Người dùng yêu cầu retry thủ công}
    N -->|Có và chưa vượt chín lần retry thủ công| B
    N -->|Không| X4([Kết thúc failed cần xử lý])
```

Consumer thử handler tối đa ba lần trong một lần nhận message  Job failed có thể retry thủ công tối đa chín lần  Đây không phải cơ chế retry chung cho toàn bộ API

## 6  Vòng đời Requirements và ranh giới template

```mermaid
flowchart TD
    S([Bắt đầu Requirements]) --> A[Người dùng có quyền chọn project]
    A --> B{Nguồn đầu vào}
    B -->|Template starter hoặc template project| C[Chọn template và phiên bản]
    B -->|SRS User Story hoặc tài liệu nguồn| D[Lưu hoặc đọc requirement source]
    B -->|API definition| E[Đọc đặc tả API]
    B -->|Nhập tay| F[Tạo requirement draft]
    C --> G[Tạo preview requirement candidates]
    D --> H[Trích xuất candidate có source reference]
    E --> H
    F --> G
    H --> G
    G --> I[Kiểm tra quyền đọc nguồn và source reference]
    I --> J{Nguồn hợp lệ và candidate có nội dung}
    J -->|Không| K[Giữ preview để người dùng sửa hoặc bổ sung]
    K --> G
    J -->|Có| L[So sánh requirement hiện có và candidate trong lần import]
    L --> M{Có trùng hoặc xung đột}
    M -->|Có| N[Người dùng gộp tách từ chối hoặc phân giải]
    N --> G
    M -->|Không| O[Người dùng chọn candidate để import]
    O --> P{Xác nhận import}
    P -->|Không| X1([Giữ preview hoặc kết thúc không thay đổi])
    P -->|Có| Q[Claim job preview ready sang confirming]
    Q --> R[Tạo Requirement và Requirement Version]
    R --> T{Tất cả candidate đã chọn được tạo}
    T -->|Có| U[Confirm import và ghi audit]
    U --> V[Requirement sẵn sàng cho phân tích kiểm thử]
    V --> X2([Kết thúc thành công])
    T -->|Không| W[Compensation của import hiện tại]
    W --> W1[Xóa record và artifact version vừa tạo]
    W1 --> W2[Reset job về preview ready và ghi audit lỗi]
    W2 --> K
```

Template kết thúc khi Requirement sẵn sàng cho phân tích kiểm thử  Template không tạo test case

## 7  Vòng đời kiểm thử cấp nghiệp vụ

```mermaid
flowchart TD
    S([Bắt đầu]) --> A[Requirement version đã xác nhận]
    A --> B[Phân tích kiểm thử]
    B --> C[Điều kiện kiểm thử và finding]
    C --> D{Requirement cần làm rõ hoặc thay đổi}
    D -->|Có| A
    D -->|Không| E[Thiết kế kịch bản test case dữ liệu và chiến lược]
    E --> F[Review và phê duyệt theo workflow]
    F --> G{Được dùng cho thực thi}
    G -->|Chưa| E
    G -->|Có| H[Lập suite test run build và environment]
    H --> I[Thực thi và ghi test result]
    I --> J{Có defect finding hay change impact}
    J -->|Có| K[Quản lý defect change impact regression và truy vết]
    K --> L{Cần cập nhật Requirement hoặc Test Design}
    L -->|Có| A
    L -->|Không| H
    J -->|Không| M[Báo cáo trạng thái hoặc hoàn tất kiểm thử]
    M --> X([Kết thúc])
```

Không được vẽ mọi defect tự động sửa Requirement  Điểm quay về Requirement chỉ xảy ra khi có thay đổi ảnh hưởng hoặc cần làm rõ

## 8  AI assistance của Testing

```mermaid
flowchart TD
    S([Bắt đầu AI assistance]) --> A[Testing kiểm tra quyền project và input]
    A --> B[Testing gọi AI internal assistance]
    B --> C{Có yêu cầu streaming}
    C -->|Có| D[AI gửi SSE delta result hoặc error]
    C -->|Không| E[AI trả structured result]
    D --> F[Testing chuyển trạng thái xử lý cho Frontend]
    E --> F
    F --> G{Kết quả hợp lệ và có evidence}
    G -->|Không| H[Trả draft hoặc lỗi retryable khi phù hợp]
    H --> X1([Kết thúc không tự thay đổi dữ liệu])
    G -->|Có| I[Tạo hoặc cập nhật bản nháp hay proposal]
    I --> J[Người dùng review và xác nhận theo nghiệp vụ]
    J --> X2([Kết thúc])
```

AI assistance không tự áp dụng thay đổi vào bản chính chỉ vì model đã trả output

## 9  AI agent workflow

```mermaid
flowchart TD
    S([Bắt đầu Agent Run]) --> A[Kiểm tra token quyền project capability]
    A --> B{Được phép chạy}
    B -->|Không| X1([Từ chối không tạo run])
    B -->|Có| C[Tạo run với user role project intent]
    C --> D[Nạp ngữ cảnh]
    D --> E[Truy hồi artifact có thẩm quyền từ Testing]
    E --> F[Truy hồi vector Qdrant graph Neo4j và verified memory]
    F --> G[Chỉ giữ vector graph khớp artifact có thẩm quyền]
    G --> H{Intent có tool trực tiếp hợp lệ}
    H -->|Có| I[Tạo một task trực tiếp]
    H -->|Không| J[Model lập plan có cấu trúc]
    J --> K{Plan và tool call hợp lệ}
    K -->|Không| X2([Kết thúc failed hoặc insufficient evidence])
    K -->|Có| I
    I --> L[Thực thi tool trong phạm vi project]
    L --> M{Tool cần phê duyệt trước khi thay đổi}
    M -->|Có| N[Đặt approval required và lưu proposal]
    N --> O{Người dùng duyệt}
    O -->|Không| P[Xác minh kết quả không áp dụng]
    O -->|Có| Q[Apply tool]
    M -->|Không| P
    Q --> P
    P --> R{Verification thành công}
    R -->|Có| T[Lưu run và verified long term memory khi completed]
    T --> X3([Kết thúc completed])
    R -->|Không| X4([Kết thúc failed hoặc insufficient evidence])
```

Agent workflow xử lý tối đa một task trong một lượt chạy theo giới hạn hiện tại  Không được vẽ nhiều agent chạy song song trong một Agent Run

## 10  Evidence  fallback và compensation

```mermaid
flowchart TD
    S([Bắt đầu dependency call]) --> A{Loại dependency}
    A -->|Model provider| B[Retry có giới hạn theo model runtime]
    B --> C{Có output hợp lệ}
    C -->|Có| X1([Quay lại workflow])
    C -->|Không| X2([Trả provider unavailable hoặc invalid output])
    A -->|Knowledge vector graph| D[Gắn degraded flag]
    D --> E[Chỉ dùng evidence còn xác minh được]
    E --> F{Đủ evidence}
    F -->|Có| X1
    F -->|Không| X3([Trả insufficient evidence])
    A -->|Worker task| G[Consumer thử handler tối đa ba lần]
    G --> H{Thành công}
    H -->|Có| X1
    H -->|Không| I[Ghi failed và reject message không requeue]
    I --> J{Người dùng retry thủ công trong giới hạn}
    J -->|Có| G
    J -->|Không| X4([Failed cần xử lý])
    A -->|Import Requirement sau ghi một phần| K[Chạy compensation riêng của import]
    K --> L{Compensation thành công}
    L -->|Có| X5([Preview ready để người dùng xử lý lại])
    L -->|Không| X6([Cần can thiệp thủ công])
```

Không có rollback toàn cục giữa MongoDB  Qdrant  Neo4j  object storage và RabbitMQ

Không có fallback nào cho phép AI tự bịa dữ liệu hoặc tự bỏ qua xác nhận của người dùng

## Checklist trước khi vẽ lại

- Mỗi service chỉ vẽ mũi tên đến service có client hoặc callback thật
- Mỗi request ghi dữ liệu phải có kết thúc thành công  từ chối trước ghi  lỗi sau ghi hoặc compensation
- Mọi hình thoi có nhánh Có và Không
- Mọi nhánh lỗi phải có kết thúc hoặc quay lại checkpoint xác định
- Không ghi rollback nếu chỉ là validation  rejection  archive hoặc retry
- Không ghi fallback nếu chưa có hành vi thay thế trong mã nguồn
- Không ghi event driven cho HTTP webhook hay queue trong bộ nhớ
- Không ghi multi agent parallel cho Agent Run hiện tại
- Không vẽ Testing truy cập trực tiếp Qdrant hoặc Neo4j
- Không vẽ AI tự sửa dữ liệu chính nếu chưa có approval hoặc xác nhận nghiệp vụ

## Giới hạn tài liệu

- Tài liệu mô tả kiến trúc và luồng từ mã nguồn hiện tại  không thay thế kiểm thử tích hợp đầy đủ cho từng endpoint
- Một dependency trong Docker Compose không chứng minh nó được gọi trong mọi nghiệp vụ
- Workflow mới ghi qua nhiều service phải được thiết kế idempotency  trạng thái quan sát được và compensation riêng trước khi được thêm vào framework
