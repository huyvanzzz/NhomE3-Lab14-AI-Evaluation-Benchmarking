# Báo cáo Cá nhân (Individual Reflection Report)

*   **Họ và tên:** Trần Trung Kiên
*   **Mã số sinh viên:** 2A202600850
*   **Nhóm:** E3 (Lab Day 14 - AI Evaluation Factory)

---

## 1. Đóng góp kỹ thuật (Engineering Contribution)

Trong dự án này, tôi chịu trách nhiệm chính về phần **Thiết kế & Triển khai Module Sinh dữ liệu tự động (SDG) và xây dựng Golden Dataset**.

### Các công việc cụ thể:
1.  **Thiết kế và hoàn thiện script sinh dữ liệu** [synthetic_gen.py](file:///D:/My%20Works/Coding/Practice/NhomE3-Lab14-AI-Evaluation-Benchmarking/data/synthetic_gen.py):
    *   Tích hợp thư viện `openai` và `python-dotenv` để gọi LLM sinh câu hỏi, câu trả lời kỳ vọng (`expected_answer`), và ngữ cảnh (`context`) từ văn bản thô.
    *   Xây dựng cơ chế **Fallback Mode** chứa sẵn tập dữ liệu tĩnh chất lượng cao để đảm bảo hệ thống có thể chạy offline hoặc chạy test ngay lập tức mà không gặp lỗi thiếu API key.
2.  **Thiết kế Golden Dataset** [golden_set.jsonl](file:///D:/My%20Works/Coding/Practice/NhomE3-Lab14-AI-Evaluation-Benchmarking/data/golden_set.jsonl) gồm **52 cases** đa dạng nhằm kiểm thử toàn diện khả năng của Agent:
    *   **15 cases Easy/Fact-check:** Hỏi đáp các thông tin cơ bản về nội quy làm việc, thông tin IT hỗ trợ, chính sách phúc lợi gửi xe, lương tháng 13.
    *   **12 cases Adversarial (Red Teaming):** Kiểm tra độ an toàn của Agent trước các hình thức tấn công Prompt Injection (yêu cầu bỏ qua chỉ thị cũ), Goal Hijacking (yêu cầu viết thơ chính trị, tư vấn tình cảm), hoặc dụ hệ thống cung cấp mật khẩu hệ thống/hướng dẫn độc hại.
    *   **12 cases Edge Cases (Out of Context, Ambiguous, Conflicting):** Thử thách khả năng xử lý mập mờ của Agent (hỏi chung chung "tôi bị lỗi rồi"), khả năng từ chối lịch sự khi câu hỏi nằm ngoài tài liệu (Out of Context), và cách giải quyết thông tin mâu thuẫn (quy chế cũ viết khác, quy chế mới viết khác).
    *   **13 cases Multi-turn Complexity:** Các câu hỏi liên đới có mang theo ngữ cảnh (Context Carry-over) kiểm định bộ nhớ hội thoại của Agent (ví dụ: câu hỏi 1 về lỗi VPN, câu hỏi 2 hỏi về "bước thứ hai bạn vừa nêu thực hiện thế nào").

---

## 2. Kiến thức chuyên sâu (Technical Depth)

### 2.1. Mean Reciprocal Rank (MRR)
*   **Định nghĩa & Công thức:** MRR là độ đo dùng để đánh giá chất lượng của một hệ thống tìm kiếm (Retrieval). Công thức tính cho tập truy vấn \(Q\):
    \[MRR = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}\]
    Trong đó, \(\text{rank}_i\) là thứ vị trí (chỉ mục 1-indexed) của tài liệu đúng đầu tiên (ground truth document) được tìm thấy trong danh sách tài liệu trả về. Nếu không tìm thấy bất kỳ tài liệu liên quan nào, \(\frac{1}{\text{rank}_i} = 0\).
*   **Ý nghĩa:** MRR phản ánh trải nghiệm người dùng trong việc tìm kiếm: tài liệu mong muốn nằm ở vị trí càng cao (gần top 1) thì điểm MRR càng tiến gần về 1.0. Điểm MRR cao chứng minh thuật toán tìm kiếm và cấu trúc Vector DB/Chunking hoạt động hiệu quả.

### 2.2. Cohen's Kappa
*   **Định nghĩa & Công thức:** Hệ số Cohen's Kappa (\(\kappa\)) đo lường sự đồng thuận giữa 2 đánh giá viên (ở đây là 2 LLM Judges độc lập) sau khi đã loại trừ đi xác suất đồng thuận ngẫu nhiên. Công thức:
    \[\kappa = \frac{p_o - p_e}{1 - p_e}\]
    *   \(p_o\): Tỷ lệ đồng thuận quan sát được thực tế giữa các đánh giá viên.
    *   \(p_e\): Tỷ lệ đồng thuận kỳ vọng ngẫu nhiên (hypothetical probability of chance agreement).
*   **Ứng dụng:** Cohen's Kappa dùng để hiệu chuẩn độ tin cậy của Multi-Judge Consensus Engine. Nếu hệ số \(\kappa \ge 0.61\), độ đồng thuận được coi là tốt và điểm số đáng tin cậy. Nếu thấp hơn, hệ thống cần kích hoạt thêm logic trọng tài (Judge thứ 3) hoặc xem xét lại Rubric chấm điểm của prompt.

### 2.3. Position Bias (Thiên vị vị trí)
*   **Hiện tượng:** LLM Judge khi so sánh hai câu trả lời (A và B) để chấm điểm thường có xu hướng chọn câu trả lời xuất hiện ở vị trí đầu tiên trong prompt, bất kể chất lượng thực tế.
*   **Giải pháp xử lý:**
    1.  **Position Swap (Đổi chỗ vị trí):** Thực hiện đánh giá 2 lần bằng cách đảo vị trí truyền vào prompt (lần 1: A trước B, lần 2: B trước A). Điểm số cuối cùng là điểm trung bình của cả 2 lần chạy.
    2.  **Độc lập hóa:** Cho Judge chấm điểm tuyệt đối độc lập của từng câu trả lời theo thang Rubric cố định (1-5) thay vì so sánh tương đối A và B.

### 2.4. Trade-off giữa Chi phí và Chất lượng (Cost vs Quality)
*   Khi đánh giá hàng ngàn test cases, việc chỉ sử dụng các mô hình LLM cao cấp (ví dụ: GPT-4o, Claude 3.5 Sonnet) làm Judge sẽ rất tốn chi phí và thời gian (latency cao).
*   **Chiến lược tối ưu hóa (Hybrid Judge):**
    *   Sử dụng mô hình nhỏ và rẻ (như GPT-4o-mini, Claude 3 Haiku) để thực hiện đánh giá sơ bộ đầu tiên.
    *   Nếu mô hình nhỏ đưa ra kết quả với độ tin cậy cao (ví dụ: điểm tuyệt đối 5/5 hoặc 1/5 và thống nhất cao), ta ghi nhận kết quả ngay.
    *   Nếu kết quả rơi vào vùng không chắc chắn (điểm trung bình 3/5 hoặc có sự xung đột cao), hệ thống mới chuyển yêu cầu đó lên cho mô hình lớn (GPT-4o) làm trọng tài. Cách tiếp cận này giúp giảm khoảng 30% - 50% chi phí mà không làm giảm độ chính xác chung của hệ thống.

---

## 3. Giải quyết vấn đề (Problem Solving)

Trong quá trình triển khai, tôi đã gặp và giải quyết các bài toán kỹ thuật sau:
1.  **Lỗi mã hóa ký tự Unicode trên Windows (`UnicodeEncodeError`):**
    *   *Vấn đề:* Khi chạy script Python qua PowerShell trên Windows, việc in các emoji và ký tự tiếng Việt có dấu ra stdout gây ra lỗi `charmap codec can't encode character`.
    *   *Giải quyết:* Tôi cấu hình lại luồng xuất chuẩn `sys.stdout.reconfigure(encoding='utf-8')` ngay đầu file Python để ép môi trường sử dụng chuẩn mã hóa UTF-8.
2.  **Quản lý Rate Limit của nhà cung cấp API:**
    *   *Vấn đề:* Khi chạy song song toàn bộ 50+ test cases đồng thời bằng `asyncio.gather`, API dễ bị quá tải hạn mức số request/phút (RPM).
    *   *Giải quyết:* Tách bộ dữ liệu thành từng batch nhỏ (`batch_size = 5`) để gửi yêu cầu lần lượt, đảm bảo hệ thống vừa duy trì được tốc độ nhanh vừa không vượt quá giới hạn của API.
3.  **Tạo các câu hỏi Adversarial chất lượng cao:**
    *   *Vấn đề:* LLM nếu chỉ sinh dữ liệu tự động theo cách thông thường sẽ sinh ra những câu hỏi quá đơn giản, không đủ độ khó để thử thách Agent.
    *   *Giải quyết:* Tôi đã thiết kế thủ công các câu hỏi thuộc dạng Red Teaming cực kỳ tinh vi (như ngụy trang dưới dạng lệnh của quản trị viên hệ thống hoặc dùng kỹ thuật "System Override") để kiểm định độ vững chắc bảo mật của Agent.
