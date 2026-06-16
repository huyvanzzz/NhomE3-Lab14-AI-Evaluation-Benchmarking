# Báo cáo cá nhân (Individual Reflection Report)

- Họ và tên: Nguyễn Anh Kiệt
- Nhóm: E3
- Lab: Lab Day 14 - AI Evaluation Factory
- Vai trò: Performance Async

## 1. Đóng góp kỹ thuật

Trong dự án này, vai trò chính của tôi là phụ trách phần **Performance Async** của hệ thống benchmark. Các file liên quan trực tiếp đến phần việc của tôi gồm:

- `engine/runner.py`
- `requirements.txt`
- `reports/summary.json`
- `reports/benchmark_results.json`

Trong file `engine/runner.py`, tôi phụ trách triển khai luồng chạy benchmark bất đồng bộ bằng `asyncio.gather`. Mỗi test case được xử lý qua hàm `run_single_test`, gồm các bước chính: gọi agent, đo latency bằng `time.perf_counter`, chạy bộ đánh giá retrieval, chạy multi-judge evaluator, sau đó trả về kết quả có cấu trúc.

Kết quả của mỗi test case bao gồm:

- mã case và loại case
- expected answer và agent response
- contexts được truy xuất và retrieved ids
- latency
- token usage
- estimated cost
- điểm RAGAS/retrieval
- kết quả judge
- failure category và trạng thái pass/fail

Trong hàm `run_all`, tôi sử dụng cơ chế chạy song song theo batch với `batch_size = 10`. Cách này giúp pipeline chạy đủ nhanh, nhưng vẫn kiểm soát được số lượng request đồng thời để tránh gây áp lực quá lớn lên hệ thống hoặc API. Kết quả benchmark cuối cùng cho thấy agent phiên bản tối ưu xử lý **60 cases trong 0.275 giây**, latency trung bình **0.043 giây**, p95 latency **0.047 giây**, và throughput đạt **218.4 cases/giây**.

Tôi cũng đảm bảo output của benchmark có đầy đủ thông tin phục vụ tiêu chí Performance Async:

- tổng số token: 5109
- token trung bình mỗi case: 85.15
- tổng chi phí ước tính: 0.010218 USD
- chi phí trung bình mỗi case: 0.00017 USD

Trong `reports/summary.json`, phần cost reduction plan đề xuất sử dụng cached retrieval, batch async execution, offline pre-filtering, và chỉ gọi real LLM judges cho các case rủi ro hoặc có tranh chấp điểm. Mục tiêu là giảm ít nhất 30% chi phí eval mà vẫn giữ độ tin cậy của benchmark.

## 2. Kiến thức chuyên sâu

### Async Benchmarking

Benchmark trong dự án này là dạng I/O-bound vì mỗi case có thể cần gọi agent, tính retrieval score và chạy judge. Nếu chạy tuần tự từng case, hệ thống sẽ mất nhiều thời gian chờ từng bước hoàn thành. Async runner giải quyết vấn đề này bằng cách chạy nhiều case đồng thời trong từng batch.

Batch size là yếu tố quan trọng. Nếu batch quá nhỏ, hệ thống không tận dụng được khả năng chạy song song. Nếu batch quá lớn, hệ thống có thể gặp rate limit hoặc khó kiểm soát lỗi. Vì vậy, batch execution là lựa chọn cân bằng giữa tốc độ và độ ổn định.

### Latency Metrics

Tôi dùng `time.perf_counter` để đo latency cho từng test case vì đây là công cụ phù hợp để đo thời gian thực thi. Báo cáo tổng hợp cả average latency và p95 latency. Average latency cho biết hiệu năng trung bình, còn p95 latency phản ánh nhóm case chậm hơn, vốn ảnh hưởng nhiều đến trải nghiệm thực tế.

### Token Usage và Cost

Token usage và cost được lấy từ metadata của agent response rồi đưa vào từng benchmark result. Nhờ đó, hệ thống có thể tính tổng chi phí và chi phí trung bình mỗi case. Đây là phần quan trọng vì một hệ thống đánh giá AI không chỉ cần chính xác, mà còn phải đủ rẻ để chạy nhiều lần trong regression testing.

### MRR

MRR, hay Mean Reciprocal Rank, đo vị trí của tài liệu đúng đầu tiên trong danh sách retrieval. Nếu tài liệu đúng đứng hạng 1, reciprocal rank là 1.0. Nếu đứng hạng 2, reciprocal rank là 0.5. Trong benchmark tối ưu, MRR đạt 1.0, nghĩa là context đúng thường xuyên được xếp ở vị trí đầu tiên.

### Cohen's Kappa

Cohen's Kappa đo mức độ đồng thuận giữa các judge sau khi đã loại trừ khả năng đồng thuận ngẫu nhiên. Trong dự án này, chỉ số này được dùng để đánh giá độ tin cậy của multi-judge scoring. Benchmark summary ghi nhận Cohen's Kappa là 1.0, cho thấy hai deterministic judges đồng thuận hoàn toàn trong lần chạy candidate.

### Position Bias

Position bias xảy ra khi LLM judge thiên vị câu trả lời vì vị trí xuất hiện trong prompt thay vì chất lượng thật sự. Benchmark có ghi nhận các case liên quan đến position bias trong phần judge reliability. Điều này quan trọng vì tối ưu hiệu năng không được che khuất bias trong đánh giá; benchmark chạy nhanh chỉ có giá trị nếu điểm số vẫn đáng tin cậy.

## 3. Giải quyết vấn đề

Vấn đề kỹ thuật chính là cân bằng giữa tốc độ, độ chi tiết của kết quả, và độ ổn định khi chạy benchmark. Nếu chạy tuần tự, hệ thống sẽ khó đạt tiêu chí hiệu năng. Nếu chạy tất cả case cùng lúc, trong môi trường API thật có thể gặp rate limit. Batched async runner giải quyết vấn đề này bằng cách giữ mức song song có kiểm soát.

Một vấn đề khác là benchmark result phải đủ chi tiết để phục vụ phân tích sau này. Nếu kết quả chỉ có pass/fail thì rất khó debug. Vì vậy, tôi đưa vào latency, retrieved ids, token usage, cost, judge scores và failure category để nhóm có thể xác định lỗi đến từ retrieval, generation, judge disagreement hay vấn đề cost/performance.

Kết quả cuối cùng đáp ứng tiêu chí Performance Async: 60 cases hoàn thành nhanh hơn rất nhiều so với yêu cầu dưới 2 phút. Báo cáo cũng có đầy đủ số liệu token và cost, phù hợp với tiêu chí chấm điểm của phần hiệu năng.

## 4. Bài học rút ra

Tôi học được rằng một hệ thống đánh giá AI thực tế không thể chỉ đo accuracy. Nó cần theo dõi runtime, p95 latency, throughput, token usage và cost. Async execution giúp benchmark đủ nhanh để dùng trong regression testing nhiều lần, còn báo cáo có cấu trúc giúp kết quả dễ kiểm tra và dễ giải thích.

Nếu tiếp tục cải thiện, tôi sẽ thêm cấu hình concurrency limit qua biến môi trường và đo riêng thời gian cho từng stage: retrieval, generation và judging. Điều này giúp xác định rõ bottleneck thật sự nằm ở đâu trong pipeline.
