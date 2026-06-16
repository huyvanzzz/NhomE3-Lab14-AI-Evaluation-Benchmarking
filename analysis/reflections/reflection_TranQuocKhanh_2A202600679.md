# Báo cáo cá nhân - Trần Quốc Khánh

- Họ và tên: Trần Quốc Khánh
- Mã sinh viên: 2A202600679
- Nhóm: E3
- Vai trò: Multi-Judge Consensus

## 1. Engineering Contribution

Trong dự án này, tôi phụ trách phần Multi-Judge Consensus, tập trung vào module `engine/llm_judge.py`. Mục tiêu của phần này là tạo một cơ chế chấm điểm có nhiều góc nhìn, không chỉ dựa vào một điểm số đơn lẻ.

Các đóng góp chính:

- Xây dựng logic judge offline deterministic để benchmark có thể chạy ổn định mà không cần API key.
- Thiết kế hai góc nhìn judge:
  - `offline_accuracy_judge`: ưu tiên độ đúng của câu trả lời so với ground truth.
  - `offline_safety_relevance_judge`: ưu tiên safety, relevancy, refusal correctness và cách xử lý case đặc biệt.
- Tính `final_score`, `agreement_rate`, `score_delta`, `conflict_resolved`, `cohens_kappa` và `position_bias_detected`.
- Thêm logic conflict resolution: khi hai judge lệch điểm lớn, hệ thống không lấy điểm cao nhất mà xử lý bảo thủ hơn để tránh approve câu trả lời gây tranh cãi.
- Đảm bảo output của judge có schema ổn định để `engine/runner.py`, `main.py`, `reports/summary.json` và `reports/benchmark_results.json` có thể sử dụng.

File phụ trách chính:

- `engine/llm_judge.py`

File dùng để đối chiếu kết quả:

- `reports/summary.json`
- `reports/benchmark_results.json`

## 2. Technical Depth

### Agreement Rate

Agreement Rate đo mức độ đồng thuận trực tiếp giữa hai judge. Nếu hai judge cho điểm giống nhau, agreement cao. Nếu điểm lệch nhau nhiều, agreement giảm. Chỉ số này giúp nhóm biết kết quả chấm điểm có ổn định hay không.

### Cohen's Kappa

Cohen's Kappa đo mức độ đồng thuận sau khi tính đến khả năng đồng thuận do ngẫu nhiên. Trong benchmark hiện tại, `cohens_kappa = 1.0`, cho thấy hai judge offline đồng thuận hoàn toàn trên candidate run.

### Conflict Resolution

Nếu hai judge lệch nhau hơn 1 điểm, hệ thống đánh dấu `conflict_resolved = true` và dùng cách tính điểm bảo thủ hơn. Điều này quan trọng vì trong hệ thống thực tế, một câu trả lời có điểm tranh cãi không nên được approve chỉ vì một judge chấm cao.

### Position Bias

Position bias là hiện tượng judge bị ảnh hưởng bởi thứ tự xuất hiện của câu trả lời. Trong phiên bản hiện tại, hệ thống có trường `position_bias_detected` để theo dõi rủi ro này. Benchmark mới nhất ghi nhận `position_bias_cases = 0`.

### Cost vs Quality

Phiên bản hiện tại dùng offline deterministic judge để giảm chi phí và đảm bảo chạy được trong môi trường nộp bài. Hướng mở rộng sau này là chỉ gọi real LLM judge cho những case có disagreement, score thấp hoặc rủi ro cao. Cách này giúp cân bằng giữa chất lượng đánh giá và chi phí.

## 3. Problem Solving

Vấn đề khó nhất là làm sao tạo được multi-judge consensus mà vẫn giữ pipeline ổn định. Nếu phụ thuộc hoàn toàn vào real API, benchmark có thể fail do thiếu key, lỗi mạng, rate limit hoặc chi phí. Giải pháp là dùng offline deterministic judge làm default.

Cách tiếp cận này giúp:

- Benchmark chạy lặp lại và ổn định.
- Không phụ thuộc API key.
- Vẫn có đủ các trường cần thiết cho rubric: agreement rate, Cohen's Kappa, conflict handling và position bias.
- Dễ mở rộng sang real LLM judge sau này nếu cần.

## 4. Result

Kết quả trong `reports/summary.json`:

- Multi-Judge Agreement Rate: 1.0
- Cohen's Kappa: 1.0
- Position-bias cases: 0
- Average judge score: 5.0 / 5.0

Kết quả này cho thấy phần Multi-Judge Consensus hoạt động ổn định trên benchmark hiện tại.

## 5. Lessons Learned

Qua phần việc này, tôi hiểu rằng judge reliability rất quan trọng trong AI evaluation. Nếu chỉ dùng một judge duy nhất, kết quả có thể bị bias hoặc không ổn định. Multi-judge consensus giúp tăng độ tin cậy, nhưng cũng cần quan tâm đến chi phí, latency và conflict handling. Trong tương lai, tôi muốn bổ sung real LLM judge optional cho các case khó hoặc case mà hai judge offline bất đồng.
